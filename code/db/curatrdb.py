import time
import logging as log
from db.util import GenericDB
from db.booksql import sql_statements

# --------------------------------------------------------------

# core_tables = [ "Users", "Books", "Authors", "BookAuthors", "Volumes", "Classifications", "Lexicons", "LexiconWords", "LexiconIgnores", "Corpora", "CorpusMetadata", 
# 	"Recommendations", "MudiesMatches", "Ngrams", "VolumeExtracts", "VolumeWordCounts", "VolumeFileSizes" ]
core_tables = ["Books", "Authors", "BookAuthors", "BookPublished", "BookShelfmarks",
	"Volumes", "BookLinks", "Classifications", "Users", "Recommendations", "Ngrams"]

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
		sql = "INSERT INTO BookPublished (book_id,kind,location) VALUES(%s,%s,%s)"
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

	def published_count(self):
		try:
			self.cursor.execute("SELECT COUNT(*) FROM BookPublished")
			result = self.cursor.fetchone()
			return result[0]
		except Exception as e:
			log.error("SQL error in published_count(): %s" % str(e))
			return 0

	def classification_count(self):
		try:
			self.cursor.execute("SELECT COUNT(*) FROM Classifications")
			result = self.cursor.fetchone()
			return result[0]
		except Exception as e:
			log.error("SQL error in classification_count(): %s" % str(e))
			return 0

	def link_count(self):
		try:
			self.cursor.execute("SELECT COUNT(*) FROM Classifications")
			result = self.cursor.fetchone()
			return result[0]
		except Exception as e:
			log.error("SQL error in link_count(): %s" % str(e))
			return 0

	def recommendation_count(self):
		try:
			self.cursor.execute("SELECT COUNT(*) FROM Recommendations")
			result = self.cursor.fetchone()
			return result[0]
		except Exception as e:
			log.error("SQL error in recommendation_count(): %s" % str(e))
			return 0

	def volume_count(self):
		try:
			self.cursor.execute("SELECT COUNT(*) FROM Volumes")
			result = self.cursor.fetchone()
			return result[0]
		except Exception as e:
			log.error("SQL error in volume_count(): %s" % str(e))
			return 0

	def get_volumes(self):
		try:
			return self._bulk_sql_to_dict("SELECT * FROM Volumes")
		except Exception as e:
			log.error("SQL error: %s" % str(e))
			return []

	def get_volume(self, volume_id):
		""" Return the details for the volume with the specified ID """
		try:
			return self._sql_to_dict("SELECT * FROM Volumes WHERE id=%s", volume_id)
		except Exception as e:
			log.error("SQL error: %s" % str(e))
			return None

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
			log.error( "SQL error in set_volume_word_count(): %s" % str(e) )
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

	def get_book_year_range(self):
		""" Return the earliest and latest publication years from all books in the collection """
		try:
			self.cursor.execute("SELECT min(year), max(year) FROM Books")
			result = self.cursor.fetchone()
			return (result[0], result[1])
		except Exception as e:
			log.error("SQL error in get_book_year_range(): %s" % str(e))
			return (0,0)		

	def add_ngram_count(self, ngram, year, count):
		""" Add the count for the specific ngram for a givne year"""
		sql = "INSERT INTO Ngrams (ngram, year, count) VALUES(%s,%s,%s)"
		self.cursor.execute(sql, (ngram, year, count) )	

	def get_ngram_count(self, ngram, year_start, year_end):
		""" Return the counts for the specified ngram within the given year range"""
		count_map = {}
		try:
			sql = "SELECT year,count FROM Ngrams WHERE year >= %s AND year <= %s AND ngram=%s"		
			self.cursor.execute(sql, (year_start, year_end, ngram) )
			for row in self.cursor.fetchall():
				count_map[row[0]] = row[1]
		except Exception as e:
			log.error("SQL error in get_ngram_count(): %s" % str(e))
		return count_map			

	def total_ngram_count(self):
		""" Return total number of ngrams stored in the database """
		try:
			self.cursor.execute("SELECT COUNT(*) FROM Ngrams")
			result = self.cursor.fetchone()
			return result[0]
		except Exception as e:
			log.error("SQL error in total_ngram_count(): %s" % str(e))
			return 0
