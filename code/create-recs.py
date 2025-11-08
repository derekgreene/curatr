#!/usr/bin/env python
"""
This script implements the functionality required to do initial setup of the MySQL database
required by Curatr.

Same usage:
	python code/create-recs.py core
"""
import logging as log
import sys
from optparse import OptionParser
from pathlib import Path
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from core import CoreCuratr
from preprocessing.text import load_stopwords, build_bow, VolumeGenerator

# --------------------------------------------------------------

def add_recommendations(core, top=50):
	""" Add volume recommendations, based on pairwise cosine similarities
	calculated on a sparse bag-of-words model. """

	# initialize word embeddings
	log.info("Initializing embeddings ...")
	if not core.init_embeddings():
		sys.exit(1)
	# set up the DB connection
	log.info("Connecting to database ...")
	if not core.init_db():
		sys.exit(1)

	# get default stopwords list
	stopwords = load_stopwords()
	log.info("Using default list of %d stopwords" % len(stopwords))

	# build the bag-of-words model
	docgen = VolumeGenerator(core)
	log.info("Building bag-of-words model ...")
	(X, terms) = build_bow(docgen, stopwords)
	log.info("Built document-term matrix: %d documents, %d terms" % (X.shape[0], X.shape[1]))

	# calculate pairwise similarities
	log.info("Computing pairwise similarities ...")
	S = cosine_similarity(X)
	log.info("Computed %d X %d similarity matrix" % (S.shape[0], S.shape[1]))

	# ensure required DB table exists
	db = core.get_db()
	db.ensure_table_exists("Recommendations")
	# get recommendations for each volume
	num_entries_added = 0
	log.info("Adding top %d recommendations for %d volumes ..." % (top, len(docgen.volume_ids)))
	for query_row, volume_id in enumerate(docgen.volume_ids):
		log.debug("%d/%d: Performing query for %s ..." % ((query_row+1), len(docgen.volume_ids), volume_id))
		# get ranking for this volume
		scores =  S[query_row,:]
		ordering = np.argsort(scores)[::-1]
		# add the top ranked options
		pos, rank = 0, 1
		while True:
			if rank > top:
				break
			result_row = ordering[pos]
			result_volume_id = docgen.volume_ids[result_row]
			if not volume_id == result_volume_id:
				db.add_recommendation(volume_id, result_volume_id, rank)
				num_entries_added += 1
				rank += 1
			pos += 1
		if (query_row+1) % 5000 == 0:
			log.info("Completed processing %d/%d volumes" % (query_row+1, len(docgen.volume_ids)))
	log.info("Added %d recommendations" % num_entries_added)
	
	# commit the changes
	db.commit()
	log.info("Database now has %d recommendation entries" % db.recommendation_count())
	db.close()

# --------------------------------------------------------------

def main():
	log.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=log.INFO)
	parser = OptionParser(usage="usage: %prog [options] dir_core")
	parser.add_option("-c","--collection", action="store", type="string", dest="collection", help="set of books to use (all, fiction, nonfiction)", default="all")
	parser.add_option("-b","--bigrams", action="store_true", dest="bigrams", help="produce bigrams in addition to unigrams")
	(options, args) = parser.parse_args()
	if len(args) < 1:
		parser.error("Must specify core directory")

	# create the core
	dir_root = Path(args[0])
	if not dir_root.exists():
		parser.error("Invalid core directory: %s" % dir_root)
	core = CoreCuratr(dir_root)

	# generate the recommendations and add them to the database
	add_recommendations(core)

	# finished
	log.info("Action complete")
	core.shutdown()
	
# --------------------------------------------------------------

if __name__ == "__main__":
	main()
