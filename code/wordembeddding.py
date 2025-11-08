"""
Classes and functions for dealing with word embeddings.
"""
import logging as log
from collections import OrderedDict
import gensim

# --------------------------------------------------------------

# default maximum number of neighbour lists to cache
default_max_cache_size = 5000
# default number of neighbours per word
default_max_k = 20

# --------------------------------------------------------------

def filter_list(existing, ignores, max_len):
	"""Convenience function to filter a list and limit its size"""
	ignores_set = set(ignores)
	filtered_values = [item for item in existing if item not in ignores_set]
	return filtered_values[0:max_len]

def normalize_word(word):
	"""Normalise a word for embedding lookup"""
	return word.lower().replace("-", "_").replace('"', "").strip()

# --------------------------------------------------------------

class EmbeddingWrapper:
	"""Wrapper for Gensim word embeddings which implements caching"""
	def __init__(self, filepath, preload=False):
		self.filepath = filepath
		self._model = None
		self._cache = OrderedDict()
		self.capacity = default_max_cache_size
		self.loaded = False
		# should we load the model now?
		if preload:
			log.info(f"Preloading embedding model from {self.filepath.resolve()} ...")
			self.load()

	def load(self):
		"""Load the underlying Gensim word embedding model"""
		# check if already loaded
		if self.loaded and self._model is not None:
			log.debug(f"Embedding model already loaded from {self.filepath.resolve()}")
			return

		self._model = None
		self.loaded = False
		try:
			# loading Gensim .kv format?
			if self.filepath.suffix == ".kv":
				log.info(f"Loading Word2vec model in .kv format from {self.filepath.resolve()} ...")
				self._model = gensim.models.KeyedVectors.load(str(self.filepath), mmap="r")
			# otherwise assume this is a word2vec binary format
			else:
				log.info(f"Loading Word2vec model in binary format from {self.filepath.resolve()} ...")
				self._model = gensim.models.KeyedVectors.load_word2vec_format(str(self.filepath), binary=True)
			self.loaded = True
		except Exception as e:
			log.error(f"Failed to load embedding model from {self.filepath.resolve()}")
			log.error(str(e))

	def in_vocab(self, word):
		"""Check if the specified word is in the embedding vocabulary"""
		# no model loaded?
		if self._model is None:
			log.info("Loading embedding model for in_vocab() check ...")
			self.load()
			# still no model?
			if self._model is None:
				log.warning(f"Warning: No embedding model loaded after in_vocab() attempt - {self.filepath.resolve()}")
				return False
		# ensure the input word is lowercase and tidy
		word = normalize_word(word)
		return word in self._model.key_to_index

	def get(self, word, k=default_max_k, ignores=[]):
		"""Return back neighbours for the specified list"""
		# no model loaded?
		if self._model is None:
			log.info("Loading embedding model for get() operation ...")
			self.load()
			# still no model?
			if self._model is None:
				log.warning(f"Warning: No embedding model loaded after get() attempt - {self.filepath.resolve()}")
				return []
		# ensure the input word is lowercase and tidy
		word = normalize_word(word)
		# cached already?
		if word in self._cache:
			neighbors = self._cache[word]
			# keep it in the cache
			self._cache.move_to_end(word)
			# sufficient neighbours? if not, we'll replace the list
			if len(neighbors) >= k:
				# return back the number of neighbours that was requested, after filtering
				return filter_list(neighbors, ignores, k)
		# not cached?
		try:
			# get the word's neighbours in the embedding
			# we go beyond the maximum required
			actual_k = max(k, default_max_k) * 2
			embed_results = self._model.most_similar(positive=[word], topn=actual_k)
			# add it to the cache
			self._cache[word] = [x[0] for x in embed_results]
			# is the cache too large? remove oldest items
			if len(self._cache) > self.capacity:
				self._cache.popitem(last=False)
			# return back the number of neighbours that was requested, after filtering
			return filter_list(self._cache[word], ignores, k)
		except KeyError as e:
			log.warning(f"Warning: Failed to find most similar words for '{word}'")
			log.warning(e)
			return []
