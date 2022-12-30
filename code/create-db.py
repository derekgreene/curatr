#!/usr/bin/env python
"""
This script implements the functionality required to do initial setup of the MySQL database
required by Curatr.

Same usage:
	python code/create-db.py core all
"""
import sys, json
import logging as log
from optparse import OptionParser
from pathlib import Path
from collections import Counter
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from preprocessing.util import CorePrep
from core import CoreCuratr
from preprocessing.cleaning import clean, clean_content, format_author_sortname
from preprocessing.text import custom_tokenizer, build_bow, VolumeGenerator

# --------------------------------------------------------------

def create_tables(core):
	""" Create all required empty database tables """
	db = core.get_db()
	# Create any missing tables
	log.info("++ Creating database tables ...")
	db.create_tables()
	db.commit()
	db.close()

def add_metadata(core):
	""" Add all key metadata to the database """
	core_prep = CorePrep(core.dir_root)
	db = core.get_db()

	# ensure any required tables exist
	for table_name in ["Books", "Authors", "BookAuthors", "Volumes", "Classifications"]:
		db.ensure_table_exists(table_name)

	df_books = core_prep.get_book_metadata()
	df_volumes = core_prep.get_volumes_metadata()	

	# add default author
	default_author = "Unknown"
	db.add_author(1, default_author)
	authors = {default_author: 1}

	# add core book metadata
	log.info("Adding %d books ..." % len(df_books))
	num_added = 0
	for book_id, row in df_books.iterrows():
		book = dict(row)
		# add authors, if necessary
		if book["authors"] is None:
			book["authors"] = [default_author]
		# do we have a full version?
		if book["authors_full"] is None:
			book["authors_full"] = json.dumps({"creator":default_author})
		else:
			# need to convert the JSON to a string
			book["authors_full"] = json.dumps(book["authors_full"])
		author_ids = []
		for author in book["authors"]:
			if author in authors:
				author_ids.append(authors[author])
			else:
				author_id = len(authors)+1
				db.add_author(author_id, author)
				authors[author] = author_id
				author_ids.append(author_id)
		book["publisher_full"] = clean(book["publisher_full"])
		# add the published locations
		if not book["publication_place"] is None:
			for place in book["publication_place"]:
				db.add_published_location(book_id, "place", place)
		if not book["publication_country"] is None:
			for country in book["publication_country"]:
				db.add_published_location(book_id, "country", country)
		# add the shelfmarks
		if not book["shelfmarks"] is None:
			for shelfmark in book["shelfmarks"]:
				db.add_shelfmark(book_id, shelfmark)
		# add the actual book
		book["decade"] = int(str(book["year"])[0:3] + "0")
		del book["authors"]
		del book["publication_place"]
		del book["publication_country"]
		del book["shelfmarks"]
		log.debug("%d/%d: Adding book %s" % ((num_added+1), len(df_books), book_id))
		db.add_book(book_id, book, author_ids)
		num_added += 1
		if num_added % 5000 == 0:
			log.info("Completed adding %d/%d books" % (num_added, len(df_books)))
	db.commit()
	log.info("Added %d books" % num_added)
	log.info("Database now has %d books, %d authors, %d locations" % (db.book_count(), db.author_count(), db.published_location_count()))

	# add the classifications
	df_classifications = core_prep.get_book_classifications()
	for book_id, row in df_classifications.iterrows():
		db.add_classification(book_id, row["primary"], row["secondary"], row["tertiary"])
	db.commit()
	log.info("Database now has %d classification entries" % db.classification_count())

	# add volume information
	num_added = 0
	df_volumes = core_prep.get_volumes_metadata()
	for volume_id, row in df_volumes.iterrows():
		volume = dict(row)
		db.add_volume(volume_id, volume)
		num_added += 1
	db.commit()
	log.info("Added %d volumes" % num_added)
	log.info("Database now has %d volume entries" % db.volume_count())

	# add book links
	num_added = 0
	df_links = core_prep.get_book_links()
	for _, row in df_links.iterrows():
		db.add_link(row["book_id"], row["kind"], row["url"])
		num_added += 1
	db.commit()
	log.info("Added %d links" % num_added)
	log.info("Database now has %d link entries" % db.link_count())
	db.close()

