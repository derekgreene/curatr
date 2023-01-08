#!/usr/bin/env python
"""
Script to index a corpus of texts on a Solr server.

Sample usage:
	python code/create-search.py core
"""
import sys, re, ast
import logging as log
from collections import defaultdict
from pathlib import Path
import numpy as np
import pandas as pd
from optparse import OptionParser
from preprocessing.cleaning import clean_content
from core import CoreCuratr

# --------------------------------------------------------------

def segment_text(text, length):
	""" Split the specified string into segments of the specified length """
	return (text[0+i:length+i] for i in range(0, len(text), length))

def create_segment_documents(book, volume, content, segment_size):
	if len(content) <= segment_size:
		segments = [content]
	else:
		segments = list(segment_text(content, segment_size))
	log.info( "Indexing %s, volume %d into %d segments" % (book["id"], volume["num"], len(segments)))
	# index each segment as a separate document
	docs = []
	for i, segment in enumerate(segments):
		doc = {"id" : "%s_%06d" % (volume["id"], (i+1)),
			"authors" : book["authors"],
			"authors" : book["authors_full"],
			"authors_genders": book["author_genders"],
			"book_id" : book["id"], 
			"category" : book["category"],
			"classification" : book["classification"],
			"edition" : book["edition"],
			"location_countries" : book["location_countries"], 
			"location_places" : book["location_places"],
			"max_segment" : len(segments),
			"max_volume" : book["volumes"],
			"mudies_description": 0, # TODO
			"mudies_match": None, # TODO
			"physical_descr" : book["physical_descr"],
			"publisher": book["publisher"],
			"publisher_full": book["publisher_full"],
			"segment": i+1,
			"shelfmarks" : book["shelfmarks"],
			"subclassification" : book["subclassification"],
			"title" : book["title"], 
			"title_full": book["title_full"], 
			"url_ark": book["url_ark"],
			"url_flickr": book["url_flickr"],
			"url_mudies": book["url_mudies"],
			"url_pdf": book["url_pdf"],
			"volume" : volume["num"],
			"year" : book["year"], 
			"content" : segment}
		docs.append(doc)
	return docs

def create_volume_document(book, volume, content):
	log.info("Indexing %s, volume %d" % ( book["id"], volume["num"]))
	doc = {"id" : volume["id"],
		"authors" : book["authors"],
		"authors" : book["authors_full"],
		"authors_genders": book["author_genders"],
		"book_id" : book["id"], 
		"category" : book["category"],
		"classification" : book["classification"],
		"edition" : book["edition"],
		"location_countries" : book["location_countries"], 
		"location_places" : book["location_places"],
		"max_segment" : 1,
		"max_volume" : book["volumes"],
		"mudies_description": 0, # TODO
		"mudies_match": None, # TODO
		"physical_descr" : book["physical_descr"],
		"publisher": book["publisher"],
		"publisher_full": book["publisher_full"],
		"segment": 1,
		"shelfmarks" : book["shelfmarks"],
		"subclassification" : book["subclassification"],
		"title" : book["title"], 
		"title_full": book["title_full"], 
		"url_ark": book["url_ark"],
		"url_flickr": book["url_flickr"],
		"url_mudies": book["url_mudies"],
		"url_pdf": book["url_pdf"],
        "volume" : volume["num"],
        "year" : book["year"], 
		"content" : content}
	return doc

