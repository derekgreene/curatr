#!/usr/bin/env python
"""
This script implements the functionality required to generate word embeddings from the 
full-text British Library

Same usage:
	python code/create-embedding.py core
"""
import logging as log
import sys
from optparse import OptionParser
from pathlib import Path
from gensim.models import Word2Vec
from preprocessing.util import CorePrep
from preprocessing.text import BookTokenGenerator

# --------------------------------------------------------------

def main():
	log.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=log.INFO)
	parser = OptionParser(usage="usage: %prog [options] dir_core")
	parser.add_option("--seed", action="store", type="int", dest="seed", help="random seed", default=1000)
	parser.add_option("--df", action="store", type="int", dest="min_df", help="minimum number of documents for a term to appear", default=10)
	parser.add_option("-d","--dimensions", action="store", type="int", dest="dimensions", help="the dimensionality of the word vectors", default=100)
	parser.add_option("--window", action="store", type="int", dest="window_size", 
		help="the maximum distance for Word2Vec to use between the current and predicted word within a sentence", default=5)
	parser.add_option("-m", action="store", type="string", dest="embed_type", help="type of word embedding to build (sg or cbow)", default="cbow")
	(options, args) = parser.parse_args()
	if len(args) < 1:
		parser.error("Must specify core directory" )

	# set up the basic Curatr core
	dir_root = Path(args[0])
	if not dir_root.exists():
		log.error("Invalid core directory: %s" % dir_root.absolute())
		sys.exit(1)
	core = CorePrep(dir_root)
	if not core.dir_fulltext.exists():
		log.error("Cannot create embedding. Directory of full-text files does not exist: %s" % core.dir_fulltext.absolute())
		sys.exit(1)
	df_books = core.get_book_metadata()
	book_ids = list(df_books.index)

	# get default stopwords list
	stopwords = core.get_stopwords()
	log.info("Using default list of %d stopwords" % len(stopwords))

	# build the Word2Vec embedding from the documents that we have found
	token_generator = BookTokenGenerator(core.dir_fulltext, book_ids, stopwords=stopwords)
	log.info("Building word2vec-%s embedding from %d books (window=%d dimensions=%d)..." 
		% (options.embed_type, len(book_ids), options.window_size, options.dimensions))
	if options.embed_type == "cbow":
		sg = 0
	elif options.embed_type == "sg":
		sg = 1
	else:
		log.error("Unknown embedding variant type '%s'" % options.embed_type)
		sys.exit(1)
	embed = Word2Vec(token_generator, vector_size=options.dimensions, min_count=options.min_df, 
		window=options.window_size, workers=4, sg=sg, seed=options.seed, sorted_vocab=1)
	log.info( "Built word embedding %s" % embed)

	# save the Word2Vec model
	fname = "bl-w2v-%s-d%d.bin" % (options.embed_type, options.dimensions)
	out_path = core.dir_embeddings / fname
	log.info("Writing word embedding to %s ..." % out_path)
	# always save in binary format
	embed.wv.save_word2vec_format(out_path, binary=True) 

# --------------------------------------------------------------

if __name__ == "__main__":
	main()
