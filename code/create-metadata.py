#!/usr/bin/env python
"""
This script implements the functionality required to do initial preprocessing of the British Library
Digital Collection and associated raw data files, prior to setting up Curatr.

Same usage:
	python code/create-metadata.py core all


Note: The core directory should contain the required raw metadata files for the British Library
Digital Collection.
"""
import logging as log
import math, sys
from optparse import OptionParser
from pathlib import Path
import pandas as pd
from preprocessing.util import CorePrep
from preprocessing.cleaning import clean, clean_title, clean_shelfmarks, extract_publication_location, extract_authors

# --------------------------------------------------------------

def prep_book_metadata(core):
	""" Function to export the core book metadata for Curatr """
	log.info("++ Preparing book metadata ...")
	filter_book_ids = core.get_filter_book_ids()
	# load the original custom UCD metadata
	df_original = core.get_original_rawdata()
	# load the British library metadata
	df_bl = core.get_bl_rawdata()
	# process the books
	log.info("Cleaning metadata for %d books ..." % len(df_bl))
	rows = []
	matched = 0
	for book_id, row_curatr in df_original.iterrows():
		if (book_id in filter_book_ids) or (not book_id in df_bl.index):
			continue
		row_bl = df_bl.loc[book_id]
		matched += 1
		row = {"book_id": book_id}
		# TODO: should we change this?
		row["year"] = row_curatr["year"]
		# handle title
		row["title"] = clean_title(row_bl["Title"])
		row["title_full"] = clean(row_bl["Title"])
		# handle authors
		row["authors"] = extract_authors(row_curatr["authors"])
		if row_curatr["authors"] is None or len(row_curatr["authors"]) == 0:
			row["authors_full"] = None
		else:
			row["authors_full"] = row_curatr["authors"]
		row["resource_type"] = clean(row_bl["Type of resource"])
		# handle publisher
		row["publisher"] = clean(row_bl["Publisher"])
		row["publisher_full"] = clean(row_curatr["holdings_publication"])
		# handle publication locations
		row["publication_place"], row["publication_country"] = extract_publication_location(
			row_bl["Place of publication"], row_bl["Country of publication"])
		# other fields
		row["edition"] = clean(row_bl['Edition'])
		row["physical_descr"] = clean(row_bl['Physical description'])
		row["shelfmarks"] = clean_shelfmarks(row_curatr["shelfmarks"])
		row["bl_record_id"] = row_bl["BL record ID"]
		rows.append(row)
	df_books = pd.DataFrame(rows).set_index("book_id").sort_index()
	log.info("Created %d rows, %d columns" % (len(df_books), len(df_books.columns)))
	# export the data
	out_path = core.meta_books_path
	log.info("Writing %d books to %s" % (len(df_books), out_path))
	df_books.reset_index().to_json(out_path, orient="records", indent=3)	

def prep_book_classifications(core):
	""" Function to export the Alston index book classification metadata for Curatr """
	log.info("++ Preparing book classifications ...")
	# load the original custom UCD metadata
	df_original = core.get_original_rawdata()
	# load the clean set of books
	df_books = core.get_book_metadata()
	# extract the classification information
	log.info("Extracting classification information ...")
	rows = []
	for book_id, row_curatr in df_original.iterrows():
		if not book_id in df_books.index:
			continue
		book_class = row_curatr["ClassificationTitle"].strip()
		book_subclass = row_curatr["ClassificationSubTitle"].strip()
		if len(book_subclass) == 0 or book_subclass.lower() == "uncategorised":
			book_subclass = None
		row = {"book_id": book_id}
		if book_class.lower() == "fiction":
			row["primary"] = "Fiction"
		else:
			row["primary"] = "Non-Fiction"
		row["secondary"] = book_class
		row["tertiary"] = book_subclass
		rows.append(row)
	df_classifications = pd.DataFrame(rows).sort_values(by=["book_id"]).reset_index(drop=True)
	# export the data
	out_path = core.meta_classifications_path
	log.info("Writing %d classifications to %s" % (len(df_classifications), out_path))
	df_classifications.to_csv(out_path, index=False, sep="\t")

def prep_book_links(core):
	""" Function to export the link metadata for Curatr """
	log.info("++ Preparing book links ...")
	# load the original custom UCD metadata
	df_original = core.get_original_rawdata()
	# load the clean set of books
	df_books = core.get_book_metadata()
	# get data with raw Ark links
	df_ark = core.get_ark_rawdata()
	# get PDF links
	rows = []
	for book_id, url in df_original["url_pdf"][df_original["url_pdf"].notna()].iteritems():
		if not book_id in df_books.index:
			continue
		rows.append({"book_id": book_id, "kind": "pdf", "url": url})
	# add Flickr links
	for book_id, url in df_original["url_images"][df_original["url_images"].notna()].iteritems():
		if not book_id in df_books.index:
			continue
		rows.append({"book_id": book_id, "kind": "flickr", "url": url})
	df_links = pd.DataFrame(rows).sort_values(by=["book_id", "kind"]).reset_index(drop=True)
	# match Ark links to books
	aleph_col = "Aleph system no."
	blrecord_col = "bl_record_id"
	df_merged1 = df_books.reset_index()[["book_id", blrecord_col]].merge(df_ark[[aleph_col,'Ark','Link']], 
							how="left", left_on=blrecord_col, right_on=aleph_col).copy()
	df_merged1["kind"] = "ark"
	df_merged2 = df_merged1[["book_id","kind","Link"]].copy()
	df_merged2.rename(columns={"Link": "url"}, inplace=True)
	log.info("Merged Curatr books and Ark links: %d rows" % len(df_merged2))
	df_merged2.dropna(subset=["url"], inplace=True)
	log.info("After dropping missing values, merged Curatr books and Ark links: %d rows" % len(df_merged2))
	# add Ark links
	df_links2 = pd.concat([df_links, df_merged2])
	df_links2.sort_values(by=["book_id","kind"], inplace=True)
	# export the data
	out_path = core.meta_links_path
	log.info("Writing %d links to %s" % (len(df_links2), out_path))
	df_links2.to_csv(out_path, index=False, sep="\t")

