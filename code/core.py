from pathlib import Path
import configparser
import logging as log
from collections import Counter
from search import SolrWrapper
from wordembeddding import EmbeddingWrapper
from preprocessing.text import stem_word, stem_words
from SolrClient import SolrClient
from db.pool import CuratrDBPool

# --------------------------------------------------------------

class CoreBase:
	""" Base class for Curatr Core system implementation """
	def __init__(self, dir_root):
		# set up paths
		self.dir_root = Path(dir_root)
		log.info("Using library core configuration in %s" % self.dir_root.absolute())
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
		self._solr_volumes, self._solr_segments = None, None
		self.cache = {}
	
# --------------------------------------------------------------

class CoreCuratr(CoreBase):
	def __init__(self, dir_root):
		super().__init__(dir_root)
		# set up the embeddings
		self.default_embedding_id = self.config["app"].get("default_embedding", None)
		self._embeddings = {}
		for embed_id in self.config["embeddings"]:
			# make sure it exists
			embedding_path = self.dir_embeddings / self.config["embeddings"][embed_id]
			if not embedding_path.exists():
				log.warning("Embedding '%s' does not exist: %s" % (embed_id, embedding_path))
				continue
			log.debug("Embedding '%s' found %s" % (embed_id, embedding_path))
			# use this as our default?
			if self.default_embedding_id is None:
				self.default_embedding_id = embed_id
			# create the wrapper
			self._embeddings[embed_id] = EmbeddingWrapper(embedding_path, False)
		log.info("Embeddings: %s" % str(self.get_embedding_ids()))
		log.info("Default embedding: %s" % self.default_embedding_id)

	def shutdown(self):
		""" Close down the Curatr core - i.e. the database pool """
		log.info("Shutting down core ...")
		try:
			if not self._pool is None:
				self._pool.close()
				self._pool = None
		except Exception as e:
			log.error("Failed to close database pool: %s" % str(e))
		return None

	def init_db(self, autocommit=False, default_pool_size=5):
		""" Creates a connection to the Curatr MySQL database """
		try:
			db_hostname = self.config["db"].get("hostname", "localhost")
			db_port = self.config["db"].getint("port", 3306)
			db_name = self.config["db"].get("dbname", "curatr")
			db_username = self.config["db"].get("username", "curatr")
			db_password = self.config["db"].get("pass", "")
			pool_size = self.config["db"].getint("pool_size", default_pool_size)
			self._pool = CuratrDBPool(pool_size, db_hostname, db_port, db_username, db_password, db_name, autocommit)
			return True
		except Exception as e:
			log.error("Failed to initalize database: %s" % str(e))
			return False

	def get_db(self):
		return self._pool.get_connection()

	def init_solr(self):
		""" Initialize the Solr connection """
		# server settings
		solr_hostname = self.config["solr"].get("hostname", "localhost")
		solr_port = self.config["solr"].getint("port", 8983)
		solr_url = 'http://%s:%d/solr' % (solr_hostname, solr_port)
		# core names
		self.solr_core_segments = self.config["solr"].get("core_segments", "blsegments")
		self.solr_core_volumes = self.config["solr"].get("core_volumes", "blvolumes")
		# create connections to the Solr server
		try:
			log.info("Connecting to %s for volumes ..." % solr_url)			
			client_volumes = SolrClient(solr_url)
			self._solr_volumes= SolrWrapper(client_volumes, self.solr_core_volumes)
			log.info("Connecting to %s for segments ..." % solr_url)			
			client_segments = SolrClient(solr_url)
			self._solr_segments = SolrWrapper(client_segments, self.solr_core_segments)
		except Exception as e:
			log.error("Failed to initalize Solr: %s" % str(e))
			return False
		return True

	def get_solr(self, kind = "volumes"):
		""" Access the specified Solr core index """
		if kind.lower().startswith("segment"):
			return self._solr_segments
		return self._solr_volumes

	def cache_values( self ):
		""" Caches relevant values from the Curatr MySQL database """
		log.info("Caching database values ...")
		db = self.get_db()

		# basic statistics
		self.cache["book_count"] = db.book_count()
		self.cache["volume_count"] = db.volume_count()
		# TODO: calculate dynamically
		self.cache["segment_count"] = 12322488
		self.cache["author_count"] = db.author_count()
		year_range = db.get_book_year_range()
		self.cache["year_min"] = year_range[0]
		self.cache["year_max"] = year_range[1]
		# book published place info
		self.cache["place_names"] = db.get_published_location_names("place")
		self.cache["place_counts"] = db.get_published_location_counts("place")
		self.cache["top_place_counts"] = db.get_published_location_counts(top=150, kind="place")
		self.cache["top_place_names"] = sorted([name for name in self.cache["top_place_counts"]])
		# book published country info
		self.cache["country_names"] = db.get_published_location_names("country")
		self.cache["country_counts"] = db.get_published_location_counts("country")
		self.cache["top_country_counts"] = db.get_published_location_counts(top=150, kind="country")
		self.cache["top_country_names"] = sorted([name for name in self.cache["top_country_counts"]])
		# author information
		self.cache["author_catalogue"] = db.get_cached_author_details()
		# classification information
		self.cache["category_names"] = db.get_classification_names(level=0)
		self.cache["class_names"] = db.get_classification_names(level=1)
		self.cache["subclass_names"] = db.get_classification_names(level=2)
		self.cache["category_counts"] = db.get_classification_counts(level=0, top=-1)
		self.cache["class_counts"] = db.get_classification_counts(level=1, top=-1)
		self.cache["top_subclass_counts"] = db.get_classification_counts(level=2, top=30)		
		# TODO
		try:
			pass
		except Exception as e:
			log.error("Failed to cache values from database: %s" % str(e))
			db.close()
			return False
		db.close()
		return True

	def volume_full_paths(self):
		""" Return back a dictionary of volume ID to full path to the corresponding plain-text file """
		db = self.get_db()
		volumes = db.get_volumes()
		volume_path_map = {}
		for volume in volumes:
			volume_path_map[volume["id"]] = self.dir_fulltext / volume["path"]
		db.close()
		return volume_path_map

	def get_embedding(self, embed_id=None):
		""" Return back the specified word embedding wrapper used by Curatr. 
		If no embedding ID is specified, we return the default embedding. """
		# use the default embedding?
		if embed_id is None:
			embed_id = self.default_embedding_id
		if embed_id is None or not embed_id in self._embeddings:
			log.error("No word embedding model ID specified")
			return None
		return self._embeddings[embed_id]

	def get_embedding_ids(self):
		""" Return list of identifiers for all available word embedding models """
		return sorted(self._embeddings.keys())

	def has_embedding(self, embed_id):
		""" Check if the word embedding model with the specified ID exists """
		return embed_id in self._embeddings

	def word_similarity(self, word, k=10, embed_id=None, ignores=[]):
		""" Find top-K most similar words to the specified word, using the
		word embedding model with the specified ID. If no ID is specified, 
		we use the default model """
		# do we have the requested model?
		embedding = self.get_embedding(embed_id)
		if embedding is None:
			log.warning("Warning: Failed to find most similar words for '%s'" % word )
			return []
		return embedding.get(word, k, ignores)
	
	def multi_word_similarity(self, words, k=10, embed_id=None, ignores=[]):
		""" Find top-K most similar words for one or more input words, using the
		word embedding model with the specified ID. If no ID is specified, 
		we use the default model """
		# note we ignore words in the current list
		ignores = set(ignores).union(words)
		# get the nearest neighbors in the model for each input word
		word_neighbors = {}
		for word in words:
			word_neighbors[word] = self.word_similarity(word, k, embed_id, ignores)
		return word_neighbors

	def aggregate_word_similarity(self,  words, k=10, embed_id=None, ignores=[], enforce_diversity=False):
		""" Combine words recommendations for an input set of multiple query words,
		using the specified word embedding model """
		# get the similar words
		recommendations = self.multi_word_similarity(words, k*3, embed_id, ignores)
		# turn the variouis rankings into scores based on reciprocal rank
		scores = Counter()
		for word in recommendations:
			for i, neighbor in enumerate(recommendations[word]):
				rank = i+1
				score = 0.5 + (1.0/rank)
				scores[neighbor] += score
		# rank the top ranked words
		ranked_words = scores.most_common()
		# merge the words
		word_stems = set()
		if enforce_diversity:
			word_stems = set(stem_words(words))
		merged, pos = [], 0
		while len(merged) < k and pos < len(ranked_words):
			word = ranked_words[pos][0]
			pos += 1
			# need to enforce diversity in the final aggregated list?
			if enforce_diversity:
				word_stem = stem_word(word)
				if word_stem in word_stems:
					continue
				word_stems.add(word_stem)
			merged.append(word)
		return merged

	def get_subcorpus_zipfile(self, subcorpus_id):
		""" Create the path for a ZIP file for exporting a sub-corpus """
		db = self.get_db()
		filepath = None
		try:
			subcorpus = db.get_subcorpus(subcorpus_id)
			filepath = self.dir_export / subcorpus["filename"]
		except Exception as e:
			log.error( "Failed to get subcorpus ZIP file: %s" % str(e) )
		db.close()
		return filepath