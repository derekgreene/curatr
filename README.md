# Curatr

*Curatr* is a bespoke online platform designed to improve the accessibility of the [British Library Nineteenth Century Digitised Books Collection](https://doi.org/10.21250/db14) (BL19). The collection is provided by British Library Labs and the platform was developed by the ERC-funded [VICTEUR project](https://projectvicteur.com), in collaboration with researchers at the [Insight Research Ireland Centre for Data Analytics](http://www.insight-centre.org/) as part of Insight's Cultural Analytics Research Initiative. *Curatr* hosts digitised plain-text versions of all English-language books from the BL19 collection, corresponding to 35,884 unique out-of-copyright English-language titles, both fiction and non-fiction, from 1700 to 1899. 

## Dependencies

The following Python 3 packages should be installed prior to installing Curatr, which are available via PIP:

- NumPy: https://numpy.org
- Pandas: https://pandas.pydata.org
- PyMySQL: https://pypi.org/project/PyMySQL
- scikit-learn: https://scikit-learn.org/stable
- requests: https://docs.python-requests.org
- SolrClient: https://github.com/moonlitesolutions/SolrClient
- Gensim: https://radimrehurek.com/gensim
- ftfy: https://pypi.org/project/ftfy
- Passlib: https://pypi.org/project/passlib
- Flask: https://flask.palletsprojects.com/en/2.3.x/
- Flask-Login: https://flask-login.readthedocs.io/en/latest/
- NetworkX: https://networkx.org/
- NLTK: https://www.nltk.org/

Additional dependencies:
- MySQL: https://www.mysql.com (tested with 5.7.40 and 8.0.33)
- Apache Solr: https://solr.apache.org (tested with 8.11.2)
- A Java JDK supported by Apache Solr (tested with OpenJDK 17.0.7 and 19.0.1)

Frontend dependencies (loaded from CDN):
- Highcharts: https://www.highcharts.com (Ngram Viewer)
- vis-network: https://visjs.github.io/vis-network (Semantic Networks)

Dependencies for optional advanced network viewer:
- dash
- dash-bootstrap-components
- dash-cytoscape

## Platform Features

Curatr provides a range of tools for searching, browsing, and analysing the BL19 collection:

- **Collection Search**: a searchable index of over 12 million pages, filterable by author, title, year, classification, publication location, and document type, with sorting by relevance, date, or title.
- **Classification Index**: a browsable version of the hierarchical topical index used by the British Library from 1823 to 1985, from broad categories such as "Fiction" and "Geography" down to more fine-grained sub-topics.
- **Catalogue**: a sortable and searchable table of all books in the collection, browsable by title, author, and year of publication.
- **Authors**: browse the collection by author, with links to all associated volumes.
- **Ngram Viewer**: plot the frequency of one or more words across the collection over time, with the option to click through to the corresponding search results for any given year. Results can be exported as a CSV file.
- **Semantic Networks**: visualise conceptual relationships in the collection by constructing interactive semantic networks from seed words, with associated words identified using word embedding models.
- **Concordance**: identify every occurrence of a particular word or phrase within the collection, presented alongside its immediate linguistic context.
- **Word Lexicons**: create and manage curated lists of keywords related to a given research topic. Lexicons can be expanded automatically using a word embedding model to suggest semantically similar terms, and used to drive searches and sub-corpus exports.
- **Sub-Corpora**: define and export smaller, topic-specific sub-corpora of the collection, filtered thematically, chronologically, and by classification, for close reading and offline analysis.

## Acknowledgements

This work is part of the [VICTEUR project](https://projectvicteur.com/), which has received funding from the [European Research Council (ERC)](https://erc.europa.eu/) under the European Union’s Horizon 2020 research and innovation programme (grant agreement No 884951), and is being undertaken by members of the [UCD School of English, Drama and Film](http://www.ucd.ie/englishdramafilm/), in collaboration with researchers from the [Insight Research Ireland Centre for Data Analytics](http://www.insight-centre.org/) at the [UCD School of Computer Science](https://www.ucd.ie/cs/). The BL19 digitised book collection was provided by British Library Labs. Curatr is licensed under a [Creative Commons BY-NC-ND 4.0 Licence](https://creativecommons.org/licenses/by-nc-nd/4.0/).

