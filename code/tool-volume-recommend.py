#!/usr/bin/env python
"""
Script to test Curatr volume recommendations.

Sample usage:
``` python code/tool-volume-recommend.py core 000000196_01 -n 20 ```
"""
import sys
from pathlib import Path
import logging as log
from optparse import OptionParser
from core import CoreCuratr

# --------------------------------------------------------------

def main():
	log.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=log.INFO, datefmt='%Y-%m-%d %H:%M')
	parser = OptionParser(usage="usage: %prog [options] dir_core volume_id1 volume_id2...")
	parser.add_option("-n", action="store", type="int", dest="num_volumes", help="number of recommendations", default=10)
	(options, args) = parser.parse_args()
	if len(args) < 2:
		parser.error("Must specify core directory and one or more volume IDs")
	queries = set(args[1:])
	num_volumes = options.num_volumes

	# set up the Curatr core
	dir_core = Path(args[0])
	if not dir_core.exists():
		log.error("Invalid core directory: %s" % dir_core.absolute())
		sys.exit(1)
	core = CoreCuratr(dir_core)
	# only need a single DB connection
	core.config.set("db", "pool_size", "1")
	# initialize embeddings
	if not core.init_embeddings():
		sys.exit(1)
	# try connecting to the database
	if not core.init_db():
		sys.exit(1)
	db = core.get_db()
	
	# process each volume ID
	for volume_id in queries:
		vol = db.get_volume(volume_id)
		if vol is None:
			log.warning("No such volume ID '%s'" % volume_id)
			continue
		book = db.get_book(vol["book_id"])
		if book is None:
			log.warning("No book for volume ID '%s'" % volume_id)
			continue
		log.info("++ Recommendations for volume '%s': %s" % (volume_id, book["title"]) )
		recs = db.get_volume_recommendations(volume_id, num_volumes)
		if recs is None or len(recs) == 0:
			log.warning("No recommendations for volume ID '%s'" % volume_id)
			continue
		for i, rec_volume_id in enumerate(recs):
			rec_vol = db.get_volume(rec_volume_id)
			rec_book = db.get_book(rec_vol["book_id"])
			title = f'{rec_book["title"]:.90}{"..." if len(rec_book["title"]) > 90 else ""}'
			log.info("%02d. %s: %s" % (i+1, rec_volume_id, title))

	# finished
	db.close()
	core.shutdown()
	log.info("Process complete")

# --------------------------------------------------------------

if __name__ == "__main__":
	main()
