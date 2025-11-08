#!/usr/bin/env python
"""
This script implements the functionality required to generate ngram counts from the 
full-text British Library

Default usage:
	python code/create-ngrams.py core

Note that we can also create additional ngram counts from subsets of the collection
	python code/create-ngrams.py core -c fiction
	python code/create-ngrams.py core -c nonfiction
"""
import logging as log
import sys
from optparse import OptionParser
from pathlib import Path
from collections import Counter
import nltk
from core import CoreCuratr
from preprocessing.cleaning import clean_content
from preprocessing.text import custom_tokenizer, load_stopwords, strip_accents_unicode

# --------------------------------------------------------------

def extract_tokens(volume_path, stopwords, use_bigrams=False, min_ngram_length=2, max_ngram_length=80):
	with open(volume_path, 'r', encoding="utf8", errors='ignore') as fin:
		volume_tokens = set()
		content = clean_content(fin.read())
		tokens = custom_tokenizer(content, min_term_length=min_ngram_length)
		stripped_tokens = []
		for token in tokens:
			# remove diacritics (accent marks) from using NFKD normalization
			token = strip_accents_unicode(token)
			stripped_tokens.append(token)
			# too short/long or a stopword?
			if len(token) < min_ngram_length or len(token) > max_ngram_length or token in stopwords:
				continue
			volume_tokens.add(token)
		# add bigrams too?
		if use_bigrams:
			for b in nltk.bigrams(stripped_tokens):
				# first token too short/long or a stopword?
				if len(b[0]) < min_ngram_length or len(b[0]) > max_ngram_length or b[0] in stopwords:
					continue
				# second token too short/long or a stopword?
				if len(b[1]) < min_ngram_length or len(b[1]) > max_ngram_length or b[1] in stopwords:
					continue
				# create the bigram
				bigram = "%s_%s" % (b[0], b[1])
				# bigram too long or a stopword?
				if len(bigram) > max_ngram_length or bigram in stopwords:
					continue
				volume_tokens.add(bigram)
		return volume_tokens

# --------------------------------------------------------------

def main():
	log.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=log.INFO)
	parser = OptionParser(usage="usage: %prog [options] dir_core")
	parser.add_option("-c","--collection", action="store", type="string", dest="collection", help="set of books to use (all, fiction, nonfiction)", default="all")
	parser.add_option("-b","--bigrams", action="store_true", dest="bigrams", help="produce bigrams in addition to unigrams?")
	parser.add_option("-s","--stopwords", action="store_true", dest="use_stopwords", help="filter tokens based on English stopwords?")
	(options, args) = parser.parse_args()
	if len(args) < 1:
		parser.error("Must specify core directory")

	# create the core
	dir_root = Path(args[0])
	if not dir_root.exists():
		parser.error("Invalid core directory: %s" % dir_root)
	core = CoreCuratr(dir_root)
	# initialize embeddings
	if not core.init_embeddings():
		sys.exit(1)
	# try connecting to the database
	if not core.init_db():
		sys.exit(1)
	db = core.get_db()

	# which books will we include?
	classmap = db.get_book_classifications_map()
	collection_id = options.collection.lower()
	if collection_id == "all":
		book_ids = set(classmap.keys())
	else:
		book_ids = set()
		for book_id in classmap:
			if collection_id == "fiction" and classmap[book_id][0] == "Fiction":
				book_ids.add(book_id)
			elif collection_id == "nonfiction" and classmap[book_id][0] == "Non-Fiction":
				book_ids.add(book_id)
	if len(book_ids) == 0:
		log.error("No books available for collection from which to count ngrams")
		sys.exit(1)
	log.info("Processing %s books from collection '%s'..." % (len(book_ids), collection_id))

	# read the stopword list
	if options.use_stopwords:
		stopwords = load_stopwords()
		log.info("Stopwords: Using default list of %d stopwords" % len(stopwords))
	else:
		stopwords = set()
		log.info("Stopwords: Not applying any stopword filtering")
	# get year ranges
	year_map = db.get_book_year_map()
	year_min, year_max = db.get_book_year_range()

	if options.bigrams:
		log.info("Extracting unigrams and bigrams by year...")
	else:
		log.info("Extracting unigrams by year...")

	# process each year
	num_volumes = 0
	for year in range(year_min, year_max+1):
		volumes = db.get_volumes_by_year(year)
		if len(volumes) == 0:
			continue
		log.info("Processing year %d..." % year)
		# process each volume from this year from the book IDs that are relevant
		year_counts = Counter()
		for volume in volumes:
			# skip this one?
			if not volume["book_id"] in book_ids:
				continue
			num_volumes += 1
			log.info("Volume %d (%s): %s" % (num_volumes, year, volume["path"]))
			volume_path = core.dir_fulltext / volume["path"]
			if not volume_path.exists():
				log.error("Error: Missing volume file %s" % volume_path)
				continue
			# get all the ngrams
			volume_tokens = extract_tokens(volume_path, stopwords, options.bigrams)
			log.info("Volume contains %d tokens" % len(volume_tokens))
			for token in volume_tokens:
				year_counts[token] += 1
			log.debug("Year dictionary now contains %d ngrams" % len(year_counts))
		# now update the database
		log.info("Adding counts for %d ngrams to database" % len(year_counts))
		for token in year_counts:
			db.add_ngram_count(token, year, year_counts[token], collection_id)
		db.commit()

	# finished
	db.close()
	log.info("Process complete: Added ngrams for %d volumes" % num_volumes)
	core.shutdown()

# --------------------------------------------------------------

if __name__ == "__main__":
	main()
