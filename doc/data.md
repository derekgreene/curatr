# Data Formats in Curatr

This document describes every data format used by the Curatr platform: the raw British
Library source files, the cleaned metadata files that Curatr actually consumes, the
plain-text corpus, the MySQL schema, the Solr index documents, the word embedding
files, and the formats produced when users export data from the web interface.

All persistent data lives under a single *core* directory (`core/` by default), which is
passed as the first argument to every command-line script. The paths below are all
relative to that directory, as defined in `CoreBase.__init__` (`code/core.py`).

## Core directory layout

```
core/
├── config.ini              # platform configuration (see "Configuration file")
├── metadata/               # cleaned metadata consumed by Curatr
│   ├── book-metadata.json
│   ├── book-classifications.csv
│   ├── book-links.csv
│   ├── book-volumes.csv
│   └── raw/                # original British Library / UCD source files
├── fulltext/               # plain-text volume files, in 4-digit prefix directories
├── embeddings/             # word2vec models (.kv / .bin)
├── export/                 # user-generated sub-corpus ZIP files
└── log/                    # application logs
```

## Data pipeline

The formats are produced and consumed in a fixed order. Each stage reads the output of
the previous one:

```
raw/*.json,csv,xlsx  ──create-metadata.py──►  metadata/*.json,*.csv
metadata/*  +  fulltext/*  ──create-db.py──►  MySQL database
MySQL  +  fulltext/*       ──create-search.py──►  Solr cores (blvolumes, blsegments)
MySQL  +  fulltext/*       ──create-ngrams.py──►  MySQL Ngrams table
MySQL  +  fulltext/*       ──create-recs.py──►    MySQL Recommendations table
fulltext/*                 ──create-embedding.py──►  embeddings/*.kv, *.bin
```

## 1. Raw source data

The files in `core/metadata/raw/` are the original inputs, used only by
`code/create-metadata.py` (via `CorePrep` in `code/preprocessing/util.py`). They are not
read at runtime by the web application.

| File | Format | Index column | Purpose |
|---|---|---|---|
| `ucd_digitised_books_2021.json` | JSON (column-oriented, as written by Pandas) | `identifier` | UCD-curated metadata: year, authors, shelfmarks, Alston classification titles, PDF/Flickr URLs |
| `ms_digitised_books_2021-01-09.csv` | CSV, comma-separated | `BL record ID for physical resource` | British Library Microsoft Digitised Books catalogue export |
| `MicrosoftBooks_FullIndex_27_09_2018.xlsx` | Excel workbook | `Aleph system no.` | Ark persistent identifiers and viewer links |
| `books-filter.txt` | Plain text, one book ID per line | — | Optional list of book IDs to exclude from Curatr |

Key columns used from `ms_digitised_books_2021-01-09.csv`: `BL record ID`,
`Type of resource`, `Title`, `Country of publication`, `Place of publication`,
`Publisher`, `Edition`, `Physical description`.

Key columns used from `ucd_digitised_books_2021.json`: `year`, `authors`,
`holdings_publication`, `shelfmarks`, `ClassificationTitle`,
`ClassificationSubTitle`, `url_pdf`, `url_images`.

