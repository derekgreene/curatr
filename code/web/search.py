"""
Various functions for implementing Curatr's web search functionality.
"""
import urllib.parse, re
import logging as log
from flask import Markup, abort
# project imports
from preprocessing.cleaning import tidy_title, tidy_authors, tidy_snippet, tidy_location_places
from web.util import parse_arg_int, parse_arg_bool
from web.format import field_name_map, field_plural_map

# --------------------------------------------------------------

def parse_search_request(req):
	""" Parse all of the parameters from a search request response """
	spec = {}
	# query words
	spec["query"] = req.args.get("qwords", default = "").strip()
	# what type of document?
	spec["type"] = req.args.get("type", default = "volume").strip().lower()
	# which field?
	spec["field"] = req.args.get("field", default = "").strip().lower()
	if (not spec["field"] in field_name_map) or (spec["field"] == "*"):
		spec["field"] = "all"
	if spec["field"] != "all" and spec["query"].startswith(spec["field"] +":"):
		spec["query"] = spec["query"][len(spec["field"])+1:]
	# sort information
	sort_info = req.args.get("sort", default=None)
	if sort_info is None:
		spec["sort_field"], spec["sort_order"] = None, None
	else:
		parts = sort_info.lower().strip().rsplit("-", 1)
		# just relevance? then treat as no sorting
		if parts[0] == "rel" or parts[0] == "relevance" or parts[0] == "":
			spec["sort_field"], spec["sort_order"] = None, None
		# otherwise parts the sort field and the order
		else:
			if len(parts) == 1:
				spec["sort_field"], spec["sort_order"] = parts[0], "asc"
			else:
				spec["sort_field"], spec["sort_order"] = parts[0].strip(), parts[1].strip()
				if not spec["sort_order"] in ["asc", "desc"]:
					spec["sort_order"] = "asc"
	# date range
	spec["year_start"] = max(0, parse_arg_int(req, "year_start", 0))
	spec["year_end"] = max(0, parse_arg_int(req, "year_end", 2000))
	# just in case the user has specified these in the wrong order, swap them
	if spec["year_start"] > spec["year_end"]:
		spec["year_start"], spec["year_end"] = spec["year_end"], spec["year_start"]
	spec["class"] = req.args.get("class", default = "all").strip()
	if spec["class"] is None or len(spec["class"]) < 2:
		spec["class"] = "All"
	spec["subclass"] = req.args.get("subclass", default = "all").strip()
	if spec["subclass"] is None or len(spec["subclass"]) < 2:
		spec["subclass"] = "All"
	# just in case a specific book_id was specified
	spec["book_id"] = req.args.get("book_id", default = "").strip()
	# location name specified? NB: convert to title case
	spec["location"] = req.args.get("location", default = "").strip().title()
	if len(spec["location"]) == 0 or spec["location"] == "All" or spec["location"] == "*":
		spec["location"] = "all"
	# lexicon id specified?
	spec["lexicon_id"] = req.args.get("lexicon_id", default = "").strip()
	# looking for a Mudie's library match?
	mudies_match = req.args.get("mudies_match", default = "false").lower().strip()
	if mudies_match in [ "true", "yes", "1" ]:
		spec["mudies_match"] = True
	else:
		spec["mudies_match"] = False
	return spec