def add_wordcounts(core):
	""" Add all volume word counts to the database """
	log.info("++ Adding volume word counts to database ...")
	core_prep = CorePrep(core.dir_root)
	db = core.get_db()
	# get metadata for all volumes
	volumes = db.get_volumes()
	# process all volume files
	counts = {}
	num_volumes = 0
	for volume in volumes:
		num_volumes += 1
		volume_id = volume["id"]
		log.debug("Volume %d/%d: Counting tokens in %s" % (num_volumes, len(volumes), volume["path"]))
		volume_path = core.dir_fulltext / volume["path"]
		if not volume_path.exists():
			log.error("Missing volume file %s" % volume_path)
			continue
		# process the content
		with open(volume_path, 'r', encoding="utf8", errors='ignore') as fin:
			content = clean_content(fin.read())
			tokens = custom_tokenizer(content)
			db.set_volume_word_count(volume_id, len(tokens))	
		if num_volumes % 5000 == 0:
			log.info("Completed processing %d/%d volumes" % (num_volumes, len(volumes)))
	log.info("Updated word counts for %d volumes" % num_volumes)
	db.close()

def add_recommendations(core, top=50):
	""" Add volume recommendations, based on pairwise cosine similarities
	calculated on a sparse bag-of-words model. """
	log.info("++ Adding volume recommendations to database ...")
	core_prep = CorePrep(core.dir_root)
	db = core.get_db()
	# get default stopwords list
	stopwords = core_prep.get_stopwords()
	log.info("Using default list of %d stopwords" % len(stopwords))
	# build the bag-of-words model
	docgen = VolumeGenerator(core)
	log.info("Building bag-of-words model ...")
	(X,terms) = build_bow(docgen, stopwords)
	log.info("Built document-term matrix: %d documents, %d terms" % (X.shape[0], X.shape[1]))

	# calculate pairwise similarities
	log.info("Computing similarities ...")
	S = cosine_similarity( X )
	log.info("Computed %d X %d similarity matrix" % (S.shape[0], S.shape[1]))
	
	# ensure required DB table exists
	db.ensure_table_exists("Recommendations")
	# get recommendations for each volume
	num_entries_added = 0
	log.info("Finding top %d recommendations for %d volumes ..." % (top, len(docgen.volume_ids)))
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

def add_ngrams(core, max_ngram_length=99):
	""" Function to add unigram or bigram count data to the Curatr database.
	Note that this takes a while to run."""
	log.info("++ Adding volume ngrams to database ...")
	core_prep = CorePrep(core.dir_root)
	db = core.get_db()
	# get default stopwords list
	stopwords = core_prep.get_stopwords()
	log.info("Using default list of %d stopwords" % len(stopwords))
	# get collection date range
	year_map = db.get_book_year_map()
	year_min, year_max = db.get_book_year_range()
	log.info("Extracting unigrams by year for range [%d,%d] ..." % (year_min, year_max))
	# process each volume by year
	for year in range(year_min, year_max+1):
		volumes = db.get_volumes_by_year(year)
		if len(volumes) == 0:
			continue
		log.info("Year %d: Extracting ngrams from %d volumes ..." % (year, len(volumes)))
		# get the number of volumes in which this word appears
		year_counts = Counter()
		for volume in volumes:
			volume_path = core.dir_fulltext / volume["path"]
			if not volume_path.exists():
				log.error("Missing volume file %s" % volume_path)
				continue
			# get all unique tokens in this file
			with open(volume_path, 'r', encoding="utf8", errors='ignore') as fin:
				content = clean_content(fin.read())
				tokens = custom_tokenizer(content)
				volume_unique_tokens = set()
				for token in tokens:
					if not (token in stopwords or len(token) > max_ngram_length):
						volume_unique_tokens.add(token)
			# now update the year counts
			for token in volume_unique_tokens:
				year_counts[token] += 1
		# add the counts for this year to the database
		log.info("Adding counts for %d ngrams and %d volumes to database" % (len(year_counts),len(volumes)) )
		for token in year_counts:
			db.add_ngram_count(token, year, year_counts[token])
		db.commit()
	log.info("Database now has %d ngram entries" % db.total_ngram_count())
	db.close()

