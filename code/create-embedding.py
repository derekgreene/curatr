#!/usr/bin/env python
"""
This script implements the functionality required to generate word embeddings from the 
full-text British Library. We use Gensim to create the embeddings.

Default usage:
	python code/create-embedding.py core

Note that we can also create additional embeddings from subsets of the collection
	python code/create-embedding.py core -c fiction
	python code/create-embedding.py core -c nonfiction
	python code/create-embedding.py core -c fiction --ymin 1864 --ymax 1880
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
	parser.add_option("-c","--collection", action="store", type="string", dest="collection", help="set of books to use (all, fiction, nonfiction)", default="all")
	parser.add_option("--ymin", action="store", type="int", dest="year_min", help="start year", default=-1)
	parser.add_option("--ymax", action="store", type="int", dest="year_max", help="end year", default=-1)
	(options, args) = parser.parse_args()
	if len(args) < 1:
		parser.error("Must specify core directory")

	# set up the Curatr preprocessing core
	dir_core = Path(args[0])
	if not dir_core.exists():
		log.error("Invalid core directory: %s" % dir_core.absolute())
		sys.exit(1)
	core_prep = CorePrep(dir_core)
	if not core_prep.dir_fulltext.exists():
		log.error("Cannot create embedding. Directory of full-text files does not exist: %s" % core_prep.dir_fulltext.absolute())
		sys.exit(1)
	df_books = core_prep.get_book_metadata()
	# which set of book IDs are we using?
	if options.collection == "all":
		book_ids = list(df_books.index)
		log.info("Building embedding from all %d books ..." % len(book_ids))
	else:
		df_classifications = core_prep.get_book_classifications()
		if options.collection == "fiction":
			book_ids = list(df_classifications[df_classifications["primary"]=="Fiction"].index)
			log.info("Building embedding from %d fiction books ..." % len(book_ids))
		elif options.collection == "nonfiction":
			book_ids = list(df_classifications[df_classifications["primary"]=="Non-Fiction"].index)
			log.info("Building embedding from %d non-fiction books ..." % len(book_ids))
		else:
			log.error("Unknown collection subset: %s" % options.collection)
			sys.exit(1)

	# do we need to filter on year?
	# year_prefix will be added to the filename if filtering by year range
	year_prefix = ""
	if options.year_min > 0 and options.year_max > 0:
		# ensure year_min is within the available data range
		year_min = max(options.year_min, df_books["year"].min())
		year_max = options.year_max
		# if year_max is before year_min, extend to the latest available year
		if year_max < year_min:
			year_max = df_books["year"].max()
		# filter books to only include those within the specified date range
		filtered_book_ids = []
		for book_id, year in df_books["year"].items():
			if not book_id in book_ids:
				continue
			if year >= year_min and year <= year_max:
				filtered_book_ids.append(book_id)
		book_ids = filtered_book_ids
		log.info("Filtering based on date range [%d,%d] down to %d books" % (year_min, year_max, len(book_ids)))
		# add year range to filename for identification
		year_prefix = "_%d_%d" % (year_min, year_max)

	# get default stopwords list
	stopwords = core_prep.get_stopwords()
	log.info("Using default list of %d stopwords" % len(stopwords))

	# build the Word2Vec embedding from the documents that we have found
	token_generator = BookTokenGenerator(core_prep.dir_fulltext, book_ids, stopwords=stopwords)
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

	# save the Word2Vec model in binary format
	if options.collection == "all":
		fname = "bl-w2v-%s%s-d%d.bin" % (options.embed_type, year_prefix, options.dimensions)
	else:
		fname = "bl%s-w2v-%s%s-d%d.bin" % (options.collection, options.embed_type, year_prefix, options.dimensions)
	out_path = core_prep.dir_embeddings / fname
	log.info("Writing word embedding to %s ..." % out_path)
	embed.wv.save_word2vec_format(out_path, binary=True)

	# save the Word2Vec model in native Gensim .kv format
	if options.collection == "all":
		fname = "bl-w2v-%s%s-d%d.kv" % (options.embed_type, year_prefix, options.dimensions)
	else:
		fname = "bl%s-w2v-%s%s-d%d.kv" % (options.collection, options.embed_type, year_prefix, options.dimensions)
	out_path = core_prep.dir_embeddings / fname
	log.info("Writing word embedding (Gensim format) to %s ..." % out_path)
	embed.wv.save(str(out_path))
	
	log.info("Actions complete")

# --------------------------------------------------------------

if __name__ == "__main__":
	main()
