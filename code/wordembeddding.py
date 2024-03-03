"""
Classes and functions for deling with word embeddings.
"""
import logging as log
from collections import OrderedDict
import gensim

# --------------------------------------------------------------

# default maximum number of neighbor lists to cache
default_max_cache_size = 5000
# default number of neighbors per word
default_max_k = 20

# --------------------------------------------------------------

def filter_list(existing, ignores, max_len):
	""" Convenience function to filter a list and limit its size"""
	ignores_set = set(ignores) 
	filtered_values = [item for item in existing if item not in ignores_set]
	return filtered_values[0:max_len]

class EmbeddingWrapper:
	""" Wrapper for Gensim word embeddings which implements caching """
	def __init__(self, filepath, preload=False):
		self.filepath = filepath
		self._model = None
		self._cache = OrderedDict()
		# TODO: make this configurable in the settings
		self.capacity = default_max_cache_size
		# should we load the model now?
		if preload:
			self.load()

	def load(self):
		""" Load the underlying Gensim word embedding model"""
		self._model = None
		try:
			# is this a FastText embedding?
			if "-ft" in self.filepath.stem:
				log.info("Loading FastText model from %s ..." % self.filepath.resolve())
				self._model = gensim.models.FastText.load(self.filepath)
			# otherwise assume this is a word2vec embedding
			else:
				log.info("Loading Word2vec model from %s ..." % self.filepath.resolve())
				self._model= gensim.models.KeyedVectors.load_word2vec_format(self.filepath, binary=True)  			
		except Exception as e:
			log.error("Failed to load embedding model from %s" % self.filepath.resolve())
			log.error(str(e))

	def get(self, word, k=default_max_k, ignores=[]):
		""" Return back neighbors for the specified list"""
		# no model loaded?
		if self._model is None:
			self.load()
			# still no model?
			if self._model is None:
				return []
		# ensure the input word is lowercase and tidy
		word = word.lower().replace("-","_").replace('"','')
		# cached already?
		if word in self._cache:
			neighbors = self._cache[word]
			# keep it in the cache
			self._cache.move_to_end(word)
			# sufficient neighbors? if not, we'll replace the list
			if len(neighbors) >= k:
				# return back the number of neighbors that was requested, after filtering
				return filter_list(neighbors, ignores, k)
		# not cached?
		try:
			# get the word's neighbors in the embedding
			# we go beyond the maximum required
			actual_k = max(k, default_max_k) * 2
			embed_results = self._model.most_similar(positive=[word], topn=actual_k)
			# add it to the cache
			self._cache[word] = [x[0] for x in embed_results]
			# is the cache too large? remove oldest items
			if len(self._cache) > self.capacity:
				self._cache.popitem(last=False)
			# return back the number of neighbors that was requested, after filtering
			return filter_list(self._cache[word], ignores, k)		
		except KeyError as e:
			log.warning("Warning: Failed to find most similar words for '%s'" % word)
			log.warning(e)
			return []
		