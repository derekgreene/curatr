# Metadata Files

This directory contains cleaned, augmented metadata for the English-language books in the [British Library Nineteenth Century Digitised Books Collection](https://doi.org/10.21250/db14) (BL19). The original metadata was provided by British Library Labs. All metadata provided here is licensed under a [Creative Commons BY-NC-ND 4.0 Licence](https://creativecommons.org/licenses/by-nc-nd/4.0/).

These files are generated from the original source data in the *raw* sub-directory by the script *code/create-metadata.py*. For a fuller description of these formats, and of all other data formats used by Curatr, see [doc/data.md](../../doc/data.md).

## Book Metadata

The file *book-metadata.json* is a JSON array containing one object per book, with the following fields:

- book_id: unique book identifier from the British Library Microsoft Digital Collection, stored as a zero-padded string
- year: publication year
- title: cleaned form of the book title
- title_full: original form of the book title, from the British Library Microsoft Digital Collection
- authors: cleaned form of book author(s), stored as a list
- authors_full: original form of the book author(s), from the British Library Microsoft Digital Collection, stored as an object which maps each role (e.g. creator, contributor) to a list of names
- resource_type: type or issuance of this book (e.g. Monograph)
- publisher: cleaned form of the publisher name
- publisher_full: original form of the holdings publication source, from the British Library Microsoft Digital Collection
- publication_place: one or more publication place (e.g. city), stored as a list
- publication_country: one or more publication country, stored as a list
- edition: details of the edition of this book
- physical_descr: physical description of the book at the British Library
- shelfmarks: shelfmarks associated with this book, stored as a list
- bl_record_id: identifier for the corresponding British Library catalogue record
- volumes: number of volumes associated with this book

Any field other than *book_id*, *year*, *bl_record_id* and *volumes* may be null, where no value was available in the original metadata.

The file *sample-metadata.json* contains a small excerpt of this data in the same format, for testing and development purposes.

## Book Classifications

The tab-separated file *book-classifications.csv* contains one row per book, describing its position in the hierarchical topical index used by the British Library from 1823 to 1985, with the following fields:

- book_id: identifier referring back to book metadata
- primary: the top-level category, either Fiction or Non-Fiction
- secondary: the broad classification assigned to the book (e.g. Topography, Poetry)
- tertiary: the more fine-grained sub-classification assigned to the book (e.g. Great Britain & Ireland). This is left empty where no sub-classification was available

## Book Links

The tab-separated file *book-links.csv* contains one link per line associated with a given book, with the following fields:

- book_id: identifier referring back to book metadata
- kind: the kind of the resource (i.e. ark, pdf, flickr, mudies)
- url: the URL of the resource

## Volume Text Information

The tab-separated file *book-volumes.csv* contains one volume per line, with the following fields:

- volume_id: unique identifier of this volume, in the form <book_id>_<volume number>
- book_id: identifier referring back to book metadata
- num: the number of the volume for a given book
- total: total number of volumes for this book
- path: relative path of the full-text file of this volume, relative to the *fulltext* directory
- filesize: size of the full-text file of this volume, in kilobytes

## Mudie's Metadata

The additional file *book-mudies.json*, described in [Mudies.md](Mudies.md), is not currently included in this directory.