def build_index(core, do_segment):
	db = core.get_db()
	# cache necessary metadata
	log.info("Retrieving book metadata from database ...")
	books = db.get_books()
	author_name_map = db.get_author_name_map()
	author_gender_map = db.author_gender_map()
	classification_map = db.get_book_classifications_map()
	shelfmark_map = db.get_book_shelfmarks_map()
	link_map = db.get_book_link_map()
	locations_map = db.get_published_locations_map()

	# create a connection to the solr server
	if not core.init_solr():
		return False

	# split into segments?
	if do_segment:
		solr = core.get_solr("segments")
		core_name = core.solr_core_segments
		segment_size = core.config["solr"].getint("segment_size", 2000)
		log.info("Indexing full-texts based on segments of at most %d characters (core=%s)" % (segment_size, core_name))
	else:
		solr = core.get_solr("volumes")
		core_name = core.solr_core_volumes
		log.info("Indexing full-texts based on complete volumes (core=%s)" % core_name)
	if solr is None:
		log.error("Failed to connect to Solr core")
		sys.exit(1)	

	# Process each book in the library
	log.info("Processing %d books ..." % len(books))
	num_books, num_indexed = 0, 0
	for book in books:
		num_books += 1
		if book["title"] is None:
			book["title"] = "Untitled"
		log.info("Book %d/%d: (%s) %s ..." % (num_books, len(books), book["id"], book["title"][:50]))
		# add extra book metadata
		book["authors"], book["author_genders"] = [], []
		for author_id in db.get_book_author_ids(book["id"]):
			book["authors"].append(author_name_map[author_id])
			book["author_genders"].append(author_gender_map[author_id])
		book["shelfmarks"] = shelfmark_map.get(book["id"], [])
		book["category"], book["classification"], book["subclassification"] = classification_map.get(book["id"], (None, None, None))
		# add extra link info
		link_kinds = ["ark", "pdf", "flickr", "mudies"]
		for kind in link_kinds:
			book["url_%s" % kind] = None
		if book["id"] in link_map:
			for kind in link_kinds:
				if kind in link_map[book["id"]]:
					book["url_%s" % kind] = link_map[book["id"]][kind]
		# add extra published location info
		book["location_countries"] = []
		book["location_places"] = []
		if book["id"] in locations_map:
			for kind, loc in locations_map[book["id"]]:
				if kind == "place":
					book["location_places"].append(loc)	
				elif kind == "country":
					book["location_countries"].append(loc)	
		# process volumes for this book
		docs = []
		num_book_volumes = book["volumes"]
		for vol in db.get_book_volumes(book["id"]):
			volume_path = core.dir_fulltext / vol["path"]
			if not volume_path.exists():
				log.error("Missing volume file %s" % volume_path)
				continue
			# process the content
			with open(volume_path, 'r', encoding="utf8", errors='ignore') as fin:
				content = clean_content( fin.read().strip() )
				log.debug("Full text is %d characters" % len(content) )
				# do we need to segment the text into smaller parts?
				if do_segment:
					docs.extend(create_segment_documents(book, vol, content, segment_size))
				# otherwise index the full text as a single document
				else:
					docs.append(create_volume_document(book, vol, content))
		# no documents?
		if len(docs) == 0:
			log.warning("Book %s has no documents" % book["id"])
			continue				
		# now actually write and commit the segments for this book
		solr.index(docs)
		solr.commit()
		log.info("Indexed %d document(s)" % len(docs))
		num_indexed += len(docs)
		# # TODO: remove
		# if num_indexed >= 100:
		# 	break

	# finished
	if do_segment:
		log.info("Total: Indexed %d segments from %d books" % (num_indexed, num_books))
	else:
		log.info("Total: Indexed %d volumes from %d books" % (num_indexed, num_books))
	db.close()
	return True

# --------------------------------------------------------------

def main():
	log.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=log.INFO)
	parser = OptionParser(usage="usage: %prog [options] dir_core")
	parser.add_option("-s","--segment", action="store_true", dest="segment", help="segment volumes into shorter documents")
	(options, args) = parser.parse_args()
	if len(args) < 1:
		parser.error("Must specify core directory" )

	# create the core
	dir_root = Path(args[0])
	if not dir_root.exists():
		parser.error("Invalid core directory: %s" % dir_root)
	core = CoreCuratr(dir_root)
	# try connecting to the database
	if not core.init_db():
		sys.exit(1)

	# apply the indexing
	if build_index(core, options.segment):
		log.info("Indexing complete")
	else:
		log.info("Indexing cancelled")
	# finished
	core.shutdown()

# --------------------------------------------------------------

if __name__ == "__main__":
	main()
