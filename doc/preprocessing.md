# Preprocessing in Curatr

Curatr makes the English-language subset of the British Library Nineteenth Century
Digitised Books Collection, referred to here as BL19, searchable and analysable. This
document describes every preprocessing step applied to BL19 by Curatr: the cleaning of
the raw metadata, the cleaning of the OCR full text, and the separate tokenisation
pipelines used to build the search index, the n-gram counts, the word embeddings, and
the volume recommendations.

The important thing to understand is that **there is no single preprocessing pipeline**.
A small amount of cleaning is shared, but each downstream feature tokenises the text its
own way, with different rules about stopwords, accents, numerals, and case. Counts
produced by one pipeline will therefore not match counts produced by another, and this
is by design rather than by accident.

Implementation lives in two modules:

- `code/preprocessing/cleaning.py` — string cleaning for metadata and full text
- `code/preprocessing/text.py` — tokenisers, stopwords, stemming, and corpus iterators

## Overview of the pipelines

| Pipeline | Script | Cleaning | Tokeniser | Case | Stopwords | Accents | Numerals |
|---|---|---|---|---|---|---|---|
| Search index | `create-search.py` | `clean_content` | Solr `StandardTokenizer` | lower-cased | Solr's own list | kept | kept |
| N-gram counts | `create-ngrams.py` | `clean_content` | `custom_tokenizer` | lower-cased | optional (`-s`) | stripped | dropped |
| Word embeddings | `create-embedding.py` | **none** | `simple_tokenizer` | lower-cased | replaced with placeholder | kept | dropped |
| Recommendations | `create-recs.py` | `clean_content` | `custom_tokenizer` | lower-cased | removed | stripped | dropped |
| Word counts | `create-db.py` | `clean_content` | `custom_tokenizer` | lower-cased | kept | kept | dropped |

## 1. Metadata preprocessing

Applied once by `code/create-metadata.py` when the metadata files are generated from the
raw British Library and UCD sources. All functions are in `preprocessing/cleaning.py`
and return `None` (or a supplied default) rather than an empty string when nothing
usable survives.

### General field cleaning — `clean()`

