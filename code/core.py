from pathlib import Path
import configparser
import logging as log
from collections import Counter
import gensim
from search import SolrWrapper
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
		self._embedding_paths = {}
		self._embeddings = {}
		self.default_embedding_id = self.config["app"].get("default_embedding", None)
		for embed_id in self.config["embeddings"]:
			if self.default_embedding_id is None:
				self.default_embedding_id = embed_id
			self._embedding_paths[embed_id] = self.dir_embeddings / self.config["embeddings"][embed_id]
			if not self._embedding_paths[embed_id].exists():
				log.warning("Embedding '%s' does not exist: %s" % (embed_id, self._embedding_paths[embed_id]))
			else:
				log.debug("Embedding '%s' found %s" % (embed_id, self._embedding_paths[embed_id]))
		log.info("Embeddings: %s" % str(self.get_embedding_ids()))
		log.info("Default embedding: %s" % self.default_embedding_id)

	def shutdown(self):
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
		self.solr_core_segments = self.config["solr"].get("segments", "bl_segments")
		self.solr_core_volumes = self.config["solr"].get("volumes", "bl_volumes")
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
		""" Return back the specified word embedding model used by Curatr. 
		If no embeedding ID is specified, we return the default embedding. """
		if embed_id is None:
			embed_id = self.default_embedding_id
		if embed_id is None or not embed_id in self._embedding_paths:
			log.error("No word embedding model ID specified")
			return None
		# has the embedding already been loaded?
		if not embed_id in self._embeddings:
	 		# load the embedding model
			filepath = self._embedding_paths[embed_id]
			try:
				# is this a FastText embedding?
				if "-ft" in filepath.stem:
					log.info("Loading FastText model from %s ..." % filepath)
					self._embeddings[embed_id] = gensim.models.FastText.load(filepath)
				# otherwise assume this is a word2vec embedding
				else:
					log.info("Loading Word2vec model from %s ..." % filepath)
					self._embeddings[embed_id] = gensim.models.KeyedVectors.load_word2vec_format(filepath, binary=True)  			
			except Exception as e:
				log.error("Failed to load embedding model from %s" % filepath)
				log.error(str(e))
				return None
		return self._embeddings[embed_id]

	def get_embedding_ids(self):
		""" Return list of identifiers for all available word embedding models """
		return sorted(self._embedding_paths.keys())

	def has_embedding(self, embed_id):
		""" Check if the word embedding model with the specified ID exists """
		return embed_id in self._embedding_paths

	def similar_words(self, embed_id, word, topn=10):
		""" Find top-N most similar words to the specified word, using the
		word embedding model with the specified identifier """
		try:
			# ensure the input word is lowercase and tidy
			word = word.lower().replace("-","_").replace('"','')
			# get the word's neighbors in the embedding
			neighbors = self.get_embedding(embed_id).most_similar(positive=[word], topn=topn*2)
			return [ x[0] for x in neighbors ]
		except KeyError as e:
			log.warning("Warning: Failed to find most similar words for '%s'" % word )
			log.warning(e)
			return []

	def recommend_words(self, words, ignores, topn=10):
		""" Find top-N most similar words to a set of one or more input words,
		using the default word embedding model """
		# get the embedding model to use for recommendations
		embedding = self.get_embedding()
		recommendations = {}
		# get the nearest neighbors in the model for each input word
		for word in words:
			try:
				# ensure this word is lowercase and tidy
				word = word.lower().replace("-","_").replace('"','')
				neighbors = embedding.most_similar(positive=[word], topn=topn*2)
			except KeyError as e:
				log.warning("Warning: Failed to find most similar words for '%s'" % word )
				log.warning(e)
				recommendations[word] = []
				continue
			nwords = []
			for n in neighbors:
				if len(nwords) == topn:
					break
				# do not add existing words
				if not (n[0] in words or n[0] in ignores):
					nwords.append( n[0] )
			recommendations[word] = nwords
		return recommendations

	def aggregate_recommend_words(self, words, ignores, topn=10, enforce_diversity=False):
		""" Combine words recommendations for an input set of multiple query words,
		using the default word embedding model """
		recommendations = self.recommend_words(words, ignores, topn*3)
		scores = Counter()
		for word in recommendations:
			for i, neighbor in enumerate(recommendations[word]):
				rank = i+1
				score = 0.5 + ( 1.0/rank )
				scores[neighbor] += score
		# rank the top words
		top_words = scores.most_common(topn)
		# merge the words
		word_stems = set()
		stemmer = gensim.parsing.porter.PorterStemmer()
		if enforce_diversity:
			for word in words:
				word_stems.add(stemmer.stem(word))
		merged, pos = [], 0
		while len(merged) < topn and pos < len(top_words):
			word = top_words[pos][0]
			pos += 1
			# need to enforce diversity in the recommendations?
			if enforce_diversity:
				word_stem = stemmer.stem(word)
				if word_stem in word_stems:
					continue
				word_stems.add(word_stem)
			merged.append(word)
		return merged
