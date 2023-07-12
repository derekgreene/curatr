"""
Implementation of a convenience wrapper for accessing Solr, via the SolrClient library.
"""
import logging as log
from SolrClient import SolrClient

# --------------------------------------------------------------

class SolrWrapper:
	def __init__(self, client, core_name):
		self.client = client
		self.host = client.host
		self.core_name = core_name
		# search settings
		self.page_size = 10
		self.num_snippets = 3
		self.fragsize = 300

	def query(self, query_string, field, filters=[], start=0, highlight=True, num_snippets=0, page_size=0, fl=None, sort=None):
		""" Perform a query on the current Solr core using the specified criteria """
		# remove problematic square brackets
		query_string = query_string.replace("[", "").replace("]", "")
		# querying a non-standard field?
		if field != "all":
			query_string = "%s:%s" % (field,query_string)
		# basic Solr parameters
		if page_size < 1:
			page_size = self.page_size
		params = { "q" : query_string, "rows" : page_size, "start" : start }
		# need to add highlighting parameters?
		if highlight:
			params["highlight"] = True
			params["hl"] = True
			params["hl.fragsize"] = self.fragsize
			params["hl.fl"] = "content"
			params["hl.usePhraseHighlighter"] = True
			params["hl.simple.pre"] = "<span class='highlight'>"
			params["hl.simple.post"] = "</span>"
			if num_snippets < 1:
				num_snippets = self.num_snippets
			params["hl.snippets"] = num_snippets
		# add custom filters
		fq = ""
		for key in filters:
			if len(fq) > 0:
				fq += " AND "
			fq += "+%s:%s" % ( key, filters[key] )
		if len(fq) > 0:
			params["fq"] = fq
		# was a return field list specified?
		if not fl is None:
			params["fl"] = ",".join( fl )
		# perform the search
		log.debug("Running query: %s" % str(params) )
		try:
			res = self.client.query(self.core_name, params, sort=sort)
		except Exception as e:
			log.error("Error: Failed to make Solr search query")
			log.error(str(e))
			log.error("Query was: %s" % str(params))
			return None
		return res

	def query_document(self, segment_id):
		""" Get back details for a single segment document """
		params = {"q" : segment_id}
		try:
			res = self.client.query(self.core_name, params)
		except Exception as e:
			log.error("Error: Failed to make Solr document query")
			log.error( str(e) )
			return None
		if res.get_results_count() != 1:
			log.warning("Did not find matching segment for %s" % segment_id )
			return None
		return res.docs[0]

	def query_book(self, book_id):
		""" Get back details for a single book document """
		# need to convert a book_id to a segment_id
		# e.g. 000485481 -> 000485481_01_000001
		segment_id = "%s_01_000001" % book_id
		return self.query_document(segment_id)

	def index(self, documents):
		""" Add a set of documents to the current core """
		self.client.index(self.core_name, documents)

	def commit(self):
		""" Commit any recent changes which have been made to the current core """
		self.client.commit(self.core_name, openSearcher=True)

	def ping(self):
		""" Perform a simple query to ensure the Solr server is alive """
		result = self.query("test", field="all", page_size=1, num_snippets=1, highlight=False)		
		return (result is not None)