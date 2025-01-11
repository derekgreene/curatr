import time
import logging as log
from db.util import GenericDB
from db.booksql import sql_statements, sql_indexing_statements
from user import User, dict_to_user

# --------------------------------------------------------------

core_tables = ["Books", "Authors", "BookAuthors", "BookLocations", "BookShelfmarks",
	"Volumes", "BookLinks", "Classifications", "Recommendations", "Ngrams", "VolumeExtracts",
	"Users", "Lexicons", "LexiconWords", "LexiconIgnores", "Corpora", "CorpusMetadata", "Bookmarks"]

cache_tables = ["CachedAuthors", "CachedBookYears", "CachedVolumeYears", 
	"CachedClassificationCounts", "CachedPlaceCounts", "CachedCountryCounts"]

# --------------------------------------------------------------

class CuratrDB(GenericDB):
	""" Main interface to the Curatr database """
	def __init__(self, hostname, port, username, password, dbname, autocommit=False):
		super().__init__(hostname, port, username, password, dbname, autocommit, sql_statements)

	def create_tables(self):
		""" Create core tables in the database """
		tables = self._get_existing_tables()
		log.info("Previous tables: %s" % tables )
		# create each missing tables
		for table_name in core_tables:
			if not table_name in tables:
				log.info( "Creating table %s ..." % table_name )
				self.cursor.execute( sql_statements["Table%s" % table_name] )
				log.info("Columns: %s" % self._get_table_columns( table_name ) )
		# check tables now
		tables = self._get_existing_tables()
		log.info("Current tables: %s" % tables)

	def delete_tables(self):
		""" Delete all existing tables in the database. Apply with care! """
		tables = self._get_existing_tables()
		log.info("Previous tables: %s" % tables)
		# drop previous tables
		for table_name in tables:
			if table_name in core_tables:
				log.info("Dropping table %s" % table_name)
				self.cursor.execute( "DROP TABLE %s" % table_name )
		self.conn.commit()
		# check tables now
		tables = self._get_existing_tables()
		log.info("Current tables: %s" % tables)

	def index_tables(self):
		""" Index all certain tables in the database to improve performance. """
		try:
			for x in sql_indexing_statements:
				log.info("Building database index '%s' ..." % x)
				self.cursor.execute(sql_indexing_statements[x])
		except Exception as e:
			log.error("SQL error in index_tables(): %s" % str(e))
			return 0
		
	def add_book(self, book_id, book, author_ids):
		columns = self._get_table_columns("Books")
		dbrow = {"id" : book_id} 
		for key in book:
			if key in columns:
				dbrow[key] = book[key]
		# add the book
		placeholder = ", ".join(["%s"] * len(dbrow))
		sql = "INSERT INTO Books ({columns}) VALUES ({values});".format(columns=",".join(dbrow.keys()), values=placeholder)
		self.cursor.execute(sql, list(dbrow.values()))		
		# add the book authors
		for author_id in author_ids:
			sql = "INSERT INTO BookAuthors (book_id,author_id) VALUES (%s,%s)"
			self.cursor.execute(sql, (book_id,author_id))

	def add_author(self, author_id, name):
		sql = "INSERT INTO Authors (id,name) VALUES(%s,%s)"
		self.cursor.execute(sql, (author_id, name))

	def add_published_location(self, book_id, kind, location):
		sql = "INSERT INTO BookLocations (book_id,kind,location) VALUES(%s,%s,%s)"
		self.cursor.execute(sql, (book_id, kind, location))

	def add_shelfmark(self, book_id, shelfmark):
		sql = "INSERT INTO BookShelfmarks (book_id, shelfmark) VALUES(%s,%s)"
		self.cursor.execute(sql, (book_id, shelfmark))

	def add_volume(self, volume_id, volume):
		sql = "INSERT INTO Volumes (id, num, total, book_id, path) VALUES(%s,%s,%s,%s,%s)"
		self.cursor.execute(sql, (volume_id, volume["num"], volume["total"], 
			volume["book_id"], volume["path"]))

	def add_classification(self, book_id, overall, secondary, tertiary):
		sql = "INSERT INTO Classifications (book_id, overall, secondary, tertiary) VALUES(%s,%s,%s,%s)"
		self.cursor.execute(sql, (book_id, overall, secondary, tertiary))

	def add_link(self, book_id, kind, url):
		sql = "INSERT INTO BookLinks (book_id,kind,url) VALUES(%s,%s,%s)"
		self.cursor.execute(sql, (book_id, kind, url))

	def add_recommendation(self, volume_id, rec_volume_id, rank ):
		sql = "INSERT INTO Recommendations (volume_id, rec_volume_id, rank_num) VALUES(%s,%s,%s)"
		self.cursor.execute(sql, (volume_id, rec_volume_id, rank))	

	def get_book(self, book_id):
		""" Return basic details for a single book with the specified ID """
		try:
			return self._sql_to_dict("SELECT * FROM Books WHERE id=%s", book_id)
		except Exception as e:
			log.error("SQL error in get_book(): %s" % str(e))
			return None

	def get_book_by_volume(self, volume_id):
		""" Return basic details for a single book, based on an associated volume's ID """
		try:
			self.cursor.execute("SELECT book_id FROM Volumes WHERE id=%s", volume_id)
			result = self.cursor.fetchone()
			if result is None:
				return None
			book_id = result[0]
			return self._sql_to_dict("SELECT * FROM Books WHERE id=%s", book_id)
		except Exception as e:
			log.error("SQL error in get_book_by_volume(): %s" % str(e))
			return None

	def get_books(self):
		""" Return back basic details for all books in the database """
		try:
			return self._bulk_sql_to_dict("SELECT * FROM Books")
		except Exception as e:
			log.error("SQL error: %s" % str(e))
			return []

	def book_count(self):
		try:
			self.cursor.execute("SELECT COUNT(id) FROM Books")
			result = self.cursor.fetchone()
			return result[0]
		except Exception as e:
			log.error("SQL error in book_count(): %s" % str(e))
			return 0

	def author_count(self):
		try:
			self.cursor.execute("SELECT COUNT(id) FROM Authors")
			result = self.cursor.fetchone()
			return result[0]
		except Exception as e:
			log.error("SQL error: %s" % str(e))
			return 0

	def get_shelfmarks(self, book_id):
		""" Return back list of shelfmarks associated with the specified book. """
		shelfmarks = []
		try:
			sql = "SELECT shelfmark FROM BookShelfmarks WHERE book_id = %s"
			self.cursor.execute(sql, book_id)
			for row in self.cursor.fetchall():
				shelfmarks.append(row[0])
		except Exception as e:
			log.error("SQL error in get_shelfmarks(): %s" % str(e))
		return shelfmarks

	def get_book_shelfmarks_map(self):
		""" Return back all shelfmarks associatd with all books. """
		shelfmark_map = {}
		try:
			sql = "SELECT book_id,shelfmark FROM BookShelfmarks"
			self.cursor.execute(sql)
			for row in self.cursor.fetchall():
				if not row[0] in shelfmark_map:
					shelfmark_map[row[0]] = []
				shelfmark_map[row[0]].append(row[1])
		except Exception as e:
			log.error("SQL error in get_book_shelfmarks_map(): %s" % str(e))
		return shelfmark_map

	def published_location_count(self, kind=None):
		try:
			if kind is None:
				self.cursor.execute("SELECT COUNT(*) FROM BookLocations")
			else:
				sql = "SELECT COUNT(*) FROM BookLocations WHERE kind = %s"
				self.cursor.execute(sql, kind)
			result = self.cursor.fetchone()
			return result[0]
		except Exception as e:
			log.error("SQL error in location_count(): %s" % str(e))
			return 0

	def get_published_locations(self, book_id):
		""" Get all published locations associated with the specified book. 
		The result is a list of 0 or more tuples of the format (kind, location_name) """
		locations = []
		try:
			sql = "SELECT kind, location FROM BookLocations WHERE book_id = %s"
			self.cursor.execute(sql, book_id)
			for row in self.cursor.fetchall():
				locations.append((row[0], row[1]))
		except Exception as e:
			log.error("SQL error in get_published_locations(): %s" % str(e))
		return locations

	def get_published_locations_map(self):
		""" Return back all published locations associatd with all books. These are
		returned as tuples of the format (kind, location) """
		location_map = {}
		try:
			sql = "SELECT book_id, kind, location FROM BookLocations"
			self.cursor.execute(sql)
			for row in self.cursor.fetchall():
				if not row[0] in location_map:
					location_map[row[0]] = []
				location_map[row[0]].append((row[1], row[2]))
		except Exception as e:
			log.error("SQL error in get_published_locations_map(): %s" % str(e))
		return location_map

	def get_published_location_names(self, kind=None):
		""" Return back all unique published location names """
		locations = []
		try:
			if kind is None:
				sql = "SELECT DISTINCT location FROM BookLocations ORDER BY location"
				self.cursor.execute(sql)
			else:
				sql = "SELECT DISTINCT location FROM BookLocations WHERE kind = %s ORDER BY location"
				self.cursor.execute(sql, kind)
			for row in self.cursor.fetchall():
				locations.append(row[0])
		except Exception as e:
			log.error("SQL error in get_published_location_names(): %s" % str(e))
		return locations		

	def get_published_location_counts(self, kind=None, top = -1):
		""" Return back counts for all book published locations """
		location_counts = {}
		try:
			if kind is None:
				if top == -1:
					sql = "SELECT location, count(*) as c from BookLocations GROUP BY location ORDER BY c DESC"
					self.cursor.execute(sql)
				else:
					sql = "SELECT location, count(*) as c from BookLocations GROUP BY location ORDER BY c DESC LIMIT %s"
					self.cursor.execute(sql, top)
			else:
				if top == -1:
					sql = "SELECT location, count(*) as c from BookLocations WHERE kind = %s GROUP BY location ORDER BY c DESC"
					self.cursor.execute(sql, kind)
				else:
					sql = "SELECT location, count(*) as c from BookLocations WHERE kind = %s GROUP BY location ORDER BY c DESC LIMIT %s"
					self.cursor.execute(sql, (kind, top))
			for row in self.cursor.fetchall():
				location_counts[row[0]] = row[1]
		except Exception as e:
			log.error("SQL error in get_published_location_counts(): %s" % str(e))
		return location_counts

	def get_book_classifications_map(self):
		classification_map = {}
		try:
			sql = "SELECT book_id, overall, secondary, tertiary FROM Classifications"
			self.cursor.execute(sql)
			for row in self.cursor.fetchall():
				classification_map[row[0]] = (row[1], row[2], row[3])
		except Exception as e:
			log.error("SQL error in get_book_classifications_map(): %s" % str(e))
		return classification_map

	def classification_count(self):
		""" Return the total number of classification entries in the database """
		try:
			self.cursor.execute("SELECT COUNT(*) FROM Classifications")
			result = self.cursor.fetchone()
			return result[0]
		except Exception as e:
			log.error("SQL error in classification_count(): %s" % str(e))
			return 0
	
	def get_book_classifications(self, book_id):
		""" Return all classification associated with the specified book """
		try:
			return self._sql_to_dict("SELECT * FROM Classifications WHERE book_id=%s", book_id)
		except Exception as e:
			log.error("SQL error in get_book_classifications(): %s" % str(e))
			return None

	def _classification_level_to_name(self, level):
		level_map = {0:"overall", 1:"secondary", 2:"tertiary"}
		if not level in level_map:
			return None
		return level_map[level]

	def get_classification_names(self, level):
		""" Return back all unique classification names at the specified level"""
		class_names = []
		try:
			level_name = self._classification_level_to_name(level)
			sql = "SELECT DISTINCT " + level_name + " FROM Classifications ORDER BY " + level_name
			self.cursor.execute(sql)
			for row in self.cursor.fetchall():
				if not row[0] is None:
					class_names.append(row[0])
		except Exception as e:
			log.error("SQL error in get_classification_names(): %s" % str(e))
		return class_names

	def get_classification_counts(self, level, top=-1):
		""" Return back the number of books in each category at the specified level """
		class_counts = {}
		try:
			level_name = self._classification_level_to_name(level)
			sql = "SELECT %s, count(book_id) AS c FROM Classifications GROUP BY %s" % (level_name,level_name)
			if top == -1:
				self.cursor.execute(sql)
			else:
				sql += " LIMIT %s"
				self.cursor.execute(sql, top)
			for row in self.cursor.fetchall():
				if not row[0] is None:
					class_counts[row[0]] = row[1]
		except Exception as e:
			log.error("SQL error in get_top_classification_counts(): %s" % str(e))
		return class_counts

	def volume_count(self):
		""" Return the total number of volumes in the database """
		try:
			self.cursor.execute("SELECT COUNT(*) FROM Volumes")
			result = self.cursor.fetchone()
			return result[0]
		except Exception as e:
			log.error("SQL error in volume_count(): %s" % str(e))
			return 0

	def get_volumes(self):
		""" Return back all volumes in the database. """
		try:
			return self._bulk_sql_to_dict("SELECT * FROM Volumes")
		except Exception as e:
			log.error("SQL error in get_volumes(): %s" % str(e))
			return []

	def get_volume(self, volume_id):
		""" Return the details for the volume with the specified ID """
		try:
			return self._sql_to_dict("SELECT * FROM Volumes WHERE id=%s", volume_id)
		except Exception as e:
			log.error("SQL error in get_volume(): %s" % str(e))
			return None

	def get_book_volumes(self, book_id):
		""" Return the details for all volumes associated with the specified book """
		try:
			sql = "SELECT * FROM Volumes WHERE book_id=%s" 
			return self._bulk_sql_to_dict( sql, book_id )
		except Exception as e:
			log.error("SQL error in get_book_volumes(): %s" % str(e))
			return []

	def get_volume_metadata(self, volume_id):
		""" Return complete details for the volume with the specified ID, including
		information related to the associated book """
		vol = self.get_volume(volume_id)
		if vol is None:
			return None
		doc = self.get_book(vol["book_id"])
		if doc is None:
			return None
		# add/update volume-related fields
		doc["book_id"] = doc["id"]
		doc["id"] = vol["id"]
		doc["volume"] = vol["num"]
		doc["path"] = vol["path"]
		# add other detailed book metadata
		doc["authors"] = self.get_book_author_names(doc["book_id"])
		book_classifications = self.get_book_classifications(doc["book_id"])
		doc["category"] = book_classifications.get("overall", "Unknown")
		doc["classification"] = book_classifications.get("secondary", "Unknown")
		doc["subclassification"] = book_classifications.get("tertiary", "Unknown")
		doc["published_locations"] = self.get_published_locations(doc["book_id"])
		return doc

	def get_volumes_by_year(self, year):
		""" Return the details of all volumes associated with books published in the specified year """
		try:
			sql = "SELECT Volumes.* FROM Books, Volumes WHERE Volumes.book_id = Books.id and Books.year=%s"
			return self._bulk_sql_to_dict(sql, year)
		except Exception as e:
			log.error("SQL error in get_volumes_by_year(): %s" % str(e))
			return []

	def set_volume_word_count(self, volume_id, count):
		""" Update the word count for the volume with the specified identifier """
		try:
			sql = "UPDATE Volumes SET word_count=%s WHERE id=%s"
			self.cursor.execute(sql, (count, volume_id))
		except Exception as e:
			log.error("SQL error in set_volume_word_count(): %s" % str(e))
			return False
		return True

	def get_book_year_map(self):
		""" Return a dictionary which maps each book ID to its publication year """
		year_map = {}
		try:
			self.cursor.execute("SELECT year, id FROM Books")
			for row in self.cursor.fetchall():
				year_map[row[1]] = row[0]
		except Exception as e:
			log.error("SQL error in get_book_year_map(): %s" % str(e))
		return year_map

	def get_volume_year_map(self):
		""" Return a dictionary which maps each volume ID to its book's publication year """
		year_map = {}
		try:
			sql = "SELECT Books.year, Volumes.id FROM Books, Volumes WHERE Volumes.book_id = Books.id"
			self.cursor.execute(sql)
			for row in self.cursor.fetchall():
				year_map[row[1]] = row[0]
		except Exception as e:
			log.error("SQL error in get_volume_year_map(): %s" % str(e))
		return year_map

	def get_book_year_range(self):
		""" Return the earliest and latest publication years from all books in the collection """
		try:
			self.cursor.execute("SELECT min(year), max(year) FROM Books")
			result = self.cursor.fetchone()
			return (result[0], result[1])
		except Exception as e:
			log.error("SQL error in get_book_year_range(): %s" % str(e))
			return (0,0)		

	def get_book_author_names(self, book_id):
		""" Return the names of all authors for a given book """
		authors = []
		try:
			sql = "SELECT Authors.name FROM Authors, BookAuthors WHERE BookAuthors.book_id=%s AND Authors.id = BookAuthors.author_id"
			self.cursor.execute(sql, book_id)
			for row in self.cursor.fetchall():
				authors.append(row[0])
		except Exception as e:
			log.error("SQL error in get_book_author_names(): %s" % str(e))
		return authors

	def get_book_author_ids(self, book_id):
		""" Return the IDs of all authors for a given book """
		author_ids = []
		try:
			sql = "SELECT author_id FROM BookAuthors WHERE book_id=%s"
			self.cursor.execute(sql, book_id)
			for row in self.cursor.fetchall():
				author_ids.append( row[0] )
		except Exception as e:
			log.error("SQL error in get_book_author_ids(): %s" % str(e))
		return author_ids

	def get_author_book_ids(self, author_id):
		""" Return the IDs of all books by a given author """
		book_ids = []
		try:
			sql = "SELECT book_id FROM BookAuthors WHERE author_id=%s"
			self.cursor.execute(sql, author_id)
			for row in self.cursor.fetchall():
				book_ids.append( row[0] )
		except Exception as e:
			log.error("SQL error in get_author_book_ids(): %s" % str(e))
		return book_ids

	def get_author_volume_ids(self, author_id ):
		""" Return the IDs of all volumes by a given author """
		volume_ids = []
		try:
			sql = "SELECT Volumes.id FROM BookAuthors, Volumes WHERE BookAuthors.author_id = %s AND BookAuthors.book_id = Volumes.book_id"
			self.cursor.execute(sql, author_id)
			for row in self.cursor.fetchall():
				volume_ids.append( row[0] )
		except Exception as e:
			log.error("SQL error in get_author_volume_ids(): %s" % str(e))
		return volume_ids

	def get_author_name_map(self):
		""" Return a dictionary mapping each author ID to their corresponding name """
		name_map = {}
		try:
			sql = "SELECT name, id FROM Authors"
			self.cursor.execute(sql)
			for row in self.cursor.fetchall():
				name_map[row[1]] = row[0]
		except Exception as e:
			log.error("SQL error in get_author_name_map(): %s" % str(e))
		return name_map

	def author_gender_map(self):
		""" Return a dictionary mapping each author ID to their corresponding gender """
		gender_map = {}
		try:
			sql = "SELECT gender, id FROM Authors"
			self.cursor.execute(sql)
			for row in self.cursor.fetchall():
				gender_map[row[1]] = row[0]
		except Exception as e:
			log.error("SQL error in get_author_gender_map(): %s" % str(e))
		return gender_map

	def link_count(self):
		""" Return total number of links stored in the database """
		try:
			self.cursor.execute("SELECT COUNT(*) FROM BookLinks")
			result = self.cursor.fetchone()
			return result[0]
		except Exception as e:
			log.error("SQL error in link_count(): %s" % str(e))
			return 0

	def get_book_link_map(self):
		""" Return back all links associated with all books. """
		link_map = {}
		try:
			sql = "SELECT book_id,kind,url FROM BookLinks"
			self.cursor.execute(sql)
			for row in self.cursor.fetchall():
				if not row[0] in link_map:
					link_map[row[0]] = {}
				link_map[row[0]][row[1]] = row[2]
		except Exception as e:
			log.error("SQL error in get_book_link_map(): %s" % str(e))
		return link_map

	def add_ngram_count(self, ngram, year, count, collection_id):
		""" Add the count for the specific ngram for a given year """
		sql = "INSERT INTO Ngrams (ngram, year, count, collection) VALUES(%s,%s,%s,%s)"
		self.cursor.execute(sql, (ngram, year, count, collection_id))	

	def get_ngram_count(self, ngram, year_start, year_end, collection_id):
		""" Return the counts for the specified ngram within the given year range"""
		count_map = {}
		try:
			sql = "SELECT year,count FROM Ngrams WHERE year >= %s AND year <= %s AND ngram=%s AND collection=%s"		
			self.cursor.execute(sql, (year_start, year_end, ngram, collection_id))
			for row in self.cursor.fetchall():
				count_map[row[0]] = row[1]
		except Exception as e:
			log.error("SQL error in get_ngram_count(): %s" % str(e))
		return count_map			

	def total_ngram_count(self, collection_id):
		""" Return total number of ngrams stored in the database """
		try:
			self.cursor.execute("SELECT COUNT(*) FROM Ngrams WHERE collection=%s", collection_id)
			result = self.cursor.fetchone()
			return result[0]
		except Exception as e:
			log.error("SQL error in total_ngram_count(): %s" % str(e))
			return 0

	def add_volume_extract(self, volume_id, content):
		sql = "INSERT INTO VolumeExtracts (volume_id, content) VALUES(%s,%s)"
		self.cursor.execute(sql, (volume_id, content))	

	def get_volume_extract(self, volume_id):
		try:
			sql = "SELECT content FROM VolumeExtracts WHERE volume_id=%s"
			self.cursor.execute( sql, volume_id)
			result = self.cursor.fetchone()
			return result[0]
		except Exception as e:
			log.error("SQL error in get_volume_extract(): %s" % str(e))
			return None

	def extract_count(self):
		""" Return total number of volume extracts stored in the database """
		try:
			self.cursor.execute("SELECT COUNT(*) FROM VolumeExtracts")
			result = self.cursor.fetchone()
			return result[0]
		except Exception as e:
			log.error("SQL error in extract_count(): %s" % str(e))
			return 0
			
	def add_lexicon(self, name, user_id, description, classification, seed_words, ignore_words = []):
		""" Add a new word lexicon to the datbase """
		try:
			sql = "INSERT INTO Lexicons (name, user_id, description, class_name) VALUES (%s,%s,%s,%s)"
			self.cursor.execute(sql, (name, user_id, description, classification))
		except Exception as e:
			log.error("SQL error in add_lexicon(): %s" % str(e))
			return False
		# get the ID of the new lexicon
		try:
			self.cursor.execute("SELECT LAST_INSERT_ID()")
			result = self.cursor.fetchone()
			lexicon_id = result[0]
			log.info("Added lexicon %s (ID=%s)" % ( name, lexicon_id ) )
		except Exception as e:
			log.error("SQL error in add_lexicon(): %s" % str(e))
			return False
		# add the words
		for word in seed_words:
			word = word.strip().lower()
			if len(word) > 0:
				self.add_lexicon_word( lexicon_id, word )
		# add the ignores, if any
		for word in ignore_words:
			word = word.strip().lower()
			if len(word) > 0:
				self.add_lexicon_ignore( lexicon_id, word )
		return True

	def recommendation_count(self):
		try:
			self.cursor.execute("SELECT COUNT(*) FROM Recommendations")
			result = self.cursor.fetchone()
			return result[0]
		except Exception as e:
			log.error("SQL error in recommendation_count(): %s" % str(e))
			return 0

	def get_volume_recommendations(self, volume_id, max_recommendations=-1):
		""" Return back similar volumes to the specified volume"""
		recs = []
		try:
			sql = "SELECT rank_num, rec_volume_id FROM Recommendations WHERE volume_id=%s ORDER BY rank_num"
			if max_recommendations > 0:
				sql += " LIMIT %d" % max_recommendations
			self.cursor.execute(sql, volume_id)
			for row in self.cursor.fetchall():
				recs.append(row[1])
		except Exception as e:
			log.error("SQL error in get_volume_recommendations(): %s" % str(e))
		return recs

	def add_lexicon_word(self, lexicon_id, word):
		""" Add a word to an existing word lexicon """
		try:
			sql = "INSERT INTO LexiconWords (lexicon_id, word) VALUES(%s,%s)"
			self.cursor.execute(sql, (lexicon_id, word))
			return True
		except Exception as e:
			log.error("SQL error in add_lexicon_word(): %s" % str(e))
			return False

	def add_lexicon_ignore(self, lexicon_id, word):
		""" Add an 'ignore word' to an existing word lexicon """
		try:
			sql = "INSERT INTO LexiconIgnores (lexicon_id, word) VALUES(%s,%s)"
			self.cursor.execute(sql, (lexicon_id, word))
			return True
		except Exception as e:
			log.error("SQL error in add_lexicon_ignore(): %s" % str(e))
			return False

	def has_lexicon(self, lexicon_id):
		""" Check if the lexicon with the specified ID exists """
		return lexicon_id in self.get_lexicon_ids()

	def get_lexicon_ids(self):
		""" Return list of all valid lexicon IDs """
		lex_ids = []
		try:
			sql = "SELECT id FROM Lexicons"
			self.cursor.execute(sql)
			for row in self.cursor.fetchall():
				lex_ids.append( row[0] )
		except Exception as e:
			log.error("SQL error in get_lexicon_ids(): %s" % str(e))
		return lex_ids

	def get_lexicon_names(self):
		""" Return list of all valid lexicon names """
		lex_names = []
		try:
			sql = "SELECT name FROM Lexicons"
			self.cursor.execute(sql)
			for row in self.cursor.fetchall():
				lex_names.append( row[0] )
		except Exception as e:
			log.error("SQL error in get_lexicon_names(): %s" % str(e))
		return lex_names

	def get_all_lexicons(self):
		""" Return all lexicons currently stored in Curatr associated with all users """
		try:
			sql = "SELECT * FROM Lexicons ORDER BY name" 
			return self._bulk_sql_to_dict(sql)
		except Exception as e:
			log.error("SQL error in get_all_lexicons(): %s" % str(e))
			return []

	def get_user_lexicons(self, user_id):
		""" Return all lexicons currently stored in Curatr associated with the specified user """
		try:
			sql = "SELECT * FROM Lexicons WHERE user_id=%s ORDER BY name" 
			return self._bulk_sql_to_dict(sql, user_id)
		except Exception as e:
			log.error("SQL error in get_user_lexicons(): %s" % str(e))
			return []

	def get_lexicon(self, lexicon_id):
		""" Return the word lexicon with the specified ID """
		try:
			sql = "SELECT * FROM Lexicons WHERE id=%s" 
			return self._sql_to_dict(sql, lexicon_id)
		except Exception as e:
			log.error("SQL error in get_lexicon(): %s" % str(e))
			return None

	def get_lexicon_words(self, lexicon_id):
		""" Return all words in the lexicon with the specified ID """
		words = []
		try:
			sql = "SELECT word FROM LexiconWords WHERE lexicon_id=%s ORDER BY word"
			self.cursor.execute(sql, lexicon_id)
			for row in self.cursor.fetchall():
				words.append(row[0])
		except Exception as e:
			log.error("SQL error in get_lexicon_words(): %s" % str(e))
		return words

	def get_lexicon_ignores(self, lexicon_id):
		""" Return all 'ignore words' for the lexicon with the specified ID """
		ignores = []
		try:
			sql = "SELECT word FROM LexiconIgnores WHERE lexicon_id=%s ORDER BY word"
			self.cursor.execute(sql, lexicon_id)
			for row in self.cursor.fetchall():
				ignores.append( row[0] )
		except Exception as e:
			log.error("SQL error in get_lexicon_ignores(): %s" % str(e))
		return ignores

	def delete_lexicon(self, lexicon_id):
		""" Delete the word lexicon with the specified ID. """
		# remove the lexicon itself
		try:
			sql = "DELETE FROM Lexicons WHERE id = %s"
			self.cursor.execute(sql, lexicon_id)
		except Exception as e:
			log.error("SQL error in delete_lexicon(): %s" % str(e))
			return False
		# remove the words in the lexicon
		try:
			sql = "DELETE FROM LexiconWords WHERE lexicon_id = %s"
			self.cursor.execute(sql, lexicon_id)
		except Exception as e:
			log.error("SQL error in delete_lexicon(): %s" % str(e))		
			return False
		# remove the ignored words for the lexicon
		try:
			sql = "DELETE FROM LexiconIgnores WHERE lexicon_id = %s"
			self.cursor.execute(sql, lexicon_id)
		except Exception as e:
			log.error("SQL error in delete_lexicon(): %s" % str(e))
			return False
		return True

	def remove_lexicon_word(self, lexicon_id, word):
		""" Remove a single word from the lexicon with the specified ID """
		try:
			sql = "DELETE FROM LexiconWords WHERE lexicon_id = %s AND word = %s"
			self.cursor.execute(sql, (lexicon_id,word))
		except Exception as e:
			log.error("SQL error in remove_lexicon_word(): %s" % str(e))
			return False
		return True

	def add_subcorpus(self, meta, filename, user_id):
		try:
			# get the next corpus id
			corpus_id = self._get_next_id( "Corpora" )
			# add the corpus
			sql = "INSERT INTO Corpora (id, user_id, name, format, documents, filename) VALUES(%s,%s,%s,%s,%s,%s)"
			self.cursor.execute(sql, (corpus_id, user_id, meta["name"], meta["format"], meta["documents"], filename ) )	
		except Exception as e:
			log.error("SQL error when adding corpus in add_subcorpus(): %s" % str(e))
			return -1
		# add the metadata
		for key in meta:
			if key in [ "name", "format", "filename", "documents" ]:
				continue
			try:
				sql = "INSERT INTO CorpusMetadata (corpus_id, field, value) VALUES (%s,%s,%s)"
				self.cursor.execute(sql, (corpus_id, key, str(meta[key]) ) )
			except Exception as e:
				log.error("SQL error when adding metadata in add_subcorpus(): %s" % str(e))
				return -1
		return corpus_id

	def get_all_subcorpus_ids(self):
		corpus_ids = []
		try:
			sql = "SELECT id from Corpora"
			self.cursor.execute( sql )
			for row in self.cursor.fetchall():
				corpus_ids.append( row[0] )
		except Exception as e:
			log.error("SQL error in get_all_subcorpus_ids(): %s" % str(e))
		return corpus_ids

	def get_all_subcorpus_names(self):
		corpus_names = []
		try:
			sql = "SELECT name from Corpora"
			self.cursor.execute(sql)
			for row in self.cursor.fetchall():
				corpus_names.append( row[0] )
		except Exception as e:
			log.error("SQL error in get_all_subcorpus_names(): %s" % str(e))
		return corpus_names

	def get_all_subcorpora(self):
		try:
			sql = "SELECT * FROM Corpora ORDER BY name" 
			return self._bulk_sql_to_dict(sql)
		except Exception as e:
			log.error("SQL error in get_all_subcorpora(): %s" % str(e))
			return []

	def get_user_subcorpora(self, user_id):
		try:
			sql = "SELECT * FROM Corpora WHERE user_id=%s ORDER BY name" 
			return self._bulk_sql_to_dict(sql, user_id)
		except Exception as e:
			log.error("SQL error in get_user_subcorpora(): %s" % str(e))
			return []

	def get_subcorpus(self, subcorpus_id):
		try:
			sql = "SELECT * FROM Corpora WHERE id=%s" 
			return self._sql_to_dict(sql, subcorpus_id)
		except Exception as e:
			log.error("SQL error in get_subcorpus(): %s" % str(e))
			return []

	def get_subcorpus_metadata(self, subcorpus_id):
		""" Return the metadata associated with the sub-corpus with the specified ID """
		properties = {}
		try:
			sql = "SELECT field, value FROM CorpusMetadata WHERE corpus_id=%s" 
			self.cursor.execute(sql, subcorpus_id)
			for row in self.cursor.fetchall():
				properties[row[0]] = row[1]
		except Exception as e:
			log.error("SQL error in get_subcorpus_metadata(): %s" % str(e))
			return {}
		return properties

	def clear_cache_tables(self):
		""" Delete any tables storing cached information and then re-create them """
		previous_tables = self._get_existing_tables()
		log.info("Previous tables: %s" % previous_tables)
		for table_name in cache_tables:
			# delete the old one
			if table_name in previous_tables:
				log.info("Dropping existing table %s" % table_name)
				self.cursor.execute("DROP TABLE %s" % table_name)
			# create the new one
			log.info("Creating new table %s ..." % table_name)
			self.cursor.execute(sql_statements["Table%s" % table_name])
			log.info("Columns: %s" % self._get_table_columns(table_name))
		# check tables now
		tables = self._get_existing_tables()
		log.info("Current tables: %s" % tables)

	def add_cached_author_details(self, author_id, author_name, sort_name, start_year, end_year, count):
		sql = "INSERT INTO CachedAuthors (author_id, author_name, sort_name, start_year, end_year, count) VALUES(%s,%s,%s,%s,%s,%s)"
		self.cursor.execute(sql, (author_id, author_name, sort_name, start_year, end_year, count))	

	def get_cached_author(self, author_id):
		""" Return cached details for the author with the specified ID """
		try:
			return self._sql_to_dict("SELECT * FROM CachedAuthors WHERE author_id=%s", author_id)
		except Exception as e:
			log.error("SQL error in get_cached_author(): %s" % str(e))
			return None

	def get_cached_author_details(self):
		try:
			return self._bulk_sql_to_dict("SELECT * FROM CachedAuthors")
		except Exception as e:
			log.error("SQL error in get_cached_author_details(): %s" % str(e))
			return []

	def add_cached_book_years(self, year, count):
		sql = "INSERT INTO CachedBookYears (year, count) VALUES(%s,%s)"
		self.cursor.execute(sql, (year, count))	

	def get_cached_book_years(self, year_start, year_end):
		count_map = {}
		try:
			sql = "SELECT year,count FROM CachedBookYears WHERE year >= %s AND year <= %s"		
			self.cursor.execute(sql, (year_start, year_end))
			for row in self.cursor.fetchall():
				count_map[row[0]] = row[1]
		except Exception as e:
			log.error("SQL error in get_cached_book_years(): %s" % str(e))
		return count_map

	def get_cached_volume_years(self, year_start, year_end):
		count_map = {}
		try:
			sql = "SELECT year,count FROM CachedVolumeYears WHERE year >= %s AND year <= %s"		
			self.cursor.execute(sql, (year_start, year_end))
			for row in self.cursor.fetchall():
				count_map[row[0]] = row[1]
		except Exception as e:
			log.error("SQL error in get_cached_volume_years(): %s" % str(e))
		return count_map

	def add_cached_volume_years(self, year, count):
		sql = "INSERT INTO CachedVolumeYears (year, count) VALUES(%s,%s)"
		self.cursor.execute(sql, (year, count))	

	def add_cached_classification_count(self, class_name, level, count):
		sql = "INSERT INTO CachedClassificationCounts (class_name, level, count) VALUES(%s,%s,%s)"
		self.cursor.execute(sql, (class_name, level, count))

	def add_cached_place_count(self, location, count):
		sql = "INSERT INTO CachedPlaceCounts (location, count) VALUES(%s,%s)"
		self.cursor.execute(sql, (location, count))	

	def add_cached_country_count(self, location, count):
		sql = "INSERT INTO CachedCountryCounts (location, count) VALUES(%s,%s)"
		self.cursor.execute(sql, (location, count))	

	def add_user(self, email, hashed_passwd):
		""" Add a new user to the database. """
		try:
			# get the next user id
			user_id = self._get_next_id("Users")
			# add the user
			sql = "INSERT INTO Users (email, hash) VALUES(%s,%s)"
			self.cursor.execute(sql, (email, hashed_passwd) )
		except Exception as e:
			log.error("SQL error in add_user(): %s" % str(e))
			return -1
		return user_id

	def has_user_email(self, email):
		""" Check if a user with the specified email address exists. """
		try:
			sql = "SELECT * FROM Users WHERE email=%s" 
			self.cursor.execute(sql, email)
			if self.cursor.fetchone():
				return True
			return False
		except Exception as e:
			log.error("SQL error in has_user_email(): %s" % str(e))
			return False

	def get_all_users(self):
		""" Return list of dictionaries of all user details. """
		try:
			users = []
			for d in self._bulk_sql_to_dict( "SELECT * FROM Users" ):
				users.append(dict_to_user(d))
			return users
		except Exception as e:
			log.error("SQL error in get_users(): %s" % str(e))
			return []

	def user_count(self):
		""" Return the number of users registered on the system. """
		try:
			self.cursor.execute("SELECT COUNT(id) FROM Users")
			result = self.cursor.fetchone()
			return result[0]
		except Exception as e:
			log.error("SQL error in user_count(): %s" % str(e))
			return 0

	def get_user_by_id(self, user_id):
		""" Return details for the user with the specified ID. """
		try:
			return dict_to_user(self._sql_to_dict("SELECT * FROM Users WHERE id=%s", user_id))
		except Exception as e:
			log.error("SQL error in get_user_by_id(): %s" % str(e))
			return None

	def get_user_by_email(self, email):
		""" Return details for the user with the specified email address. """
		try:
			return dict_to_user(self._sql_to_dict("SELECT * FROM Users WHERE email=%s", email))
		except Exception as e:
			log.error("SQL error in get_user_by_email(): %s" % str(e))
			return None

	def update_user_password(self, user_id, hashed_passwd):
		""" Update password for the user with the specified ID. """
		try:
			sql = "UPDATE Users SET hash=%s WHERE id=%s"
			self.cursor.execute(sql, (hashed_passwd, user_id))
		except Exception as e:
			log.error("SQL error in update_user_password(): %s" % str(e))
			return False
		return True

	def record_login(self, user_id):
		""" Update a user's last login to the current date/time and increment their login count """
		# update the date
		try:
			sql = "UPDATE Users SET last_login=NOW() WHERE id=%s"
			self.cursor.execute(sql, user_id)
		except Exception as e:
			log.error("SQL error in update_user_last_login(): %s" % str(e))
			return False
		# update the login count
		try:
			sql = "UPDATE Users SET num_logins=num_logins+1 WHERE id=%s"
			self.cursor.execute(sql, user_id)
		except Exception as e:
			log.error("SQL error in update_user_last_login(): %s" % str(e))
			return False
		return True

	def log_query(self, user_id, query):
		""" Log a user query in the database. """
		try:
			sql = "INSERT INTO QueryLog (user_id, query) VALUES(%s,%s)"
			self.cursor.execute(sql, (user_id, query))
		except Exception as e:
			log.error("SQL error in log_query(): %s" % str(e))
			return False
		return True
	
	def delete_user(self, user_id):
		""" Delete the user with the specified ID. """
		try:
			sql = "DELETE FROM Users WHERE id = %s"
			self.cursor.execute(sql, user_id)
		except Exception as e:
			log.error("SQL error in delete_user_by_id(): %s" % str(e))
			return False
		return True

	def add_bookmark(self, user_id, volume_id, segment_id=None):
		""" Add a new bookmark for the specified user and volume/segment """
		try:
			sql = "INSERT INTO Bookmarks (user_id, volume_id, segment_id) VALUES(%s,%s,%s)"
			self.cursor.execute(sql, (user_id, volume_id, segment_id))		
		except Exception as e:
			log.error("SQL error in add_bookmark(): %s" % str(e))
			return False
		return True

	def delete_bookmark(self, user_id, volume_id, segment_id=None):
		""" Delete an existing bookmark for the specified user and volume/segment """
		try:
			if segment_id is None:
				sql = "DELETE FROM Bookmarks WHERE user_id=%s AND volume_id=%s AND segment_id IS NULL"
				self.cursor.execute(sql, (user_id, volume_id) )		
			else:
				sql = "DELETE FROM Bookmarks WHERE user_id=%s AND volume_id=%s AND segment_id=%s"
				self.cursor.execute(sql, (user_id, volume_id, segment_id) )		
		except Exception as e:
			log.error("SQL error in delete_bookmark(): %s" % str(e))
			return False
		return True

	def delete_bookmark_by_bookmark_id(self, bookmark_id, user_id):
		""" Delete an existing bookmark based on its ID """
		try:
			sql = "DELETE FROM Bookmarks WHERE id=%s AND user_id=%s"
			self.cursor.execute(sql, (bookmark_id, user_id) )		
		except Exception as e:
			log.error("SQL error in delete_bookmark_by_bookmark_id(): %s" % str(e))
			return False
		return True

	def has_volume_bookmark(self, user_id, volume_id):
		""" Check if a volume has been bookmarked by a given user. """
		try:
			sql = "SELECT * from Bookmarks WHERE user_id=%s AND volume_id=%s AND segment_id IS NULL" 
			# note: segment ID is NULL for a volume
			self.cursor.execute(sql, (user_id, volume_id))
			if self.cursor.fetchone():
				return True
			return False
		except Exception as e:
			log.error("SQL error in has_volume_bookmark(): %s" % str(e))
			return False

	def has_segment_bookmark(self, user_id, volume_id, segment_id):
		""" Check if a segment has been bookmarked by a given user. """
		try:
			sql = "SELECT * from Bookmarks WHERE user_id=%s AND volume_id=%s AND segment_id=%s" 
			self.cursor.execute(sql, (user_id, volume_id, segment_id))
			if self.cursor.fetchone():
				return True
			return False
		except Exception as e:
			log.error("SQL error in has_segment_bookmark(): %s" % str(e))
			return False

	def volume_bookmark_count(self, user_id):
		try:
			sql = "select COUNT(ID) FROM Bookmarks WHERE USER_ID=%s AND ISNULL(segment_id)"
			self.cursor.execute(sql, user_id)
			result = self.cursor.fetchone()
			return result[0]
		except Exception as e:
			log.error("SQL error in volume_bookmark_count(): %s" % str(e))
			return 0
		
	def segment_bookmark_count(self, user_id):
		try:
			sql = "select COUNT(ID) FROM Bookmarks WHERE USER_ID=%s AND segment_id IS NOT NULL"
			self.cursor.execute(sql, user_id)
			result = self.cursor.fetchone()
			return result[0]
		except Exception as e:
			log.error("SQL error in volume_bookmark_count(): %s" % str(e))
			return 0

	def get_volume_bookmarks(self, user_id):
		try:
			sql = "SELECT * FROM Bookmarks WHERE user_id=%s AND ISNULL(segment_id) ORDER BY created_at DESC" 
			return self._bulk_sql_to_dict(sql, user_id)
		except Exception as e:
			log.error("SQL error in get_volume_bookmarks(): %s" % str(e))
			return []

	def get_segment_bookmarks(self, user_id):
		try:
			sql = "SELECT * FROM Bookmarks WHERE user_id=%s AND segment_id IS NOT NULL ORDER BY created_at DESC" 
			return self._bulk_sql_to_dict(sql, user_id)
		except Exception as e:
			log.error("SQL error in get_segment_bookmarks(): %s" % str(e))
			return []
		
		