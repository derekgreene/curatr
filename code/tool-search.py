#!/usr/bin/env python
"""
Script to query a corpus of texts, which has previously been indexed by Solr.

Sample usage:
``` python code/tool-search.py core ireland ```
"""
import sys
from pathlib import Path
import logging as log
from optparse import OptionParser
from core import CoreCuratr

# --------------------------------------------------------------

def main():
	log.basicConfig(format='%(message)s', level=log.INFO)
	parser = OptionParser(usage="usage: %prog [options] dir_core word1 word2...")
	parser.add_option("-s","--segment", action="store_true", dest="segment", help="use segments instead of full volumes")
	parser.add_option("-f","--field", action="store", type="string", dest="field", help="field to search (default is all)", default="all")
	parser.add_option("-n", action="store", type="int", dest="max_results", help="maximum number of results to display", default=10)
	parser.add_option("--sort", action="store", type="string", dest="sort_field", help="field to sort on")
	parser.add_option("--desc", action="store_true", dest="sort_desc", help="sort in descending order (default is ascending)")
	parser.add_option("-v","--verbose", action="store_true", dest="verbose", help="verbose output")
	(options, args) = parser.parse_args()
	if len(args) < 2:
		parser.error("Must specify core directory and a query")
	max_results = options.max_results
	# split into segments?
	if options.segment:
		kind = "segments"
	else:
		kind = "volumes"

	# set up the Curatr core
	dir_core = Path(args[0])
	if not dir_core.exists():
		log.error("Invalid core directory: %s" % dir_core.absolute())
		sys.exit(1)
	core = CoreCuratr(dir_core)
	
	# set up Solr
	if not core.init_solr():
		log.error("Failed to initialize Solr")
		sys.exit(1)
	solr = core.get_solr(kind)
	if solr is None:
		log.error("Failed to connect to Solr core")
		sys.exit(1)	

	# build the query string
	query_string = " ".join(args[1:])
	# any sorting specified?
	if options.sort_field is None:
		sort_params = None
	else:
		sort_params = options.sort_field
		if options.sort_desc:
			sort_params += " desc"
		else:
			sort_params += " asc"
	log.info("-- Running query (kind='%s', field='%s', sort='%s'): %s" % (kind, options.field, sort_params, query_string))

	# run the query with paging
	page_size = min(100, options.max_results)
	start, page = 0, 0
	current_rank = 0
	while True:
		page += 1
		res = solr.query(query_string, field=options.field, highlight=False, start=start, page_size=page_size, sort=sort_params)
		# no results?
		if res is None or len(res.docs) == 0:
			if page == 1:
				log.info("No results found for query")
			break
		# display the results
		log.info("-- Query Page %d: %d results of %d" % ( page, res.get_results_count(), res.get_num_found()))
		for doc in res.docs:
			current_rank += 1
			if current_rank > options.max_results :
				break
			if options.segment:
				log.info("%d. %s (%d) - Volume %s, Segment %s" % (current_rank, doc["title"][:75], doc["year"], doc["volume"], doc["segment"]))
			else:
				log.info("%d. %s (%d) - Volume %s" % (current_rank, doc["title"][:75], doc["year"], doc["volume"]))
			if options.verbose:
				if "content" in doc:
					doc["content"] = "%d characters" % len(doc["content"])
				log.info(doc)
		start += page_size
		# reached the end?
		if start >= min(res.get_num_found(), options.max_results):
			break	

	# finished
	core.shutdown()
	log.info("Process complete")

# --------------------------------------------------------------

if __name__ == "__main__":
	main()
