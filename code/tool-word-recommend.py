#!/usr/bin/env python
"""
Script to access Curatr word recommendations.

Sample usage:
``` python code/tool-word-recommend.py core ireland -n 10 ``` 
"""
import sys
from pathlib import Path
import logging as log
from optparse import OptionParser
from core import CoreCuratr

# --------------------------------------------------------------

def main():
	log.basicConfig(format='%(message)s', level=log.INFO, datefmt='%Y-%m-%d %H:%M')
	parser = OptionParser(usage="usage: %prog [options] dir_core word1 word2...")
	parser.add_option("-n", action="store", type="int", dest="num_words", help="number of neighbors per word", default=5)
	parser.add_option("-e","--embedding", action="store", type="string", dest="embed_id", help="embedding model to use (all, fiction, nonfiction)", default="all")
	(options, args) = parser.parse_args()
	if len(args) < 2:
		parser.error("Must specify core directory and one or more words")
	queries = set(args[1:])
	num_words = options.num_words
	embed_id = options.embed_id

	# set up the Curatr core
	dir_core = Path(args[0])
	if not dir_core.exists():
		log.error("Invalid core directory: %s" % dir_core.absolute())
		sys.exit(1)
	core = CoreCuratr(dir_core)
	
	# get the neighbors for each word
	log.info("Getting %d recommendations for %s" % (num_words, queries))
	log.info("Using embedding '%s" % embed_id)

	# first strategy - basic recommendations
	log.info("Recommending without enforcing diversity...")
	suggestions = core.aggregate_word_similarity(queries, k=num_words, embed_id=embed_id, ignores=[], enforce_diversity=False)
	log.debug("Retrieved %d similar words" % len(suggestions))
	log.info(", ".join(suggestions))

	# second strategy - enforce diversity and reduce duplicates
	log.info("Recommending and enforcing diversity...")
	suggestions = core.aggregate_word_similarity(queries, k=num_words, embed_id=embed_id, ignores=[], enforce_diversity=True)
	log.debug("Retrieved %d similar words" % len(suggestions))
	log.info(", ".join(suggestions))

	# finished
	core.shutdown()
	log.info("Process complete")

# --------------------------------------------------------------

if __name__ == "__main__":
	main()
