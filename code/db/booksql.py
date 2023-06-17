sql_statements = {}

# --------------------------------------------------------------
# CORE TABLES
# --------------------------------------------------------------

sql_statements["TableBooks"] = """
CREATE TABLE Books (
	id VARCHAR(12) NOT NULL,
	year SMALLINT NOT NULL,
	decade SMALLINT NOT NULL,
	title VARCHAR(1000) CHARACTER SET utf8 COLLATE utf8_general_ci DEFAULT "Untitled",
	title_full VARCHAR(2000) CHARACTER SET utf8 COLLATE utf8_general_ci DEFAULT "Untitled",
	authors_full VARCHAR(2000) CHARACTER SET utf8 COLLATE utf8_general_ci DEFAULT NULL,
	edition VARCHAR(1000) CHARACTER SET utf8 COLLATE utf8_general_ci DEFAULT NULL,
	resource_type VARCHAR(100) CHARACTER SET utf8 COLLATE utf8_general_ci DEFAULT NULL,
	publisher VARCHAR(300) CHARACTER SET utf8 COLLATE utf8_general_ci  DEFAULT NULL,
	publisher_full VARCHAR(1000) CHARACTER SET utf8 COLLATE utf8_general_ci  DEFAULT NULL,
	physical_descr VARCHAR(300) CHARACTER SET utf8 COLLATE utf8_general_ci DEFAULT NULL,
	volumes SMALLINT DEFAULT 1,
	bl_record_id BIGINT DEFAULT 0,
	PRIMARY KEY (id)
);
"""

sql_statements["TableAuthors"] = """
CREATE TABLE Authors (
	id MEDIUMINT NOT NULL,
	name VARCHAR(255) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
	gender VARCHAR(20) DEFAULT "Unknown",
	PRIMARY KEY (id)
);
"""

sql_statements["TableBookAuthors"] = """
CREATE TABLE BookAuthors (
	book_id VARCHAR(12) NOT NULL,
	author_id MEDIUMINT NOT NULL
);
"""

sql_statements["TableBookLocations"] = """
CREATE TABLE BookLocations (
	book_id VARCHAR(12) NOT NULL,
	kind VARCHAR(20) NOT NULL,
	location VARCHAR(300) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL
);
"""

sql_statements["TableBookShelfmarks"] = """
CREATE TABLE BookShelfmarks (
	book_id VARCHAR(12) NOT NULL,
	shelfmark VARCHAR(255) NOT NULL
);
"""

sql_statements["TableVolumes"] = """
CREATE TABLE Volumes (
	id VARCHAR(20) NOT NULL,
	num SMALLINT NOT NULL,
	total SMALLINT NOT NULL,
	book_id VARCHAR(12) NOT NULL,
	path VARCHAR(2083) DEFAULT NULL,
	word_count BIGINT DEFAULT 0,
	PRIMARY KEY (id)
);
"""

sql_statements["TableClassifications"] = """
CREATE TABLE Classifications (
	book_id VARCHAR(12) NOT NULL,
	overall VARCHAR(255) DEFAULT NULL,
	secondary VARCHAR(255) DEFAULT NULL,
	tertiary VARCHAR(255) DEFAULT NULL
);
"""

sql_statements["TableBookLinks"] = """
CREATE TABLE BookLinks (
	book_id VARCHAR(12) NOT NULL,
	kind VARCHAR(20) NOT NULL,
	url VARCHAR(2083) NOT NULL
);
"""

sql_statements["TableRecommendations"] = """
CREATE TABLE Recommendations (
	volume_id VARCHAR(20) NOT NULL,
	rec_volume_id VARCHAR(20) NOT NULL,
	rank_num SMALLINT NOT NULL
);
"""

sql_statements["TableNgrams"] = """
CREATE TABLE Ngrams (
	ngram VARCHAR(100) CHARACTER SET utf8 COLLATE utf8_general_ci DEFAULT NULL,
	year SMALLINT NOT NULL,
	count INT NOT NULL,
	collection VARCHAR(20) DEFAULT 'all'
);
"""

sql_statements["TableVolumeExtracts"] = """
CREATE TABLE VolumeExtracts (
	volume_id VARCHAR(12) NOT NULL,
	content VARCHAR(460) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL
);
"""

sql_statements["TableUsers"] = """
CREATE TABLE Users (
	id INT AUTO_INCREMENT NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	hash VARCHAR(512) NOT NULL, 
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	num_logins MEDIUMINT DEFAULT 0,
	admin BOOLEAN DEFAULT FALSE,
	PRIMARY KEY (id)
);
"""

