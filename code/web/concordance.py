"""
Various functions for implementing Curatr's concordance analysis functionality.
"""
import urllib.parse, re
import logging as log
from flask import Markup, abort
# project imports
from preprocessing.cleaning import tidy_title, tidy_authors, tidy_snippet, tidy_location_places
from web.util import parse_arg_int, parse_arg_bool
from web.format import field_name_map, field_plural_map

# --------------------------------------------------------------

# TODO: make these settings configurable
context_size = 100
max_snippets = 50
frag_size = 500

def populate_concordance_results(context, db, current_solr, spec):
	""" Perform main HTML formatting for the Curatr concordance results page """
	# no query? this shouldn't happen with concordance
	if len(spec["query"]) == 0:
		spec["query"] = "contagion"
	query_string = spec["query"]
	quoted_query_string = urllib.parse.quote_plus(query_string)
	num_snippets = max_snippets
	start = max(parse_arg_int(context.request, "start", 0), 0)
	current_page = max(int(start / current_solr.page_size) + 1, 1)
	filters = {}
	# have any sorting parameters been specified?
	if spec["sort_field"] is None:
		sort_params = None
	else:
		sort_params = spec["sort_field"]
		if spec["sort_order"] is None:
			sort_params += " asc"
		else:
			sort_params += " " + spec["sort_order"]
	# year range for search
	filters["year"] = "[%d TO %d]" % (spec["year_start"], spec["year_end"])
	# has a particular classification or subclassification been specified?
	if spec["class"].lower() != "all":
		# need to quote due to spaces?
		if " " in spec["class"] and not spec["class"][0] == '"':
			filters["classification"] = '"%s"' % spec["class"]
		else:
			filters["classification"] = spec["class"]
	if spec["subclass"].lower() != "all":
		# need to quote due to spaces?
		if " " in spec["subclass"] and not spec["subclass"][0] == '"':
			filters["subclassification"] = '"%s"' % spec["subclass"]
		else:
			filters["subclassification"] = spec["subclass"]
		# NB: remove the class specification for now
		if "classification" in filters:
			del filters["classification"]
	# has any publication location been specified?
	if spec["location"].lower() != "all":
		# need to quote due to spaces?
		if " " in spec["location"] and not spec["location"][0] == '"':
			filters["location_places"] = '"%s"' % spec["location"]
		else:
			filters["location_places"] = spec["location"]
	# perform the actual Solr search
	field_name = "all"
	res = current_solr.query(query_string, field_name, filters, start, True, num_snippets, sort=sort_params, frag_size=frag_size)
	# failed to connect to Solr?
	if res is None:
		abort(500, "Cannot connect to Solr search server to perform search")
	snippets = res.data.get("highlighting",{})
	num_total_results = res.get_num_found()
	snum_total_results = "{:,}".format(num_total_results)
	
	# create summary line before the results
	was_were = "were"
	if num_total_results == 1:
		was_were = "was"	
	if spec["field"].lower() == "all":
		if num_total_results == 1:
			field_description = "segment"
		else:
			field_description = "segments"
	else:
		field_description = "segment %s" % field_plural_map[spec["field"]]
	summary = "<b>Concordance Analysis</b>&nbsp;&mdash;&nbsp;"
	context["has_results"] = (num_total_results > 0)
	if current_page == 1:
		if num_total_results == 0:
			summary += "No matching results found"
		else:
			summary += "<strong>%s</strong> matching %s %s found" % (snum_total_results, field_description, was_were)
		if query_string != "*" and len(query_string) > 0:
			summary += " for <span class='highlight'><b>%s</b></span>" % query_string
	else:
		if num_total_results == 0:
			summary += "No matching results found"
		else:
			summary += "Page <strong>%d</strong> of <strong>%s</strong> matching %s" % (current_page, snum_total_results, field_description)
		if query_string != "*":
			summary += " for <span class='highlight'><strong>%s</strong></span>" % query_string
	if spec["class"].lower() == "all":
		# do we still have a subclass specified?
		if spec["subclass"].lower() != "all":
			summary += " in the sub-classification <strong>%s</strong>" % spec["subclass"]
		else:
			summary += ""
	else:
		summary += " in the classification <strong>%s</strong>" % spec["class"]
		# any subclass?
		if spec["subclass"].lower() != "all":
			summary += " (<strong>%s</strong>)" % spec["subclass"]

	# create the link URLs
	page_url_suffix = "field=%s&class=%s&subclass=%s" % (spec["field"], spec["class"], spec["subclass"])
	if not spec["sort_field"] is None:
		page_url_suffix += "&sort=" + spec["sort_field"]
		if not spec["sort_order"] is None:
			page_url_suffix += "-" + spec["sort_order"]
	if spec["year_start"] > 0:
		page_url_suffix += "&year_start=%d" % spec["year_start"]
		summary += " from %d" % spec["year_start"]
	if spec["year_end"] < 2000:
		page_url_suffix += "&year_end=%d" % spec["year_end"]
		# don't add if it's a single year
		if spec["year_start"] != spec["year_end"]:
			summary += " until %d" % spec["year_end"]
	elif spec["year_start"] > 0:
		summary += " onwards"
	# only in a specified location?
	if spec["location"] != "" and spec["location"].lower() != "all":
		page_url_suffix += "&location=%s" % urllib.parse.quote_plus(spec["location"])
		summary += " published in %s" % spec["location"]
	context["summary"] = Markup(summary)

	# do we need search suggestions?
	suggest = parse_arg_bool(context.request, "suggest", False)
	suggestions = []
	if suggest and len(spec["query"]) > 1:
		page_url_suffix += "&suggest=True"
		tidy_query = re.sub("[^a-zA-Z0-9_]", " ", spec["query"]).strip().lower()
		parts = re.split("\s+", tidy_query)
		query_words = []
		for p in parts:
			if len(p) > 1:
				query_words.append(p)
		if len(query_words) > 0:
			suggestions = context.core.aggregate_recommend_words(query_words, [], 5, True)
	if len(suggestions) > 0:
		context["search_suggestions"] = True
		suggestion_html = ""
		for word in suggestions:
			suggest_url = "%s/concordance?qwords=%s&%s" % (context.prefix, word, page_url_suffix)
			if len(suggestion_html) > 0:
				suggestion_html += "&nbsp;&ndash;&nbsp;"
			suggestion_html += "<a href='%s'>%s</a>" % (suggest_url, word)
		context["suggestions"] = Markup(suggestion_html)
	else:
		context["search_suggestions"] = False

	# Create the search results 
	context["results"] = Markup(format_concordance_results(context, db, spec, res, snippets))
	# do we need pagination?
	page_url_prefix = "%s/concordance?qwords=%s&%s" % (context.prefix, quoted_query_string, page_url_suffix)
	pagination_html = ""
	if num_total_results > current_solr.page_size:
		max_pages = int(num_total_results/current_solr.page_size)
		if num_total_results % current_solr.page_size > 0:
			max_pages += 1
		if current_page <= 5:
			min_page_index = 1
		else:
			min_page_index = current_page - 5
		max_page_index = min(min_page_index + 9, max_pages)
		# first page of results?
		if current_page == 1:
			pagination_html += "<li class='page-item disabled'><a href='#' class='page-link'>Previous</a></li>\n"
		else:
			page_index = current_page - 1
			page_start = (page_index-1) * current_solr.page_size
			page_url_string = "%s&start=%d" % (page_url_prefix, page_start)
			pagination_html += "<li class='page-item'><a href='%s' class='page-link'>Previous</a></li>\n" % page_url_string
		# numbered links
		for page_index in range(min_page_index,max_page_index+1):
			if current_page == page_index:
				pagination_html += "<li class='page-item active'><a href='#' class='page-link'>%d</a></li>\n" % page_index
			else:
				page_start = (page_index-1) * current_solr.page_size
				page_url_string = "%s&start=%d" % (page_url_prefix, page_start)
				pagination_html += "<li class='page-item'><a href='%s' class='page-link'>%d</a></li>\n" % (page_url_string, page_index)
		# last page of results?
		if current_page == max_pages:
			pagination_html += "<li class='page-item disabled'><a href='#' class='page-link'>Next</a></li>\n"
		else:
			page_index = current_page + 1
			page_start = (page_index-1) * current_solr.page_size
			page_url_string = "%s&start=%d" % (page_url_prefix, page_start)
			pagination_html += "<li class='page-item'><a href='%s' class='page-link'>Next</a></li>\n" % page_url_string
	context["pagination"] = Markup(pagination_html)
	return context