All string fields are passed through the cleaning functions in
`code/preprocessing/cleaning.py` (`clean`, `clean_title`, `clean_shelfmarks`,
`extract_authors`, `extract_publication_location`), which apply
[ftfy](https://pypi.org/project/ftfy) mojibake repair, whitespace normalisation, and
field-specific tidying.

The cleaned metadata files described in sections 2–5 below (everything under
`core/metadata/` except `raw/`) are licensed under a
[Creative Commons BY-NC-ND 4.0 Licence](https://creativecommons.org/licenses/by-nc-nd/4.0/),
separately from the Apache-2.0-licensed Curatr source code.

## 2. Book metadata — `book-metadata.json`

A JSON array of objects, one per book, written with
`DataFrame.to_json(orient="records", indent=3)` and sorted by `book_id`. The production
file contains 35,884 books spanning 1700–1899. A 185-book excerpt in the same format is
provided as `sample-metadata.json` for testing and development.

| Field | Type | Notes |
|---|---|---|
| `book_id` | string | Unique British Library Microsoft Digital Collection identifier, zero-padded to 9 digits. Always treat as a string — leading zeros are significant |
| `year` | integer | Publication year |
| `title` | string \| null | Cleaned title (bracketed editorial material and trailing boilerplate removed) |
| `title_full` | string \| null | Original British Library title |
| `authors` | list[string] \| null | Cleaned author names, `"Surname, Forename"` order. `null` when no author is recorded (3,624 books) |
| `authors_full` | object \| null | Original names grouped by MARC role, e.g. `{"creator": [...], "contributor": [...]}` |
| `resource_type` | string \| null | Type of issuance, e.g. `"Monograph"` |
| `publisher` | string \| null | Cleaned publisher name |
| `publisher_full` | string \| null | Original holdings publication statement, e.g. `"London : James Darling, 1851."` |
| `publication_place` | list[string] \| null | Publication place(s), title-cased |
| `publication_country` | list[string] \| null | Publication country/countries, title-cased |
| `edition` | string \| null | Edition statement |
| `physical_descr` | string \| null | Physical description, e.g. `"viii, 160 pages (12°)"` |
| `shelfmarks` | list[string] \| null | British Library shelfmarks |
| `bl_record_id` | integer | British Library catalogue record ID (links to Ark data) |
| `volumes` | integer | Number of volume full-text files found for this book |

```json
{
   "book_id": "000000037",
   "year": 1888,
   "title": "A Gossip about Old Manchester",
   "title_full": "A Gossip about Old Manchester. With illustrations [Signed: A.]",
   "authors": null,
   "authors_full": null,
   "resource_type": "Monograph",
   "publisher": "A. Heywood",
   "publisher_full": "Manchester : A. Heywood & Son, [1888]",
   "publication_place": ["Manchester"],
   "publication_country": ["England"],
   "edition": null,
   "physical_descr": "32 pages (8°)",
   "shelfmarks": ["HMNTS 10347.cc.13.(4.)"],
   "bl_record_id": 14756048,
   "volumes": 1
}
```

The `volumes` field is added by a second pass (`create-metadata.py volumes`), which
rewrites the file after scanning the full-text directory. If `book-metadata.json` is
regenerated with the `books` action alone, this field will be absent —
`create-metadata.py verify` warns about exactly this case.

## 3. Book classifications — `book-classifications.csv`

Tab-separated, one row per book (35,884 rows in production), with a header line. Encodes
the hierarchical Alston topical index used by the British Library from 1823 to 1985.

| Column | Type | Notes |
|---|---|---|
| `book_id` | string | Refers to `book-metadata.json` |
| `primary` | string | `Fiction` or `Non-Fiction`. Derived: any book whose secondary class is "Fiction" is `Fiction`, everything else is `Non-Fiction` |
| `secondary` | string | Broad class, e.g. `Topography`, `Poetry`, `History` (70 distinct values) |
| `tertiary` | string \| empty | Sub-class, e.g. `Great Britain & Ireland` (149 distinct values). Empty when the source is missing or literally "uncategorised" |

```
book_id	primary	secondary	tertiary
000000037	Non-Fiction	Topography	Great Britain & Ireland
000000196	Non-Fiction	Poetry	English Selections
```

The production split is 10,217 fiction and 25,667 non-fiction books. Empty `tertiary`
values become `None` on load (`CorePrep.get_book_classifications` replaces `np.nan`, as
MySQL will not accept NaN).

## 4. Book links — `book-links.csv`

Tab-separated, one row per external resource link (56,694 rows in production), with a
header line. A book may have several links, and books are not required to have any.

| Column | Type | Notes |
|---|---|---|
| `book_id` | string | Refers to `book-metadata.json` |
| `kind` | string | `ark`, `pdf`, `flickr`, or `mudies` |
| `url` | string | Full URL of the resource |

```
book_id	kind	url
000000037	ark	http://access.bl.uk/item/viewer/ark:/81055/vdc_000000054756
```

Production counts by kind: 47,319 `ark`, 4,688 `flickr`, 4,687 `pdf`. The `mudies` kind
is supported by the indexer and web interface (`url_mudies`) but is not produced by
`create-metadata.py`.

## 5. Volume index — `book-volumes.csv`

Tab-separated, one row per volume (46,403 rows in production), with a header line. This
file is the bridge between the metadata and the plain-text corpus, and is generated by
scanning `core/fulltext/` rather than from any source metadata.

| Column | Type | Notes |
|---|---|---|
| `volume_id` | string | `<book_id>_<NN>`, where `NN` is the zero-padded volume number, e.g. `000000037_01` |
| `book_id` | string | Refers to `book-metadata.json` |
| `num` | integer | Volume number within the book, from 1 |
| `total` | integer | Total number of volumes for this book |
| `path` | string | Path of the full-text file, relative to `core/fulltext/` |
| `filesize` | integer | Size of the full-text file, in kilobytes (rounded up) |

```
volume_id	book_id	num	total	path	filesize
000000037_01	000000037	1	1	0000/000000037_01_text.txt	43
```

## 6. Full-text corpus — `core/fulltext/`

One plain-text file per volume, UTF-8 encoded. Files are distributed across
subdirectories named after the first four characters of the book ID, to keep directory
sizes manageable:

```
core/fulltext/<book_id[0:4]>/<book_id>_<NN>_text.txt
core/fulltext/0139/013952747_01_text.txt
```

Volume numbering starts at `01` and is contiguous — `create-metadata.py` and
`BookContentGenerator` both stop scanning at the first missing volume number. Files are
always opened with `encoding="utf8", errors="ignore"`, so malformed bytes in the OCR
output are silently dropped rather than raising.

The files are raw OCR output and are not pre-cleaned on disk. `clean_content()`
(`code/preprocessing/cleaning.py`) is applied at read time everywhere the text is
indexed or counted: it repairs mojibake with ftfy, replaces `<` and `>` with spaces (so
the text is safe to embed in XML/HTML payloads), converts tabs to spaces, and normalises
`\r` to `\n`. Note that the embedding training path deliberately skips this step — see
[embeddings.md](embeddings.md).

## 7. MySQL database

Created by `code/create-db.py`; the `CREATE TABLE` statements are all in
`code/db/booksql.py`, and access is through `CuratrDB` (`code/db/curatrdb.py`). All
text columns use `utf8 / utf8_general_ci`.

### Core tables

| Table | Key columns | Contents |
|---|---|---|
| `Books` | `id` (PK) | One row per book: `year`, `decade`, `title`, `title_full`, `authors_full` (JSON string), `edition`, `resource_type`, `publisher`, `publisher_full`, `physical_descr`, `volumes`, `bl_record_id` |
| `Authors` | `id` (PK) | `name`, `gender` (default `"Unknown"`). Author ID 1 is the reserved `"Unknown"` author |
| `BookAuthors` | `book_id`, `author_id` | Many-to-many link between books and authors |
| `BookLocations` | `book_id`, `kind`, `location` | `kind` is `place` or `country` |
| `BookShelfmarks` | `book_id`, `shelfmark` | One row per shelfmark |
| `Volumes` | `id` (PK) | `num`, `total`, `book_id`, `path`, `word_count` |
| `Classifications` | `book_id` | `overall`, `secondary`, `tertiary`. Note the first column is named `overall` here, but `primary` in `book-classifications.csv` |
| `BookLinks` | `book_id`, `kind`, `url` | As per `book-links.csv` |
| `VolumeExtracts` | `volume_id` | A 450-character preview of the volume, plus a trailing `"..."`, starting at the first alphanumeric character |
| `Recommendations` | `volume_id`, `rec_volume_id`, `rank_num` | Top-50 similar volumes per volume, ranked from 1 |
| `Ngrams` | `ngram`, `year`, `count`, `collection` | Per-year document frequency of a term (see below) |

`decade` is derived on insert as the year truncated to ten years (e.g. 1888 → 1880).
`authors_full` is stored as a serialised JSON string, not as a structured column.

### User-generated tables

| Table | Contents |
|---|---|
| `Users` | `email`, `hash` (Passlib hash), `created_at`, `last_login`, `num_logins`, `admin`, `guest`, `log_queries` |
| `Bookmarks` | `user_id`, `volume_id`, optional `segment_id`, `created_at` |
| `Lexicons` | `user_id`, `name`, `description`, `class_name`, `created_at` |
| `LexiconWords` | `lexicon_id`, `word` — the words in a lexicon |
| `LexiconIgnores` | `lexicon_id`, `word` — words rejected from embedding-based suggestions |
| `Corpora` | `user_id`, `name`, `format`, `documents`, `filename` (the ZIP in `core/export/`), `created_at` |
| `CorpusMetadata` | `corpus_id`, `field`, `value` — an open key/value store describing how a sub-corpus was built |
| `QueryLog` | `query_date`, `user_id`, `query` — only populated for users with `log_queries` set |

`CorpusMetadata` values are stored as strings via `str()`, including lists — the
`date_range` field, for example, is stored as the literal `"[1850, 1899]"`.

### Cache tables

Populated by `create-db.py caches` and loaded into memory at startup by
`CoreCuratr.cache_values()`. They exist purely to avoid expensive aggregate queries on
each page load, and can be rebuilt at any time.

| Table | Columns |
|---|---|
| `CachedAuthors` | `author_id` (PK), `author_name`, `sort_name`, `start_year`, `end_year`, `count` |
| `CachedBookYears` | `year` (PK), `count` |
| `CachedVolumeYears` | `year` (PK), `count` — the denominator for normalised n-gram counts |
| `CachedPlaceCounts` | `location`, `count` |
| `CachedCountryCounts` | `location`, `count` |
| `CachedClassificationCounts` | `class_name`, `level` (0 = primary, 1 = secondary, 2 = tertiary), `count` |

### N-gram counts

The `Ngrams` table stores *document frequency by year*, not raw term frequency: each
volume contributes at most 1 to the count for a given ngram and year, because
`extract_tokens()` (`code/create-ngrams.py`) collects a `set` of tokens per volume.

- Tokens are lower-cased, must start with an alphabetic character, and are between 2 and
  80 characters long. Diacritics are stripped via NFKD normalisation.
- Bigrams (optional, `-b`) are stored with an underscore separator: `public_health`. The
  web API applies the same substitution to incoming queries, so a user searching for
  `"public health"` matches `public_health`.
- `collection` distinguishes parallel count sets built over subsets of the corpus:
  `all`, `fiction`, `nonfiction`. Each is generated by a separate run of
  `create-ngrams.py -c <collection>`.

## 8. Solr indexes

Two Solr cores are maintained, both populated by `code/create-search.py` and configured
by `core/config.ini`:

| Core | Default name | Document granularity | Document ID |
|---|---|---|---|
| Volumes | `blvolumes` | One document per volume | `<volume_id>`, e.g. `000000037_01` |
| Segments | `blsegments` | One document per fixed-length text segment (`-s` flag) | `<volume_id>_<NNNNNN>`, e.g. `000000037_01_000001` |

Segments are produced by splitting the cleaned volume text into fixed-width character
chunks of `solr.segment_size` characters (default 2,000) — a purely positional split,
with no sentence or paragraph awareness. The production index holds roughly 12.3 million
segment documents.

Both cores share an identical schema (`solr/blvolumes/conf/managed-schema.xml` and
`solr/blsegments/conf/managed-schema.xml` are byte-identical in their field definitions),
so a query can be pointed at either core without change:

| Field | Solr type | Multi-valued | Notes |
|---|---|---|---|
| `id` | `string` | | Unique key |
| `book_id` | `string` | | |
| `volume`, `max_volume` | `pint` | | Volume number, and volume count for the book |
| `segment`, `max_segment` | `pint` | | Segment number, and segment count for the volume. Both are `1` in the volumes core |
| `year` | `pint` | | Used for range filtering, e.g. `year:[1850 TO 1899]` |
| `title`, `title_full` | `string` | | Stored, exact-match |
| `title_text` | `text_general` | | Indexed-only, analysed copy for free-text title search |
| `authors` | `string` | ✓ | |
| `authors_full` | `string` | | JSON string of role → names |
| `authors_genders` | `string` | ✓ | Parallel to `authors` |
| `authors_text` | `text_general` | ✓ | Indexed-only, analysed copy |
| `category`, `classification`, `subclassification` | `string` | | Correspond to `primary`, `secondary`, `tertiary` in the classification metadata; each defaults to `unknown` |
| `publisher`, `publisher_text` | `string` | ✓ | |
| `publisher_full`, `edition`, `physical_descr` | `string` | | |
| `location_places`, `location_countries` | `string` | ✓ | |
| `shelfmarks` | `string` | ✓ | |
| `url_ark`, `url_pdf`, `url_flickr`, `url_mudies` | `string` | | Populated from `BookLinks` |
| `mudies_description`, `mudies_match` | `string` / `pint` | | Reserved for Mudie's data; currently written as `0` / `null` |
| `content` | `text_general` | | **Stored but not indexed** — full text of the volume or segment |
| `text` | `text_general` | ✓ | Indexed-only catch-all searched by default |

Because `content` is stored-but-not-indexed and `text` is indexed-but-not-stored,
full-text search runs against `text` while results are displayed from `content`.
Documents are committed per book, not per document, so indexing is restartable at book
granularity.

## 9. Word embeddings

Models live in `core/embeddings/` in two interchangeable formats — Gensim's native
`KeyedVectors` (`.kv`, plus a sidecar `.kv.vectors.npy`) and word2vec binary (`.bin`).
Filenames encode collection, algorithm and dimensionality, e.g.
`blfiction-w2v-cbow-d100.kv`. Available models are registered as `id = filename` pairs
under `[embeddings]` in `config.ini`.

The formats, training parameters, tokenisation pipeline and runtime loading behaviour
are documented in full in [embeddings.md](embeddings.md).

## 10. Export formats

### Sub-corpus ZIP

Produced asynchronously by `BulkExporter` (`code/web/export.py`) into `core/export/`,
and named `<user_id>_<slugified_name>[<n>].zip`. Each archive contains:

| Entry | Format | Contents |
|---|---|---|
| `description.json` | JSON | How the sub-corpus was built |
| `metadata.json` | JSON | Array of per-document metadata records |
| `volumes/<id>.txt` or `segments/<id>.txt` | Plain text | One file per exported document, in `volumes/` or `segments/` according to the export type — omitted when the export format is `metadata` |

`description.json` records the export parameters:

```json
{
    "name": "Contagion",
    "format": "text",
    "documents": 100,
    "properties": {
        "date_range": [1850, 1899],
        "type": "segment",
        "search_field": "Full text",
        "query": ["contagion", "disease"],
        "classification": "Fiction",
        "subclassification": "all",
        "lexicon": "12"
    }
}
```

`metadata.json` is the list of matching Solr documents with `content` and `_version_`
removed. For volume-level exports, the per-segment fields (`segment`, `max_segment`,
`book_id`, `cat_start`, `cat_end`) are also stripped and `id` is replaced by the book ID.

`format` is either `text` (full text plus metadata) or `metadata` (metadata files only).

### N-gram CSV

The Ngram Viewer exports a CSV named `ngrams-<query1>_<query2>.csv`, with a `year` column
followed by one column per query term, and one row per year in the requested range. Years
with no matches are written as `0`. With `normalize=true`, values are percentages of the
volumes published that year, to three decimal places:

```csv
year,contagion,disease
1850,12,143
1851,9,151
```

The same data is available as JSON from the API endpoint (`code/web/api.py`), returned as
a list of `[year, count]` pairs suitable for direct use by Highcharts.

### Lexicon text file

A lexicon exports as a plain-text file named after the lexicon (lower-cased, spaces
replaced by underscores), containing one word per line in alphabetical order.

## 11. Configuration file — `core/config.ini`

A standard INI file read by `configparser`. `core/sample-config.ini` is a template; the
live file contains database credentials and the Flask secret key and should not be
committed.

| Section | Keys |
|---|---|
| `[app]` | `hostname`, `port`, `prefix`, `staticprefix`, `apiprefix`, `default_embedding`, `embedding_preload`, `secret_key`, `require_login` |
| `[db]` | `hostname`, `port`, `user`, `pass`, `dbname`, `pool_size` |
| `[solr]` | `hostname`, `port`, `core_segments`, `core_volumes`, `segment_size` |
| `[embeddings]` | `<embedding_id> = <filename>` pairs, relative to `core/embeddings/` |
| `[ngrams]` | `default_query`, `default_year_min`, `default_year_max` |
| `[networks]` | `default_query`, `default_k`, and node/font sizing for the semantic network viewer |

## Appendix: planned and partial formats

Two formats are referenced by the code or metadata documentation but are not present in
the current production data:

- **Mudie's metadata** (`book-mudies.json`) — described in
  `core/metadata/Mudies.md` as a JSON object keyed by `book_id`, with `mudies_id`,
  `mudies_title` and `mudies_authors` fields. The corresponding `mudies` link kind and
  the Solr fields `url_mudies`, `mudies_match` and `mudies_description` exist, but are
  not currently populated by any script.
- **Elasticsearch index** — `sample-config.ini` carries an `[elasticsearch]` section and
  a `[search] backend` switch, but Solr is the only backend implemented.
