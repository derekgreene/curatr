# Full-Text Data

Curatr makes the English-language subset of the [British Library Nineteenth Century Digitised Books Collection](https://doi.org/10.21250/db14), referred to here as BL19, searchable and analysable. The full set of BL19 plain-text files should be placed in this directory for indexing by Solr.

There is one plain-text file per volume, UTF-8 encoded. The files are grouped into four-digit subdirectories (e.g. `0000`–`0139`) to keep directory sizes manageable. The subdirectory names correspond to the first four digits of the British Library collection unique book identifiers. Filenames follow the pattern `<id>_<part>_text.txt`, e.g. `0000/000000037_01_text.txt`, where `<id>` is the full book identifier and `<part>` is a two-digit part number distinguishing multiple volumes of the same work.