def tidy_concordance_snippet(snippet):
	if snippet is None:
		return ""
	snippet = re.sub("\s+", " ", snippet).strip()
	# trim the start of the snippet
	c = snippet[0]
	while not ( c.isalnum() or c == "<" ):
		if len(snippet) < 2:
			break
		snippet = snippet[1:]
		c = snippet[0]
	# TODO: better fix for inaccurate tags.
	snippet = snippet.replace("<i ", " ")
	snippet = snippet.replace("<b ", " ")
	return snippet

def tidy_concordance_left(snippet):
	""" Tidy the left context string for concordance results """
	return re.sub(r'[^a-zA-Z0-9]+$', '', snippet)

def tidy_concordance_right(snippet):
	""" Tidy the right context string for concordance results """
	return re.sub(r'^[^a-zA-Z0-9]+', '', snippet)

def remove_tags(snippet):
	""" Simple function to remove HTML tags from concodrance results """
	clean = ""
	in_tag = False
	for c in snippet:
		if c == "<":
			in_tag = True
		elif c == ">":
			in_tag = False
		elif not in_tag:
			clean += c
	return clean.strip()

def format_concordance_results(context, db, spec, res, snippets):
	""" Perform HTML formatting for the individual Curatr concordance results """
	# quote any strings that need to be used subsequently in URLs
	quoted_query_string = urllib.parse.quote_plus(spec["query"])
	quoted_class = urllib.parse.quote_plus(spec["class"])
	quoted_subclass = urllib.parse.quote_plus(spec["subclass"])
	quoted_location= urllib.parse.quote_plus(spec["location"])
	# construct required URL prefixes
	target_page = "segment"
	field_name = "all"
	result_url_prefix = "%s/%s?qwords=%s&field=%s&class=%s&subclass=%s&location=%s" % (context.prefix, target_page, quoted_query_string, 
		field_name, quoted_class, quoted_subclass, quoted_location)
		# process results
	html = ""
	for doc in res.docs:
		# display the snippets for this doc, if available
		if (not doc["id"] in snippets) or ( len(snippets[doc["id"]]) == 0 ):
			pass
		else:
			for snippet in snippets[doc["id"]].get("content",[]):
				# no snippet?
				if snippet is None or len(snippet) == 0:
					continue
				snippet = tidy_concordance_snippet(snippet)
				target1 = "<span class='highlight'>"
				target2 = "</span>"
				snippet_num = 0
				while snippet.count(target1) > 0:
					snippet_num += 1
					pos = snippet.index(target1)
					# get the left context
					left = snippet[max(0,pos-context_size):pos]
					left = remove_tags(left)
					left = tidy_concordance_left(left)
					# get the right context
					snippet = snippet[pos+len(target1):].strip()
					pos = snippet.index(target2)
					if pos == -1:
						continue
					matched_query = snippet[0:pos]
					right = snippet[pos+len(target2):min(pos+len(target2)+context_size, len(snippet))]
					right = remove_tags(right)
					right = tidy_concordance_right(right)
					url_result = "%s&id=%s" % (result_url_prefix, doc["id"])
					html += "<tr>\n"
					html += "<td class='text-center'>%d</td>" % doc["year"]
					html += "<td class='context truncate-start'><div>%s</div></td>" % left
					html += "<td class='text-center'><a href='%s' class='result-title'>%s</a></td>" % (url_result, matched_query)
					html += "<td class='context truncate-end'><div>%s</div></td>" % right
					html += "</tr>\n"
	return html