def format_search_results(context, db, spec, res, snippets, is_segments = False, verbose = True, max_title_length = 200):
	""" Perform HTML formatting for the individual Curatr search results """
	html = ""
	# quote any strings that need to be used subsequently in URLs
	quoted_query_string = urllib.parse.quote_plus(spec["query"])
	quoted_class = urllib.parse.quote_plus(spec["class"])
	quoted_subclass = urllib.parse.quote_plus(spec["subclass"])
	quoted_location= urllib.parse.quote_plus(spec["location"])
	# construct required URL prefixes
	if is_segments:
		target_page = "segment"
	else:
		target_page = "volume"
	result_url_prefix = "%s/%s?qwords=%s&field=%s&class=%s&subclass=%s&location=%s" % (context.prefix, target_page, quoted_query_string, 
		spec["field"], quoted_class, quoted_subclass, quoted_location)
	if spec["year_start"] > 0:
		result_url_prefix += "&year_start=%d" % spec["year_start"]
	if spec["year_end"] < 2000:
		result_url_prefix += "&year_end=%d" % spec["year_end"]
	# generate HTML	for each result
	for i, doc in enumerate(res.docs):
		doc_id = doc["id"]
		title = tidy_title(doc["title"])
		if len(title) > max_title_length:
			title = title[0:max_title_length] + "&hellip;"
		year = int(doc["year"])
		volume = int(doc["volume"])
		max_volume = int(doc["max_volume"])
		segment = int(doc["segment"])
		url_result = "%s&id=%s" % (result_url_prefix, doc_id)
		html += "<p class='search-result'>\n"
		html += "<div class='search-result-meta'>\n"
		# add extra metadata?
		if verbose:
			html += "<a href='%s' class='result-title'>%s" % (url_result, title)
			if is_segments:
				if volume == 1 and max_volume == 1:
					html += "&nbsp;&nbsp;&ndash;&nbsp;&nbsp;Segment %d" % (segment)
				else:
					html += "&nbsp;&nbsp;&ndash;&nbsp;&nbsp;Volume %d, Segment %d" % (volume, segment)
			else:
				if max_volume > 1:
					html += "&nbsp;&nbsp;&ndash;&nbsp;&nbsp;Volume %d" % (volume)
			html += "</a>\n"
			# do we have author information?
			if "authors" in doc:
				sauthors = tidy_authors(doc["authors"])
			else:
				sauthors = "Unknown author"
			# do we have place information?
			if "location_places" in doc:
				html += "<div>%s &ndash; %s &ndash; %s</div>\n" % (sauthors, year, tidy_location_places(doc["location_places"]))
			else:
				html += "<div>%s &ndash; %s</div>\n" % (sauthors, year)
		# just add the primary metadata
		else:
			if is_segments:
				html += "<a href='%s' class='result-title'>%s&nbsp;&nbsp;(%d)&nbsp;&nbsp;&ndash;&nbsp;&nbspVolume %d, Segment %d</a>\n" % (url_result, title, year, volume, segment)
			else:
				html += "<a href='%s' class='result-title'>%s&nbsp;&nbsp;(%d)&nbsp;&nbsp;&ndash;&nbsp;&nbspVolume %d</a>\n" % (url_result, title, year, volume)
		html += "</div>\n"
		# add all of the relevant search result snippets
		snippet_content = []
		if (not doc["id"] in snippets) or (len(snippets[doc["id"]]) == 0):
			snippet = None
			if not is_segments:
				snippet = db.get_volume_extract(doc_id)
				if not snippet is None:
					snippet = tidy_snippet(snippet)
			if snippet is None or len(snippet) == 0:
				snippet_content.append("No matching text content for the query term.")
			else:
				snippet_content.append(snippet)
		else:
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

