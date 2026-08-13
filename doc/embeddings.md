# Word Embeddings in Curatr

This document describes how word embeddings are created and used in this codebase: the
model, the preprocessing pipeline that feeds it, and the parameter choices involved.

## Model

Embeddings are trained with [Gensim](https://radimrehurek.com/gensim/)'s `Word2Vec`
implementation. Both algorithm variants are supported via the `-m` option:

- `cbow` (Continuous Bag of Words) — `sg=0` — the default
- `sg` (Skip-gram) — `sg=1`

Training happens in two near-identical scripts:

- `code/create-embedding.py` — builds the embedding used for the `all` / `fiction` /
  `nonfiction` collections
- `code/tool-embedding.py` — the same training logic, extended with `--ymin`/`--ymax`
  options to build a custom embedding restricted to a publication year range (e.g. a
  `fiction` embedding limited to 1864–1880)

Both scripts source their corpus from the plain-text full-text files under
`dir_fulltext` (one or more `<book_id>_<volume>_text.txt` files per book) via
`preprocessing.text.BookTokenGenerator`, rather than the Solr index or database.

## Corpus selection

Which books go into the training corpus is controlled by the `-c`/`--collection`
option:

- `all` — every book in `book-metadata.json`
- `fiction` — books where `book-classifications.csv` has `primary == "Fiction"`
- `nonfiction` — books where `primary == "Non-Fiction"`

`tool-embedding.py` additionally supports narrowing this set to a `[year_min, year_max]`
range using the `year` column from the book metadata (`--ymin`/`--ymax`).

## Preprocessing pipeline

Tokenization and cleaning happen in `code/preprocessing/text.py`:

1. **`BookContentGenerator`** reads and concatenates the full text of every volume for
   a book, lower-casing the content.
2. **`BookTokenGenerator`** tokenizes each book's content with `simple_tokenizer`, a
   regex word tokenizer (`\b\w\w+\b`) that lower-cases all tokens, then applies a
   stopword strategy per token:
   - tokens that are stopwords, start with a digit, or are shorter than
     `min_term_length` (2 characters) are considered "stop" tokens
   - the default strategy (`stop_stategy=2`) **replaces** each stop token with the
     literal placeholder `<stopword>` rather than removing it — this preserves the
     original context window/positions for Word2Vec instead of collapsing them
   - each book yields one list of tokens (i.e. one Word2Vec "sentence" per book, not
     per paragraph or sentence)
3. **Stopwords** are loaded via `preprocessing.util.CorePrep.get_stopwords()` /
   `preprocessing.text.load_stopwords()`, which reads the bundled
   `code/preprocessing/stopwords.txt` (346 terms).

Note that this pipeline does not stem words or strip accents — `stem_word`/
`stem_words` (Porter stemmer) and `strip_accents_unicode` exist in
`preprocessing/text.py` but are used elsewhere in Curatr (e.g. n-gram/search
processing), not in the embedding training path. Likewise `clean_content()` (from
`preprocessing/cleaning.py`, used when generating token counts via `VolumeGenerator`)
is not applied before embedding training — embedding tokenization goes straight from
the raw full-text file content into `simple_tokenizer`.

## Training parameters

`Word2Vec` is invoked with the following options, all exposed as CLI flags:

| Parameter | CLI flag | Default | Meaning |
|---|---|---|---|
| `vector_size` | `-d`, `--dimensions` | `100` | Dimensionality of the word vectors |
| `min_count` | `--df` | `10` | Minimum document frequency for a term to be kept |
| `window` | `--window` | `5` | Max distance between current and predicted word |
| `sg` | `-m` (`cbow`/`sg`) | `cbow` (`sg=0`) | Training algorithm (CBOW vs Skip-gram) |
| `seed` | `--seed` | `1000` | Random seed, for reproducibility |
| `workers` | — | `4` | Number of worker threads (not configurable via CLI) |
| `sorted_vocab` | — | `1` | Vocabulary sorted by descending frequency (not configurable via CLI) |

## Output files

Models are written to `dir_embeddings` (`<core>/embeddings/`) in two formats:

- **Word2Vec binary** (`.bin`) — via `embed.wv.save_word2vec_format(path, binary=True)`,
  compatible with the original C word2vec tools
- **Gensim native** (`.kv`) — via `embed.save(path)` (`create-embedding.py`) or
  `embed.wv.save(path)` (`tool-embedding.py`), Gensim's own `KeyedVectors` format,
  which loads faster and supports memory-mapping (see below)

`tool-embedding.py` defaults to writing `.kv` only, and writes `.bin` instead if
`-b`/`--binary` is passed; `create-embedding.py` always writes both.

Filenames encode the collection, optional year range, algorithm and dimensionality,
e.g.:

- `bl-w2v-cbow-d100.kv` — full collection
- `blfiction-w2v-cbow-d100.kv` — fiction subset
- `blnonfiction-w2v-cbow-d100.kv` — non-fiction subset
- `blcustom_fiction_1864_1880-w2v-cbow-d100.kv` — fiction subset limited to 1864–1880

`code/convert-w2v.py` is a standalone utility for converting a pre-existing `.bin`
file to `.kv` format after the fact (`KeyedVectors.load_word2vec_format` →
`.save()`), without retraining.

## Configuration and loading at runtime

Available embeddings are registered in `config.ini` under `[embeddings]` as
`id = filename` pairs (filenames relative to `dir_embeddings`), e.g.:

```ini
[embeddings]
all = bl-w2v-cbow-d100.kv
fiction = blfiction-w2v-cbow-d100.kv
nonfiction = blnonfiction-w2v-cbow-d100.kv
fiction_1864_1880 = blcustom_fiction_1864_1880-w2v-cbow-d100.kv
```

`CoreCuratr.init_embeddings()` (`code/core.py`) iterates this section, checks each
file exists under `dir_embeddings`, and wraps it in an `EmbeddingWrapper`
(`code/wordembeddding.py`). `[app] default_embedding` selects which embedding id is
used by default.

`EmbeddingWrapper` loads the model lazily on first use (`.kv` files via
`KeyedVectors.load(..., mmap="r")`; `.bin` files via
`KeyedVectors.load_word2vec_format`), and caches nearest-neighbour lookups
(`most_similar`) per word in an LRU cache (`default_max_cache_size = 5000`,
`default_max_k = 20`). Words are normalized before lookup (`normalize_word`:
lower-cased, hyphens and quotes stripped).
