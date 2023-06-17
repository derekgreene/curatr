# Installation

## Core Directory Setup

The *core* directory contains all of the key required data for Curatr. It has the following sub-directories:
- metadata: Stores all of the key metadata for the British Library Digital Collection.
- fulltext: Stores all of the individual volume plain-text files for the British Library Digital Collection.
- export: Stores sub-corpora created by Curatr users. This directory will initially be empty.

To recreate all of the key metadata from the original raw data files from the British Library and UCD, run the script below. Note this should not be required. 

```python code/create-metadata.py core all```

## Embedding Setup

For word recommendations and semantic networks, run the commands below to create word2vec embeddings from the plain text files of the British Library Digital Collection. Note that this will take some time.

```python code/create-embedding.py core```

```python code/create-embedding.py core -c fiction```

```python code/create-embedding.py core -c nonfiction```

## Database Setup

Ensure that the file *core/config.ini* contains the correct local MySQL database settings, including *hostname*, *port*, *user* and *pass*. Next create a new empty database named *curatr* should be created in your MySQL database. Once this is complete, to create the required tables, run the script below. Note that this will take some time.

```python code/create-db.py core all```

# Recommendation Setup

To create recommendations, we run the following process. Again this will take some time.

```python code/create-recs.py core```

## Ngram Setup

For ngram frequency counts, we need to run the following to process the collection and update the database. Note that this will take some time.

```python code/create-ngrams.py core```

```python code/create-ngrams.py core -c fiction```

```python code/create-ngrams.py core -c nonfiction```

## Database Indexing

To improve performance, we then create a number of indexes on the MySQL database tables:

```python code/create-db.py core index```

## Search Setup

Firstly, install Solr 9 from [https://solr.apache.org](here) which requires Java (e.g. [https://jdk.java.net/](OpenJDK)). Once Solr is installed and running, create two core directories in the solr directory, one for indexing volumes and one for indexing segments. The `solr` directory in the Curatr Github repository provides schema files for these cores:

- `solr/blvolumes/managed-schema.xml`
- `solr/blsegments/managed-schema.xml`

Then from the Solr home directory register the two Solr cores:

```./bin/solr create -c blvolumes ```

```./bin/solr create -c blsegments ```

At this stage we can index the full text of the British Library Digital Collection, for both volumes and segments:

```python code/create-search.py core ```

```python code/create-search.py --segment core ```

## Web Server Setup

TODO

## Curatr Configuration File

In the core directory, rename the empty configuration file `sample-config.ini` to `config.ini`. The key configuration settings below should be modified.

In the `app` section:

- hostname: Name of host running Flask web application. The default hostname is localhost.
- port: Port number for the Flask web application. The default port is 5000.
- secret_key: The key used by Flask for cookies. This should be set once initially and then only known to the application. 
- prefix: The prefix for dynamic pages, if the web application is being delivered on a particular path (e.g. by Apache2). By default there is no prefix.
- staticprefix: The prefix for static pages, if the web application is being delivered on a particular path (e.g. by Apache2). By default there is no prefix.
- apiprefix: The prefix for API queries, if the web application is being delivered on a particular path (e.g. by Apache2). By default there is no prefix.

In the `db` section:

- hostname: Name of host of the MySQL database server. The default hostname is localhost.
- port: Port number for the MySQL database server. The default port is 3306.
- user: MySQL username
- password: MySQL password
- dbname: The database to use for storing Curatr-based data. Default database name is "curatr".
- pool_size: Number of simultaneous database connections to maintain in the database pool. Typically 5 to 20.

In the `solr` section:

- hostname: Name of host of the Solr search server. The default hostname is localhost.
- port: Port number for the Solr search server. The default port is 8983.


## Starting Curatr

To start the Curatr web application, run the below, where the only argument to the script is the core directory path:

```python code/curatr.py core```
