# Curatr

*Curatr* is a bespoke online platform designed to improve the accessibility of the [British Library Nineteenth Century Digitised Books Collection](https://doi.org/10.21250/db14). The collection is provided by British Library Labs and the platform was developed by the ERC-funded [VICTEUR project](https://projectvicteur.com), in collaboration with researchers at the [Insight Research Ireland Centre for Data Analytics](http://www.insight-centre.org/) as part of Insight's Cultural Analytics Research Initiative. *Curatr* hosts digitised plain-text versions of the English-language portion of the collection, referred to here as *BL19*, corresponding to 35,884 out-of-copyright titles, comprising 46,403 volumes and approximately 4.09 billion words, both fiction and non-fiction, published from 1700 to 1899.

## Dependencies

The following Python 3 packages should be installed prior to installing Curatr, which are available via PIP:

- NumPy: https://numpy.org
- Pandas: https://pandas.pydata.org
- PyMySQL: https://pypi.org/project/PyMySQL
- scikit-learn: https://scikit-learn.org/stable
- SolrClient: https://github.com/moonlitesolutions/SolrClient
- Gensim: https://radimrehurek.com/gensim
- ftfy: https://pypi.org/project/ftfy
- Passlib: https://pypi.org/project/passlib
- Flask: https://flask.palletsprojects.com/en/2.3.x/
- Flask-Login: https://flask-login.readthedocs.io/en/latest/
- MarkupSafe: https://pypi.org/project/MarkupSafe
- NetworkX: https://networkx.org/
- tabulate: https://pypi.org/project/tabulate

Additional dependencies:
- MySQL: https://www.mysql.com (tested with 5.7.40 and 8.0.33)
- Apache Solr: https://solr.apache.org (tested with 8.11.2)
- A Java JDK supported by Apache Solr, i.e. Java 11 or later (tested with OpenJDK 17.0.7 and 19.0.1)

Frontend dependencies (loaded from CDN):
- Bootstrap Icons: https://icons.getbootstrap.com
- Highcharts: https://www.highcharts.com (Ngram Viewer)
- vis-network: https://visjs.github.io/vis-network (Semantic Networks)
- Font Awesome: https://fontawesome.com

Dependencies for optional advanced network viewer:
- dash: https://dash.plotly.com
- dash-bootstrap-components: https://dash-bootstrap-components.opensource.faculty.ai
- dash-cytoscape: https://dash.plotly.com/cytoscape

## Platform Features

Curatr provides a range of tools for searching, browsing, and analysing BL19:

- **Collection Search**: a searchable index of 46,403 volumes and 12,322,488 text segments, searchable by full text, title, author, or publication location, and filterable by year, classification, and document type, with sorting by relevance, date, or title.
- **Classification Index**: a browsable version of the hierarchical topical index used by the British Museum Library from the early nineteenth century until 1973, and subsequently by the British Library until the end of 1985, comprising 70 top-level categories such as "Fiction" and "Geography" and 148 more fine-grained sub-topics.
- **Catalogue**: a sortable and searchable table of all books in the collection, browsable by title, author, and year of publication.
- **Authors**: browse the collection by its 19,766 unique authors, with links to all associated volumes.
- **Ngram Viewer**: plot the frequency with which one or more words occur across the collection over time, measured as the number of volumes per year containing each term, or as a percentage of the volumes published in that year. Results can be exported as a CSV file, and any year can be clicked through to the corresponding search results.
- **Semantic Networks**: visualise conceptual relationships in the collection by constructing interactive semantic networks from seed words, with associated words identified using word embedding models.
- **Concordance**: identify occurrences of a particular word or phrase throughout the collection, presented alongside its immediate linguistic context.
- **Word Lexicons**: create and manage curated lists of keywords related to a given research topic. Lexicons can be expanded automatically using a word embedding model to suggest semantically similar terms, and used to drive searches and sub-corpus exports.
- **Sub-Corpora**: define and export smaller, topic-specific sub-corpora of the collection, filtered thematically, chronologically, and by classification, for close reading and offline analysis.
- **Similar Volumes**: for any given volume, browse the 50 most similar volumes in the collection, based on pre-computed pairwise similarities.
- **Bookmarks**: save volumes and individual text segments of interest to a personal reading list.

## Acknowledgements

This work is part of the [VICTEUR project](https://projectvicteur.com/), which has received funding from the [European Research Council (ERC)](https://erc.europa.eu/) under the European Union's Horizon 2020 research and innovation programme (grant agreement No 884951), and is being undertaken by members of the [UCD School of English, Drama and Film](http://www.ucd.ie/englishdramafilm/), in collaboration with researchers from the [Insight Research Ireland Centre for Data Analytics](http://www.insight-centre.org/) at the [UCD School of Computer Science](https://www.ucd.ie/cs/).

The British Library Nineteenth Century Digitised Books collection was provided by British Library Labs. The Curatr source code is licensed under the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0), while the accompanying metadata in this repository is licensed under a [Creative Commons BY-NC-ND 4.0 Licence](https://creativecommons.org/licenses/by-nc-nd/4.0/).
