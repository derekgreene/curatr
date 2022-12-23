"""
Implements database connection pooling, which allows us to keep database connections open so they
can be reused by Curatr.
"""
import logging as log
import queue, time, threading
from db.curatrdb import CuratrDB

# --------------------------------------------------------------

class PooledCuratrDB(CuratrDB):
	""" Represents a single pooled database. """
	_pool = None

	def __init__(self, *args, **kwargs):
		CuratrDB.__init__(self, *args, **kwargs)
		self.args = args
		self.kwargs = kwargs

	def close(self):
		""" Overwrite the close() method of BookDB to put the connection back in the pool. """
		if self._pool:
			self._pool.return_connection(self)
		else:
			CuratrDB.close(self)

	def __exit__(self, exc, value, traceback):
		log.info("PooledCuratrDB exit: %s" % str(traceback))

# --------------------------------------------------------------

class RepeatTimer(threading.Timer):
	""" A timer thread for repeatedly recyclying database connections in the pool """
	def run(self):
		while not self.finished.wait(self.interval):
			self.function(*self.args, **self.kwargs)

class CuratrDBPool:
	""" Implementation of Curatr database pooling system """
	_MAX_POOL_SIZE = 200
	_THREAD_LOCAL = threading.local()
	_THREAD_LOCAL.retry_counter = 0 
	_REYCLE_TIME = 60 * 30

	def __init__(self, pool_size, hostname, port, username, password, dbname, autocommit=False):
		self._pool_size = max(1, min(pool_size, self._MAX_POOL_SIZE))
		self._pool = queue.Queue(self._MAX_POOL_SIZE)
		# settings
		self.hostname = hostname
		self.port = port 
		self.username = username
		self.password = password
		self.dbname = dbname
		self.autocommit = autocommit
		# create the databases connections
		log.info("Creating pool of %d database connections ..." % self._pool_size )
		for i in range(self._pool_size):
			self.open_connection()
		# set the connection recycling timer
		self.thread = RepeatTimer(self._REYCLE_TIME, self.recycle)
		# ensure the thread ends when the main thread finishes
		self.thread.daemon = True
		self.thread.start()

	def open_connection(self):
		log.debug("Creating new DB connection... ")
		db = PooledCuratrDB( self.hostname, self.port, self.username, self.password, self.dbname, self.autocommit )
		db._pool = self
		self._pool.put(db)

	def get_connection(self, timeout=3, retry_num=1):
		"""
		timeout: timeout of get a connection from pool, should be a int(0 means return or raise immediately)
		retry_num: how many times will retry to get a connection
		"""
		try:
			db = self._pool.get(timeout=timeout) if timeout > 0 else self._pool.get_nowait()
			log.info("Got database from pool, size now %d" % self.size() )
			# connection closed?
			if not db.ping():
				raise queue.Empty()
			return db
		except queue.Empty:
			if not hasattr(self._THREAD_LOCAL, 'retry_counter'):
				self._THREAD_LOCAL.retry_counter = 0
			if retry_num > 0:
				self._THREAD_LOCAL.retry_counter += 1
				log.debug("Retry get connection from pool, the %d times" % self._THREAD_LOCAL.retry_counter)
				retry_num -= 1
				return self.get_connection(timeout, retry_num)
			else:
				total_times = self._THREAD_LOCAL.retry_counter + 1
				self._THREAD_LOCAL.retry_counter = 0
				raise GetConnectionFromPoolError("Cannot get database from pool({}) within {}*{} second(s)".format(self.name, timeout, total_times))

	def return_connection(self, db):
		if not db._pool:
			db._pool = self
		try:
			db.cursor().close()
		except:
			pass
		try:
			self._pool.put_nowait(db)
			log.info( "Returned database back to pool, size now %d" % self.size() )
		except queue.Full:
			log.warning( "Warning: Put database to pool error, pool is full, size: %d" % self.size() )

	def close(self, shutdown_timer=True):
		""" Close all database connections and cancel the pool timer thread """
		log.info("Closing database pool")
		# kill the timer
		try:
			self.thread.cancel()
		except Exception as e:
			log.warning("Failed to cancel database pool timer: %s" % str(e) )
		# close the connections
		while not self._pool.empty():
			try:
				db = self._pool.get()
				db.conn.commit()
				db.conn.close()
			except Exception as e:
				log.warning("Failed to close database connection: %s" % str(e) )
		log.info("Finished closing database connections")

	def size(self):
		return self._pool.qsize()

	def recycle(self):
		log.info("Recycling DB connections")
		self.close()
		log.info("Re-creating pool of %d database connections ..." % self._pool_size )
		for i in range(self._pool_size):
			self.open_connection()
		log.info("Pool size is now %d" % self.size() )			

# --------------------------------------------------------------

class GetConnectionFromPoolError(Exception):
	"""Exception raised when we cannot get a connection from pool within timeout seconds."""