Repairs mojibake with [ftfy](https://pypi.org/project/ftfy), replaces hyphens and
question marks with spaces, collapses runs of whitespace, and discards the result if
fewer than two characters remain. Used for publisher, resource type, edition, and
physical description.

Note the hyphen replacement: `Newcastle-upon-Tyne` becomes `Newcastle upon Tyne`. This
is deliberate, since the OCR and cataloguing sources use hyphens inconsistently, but it
means hyphenated names are not preserved verbatim in the cleaned fields.

### Titles — `clean_title()`

1. ftfy repair, then normalisation of ellipses (`…` → `...` → `.`)
2. removal of all bracketed editorial material, e.g. `[Signed: A.]`, `[A novel.]`
3. removal of trailing cataloguing boilerplate from a list of known suffixes
   (`with illustrations`, `edited by`, `, etc`, and around a dozen more), longest first
4. removal of a trailing full stop or comma

The original string is preserved separately as `title_full`, so nothing is lost.

### Authors — `extract_authors()` and `format_author_sortname()`

`extract_authors()` takes the role-keyed name structure from the raw metadata and
produces a flat list of cleaned names: ftfy repair, semicolons removed, then each name
split on whitespace and rebuilt, stopping at any `-` part, stripping enclosing brackets,
dropping a trailing full stop from parts longer than three characters, and capitalising
each part.

`format_author_sortname()` (used when building the `CachedAuthors` table) additionally
removes bracketed material, converts ALL-CAPS words to title case, and strips a long
list of honorifics and role descriptions that follow a ` - ` separator — `Sir`, `Mrs`,
`Esq`, `M.P.`, `Novelist`, `Vicar of ...`, `Fellow of ...`, and so on.

### Publication locations — `extract_publication_location()` and `clean_location()`

Place and country strings are split on `;`, and each value is ftfy-repaired, has hyphens
and question marks replaced, is collapsed, and is converted to title case (with `" Of "`
restored to `" of "`).

Where a book has exactly one place but no country, the country is inferred from
`place_map`, a hand-built dictionary of roughly sixty places in `cleaning.py:128`
(`Calcutta` → `India`, `Melbourne` → `Australia`, and so on).

### Shelfmarks — `clean_shelfmarks()`

Removes the literal string `British Library`, converts semicolons to colons, and
collapses whitespace.

## 2. Shared full-text cleaning

Every pipeline that reads volume text — except the embedding pipeline, see below — reads
it the same way.

Files are opened with `encoding="utf8", errors="ignore"`, so bytes that will not decode
are dropped silently rather than raising. The content is then passed through
`clean_content()` (`cleaning.py:72`):

```python
def clean_content(content):
	if content is None or type(content) is float:
		return ""
	content = ftfy.fix_text(content)
	content = content.replace("<", " ").replace(">", " ")
	content = content.replace("\t"," ")
	content = content.replace("\r","\n")
	return content.strip()
```

Four operations only:

1. **ftfy repair** of character-encoding damage, along with ftfy's default Unicode
   normalisation and control-character removal
2. **`<` and `>` replaced with spaces**, so the text is safe to embed in the XML payload
   sent to Solr
3. **tabs to spaces**
4. **carriage returns to newlines**, then a leading/trailing strip

Note what this does *not* do. There is no lower-casing, no punctuation stripping, no
collapsing of repeated whitespace or blank lines, no de-hyphenation of words broken
across lines, no removal of running headers or page numbers, and **no correction of OCR
recognition errors**. Misrecognised words pass through unchanged into every index and
every count.

## 3. Tokenisation building blocks

All in `preprocessing/text.py`, shared between pipelines.

### `simple_tokenizer(s)`

```python
token_pattern = re.compile(r"\b\w\w+\b", re.U)
```

Finds all runs of two or more word characters and lower-cases them. Numerals are kept
(`1861` is a token). Used by the embedding pipeline.

### `custom_tokenizer(s, min_term_length=2)`

The same regex, with two extra conditions: the token must be at least
`min_term_length` characters long **and** must begin with an alphabetic character. This
drops pure numerals and anything starting with a digit, which removes a large amount of
OCR noise — page numbers, dates, catalogue references. Used by the n-gram, word-count,
and recommendation pipelines.

This is the definition behind the `Volumes.word_count` column, and therefore behind any
"number of words" figure taken from the database.

### `bigrams(tokens)`

Yields every consecutive pair from a token sequence, via
`zip(tokens, islice(tokens, 1, None))`. Used only by the n-gram pipeline.

### `strip_accents_unicode(s)`

NFKD normalisation followed by removal of combining characters, with a fast path for
pure-ASCII strings. Mirrors scikit-learn's `strip_accents="unicode"`.

### `load_stopwords()`

Reads `code/preprocessing/stopwords.txt`, a list of **346** terms. As well as ordinary
English function words, it includes collection-specific terms such as `volume`, `book`,
and `edition`, which recur in title pages and running headers throughout BL19.

This list is entirely separate from the `stopwords.txt` used by Solr, which lives in the
Solr core's own `conf` directory.

### `stem_word()` / `stem_words()`

Gensim's Porter stemmer. Used **only** to enforce diversity among word suggestions
(`core.py:225`), never in any indexing or counting path.

## 4. Workflow: the Solr search index

Script: `code/create-search.py`.

1. Volume text is read and passed through `clean_content()`.
2. For the segment index, the cleaned text is divided into **fixed 2,000-character
   segments** (`[solr] segment_size`) by plain string slicing:

   ```python
   def segment_text(text, length):
       return (text[0+i:length+i] for i in range(0, len(text), length))
   ```

   The slices are consecutive and non-overlapping, with no sentence, word, paragraph, or
   page awareness — a boundary falls wherever the 2,000th character lands, frequently
   mid-word. The final segment holds the remainder; a volume shorter than the segment
   size becomes a single segment. Note the unit is Unicode characters, and includes all
   whitespace and punctuation surviving `clean_content()`.
3. For the volume index, the whole cleaned text is indexed as one document.
4. Documents are handed to Solr, which performs **all remaining preprocessing itself**.

No Python tokenisation occurs on this path. The `text_general` analysis chain in the
managed schema does the work:

| Stage | Index analyzer | Query analyzer |
|---|---|---|
| Tokenise | `StandardTokenizerFactory` | `StandardTokenizerFactory` |
| Stopwords | `StopFilterFactory` (`stopwords.txt`, `ignoreCase=true`) | same |
| Synonyms | — | `SynonymGraphFilterFactory` (`synonyms.txt`, `expand=true`) |
| Case | `LowerCaseFilterFactory` | `LowerCaseFilterFactory` |

Because Lucene's `StandardTokenizer` keeps numerals and single characters, token counts
derived from the Solr index are higher than those derived from `custom_tokenizer` — for
the full collection, 4.35 billion against 4.09 billion.

Fields are populated by copy directives in the schema:

```xml
<copyField source="content" dest="text"/>       <!-- full text only -->
<copyField source="title"   dest="title_text"/>
<copyField source="authors" dest="authors_text"/>
<copyField source="*"       dest="_text_"/>     <!-- every field -->
```

Curatr sets no `df` or `defType`, so an unfielded query is matched against `_text_`,
which contains a copy of *all* fields — meaning a "Full Text" search also matches
titles, authors, publishers, shelfmarks, and URLs.

## 5. Workflow: n-gram counts

Script: `code/create-ngrams.py`, function `extract_tokens()`.

1. Volume text is read and passed through `clean_content()`.
2. Tokenised with `custom_tokenizer(content, min_term_length=2)` — lower-cased,
   alphabetic-initial, at least two characters.
3. Each token has diacritics removed with `strip_accents_unicode()`, producing the
   `stripped_tokens` sequence.
4. A token is counted unless it is shorter than 2 or longer than 80 characters, or is a
   stopword. Stopword filtering is applied **only** when `-s`/`--stopwords` is passed;
   by default no stopword filtering occurs.
5. With `-b`/`--bigrams`, consecutive pairs are formed over `stripped_tokens` — that is,
   over the *unfiltered* sequence, so adjacency reflects the original text — and each
   pair is kept only if both members and the joined form pass the same length and
   stopword tests. Bigrams are stored joined by an underscore: `public_health`.
6. Tokens for a volume are accumulated in a **set**, so each volume contributes at most
   1 to the count for any given n-gram.

The resulting counts are therefore **document frequency by year**, not term frequency:
the number of volumes published in a given year that contain the term at least once.

Counts are built separately per collection (`all`, `fiction`, `nonfiction`) and stored
in the `Ngrams` table with a `collection` column.

Query-side, the API applies matching normalisation so user input can match stored keys:
spaces become underscores and all other non-alphanumeric characters are removed
(`web/api.py:23`).

## 6. Workflow: word embeddings

Scripts: `code/create-embedding.py` and `code/tool-embedding.py`. This pipeline is
deliberately different from the others; see [embeddings.md](embeddings.md) for the model
and training parameters.

1. `BookContentGenerator` concatenates the full text of **every volume of a book** into a
   single string, lower-casing as it reads. Note that `clean_content()` is **not**
   applied — this path goes straight from the raw file content into tokenisation.
2. `BookTokenGenerator` tokenises with `simple_tokenizer` (numerals permitted at this
   stage), then applies a stopword strategy per token. The default strategy
   (`stop_stategy=2`) **replaces** each stopword, digit-initial, or too-short token with
   the literal placeholder `<stopword>` rather than deleting it.
3. Each book yields one token list — one Word2Vec "sentence" per book, not per sentence
   or paragraph.

The placeholder substitution is the key design decision: removing stopwords outright
would pull distant words into each other's context windows, whereas replacing them
preserves the original spacing between content words.

At query time, words are normalised before embedding lookup by `normalize_word()`
(`wordembeddding.py:23`): lower-cased, hyphens converted to underscores, double quotes
removed.

## 7. Workflow: volume recommendations

Script: `code/create-recs.py`.

1. `VolumeGenerator` iterates every volume, reading and `clean_content()`-ing the text.
2. `build_bow()` vectorises the corpus with scikit-learn's `TfidfVectorizer`:

   | Parameter | Value |
   |---|---|
   | `tokenizer` | `custom_tokenizer` |
   | `stop_words` | Curatr's 346-term list |
   | `lowercase` | `True` |
   | `strip_accents` | `"unicode"` |
   | `use_idf` | `True` |
   | `norm` | `"l2"` |
   | `min_df` | `10` |

   The `min_df=10` threshold discards any term appearing in fewer than ten volumes,
   which removes the very long tail of OCR noise.
3. Pairwise cosine similarities are computed over the whole matrix, and the 50
   highest-ranked neighbours of each volume are written to the `Recommendations` table.
   Similarity scores themselves are not retained.

## 8. Workflow: database word counts and extracts

Both in `code/create-db.py`.

**Word counts** (`add_wordcounts()`) read each volume, apply `clean_content()`, tokenise
with `custom_tokenizer`, and store the token count in `Volumes.word_count`. No stopword
filtering is applied, so the figure includes function words but excludes numerals.

**Extracts** (`add_extracts()`) produce the short preview shown in search results:
`clean_content()`, then a set of cosmetic replacements (`" ` → `"`, `..` → `.`,
`. .` → `.`), then a scan forward to the first alphanumeric character, then the first
450 characters followed by an ellipsis.

## 9. Query-time and display-time processing

Preprocessing is not confined to indexing. User input is normalised on the way in:

| Context | Processing |
|---|---|
| Solr query (`search.py:22`) | square brackets stripped; field prefix prepended for fielded searches |
| Search/concordance suggestions | non-alphanumeric characters replaced with spaces, lower-cased, tokens of one character discarded |
| N-gram API (`web/api.py:23`) | spaces to underscores, all other non-alphanumeric characters removed |
| Semantic network seeds (`web/networks.py:24`) | commas, semicolons, and tabs converted to spaces |
| Embedding lookup (`wordembeddding.py:23`) | lower-cased, hyphens to underscores, quotes removed |

Output is tidied for display by a family of `tidy_*` functions in `cleaning.py` —
`tidy_title`, `tidy_author_list` (which reverses `Surname, Forename` for readability),
`tidy_snippet`, `tidy_extract`, `tidy_publisher`, and others. These affect presentation
only and never the indexed or stored data.

## 10. What Curatr does not do

Worth stating explicitly, since these are common assumptions about a digitised
collection:

- **No OCR error correction.** ftfy repairs character-*encoding* damage; it does not
  correct misrecognised words. `modem` for `modern`, or long-s artefacts, survive into
  every index and count.
- **No de-hyphenation** of words split across line breaks.
- **No spelling normalisation** of historical or variant orthography.
- **No removal of page furniture** — running headers, page numbers, catalogue stamps,
  and library plates remain in the text (the `volume`/`book`/`edition` entries in the
  stopword list are a partial mitigation).
- **No sentence segmentation.** Nothing in the platform detects sentence boundaries; the
  2,000-character segments and the one-sentence-per-book embedding input are both
  consequences of this.
- **No lemmatisation**, and no stemming outside the word-suggestion diversity filter.