def prep_book_volumes(core):
	""" Function to export the link metadata for Curatr """
	log.info("++ Preparing volume metadata ...")
	log.info("Using British Library Digital Collection full-texts in %s" % core.dir_fulltext.absolute())
	if not core.dir_fulltext.exists():
		log.error("Full-text directory not found: %s" % core.dir_fulltext.absolute())
		return
	# load the clean set of books
	df_books = core.get_book_metadata()
	# add volume information
	log.info("Adding volumes ...")
	df_books["volumes"] = 0
	rows = []
	for book_id in df_books.index:
		prefix = book_id[:4]
		dir_parent = core.dir_fulltext / prefix
		if not dir_parent.exists():
			log.warning("Skipping %s, No such directory of fulltexts: %s" % (book_id,dir_parent) )
			continue
		# check for one or more volumes
		volume_number = 0
		current_volumes = []
		while True:
			volume_number += 1
			# does it exist?
			volume_id = "%s_%02d" % ( book_id, volume_number )
			fname =  "%s_text.txt" % volume_id
			volume_path = dir_parent / fname
			if not volume_path.exists():
				break
			relative_path = str(volume_path).replace( str(core.dir_fulltext), "" )[1:]
			row = {"volume_id":volume_id, "book_id":book_id, "num": volume_number, "total":0,
				"path":str(relative_path)}
			# add file size in kb
			row["filesize"] = math.ceil(volume_path.stat().st_size / 1024.0)
			rows.append(row)
			current_volumes.append(row)
		for row in current_volumes:
			row["total"] = len(current_volumes)
		df_books.at[book_id, "volumes"] = len(current_volumes)
	df_volumes = pd.DataFrame(rows)
	# export the volume data
	out_path = core.meta_volumes_path
	log.info("Writing metadata for %d volumes to %s" % (len(df_volumes), out_path))
	df_volumes.to_csv(out_path, index=False, sep="\t")
	# export the updated books data with volume counts
	out_path = core.meta_books_path
	log.info("Writing %d books to %s" % (len(df_books), out_path))
	df_books.reset_index().to_json(out_path, orient="records", indent=3)	

def verify_data(core):
	log.info("++ Verifying metadata ...")
	# check book metadata
	log.info("Checking book metadata ...")
	if not core.meta_books_path.exists():
		log.warning("Missing book metdata: %s" % core.meta_books_path.absolute())
	else:
		df_books = core.get_book_metadata()
		log.info("Columns: %s" % list(df_books.columns))
		if not "volumes" in df_books.columns:
			log.warning("Book metadata does not contain volumes field")
		log.info("Missing values\n%s" % df_books.isna().sum())
	# check classification data
	log.info("Checking classification metadata ...")
	if not core.meta_classifications_path.exists():
		log.warning("Missing classification metdata: %s" % core.meta_classifications_path.absolute())
	else:
		df_classifications = core.get_book_classifications()
		log.info("Columns: %s" % list(df_classifications.columns))
		log.info("Missing values\n%s" % df_classifications.isna().sum())
	# check link data
	log.info("Checking link metadata ...")
	if not core.meta_links_path.exists():
		log.warning("Missing link metdata: %s" % core.meta_links_path.absolute())
	else:
		df_links = core.get_book_links()
		log.info("Columns: %s" % list(df_links.columns))	
		log.info("Links associated with %d books" % len(df_links["book_id"].unique()) )
		log.info("Missing values\n%s" % df_links.isna().sum())
	# check volume data
	log.info("Checking volume metadata ...")
	if not core.meta_volumes_path.exists():
		log.warning("Missing volume metdata: %s" % core.meta_volumes_path.absolute())
	else:
		df_volumes = core.get_volumes_metadata()
		log.info("Columns: %s" % list(df_volumes.columns))
		log.info("Volumes associated with %d books" % len(df_volumes["book_id"].unique()) )
		log.info("Missing values\n%s" % df_volumes.isna().sum())

# --------------------------------------------------------------

valid_actions = {"books":prep_book_metadata,
	"classifications":prep_book_classifications, 
	"links":prep_book_links, 
	"volumes":prep_book_volumes,
	"verify":verify_data}

def main():
	log.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=log.INFO)
	parser = OptionParser(usage="usage: %prog [options] dir_core action1 action2 actions3...")
	(options, args) = parser.parse_args()
	if len(args) < 2:
		parser.error("Must specify Curatr core directory and one or more actions from %s (or 'all')" % str(valid_actions.keys()) )
	# set up the basic Curatr core
	dir_root = Path(args[0])
	if not dir_root.exists():
		parser.error("Invalid core directory: %s" % dir_root)
	core = CorePrep(dir_root)
	# note 'all' overrides everything
	requested_actions = [x.lower() for x in args[1:]]
	if "all" in requested_actions:
		requested_actions = valid_actions.keys()
	# perform the required actions
	for action in requested_actions:
		try:
			valid_actions[action](core)
		except KeyError:
			log.error("Unknown action '%s'" % action)
			sys.exit(1)

# --------------------------------------------------------------

if __name__ == "__main__":
	main()