def populate_search_results(context, db, current_solr, spec):
	""" Perform main HTML formatting for the Curatr search results page """
	# no query? search for everything
	if len(spec["query"]) == 0:
		spec["query"] = "*"
	query_string = spec["query"]
	quoted_query_string = urllib.parse.quote_plus(query_string)
	# dealing with volumes or segments?
	if spec["type"].lower() == "segment":
		is_segments = True
	else:
		is_segments = False
	# create the Solr parameters
	start = max(parse_arg_int(context.request, "start", 0), 0)
	current_page = max(int(start / current_solr.page_size) + 1, 1)
	num_snippets = parse_arg_int(context.request, "snippets", 0)
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
	# TODO: filter by Mudie's library?
	# if spec["mudies_match"]:
	# 	filters["mudies_match"] = 1
	# has any specific book_id been specified?
	if spec["book_id"] != "":
		filters["book_id"] = spec["book_id"]
	# has any lexicon been used for this search?
	lexicon = None
	if spec["lexicon_id"] != "":
		lexicon = db.get_lexicon(spec["lexicon_id"])
		# not a valid lexicon?
		if lexicon is None:
			abort(403, "Cannot find specified lexicon in the database (lexicon_id=%s)" % spec["lexicon_id"])
		# not owned by the current user?
		if lexicon["user_id"] != context.user_id:
			abort(403, "You do not own this lexicon (lexicon_id=%s)" % spec["lexicon_id"])
		lexicon_url = "%s/lexicon?action=edit&lexicon_id=%s" % (context.prefix, spec["lexicon_id"])
	# perform the actual Solr search
	res = current_solr.query(query_string, spec["field"], filters, start, True, num_snippets, sort=sort_params)
	# failed to connect to Solr?
	if res is None:
		abort(500, "Cannot connect to Solr search server to perform search")
	snippets = res.data.get("highlighting",{})
	num_total_results = res.get_num_found()
	snum_total_results = "{:,}".format(num_total_results)
	# Create summary line before search results
	was_were = "were"
	if num_total_results == 1:
		was_were = "was"	
	if is_segments:
		if spec["field"].lower() == "all":
			if num_total_results == 1:
				field_description = "segment"
			else:
				field_description = "segments"
		else:
			field_description = "segment %s" % field_plural_map[spec["field"]]
	else:
		if spec["field"].lower() == "all":
			if num_total_results == 1:
				field_description = "volume"
			else:
				field_description = "volumes"
		else:
			field_description = "volume %s" % field_plural_map[spec["field"]]
	if current_page == 1:
		if num_total_results == 0:
			summary = "No matching results found"
		else:
			summary = "<strong>%s</strong> matching %s %s found" % (snum_total_results, field_description, was_were)
		if lexicon is None:
			if query_string != "*" and len(query_string) > 0:
				summary += " for <span class='highlight'><b>%s</b></span>" % query_string
		else:
			summary += " for the lexicon <b><a href='%s'>%s</a></b></span>" % (lexicon_url, lexicon["name"])
	else:
		if num_total_results == 0:
			summary = "No matching results found"
		else:
			summary = "Page <strong>%d</strong> of <strong>%s</strong> matching %s" % (current_page, snum_total_results, field_description)
		if lexicon is None:
			if query_string != "*":
				summary += " for <span class='highlight'><strong>%s</strong></span>" % query_string
		else:
			summary += " for the lexicon <b><a href='%s'>%s</a></b></span>" % (lexicon_url, lexicon["name"])
	# only in a single book?
	if spec["book_id"] != "":
		# can we find the title for this book from solr?
		book = current_solr.query_book(spec["book_id"])
		if book is None or not "title" in book:
			summary += " for the book with identifier <strong>%s</strong>" % spec["book_id"]
		else:
			summary += " for the book <strong>%s</strong>" % tidy_title(book["title"])
	else:
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
	# filtered by Mudie's library
	if spec["mudies_match"]:
		summary += ", filtered by Mudie's library matches"
	# create the link URLs
	page_url_suffix = "field=%s&class=%s&subclass=%s&type=%s" % (spec["field"], spec["class"], spec["subclass"], spec["type"])
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
	if spec["lexicon_id"] != "":
		page_url_suffix += "&lexicon_id=%s" % urllib.parse.quote_plus(spec["lexicon_id"])
	if spec["mudies_match"]:
		page_url_suffix += "&mudies_match=true"
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
			suggest_url = "%s/search?qwords=%s&%s" % (context.prefix, word, page_url_suffix)
			if len(suggestion_html) > 0:
				suggestion_html += "&nbsp;&ndash;&nbsp;"
			suggestion_html += "<a href='%s'>%s</a>" % (suggest_url, word)
		context["suggestions"] = Markup(suggestion_html)
	else:
		context["search_suggestions"] = False
	# add the search options?
	# note we don't provide this if we are showing all volumes for a classification
	if spec["query"] == "*" and "classification" in filters:
		context["search_options"] = False
	else:
		context["search_options"] = True
		# add selected values for document type dropdown
		if is_segments:
			context["selected_segment"] = "selected"
		else:
			context["selected_volume"] = "selected"
		# add selected values for sort order dropdown
		if spec["sort_field"] is None or spec["sort_field"] == "":
			context["selected_sort_rel"] = "selected"
		else:
			if spec["sort_field"] == "year":
				if spec["sort_order"] == "desc":
					context["selected_sort_year_desc"] = "selected"
				else:
					context["selected_sort_year_asc"] = "selected"
			elif spec["sort_field"] == "title":
				if spec["sort_order"] == "desc":
					context["selected_sort_title_desc"] = "selected"
				else:
					context["selected_sort_title_asc"] = "selected"
			else:
				context["selected_sort_rel"] = "selected"
	# Create the search results 
	context["results"] = Markup(format_search_results(context, db, spec, res, snippets, is_segments=is_segments))
	# do we need pagination?
	page_url_prefix = "%s/search?qwords=%s&%s" % (context.prefix, quoted_query_string, page_url_suffix)
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
	# create the export URL
	# note we need to remove the old page start position from the previous URL
	parts = context.request.url.split("?", 2)
	tidy_params = re.sub("&start=[0-9]+", "", parts[1], flags=re.IGNORECASE)
	if len(parts) > 1:
		context["url_export"] = "%s/export?%s&total_results=%d" % (context.prefix, tidy_params, num_total_results)
	else:
		log.warning("Warning: Cannot create search export URL from %s" % context.request.url)
	# create the search modification URL
	if len(parts) > 1:
		context["url_modify"] = "%s/search?action=modify&%s" % (context.prefix, tidy_params)
		# remove multiple actions, in case they exist
		context["url_modify"] = context["url_modify"].replace("&action=search", "")
	else:
		log.warning("Warning: Cannot create search modification URL from %s" % context.request.url)
	# create the document type URLs
	# note we need to remove the old type spec from the previous URL too
	tidy_params_type = re.sub("&type=[a-z]+", "", tidy_params, flags=re.IGNORECASE)	
	for opt in ["volume", "segment"]:
		var_name = "link_type_%s" % opt
		context[var_name] = "%s/search?%s&type=%s" % (context.prefix, tidy_params_type, opt)
	# create the sorting URLs
	# note we need to remove the old sorting spec from the previous URL too
	tidy_params_sort = re.sub("&sort=[a-z\-]+", "", tidy_params, flags=re.IGNORECASE)	
	for opt in ["rel", "year-asc", "year-desc", "title-asc", "title-desc"]:
		var_name = "link_sort_%s" % (opt.replace("-", "_"))
		context[var_name] = "%s/search?%s&sort=%s" % (context.prefix, tidy_params_sort, opt)
	return context
