""" 
Collection of utility classes and functions for working with MySQL databases
"""
import time
import logging as log
import pymysql

# --------------------------------------------------------------

class GenericDB:
	""" Simple wrapper class for working with a MySQL database """
	def __init__(self, hostname, port, username, password, dbname, autocommit=False, sql_statements={}):
		self.sql_statements = sql_statements
		# create the connection
		log.info("Connecting to database %s at %s@%s:%s ..." % ( dbname, username, port, hostname))
		self.conn = pymysql.connect(host=hostname, user=username, password=password, 
			database=dbname, port=port, charset='utf8', connect_timeout=600000)
		self.cursor = self.conn.cursor()
		self.conn.autocommit(autocommit)
		log.debug("Connected to database: autocommit=%s" % (self.conn.get_autocommit()))

	def commit( self ):
		self.conn.commit()

	def close( self ):
		if not self.conn is None:
			log.info("Closing database connection")
			self.conn.commit()
			self.conn.close()
			self.conn = None

	def ping(self, max_retries = 10):
		""" Function to check if the database connection is alive """
		if self.conn.open:
			return True
		retry_num = 1
		while self.conn.open is False:
			log.info("Database connection has closed. Re-establishing connection.")
			try:
				self.conn.ping(reconnect=True)
				return True
			except Exception as e:
				log.warning("Database ping failed on attempt %d" % retry_num)
				log.warning(str(e))
				time.sleep(5)
			retry_num += 1
			if retry_num == max_retries:
				break
		return False

	def ensure_table_exists(self, table_name):
		""" Create a database table, if it does not exist already"""
		tables = self._get_existing_tables()
		if table_name in tables:
			log.info( "Table %s already exists" % table_name)
		else:
			if not table_name in self.sql_statements:
				log.error("Cannot create unknown table %s" % table_name)
				return
			log.info("Creating table %s ..." % table_name)
			self.cursor.execute(self.sql_statements["Table%s" % table_name])
			log.info("Columns: %s" % self._get_table_columns( table_name ) )

	def check_table_counts( self ):
		""" Check the number of rows in each table in the database """
		tables = sorted( self._get_existing_tables() )
		for table_name in tables:
			self.cursor.execute("SELECT count(*) FROM %s" % table_name)
			result = self.cursor.fetchone()
			log.info("%s: %d rows" % ( table_name, result[0] ) )

	def _sql_to_dict(self, sql, params=None):
		""" Return a single result for a SQL query as a dictionary """
		self.cursor.execute(sql, params)
		columns = [column[0] for column in self.cursor.description]
		row = self.cursor.fetchone()
		if row is None:
			return None
		return dict(zip(columns, row))

	def _bulk_sql_to_dict(self, sql, params=None):
		""" Return multiple results of a single SQL query as dictionaries """
		self.cursor.execute( sql, params )
		columns = [column[0] for column in self.cursor.description]
		results = []
		for row in self.cursor.fetchall():
			results.append(dict(zip(columns, row)))
		return results

	def _get_existing_tables(self):
		""" Get table names for the current database """
		sql = "SHOW TABLES"
		self.cursor.execute( sql )
		results = self.cursor.fetchall()
		return [item[0] for item in results]

	def _get_table_columns(self, table_name):
		""" Get columns names for the specified table"""
		columns = []
		self.cursor.execute( "SHOW COLUMNS FROM %s" % table_name )
		for res in self.cursor.fetchall():
			columns.append(res[0])			
		return columns

	def _get_next_id(self, table_name):
		""" Generate the next unique identifier for the specified table """
		try:
			self.cursor.execute( "SELECT AUTO_INCREMENT FROM information_schema.tables WHERE table_name=%s", table_name )
			result = self.cursor.fetchone()
			return result[0]
		except Exception as e:
			log.error( "SQL error in _get_next_id(): %s" % str(e) )
			return 1