def add_extracts(core, extract_length=450):
	log.info("++ Adding volume extracts to database ...")
	core_prep = CorePrep(core.dir_root)
	db = core.get_db()
	# get all volume details
	volumes = db.get_volumes()
	log.info("Processing %d volumes ..." % len(volumes))
	# process all volumes
	num_volumes = 0
	for volume in volumes:
		num_volumes += 1
		volume_id = volume["id"]
		volume_path = core.dir_fulltext / volume["path"]
		if not volume_path.exists():
			log.error("Missing volume file %s" % volume_path)
			continue
		# process the content of the current volume
		with open(volume_path, 'r', encoding="utf8", errors='ignore') as fin:
			content = clean_content(fin.read())
			# tidy the content
			content = content.replace( '" ', '"' ).replace( '..', '.' ).replace( '. .', '.' ).replace( '..', '.').strip()
			# find first alphanumeric
			for start_pos in range(len(content)):
				if content[start_pos].isalnum():
					break
			# create the final extract
			actual_extract_length = min(extract_length, len(content)-start_pos)
			extract = content[start_pos:actual_extract_length+start_pos] + "..."
			# add it to the database
			db.add_volume_extract(volume_id, extract)
		if num_volumes % 5000 == 0:
			log.info("Completed processing %d/%d volume extracts" % (num_volumes, len(volumes)))	
	db.commit()
	log.info("Database now has %d extracts" % db.extract_count())
	db.close()
	