sql_statements["TableBookmarks"] = """
CREATE TABLE Bookmarks (
	id INT NOT NULL AUTO_INCREMENT,
	user_id INT NOT NULL,
	volume_id VARCHAR(12) NOT NULL,
	segment_id VARCHAR(30) DEFAULT NULL,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id)
);
"""

# --------------------------------------------------------------
# LEXICON & CORPORA TABLES
# --------------------------------------------------------------

sql_statements["TableLexicons"] = """
CREATE TABLE Lexicons (
	id INT NOT NULL AUTO_INCREMENT,
	user_id INT NOT NULL,
	name VARCHAR(255) NOT NULL,
	description VARCHAR(3000) DEFAULT NULL,
	class_name VARCHAR(255) NOT NULL,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id)
);
"""

sql_statements["TableLexiconWords"] = """
CREATE TABLE LexiconWords (
	lexicon_id int NOT NULL,
	word VARCHAR(100) CHARACTER SET utf8 COLLATE utf8_general_ci DEFAULT NULL
);
"""

sql_statements["TableLexiconIgnores"] = """
CREATE TABLE LexiconIgnores (
	lexicon_id int NOT NULL,
	word VARCHAR(100) CHARACTER SET utf8 COLLATE utf8_general_ci DEFAULT NULL
);
"""

sql_statements["TableCorpora"] = """
CREATE TABLE Corpora (
	id int NOT NULL AUTO_INCREMENT,
	user_id INT NOT NULL,
	name VARCHAR(255) NOT NULL,
	format VARCHAR(255) NOT NULL,
	documents int NOT NULL,
	filename VARCHAR(300)  NOT NULL,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id)
);
"""

sql_statements["TableCorpusMetadata"] = """
CREATE TABLE CorpusMetadata (
	corpus_id int NOT NULL,
	field VARCHAR(100) NOT NULL,
	value VARCHAR(3000)  CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL
);
"""

# --------------------------------------------------------------
# CACHE TABLES
# --------------------------------------------------------------

sql_statements["TableCachedAuthors"] = """
CREATE TABLE CachedAuthors (
	author_id MEDIUMINT NOT NULL,
	author_name VARCHAR(500) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
	sort_name VARCHAR(500) CHARACTER SET utf8 COLLATE utf8_general_ci DEFAULT NULL,
	start_year SMALLINT NOT NULL,
	end_year SMALLINT NOT NULL,
	count INT NOT NULL,
	PRIMARY KEY (author_id)
);
"""

sql_statements["TableCachedBookYears"] = """
CREATE TABLE CachedBookYears (
	year SMALLINT NOT NULL,
	count INT NOT NULL,
	PRIMARY KEY (year)
);
"""

sql_statements["TableCachedVolumeYears"] = """
CREATE TABLE CachedVolumeYears (
	year SMALLINT NOT NULL,
	count INT NOT NULL,
	PRIMARY KEY (year)
);
"""

sql_statements["TableCachedPlaceCounts"] = """
CREATE TABLE CachedPlaceCounts (
	location VARCHAR(250) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
	count INT NOT NULL
);
"""

sql_statements["TableCachedCountryCounts"] = """
CREATE TABLE CachedCountryCounts (
	location VARCHAR(250) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
	count INT NOT NULL
);
"""

sql_statements["TableCachedClassificationCounts"] = """
CREATE TABLE CachedClassificationCounts (
	class_name VARCHAR(255) NOT NULL,
	level SMALLINT NOT NULL,
	count INT NOT NULL
);
"""

# --------------------------------------------------------------
# TABLE INDEXING
# --------------------------------------------------------------

sql_indexing_statements = {}
sql_indexing_statements["ngrams1"] = "CREATE INDEX ngrams_ngram ON Ngrams(ngram);"
sql_indexing_statements["ngrams2"] = "CREATE INDEX ngrams_ngram_year ON Ngrams(ngram,year,collection);"
sql_indexing_statements["volumes1"] = "CREATE INDEX volumes_book on Volumes(book_id);"
sql_indexing_statements["volumes2"] = "CREATE INDEX cached_volume_years_year ON CachedVolumeYears(year);"
sql_indexing_statements["books1"] = "CREATE INDEX cached_book_years_year ON CachedBookYears(year);"
sql_indexing_statements["books2"] = "CREATE INDEX bookauthors_book_author on BookAuthors(book_id,author_id);"
sql_indexing_statements["recommendations"] = "CREATE INDEX recommendations_volume_rec on Recommendations(volume_id,rec_volume_id);"
