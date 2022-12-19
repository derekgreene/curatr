from pathlib import Path
import configparser
import logging as log
from db.curatrdb import CuratrDB

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
	
# --------------------------------------------------------------

class CoreCuratr(CoreBase):
	def __init__(self, dir_root):
		super().__init__(dir_root)

	def init_db(self, autocommit=False):
		""" Creates a connection to the Curatr MySQL database """
		try:
			db_hostname = self.config["db"].get( "hostname", "localhost" )
			db_port = self.config["db"].getint( "port", 3306 )
			db_name = self.config["db"].get( "dbname", "curatr" )
			db_username = self.config["db"].get( "username", "curatr" )
			db_password = self.config["db"].get( "pass", "" )
			# pool_size = self.config["db"].getint( "pool_size", 5 )
			self.db = CuratrDB(db_hostname, db_port, db_username, db_password, db_name, autocommit)
			return True
		except Exception as e:
			log.error( "Failed to initalize database: %s" % str(e))
			return False

	def get_db(self):
		return self.db