def add_caches(core):
	""" Add all of the additional cache tables which are used by Curatr for performance reasons """
	log.info("++ Adding cache tables to database ...")
	db = core.get_db()
	# get the core book data that we need
	books = db.get_books()
	log.info("Building maps...")
	volume_year_map = db.get_volume_year_map()
	author_name_map = db.get_author_name_map()
	log.info("Corpus contains %d books, %d volumes, %d authors ..." % 
		(len(books), len(volume_year_map), len(author_name_map)))
	corpus_year_min, corpus_year_max = db.get_book_year_range()
	log.info("Corpus year range: [%d,%d]" % (corpus_year_min, corpus_year_max))

	# delete any cache tables and re-create them
	db.clear_cache_tables()
	
	# populate CachedBookYears
	log.info("Populating CachedBookYears ...")
	year_counts = {}
	for y in range(corpus_year_min,corpus_year_max+1):
		year_counts[y] = 0
	for book in books:
		year_counts[book["year"]] += 1
	# add to the database
	for year in year_counts:
		db.add_cached_book_years(year, year_counts[year])
	db.commit()

	# populate CachedVolumeYears
	log.info("Populating CachedVolumeYears ...")
	year_counts = {}
	for y in range(corpus_year_min,corpus_year_max+1):
		year_counts[y] = 0
	for volume_id in volume_year_map:
		year_counts[volume_year_map[volume_id]] += 1
	# add to the database
	for year in year_counts:
		db.add_cached_volume_years(year, year_counts[year])
	db.commit()

	# populate CachedPlaceCounts & CachedCountryCounts
	log.info("Populating CachedPlaceCounts and CachedCountryCounts ...")
	num = 0
	country_counts, place_counts = Counter(), Counter()
	locations_map = db.get_book_published_locations_map()
	for book_id in locations_map:
		num += 1
		if num % 5000 == 0:
			log.info("Processed %d books" % num)
		for pair in locations_map[book_id]:
			if pair[0] == "country":
				country_counts[pair[1]] += 1
			elif pair[0] == "place":
				place_counts[pair[1]] += 1
	log.info("Adding counts for %d places to database" % len(place_counts))
	# add to the database
	for location in place_counts:
		db.add_cached_place_count(location, place_counts[location])
	db.commit()
	log.info("Adding counts for %d countries to database" % len(country_counts))
	for location in country_counts:
		db.add_cached_country_count(location, country_counts[location])
	db.commit()

	# populate CachedClassificationCounts
	log.info("Populating CachedClassificationCounts ...")
	class_map = db.get_book_classifications_map()
	class_counts = [Counter(), Counter(), Counter()]
	for book_id in class_map:
		primary, secondary, tertiary = class_map[book_id]
		if not primary is None:
			class_counts[0][primary] += 1
		if not secondary is None:
			class_counts[1][secondary] += 1
		if not tertiary is None:
			class_counts[2][tertiary] += 1
	for level in range(0, 3):
		log.info("Adding classification counts for %d classes at level %d" % (len(class_counts[level]), level))
		for class_name in class_counts[level]:
			db.add_cached_classification_count(class_name, level, class_counts[level][class_name])
		db.commit()

	# populate CachedAuthors
	log.info("Populating CachedAuthors ...")
	# get the author stats
	author_book_count = {}
	author_min_year, author_max_year, author_sort_name = {}, {}, {}
	num = 0
	for book in books:
		num += 1
		if num % 5000 == 0:
			log.info("Processed %d books" % num)
		author_ids = db.get_book_author_ids(book["id"])
		for author_id in author_ids:
			if not author_id in author_book_count:
				author_book_count[author_id] = 1	
				author_min_year[author_id] = book["year"]
				author_max_year[author_id] = book["year"]
			else:
				author_book_count[author_id] += 1
				author_min_year[author_id] = min(book["year"], author_min_year[author_id])
				author_max_year[author_id] = max(book["year"], author_max_year[author_id])
			author_sort_name[author_id] = format_author_sortname(author_name_map[author_id])
	log.info("Found %d authors" % len(author_book_count))
	# add to the database
	for author_id in author_book_count:
		db.add_cached_author_details(author_id, author_name_map[author_id], author_sort_name[author_id], author_min_year[author_id], author_max_year[author_id], author_book_count[author_id])
	db.commit()
	# finished
	db.close()

# --------------------------------------------------------------

valid_actions = {"create":create_tables, "metadata":add_metadata, 
"wordcounts":add_wordcounts, "recs":add_recommendations, "ngrams":add_ngrams,
"extracts":add_extracts, "caches": add_caches}

def main():
	log.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=log.INFO)
	parser = OptionParser(usage="usage: %prog [options] dir_core action1 action2 actions3...")
	(options, args) = parser.parse_args()
	if len(args) < 2:
		parser.error("Must specify Curatr core directory and one or more actions from %s (or 'all')" % str(valid_actions.keys()) )
	# create the core
	dir_root = Path(args[0])
	if not dir_root.exists():
		parser.error("Invalid core directory: %s" % dir_root)
	core = CoreCuratr(dir_root)
	# try connecting to the database
	if not core.init_db():
		sys.exit(1)

	requested_actions = [x.lower() for x in args[1:]]
	# note 'delete' overrides everything
	if "delete" in requested_actions:
		log.info("++ Only applying delete tables operation ...")
		db = core.get_db()
		db.delete_tables()
		db.commit()
		db.close()
		log.info("Actions complete")
		core.shutdown()
		sys.exit(0)
	# note 'all' overrides everything
	if "all" in requested_actions:
		requested_actions = valid_actions.keys()
	# perform the required actions
	for action in requested_actions:
		if action == 'delete':
			continue
		elif not action in valid_actions:
			log.error("Unknown action '%s'" % action)
			sys.exit(1)
		valid_actions[action](core)
	# finished
	log.info("Actions complete")
	core.shutdown()

# --------------------------------------------------------------

if __name__ == "__main__":
	main()
