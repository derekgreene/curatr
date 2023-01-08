#!/usr/bin/env python
"""
Script to test Curatr word recommendations.

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
	log.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=log.INFO, datefmt='%Y-%m-%d %H:%M')
	parser = OptionParser(usage="usage: %prog [options] dir_core word1 word2...")
	parser.add_option("-n", action="store", type="int", dest="num_words", help="number of neighbors per word", default=5)
	(options, args) = parser.parse_args()
	if len(args) < 2:
		parser.error("Must specify core directory and one or more words")
	queries = set(args[1:])
	num_words = options.num_words

	# set up the Curatr core
	dir_core = Path(args[0])
	if not dir_core.exists():
		log.error("Invalid core directory: %s" % dir_core.absolute())
		sys.exit(1)
	core = CoreCuratr(dir_core)
	
	# get the neighbors for each word
	log.info("Getting %d recommendations for for: %s" % (num_words, queries))

	# first strategy - basic recommendations
	log.info("Recommending without enforcing diversity...")
	suggestions = core.aggregate_recommend_words(queries, [], num_words, False)
	log.info(", ".join(suggestions))

	# second strategy - enforce diversity and reduce duplicates
	log.info("Recommending and enforcing diversity...")
	suggestions = core.aggregate_recommend_words(queries, [], num_words, True)
	log.info(", ".join(suggestions))

	# finished
	core.shutdown()
	log.info("Process complete")

# --------------------------------------------------------------

if __name__ == "__main__":
	main()
