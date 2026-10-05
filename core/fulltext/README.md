# BL19 Full-Text Data

Curatr makes the English-language subset of the [British Library Nineteenth Century Digitised Books Collection](https://doi.org/10.21250/db14), referred to here as BL19, searchable and analysable. The full set of BL19 plain-text files should be placed in this directory for indexing by Solr.

## Structure

There is one plain-text `.txt` file per volume, UTF-8 encoded. The files are grouped into four-digit subdirectories (e.g. `0000`–`0139`) to keep directory sizes manageable. The subdirectory names correspond to the first four digits of the British Library collection unique book identifiers. Filenames follow the pattern `<id>_<part>_text.txt`, e.g. `0000/000000037_01_text.txt`, where `<id>` is the full book identifier and `<part>` is a two-digit part number distinguishing multiple volumes of the same work.

## Downloading BL19 Full Texts

The BL19 full texts are available as two zip archives, split by primary classification:

- Fiction: https://curatr.ucd.ie/data/bl19-fiction-fulltexts.zip (2.5 GB)
- Non-fiction: https://curatr.ucd.ie/data/bl19-nonfiction-fulltexts.zip (6.3 GB)

Each archive expands to a top-level `fiction/` or `nonfiction/` folder containing the same four-digit subdirectory structure described above, but restricted to that classification's volumes. Since the four-digit subdirectories group volumes by the first four digits of their book ID regardless of classification, the two archives contain different files within subdirectories of the same name (e.g. both include a `0000/` folder, each with a distinct set of volumes) rather than overlapping or conflicting. To populate this directory, unzip both archives and merge their contents in the Curatr `core/fulltext/` directory:

```
unzip bl19-fiction-fulltexts.zip
unzip bl19-nonfiction-fulltexts.zip
cp -R fiction/. core/fulltext/
cp -R nonfiction/. core/fulltext/
```

This leaves `core/fulltext/` with a single flat set of four-digit subdirectories, ready for indexing by Solr.

