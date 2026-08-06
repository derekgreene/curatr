#!/usr/bin/env python
"""
Utility script to check that the configured Solr index is working, and report
the number of documents in the volumes and segments cores.

Sample usage:
``` python code/check-solr.py core ```
"""
import sys
from pathlib import Path
import logging as log
from optparse import OptionParser
from core import CoreCuratr

# --------------------------------------------------------------

def check_core(core, kind):
	""" Query the specified Solr core and report its document count """
	log.info(f"++ Checking Solr '{kind}' core...")
	solr = core.get_solr(kind)
	res = solr.query("*:*", "all", highlight=False, page_size=1)
	if res is None:
		log.error(f"Failed to query Solr '{kind}' core '{solr.core_name}'")
		return None
	doc_count = res.get_num_found()
	log.info(f"Solr '{kind}' core '{solr.core_name}' OK - {doc_count} documents")
	return doc_count

def main():
	log.basicConfig(format="%(message)s", level=log.INFO, datefmt="%Y-%m-%d %H:%M")
	parser = OptionParser(usage="usage: %prog [options] dir_core")
	(options, args) = parser.parse_args()
	if len(args) < 1:
		parser.error("Must specify core directory")

	dir_root = Path(args[0])
	if not dir_root.exists():
		log.error(f"Core directory does not exist: {dir_root}")
		sys.exit(1)
	core = CoreCuratr(dir_root)

	log.info("++ Connecting to Solr...")
	if not core.init_solr():
		log.error("Failed to connect to Solr")
		sys.exit(1)

	volume_count = check_core(core, "volumes")
	segment_count = check_core(core, "segments")
	if volume_count is None or segment_count is None:
		sys.exit(1)

	log.info("Action complete")
	core.shutdown()

# --------------------------------------------------------------

if __name__ == "__main__":
	main()