def format_concordance_resultsx(context, db, spec, res, snippets):
	""" Perform HTML formatting for the individual Curatr concordance results """
	html = ""
	# quote any strings that need to be used subsequently in URLs
	quoted_query_string = urllib.parse.quote_plus(spec["query"])
	quoted_class = urllib.parse.quote_plus(spec["class"])
	quoted_subclass = urllib.parse.quote_plus(spec["subclass"])
	quoted_location= urllib.parse.quote_plus(spec["location"])
	# construct required URL prefixes
	target_page = "segment"
	field_name = "all"
	result_url_prefix = "%s/%s?qwords=%s&field=%s&class=%s&subclass=%s&location=%s" % (context.prefix, target_page, quoted_query_string, 
		field_name, quoted_class, quoted_subclass, quoted_location)
	if spec["year_start"] > 0:
		result_url_prefix += "&year_start=%d" % spec["year_start"]
	if spec["year_end"] < 2000:
		result_url_prefix += "&year_end=%d" % spec["year_end"]
	# generate HTML	for each result
	for i, doc in enumerate(res.docs):
		doc_id = doc["id"]
		title = tidy_title(doc["title"])
		year = int(doc["year"])
		volume = int(doc["volume"])
		max_volume = int(doc["max_volume"])
		segment = int(doc["segment"])
		url_result = "%s&id=%s" % (result_url_prefix, doc_id)
		html += "<p class='search-result'>\n"
		html += "<div class='search-result-meta'>\n"
		html += "<a href='%s' class='result-title'>%s&nbsp;&nbsp;(%d)&nbsp;&nbsp;&ndash;&nbsp;&nbspVolume %d, Segment %d</a>\n" % (url_result, title, year, volume, segment)
		html += "</div>\n"
		# add all of the relevant search result snippets
		snippet_content = []
		for snippet in snippets[doc["id"]].get("content",[]):
			# no snippet?
			if snippet is None or len(snippet) == 0:
				snippet = "No text available."
			else:
				snippet = tidy_snippet(snippet)
			snippet_content.append(snippet)
		# actually format the snippets
		html += "<ul class='search-snippets'>\n"
		for snippet in snippet_content:
			html += "<li class='snippet-text'>%s</li>\n" % snippet
		html += "</ul>\n"
		# finished result
		html += "</p>\n"
	return html
