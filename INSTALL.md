# Installation

## Python Requirements

Curatr requires Python 3.8 or later. The following Python packages must be installed:

```
flask
flask-login
dash
dash-bootstrap-components
dash-cytoscape
pymysql
python-solrclient
pandas
numpy
scikit-learn
gensim
nltk
networkx
ftfy
passlib
```

You can install these packages using pip:

```pip install flask flask-login dash dash-bootstrap-components dash-cytoscape pymysql python-solrclient pandas numpy scikit-learn gensim nltk networkx ftfy passlib```

## Core Directory Setup

The Curatr *core* directory should contain all of the key required data for Curatr, with the following sub-directories:
- metadata: Stores all of the key metadata for the British Library Digital Collection (i.e. book-metadata.json, book-classifications.csv, book-links.csv, book-volumes.csv).
- fulltext: Stores all of the individual volume plain-text files for the British Library Digital Collection (e.g. fulltext/0139/013952747_01_text.txt).
- embeddings: Stores word2vec embedding model files for word recommendations and semantic networks (e.g. bl-w2v-cbow-d100.bin).
- export: Stores sub-corpora created by Curatr users. This directory will initially be empty.

To recreate all of the key metadata from the original raw data files from the British Library and UCD, run the script below. Note this should not be required. 

```python code/create-metadata.py core all```

## Embedding Setup

For word recommendations and semantic networks, run the commands below to create word2vec embeddings from the plain text files of the British Library Digital Collection. Note that this will take some time.

```python code/create-embedding.py core```

```python code/create-embedding.py core -c fiction```

```python code/create-embedding.py core -c nonfiction```

## Database Setup

Curatr has been tested with MySQL 8.0.x. Ensure that the file *core/config.ini* contains the correct local MySQL database settings, including *hostname*, *port*, *user* and *pass*. Next, create a new empty database named *curatr* in your MySQL database. Once this is complete, to create the required tables, run the script below. Note that this will take some time.

```python code/create-db.py core all```

## Recommendation Setup

To create recommendations, we run the following process. Again this will take some time.

```python code/create-recs.py core```

## Ngram Setup

For ngram frequency counts, we need to run the following to process the collection and update the database. Note that this will take some time. 

```python code/create-ngrams.py core```

```python code/create-ngrams.py core -c fiction```

```python code/create-ngrams.py core -c nonfiction```

If we want to count both unigrams and bigrams, we require an additional argument:

```python code/create-ngrams.py core -b```

```python code/create-ngrams.py core -b -c fiction```

```python code/create-ngrams.py core -b -c nonfiction```

## Database Indexing

To improve performance, we then create a number of indexes on the MySQL database tables:

```python code/create-db.py core index```

## Search Setup

Firstly, install Solr 9 from [Apache Solr](https://solr.apache.org) which requires Java 11 or later (e.g. [OpenJDK](https://jdk.java.net/)). Once Solr is installed and running, create two core directories in the solr directory, one for indexing volumes and one for indexing segments. The `solr` directory in the Curatr Github repository provides schema files for these cores:

- `solr/blvolumes/managed-schema.xml`
- `solr/blsegments/managed-schema.xml`

Then from the Solr home directory register the two Solr cores:

```./bin/solr create -c blvolumes ```

```./bin/solr create -c blsegments ```

At this stage we can index the full text of the British Library Digital Collection, for both volumes and segments:

```python code/create-search.py core ```

```python code/create-search.py --segment core ```

## Web Server Setup

The recommended web server setup is to use Apache2 with mod_wsgi to forward requests to the Curatr Python web application.

1. Install Apache2 and mod_wsgi for Python 3.
2. Copy the sample WSGI file `code/curatr.wsgi` to your deployment location.
3. Edit the WSGI file to set the following paths:
   - `dir_curatr`: Root directory of the Curatr installation
   - `dir_code`: Path to the code directory
   - `dir_core`: Path to the core configuration directory
   - `dir_log`: Path to the log directory
4. Configure Apache2 to use the WSGI file. 

## Curatr Configuration File

In the core directory, rename the empty configuration file `sample-config.ini` to `config.ini`. The key configuration settings below should be modified.

In the `app` section:

- hostname: Name of host running Flask web application. The default hostname is localhost.
- port: Port number for the Flask web application. The default port is 5000.
- secret_key: The key used by Flask for cookies. This should be set once initially and then only known to the application.
- prefix: The prefix for dynamic pages, if the web application is being delivered on a particular path (e.g. by Apache2). By default there is no prefix.
- staticprefix: The prefix for static pages, if the web application is being delivered on a particular path (e.g. by Apache2). By default there is no prefix.
- apiprefix: The prefix for API queries, if the web application is being delivered on a particular path (e.g. by Apache2). By default there is no prefix.
- require_login: Whether users must log in to access the application. The default is True.
- default_embedding: The identifier of the default word embedding model to use. The default is "all".
- embedding_preload: Whether to preload the default embedding model at startup. The default is False.

In the `db` section:

- hostname: Name of host of the MySQL database server. The default hostname is localhost.
- port: Port number for the MySQL database server. The default port is 3306.
- user: MySQL username.
- pass: MySQL password.
- dbname: The database to use for storing Curatr-based data. Default database name is "curatr".
- pool_size: Number of simultaneous database connections to maintain in the database pool. Typically 5 to 20.

In the `solr` section:

- enabled: Whether Solr search is enabled. The default is True.
- hostname: Name of host of the Solr search server. The default hostname is localhost.
- port: Port number for the Solr search server. The default port is 8983.
- core_volumes: Name of the Solr core for indexing volumes. The default is "blvolumes".
- core_segments: Name of the Solr core for indexing segments. The default is "blsegments".
- segment_size: The size of text segments in characters. The default is 2000.

In the `embeddings` section:

This section maps embedding identifiers to their corresponding model files in the embeddings directory. For example:
- all: The embedding model trained on the entire collection (e.g. bl-w2v-cbow-d100.bin).
- fiction: The embedding model trained on fiction texts only (e.g. blfiction-w2v-cbow-d100.bin).
- nonfiction: The embedding model trained on non-fiction texts only (e.g. blnonfiction-w2v-cbow-d100.bin).

In the `ngrams` section:

- default_query: Default query terms for the ngram viewer, comma-separated.
- default_year_min: Default minimum year for ngram queries.
- default_year_max: Default maximum year for ngram queries.

In the `networks` section:

- default_query: Default query terms for the network viewer, comma-separated.
- default_k: Default number of nearest neighbors to display. The default is 10.
- seed_font_size: Font size for seed words in the network visualisation.
- neighbor_font_size: Font size for neighbor words in the network visualisation.
- seed_node_size: Node size for seed words in the network visualisation.
- neighbor_node_size: Node size for neighbor words in the network visualisation.


## User Setup

Before starting Curatr, you need to create at least one user account. Use the user management tool:

```python code/tool-users.py core add```

This will prompt you to enter an email address and password for the new user. The tool supports the following actions:

- `add`: Create a new user account
- `list`: List all existing users
- `remove`: Delete a user account
- `password`: Change a user's password
- `verify`: Verify a user's password
- `role`: Change a user's role (admin, user, or guest)
- `lexicons`: List lexicons for each user
- `corpora`: List sub-corpora for each user

## Starting Curatr

To start the Curatr web application, run the below, where the only argument to the script is the core directory path:

```python code/curatr.py core```

The application will be available at http://localhost:5000 by default (or the hostname and port configured in config.ini).
