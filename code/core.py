from pathlib import Path
import configparser
import logging as log
from db.pool import CuratrDBPool

# --------------------------------------------------------------

class CoreBase:
	""" Base class for Curatr Core system implementation """
	def __init__(self, dir_root):
		# set up paths
		self.dir_root = Path(dir_root)
		log.info("Using library core configuration in %s" % self.dir_root.absolute() )
		# standard directory paths
		self.dir_metadata = self.dir_root / "metadata"
		self.dir_fulltext = self.dir_root / "fulltext"
		self.dir_embeddings = self.dir_root / "embeddings"
		self.dir_export = self.dir_root / "export"
		# metadata file paths
		self.meta_books_path = self.dir_metadata / "book-metadata.json"
		self.meta_classifications_path = self.dir_metadata / "book-classifications.csv"
		self.meta_links_path = self.dir_metadata / "book-links.csv"
		self.meta_volumes_path = self.dir_metadata / "book-volumes.csv"
		# read configuration file
		self.config_path = self.dir_root / "config.ini"
		if not self.config_path.exists():
			log.warning("Missing Curatr configuration file %s" % self.config_path)
		else:
			log.info("Loading configuration from %s ..." % self.config_path)
			self.config = configparser.ConfigParser()
			self.config.read(self.config_path)
		self._pool = None
		self.cache = {}
	
# --------------------------------------------------------------

class CoreCuratr(CoreBase):
	def __init__(self, dir_root):
		super().__init__(dir_root)

	def init_db(self, autocommit=False):
		""" Creates a connection to the Curatr MySQL database """
		try:
			db_hostname = self.config["db"].get("hostname", "localhost")
			db_port = self.config["db"].getint("port", 3306)
			db_name = self.config["db"].get("dbname", "curatr")
			db_username = self.config["db"].get("username", "curatr")
			db_password = self.config["db"].get("pass", "")
			pool_size = self.config["db"].getint("pool_size", 5)
			self._pool = CuratrDBPool(pool_size, db_hostname, db_port, db_username, db_password, db_name, autocommit)
			return True
		except Exception as e:
			log.error("Failed to initalize database: %s" % str(e))
			return False

	def get_db(self):
		return self._pool.get_connection()

	def shutdown(self):
		log.info("Shutting down core ...")
		try:
			if not self._pool is None:
				self._pool.close()
				self._pool = None
		except Exception as e:
			log.error("Failed to close database pool: %s" % str(e))
		return None

	def volume_full_paths(self):
		""" Return back a dictionary of volume ID to full path to the corresponding plain-text file """
		db = self.get_db()
		volumes = db.get_volumes()
		volume_path_map = {}
		for volume in volumes:
			volume_path_map[volume["id"]] = self.dir_fulltext / volume["path"]
		db.close()
		return volume_path_map
