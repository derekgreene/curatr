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
	title_full VARCHAR(1000) CHARACTER SET utf8 COLLATE utf8_general_ci DEFAULT "Untitled",
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

sql_statements["TableBookPublished"] = """
CREATE TABLE BookPublished (
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
	count INT NOT NULL
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

sql_statements["TableVolumeExtracts"] = """
CREATE TABLE VolumeExtracts (
	volume_id VARCHAR(12) NOT NULL,
	content VARCHAR(460) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL
);
"""