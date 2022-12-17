# Data Files

## Book Metadata

The file *book-metadata.json* is in JSON format:

- book_id: unique book identifier from the British Library Microsoft Digital Collection
- title: cleaned form of the book title
- title_full: original form of the book title, from the British Library Microsoft Digital Collection
- authors: cleaned form of book author(s), stored as a list
- authors_full: original form of the book title, from the British Library Microsoft Digital Collection, stored as a list of tuples (name, role)
- publisher: cleaned form of the publisher name
- publisher_full: original form of the holdings publication source, from the British Library Microsoft Digital Collection
- publication_places: one or more publication place (e.g. city), stored as a list
- publication_countries: one or more publication country, stored as a list
- resource_type: type or issuance of this book (e.g. monograph)
- edition: details of the edition of this book
- physical_descr: physical description of the book at the British Library
- shelfmarks: shelfmarks associated with this book, stored as a list
- num_volumes: number of volumes associated with this book

## Book Classifications

The tab-separated file *book-classifications.csv* contains one classification per line associated with a given book, with the following fields:

- book_id: identifier referring back to book metadata
- level: level for hierarchical classifications, indexed from 0
- label: name of the classification assigned to the book

## Book Links

The tab-separated file *book-links.csv* contains one link per line associated with a given book, with the following fields:

- book_id: identifier referring back to book metadata
- resource: the kind of the resource (e.g. British Library Catalogue, Ark, Flickr, Wikipedia)
- url: the URL of the resource

## Volume Text Information

The tab-separated file *book-volumes.csv* contains one volume per line, with the following fields:

- volume_id: unique identifier of this volume
- book_id: identifier referring back to book metadata
- volume_num: the number of the volume for a given book
- total: total number of volumes for this book
- path: relative path of the full-text file of this volume
- filesize: size of the full-text file of this volume, in kilobyte

