"""
Various functions for implementing Curatr's volume and segment close reading functionality.
"""
import urllib.parse, re
import logging as log
from flask import Markup, escape
from preprocessing.cleaning import tidy_title, tidy_authors, tidy_location, tidy_snippet, tidy_content
from preprocessing.cleaning import tidy_shelfmarks, tidy_publisher, tidy_edition, tidy_description

# --------------------------------------------------------------

def populate_volume(context, db, doc, spec, volume_id):
	query_string = spec["query"]
	quoted_query_string = urllib.parse.quote_plus(query_string)
	volume = max( doc["volume"], 1 )
	# Get extra details
	book_id = doc["book_id"]
	author_ids = db.get_book_author_ids(book_id)
	# Populate the template parameters with the volume metadata
	context["id"] = volume_id
	context["volume"] = volume
	context["max_volume"] = doc["max_volume"]
	context["title"] = tidy_title(doc.get("title", None))
	# context["location"] = tidy_location(doc.get("location_places", None))
	context["shelfmarks"] = tidy_shelfmarks(doc.get("shelfmarks", None))  
	context["edition"] = tidy_edition(doc.get("edition", None))
	context["description"] = tidy_description(doc.get("physical_descr", None))
	context["publisher"] = tidy_publisher(doc.get("publisher_full", None))
	# if safe_int( doc.get( "mudies_match" ) ) == 0:
	# 	context["mudies"] = "No matching author"
	# else:
	# 	context["mudies"] = tidy_content( doc.get("mudies_author",None))
	# 	if len(context["mudies"]) == 0:
	# 		context["mudies"] = "No matching author"		
	url_year = "%s/search?action=search&year_start=%s&year_end=%s" % (context.prefix, doc["year"], doc["year"])
	html_year = "<a href='%s'>%s</a>" % (url_year, doc["year"])
	context["year"] = Markup(html_year)
	# Add classifications, if any
	if "classification" in doc:
		if (doc["classification"] != "Uncategorised") and ( "subclassification" in doc ):
			context["classification"] = Markup("%s &mdash; %s" %( doc["classification"], doc["subclassification"]))
		else:
			context["classification"] = doc["classification"]
	else:
		context["classification"] = "Uncategorised"
	# Add author info
	if len(author_ids) == 0:
		# use the values from Solr
		context["authors"] = tidy_authors(doc.get("authors", None))
	else:
		# use richer author details
		author_html = ""
		for author_id in author_ids:
			if len(author_html) > 0:
				author_html += " &ndash; "
			author = db.get_cached_author(author_id)
			url_author = "%s/author?author_id=%s" % (context.prefix, author_id) 	
			author_html += "<a href='%s'>%s</a>" % (url_author, author["sort_name"])
		context["authors"] = Markup( author_html )
	# Add the main segment content
	content = tidy_content(doc["content"])
	html_text = str(escape(content))
	if len(html_text) == 0:
		html_text = "Volume text is empty."
	else:
		html_text = re.sub("[\n\r]+", "<br><br>", html_text)
		html_text = highlight_query(query_string, html_text)
	context["text"] = Markup(html_text)
	# Create the plain-text URL
	id_parts = volume_id.split("_")
	url_spec = "qwords=%s&field=%s&class=%s&subclass=%s" % (quoted_query_string, spec["field"], spec["class"], spec["subclass"])
	if spec["year_start"] > 0:
		url_spec += "&year_start=%d" % spec["year_start"]
	if spec["year_end"] < 2000:
		url_spec += "&year_end=%d" % spec["year_end"]
	context["url_bl_record"] = "http://explore.bl.uk/primo_library/libweb/action/display.do?frbrVersion=2&tabs=detailsTab&institution=BL&ct=display&fn=search&doc=BLL01%s&indx=1" % id_parts[0]
	context["url_similar"] = "%s/similar?volume_id=%s" % (context.prefix, volume_id) 	
	# Any other links?
	context["other_urls"] = ""
	if doc.get("url_pdf", None) != None:
		context["other_urls"] += "&nbsp;&nbsp;&mdash;&nbsp;&nbsp;<a href='%s' target='_blank'>Volume PDF</a>" % doc.get("url_pdf")
	if doc.get("url_images", None) != None:
		context["other_urls"] += "&nbsp;&nbsp;&mdash;&nbsp;&nbsp;<a href='%s' target='_blank'>Volume Images</a>"  % doc.get("url_images")
	context["other_urls"] = Markup(context["other_urls"])
	return context

def populate_segment(context, db, doc, spec, segment_id):
	""" Populate the main HTML context for displaying a segment's text """
	query_string = spec["query"]
	quoted_query_string = urllib.parse.quote_plus(query_string)
	segment = max(int(doc["segment"]), 1)
	max_segment = max(int(doc["max_segment"]), 1)
	volume = max(doc["volume"], 1)
	# Get extra details
	book_id = doc["book_id"]
	author_ids = db.get_book_author_ids(book_id)
	# Populate the template parameters with the segment metadata
	context["id"] = segment_id
	context["volume"] = volume
	context["max_volume"] = doc["max_volume"]
	context["segment"] = segment
	context["max_segment"] = max_segment
	context["title"] = tidy_title(doc.get("title", None))
	# context["location"] = tidy_location(doc.get("location_places", None))
	context["shelfmarks"] = tidy_shelfmarks(doc.get("shelfmarks", None)) 
	context["edition"] = tidy_edition(doc.get("edition", None))
	context["description"] = tidy_description(doc.get("physical_descr", None))
	context["publisher"] = tidy_publisher(doc.get("publisher_full", None))
	# if safe_int( doc.get( "mudies_match" ) ) == 0:
	# 	context["mudies"] = "No matching author"
	# else:
	# 	context["mudies"] = tidy_content( doc.get("mudies_author",None))
	# 	if len(context["mudies"]) == 0:
	# 		context["mudies"] = "No matching author"
	url_year = "%s/search?action=search&year_start=%s&year_end=%s&type=segment" % (context.prefix, doc["year"], doc["year"])
	html_year = "<a href='%s'>%s</a>" % (url_year, doc["year"])
	context["year"] = Markup(html_year)
	# Add classifications, if any
	if "classification" in doc:
		if (doc["classification"] != "Uncategorised") and ("subclassification" in doc):
			context["classification"] = Markup("%s &mdash; %s" %(doc["classification"], doc["subclassification"]))
		else:
			context["classification"] = doc["classification"]
	else:
		context["classification"] = "Uncategorised"
	# Add author info
	if len(author_ids) == 0:
		# use the values from Solr
		context["authors"] = tidy_authors(doc.get("authors", None))
	else:
		# use richer author details
		author_html = ""
		for author_id in author_ids:
			if len(author_html) > 0:
				author_html += " &ndash; "
			author = db.get_cached_author(author_id)
			url_author = "%s/author?author_id=%s" % (context.prefix, author_id) 	
			author_html += "<a href='%s'>%s</a>" % (url_author, author["sort_name"])
		context["authors"] = Markup(author_html)		
	# Add the main segment content
	content = tidy_content(doc["content"])
	html_text = str(escape(content))
	if len(html_text) == 0:
		html_text = "Segment text is empty."
	else:
		html_text = re.sub("[\n\r]+", "<br><br>", html_text)
		html_text = highlight_query(query_string, html_text)
		if html_text[0].islower():
			html_text = "&hellip;" + html_text
		if segment < max_segment and not html_text[-1] in ".>":
			html_text += "&hellip;"
	context["text"] = Markup(html_text)
	# Create the full-text URL
	id_parts = segment_id.split("_")
	url_spec = "qwords=%s&field=%s&class=%s&subclass=%s&location=%s" % (quoted_query_string, spec["field"], spec["class"], spec["subclass"], spec["location"])
	if spec["year_start"] > 0:
		url_spec += "&year_start=%d" % spec["year_start"]
	if spec["year_end"] < 2000:
		url_spec += "&year_end=%d" % spec["year_end"]
	# Create extra URLs
	context["url_volume"] = "%s/volume?id=%s_%02d&%s" % ( context.prefix, id_parts[0], volume, url_spec ) 	
	context["url_bl_record"] = "http://explore.bl.uk/primo_library/libweb/action/display.do?frbrVersion=2&tabs=detailsTab&institution=BL&ct=display&fn=search&doc=BLL01%s&indx=1" % id_parts[0]
	# Any other links?
	context["other_urls"] = ""
	if doc.get("url_pdf", None) != None:
		context["other_urls"] += "&nbsp;&nbsp;&mdash;&nbsp;&nbsp;<a href='%s' target='_blank'>Volume PDF</a>" % doc.get("url_pdf")
	if doc.get("url_images", None) != None:
		context["other_urls"] += "&nbsp;&nbsp;&mdash;&nbsp;&nbsp;<a href='%s' target='_blank'>Volume Images</a>"  % doc.get("url_images")
	context["other_urls"] = Markup(context["other_urls"])
	# Add the Next/Previous/Full-text links
	pagination_html = ""
	# first segment?
	if segment < 2:
		pagination_html += "<li class='page-item disabled'><a href='#' class='btn btn-primary link-button'>Previous Segment</a></li>\n"
	else:
		id_previous = "%s_%s_%06d" % (id_parts[0], id_parts[1], segment-1)
		url_previous = "%s/segment?id=%s&qwords=%s&%s" % (context.prefix, id_previous, quoted_query_string, url_spec)
		pagination_html += "<li class='page-item'><a href='%s' class='btn btn-primary link-button'>Previous Segment</a></li>\n" % url_previous
	# last segment?
	if segment >= max_segment:
		pagination_html += "<li class='page-item disabled'><a href='#' class='btn btn-primary link-button>Next Segment</a></li>\n"
	else:
		id_next = "%s_%s_%06d" % (id_parts[0], id_parts[1], segment+1 )
		url_next = "%s/segment?id=%s&qwords=%s&%s" % (context.prefix, id_next, quoted_query_string, url_spec)
		pagination_html += "<li class='page-item'><a href='%s' class='btn btn-primary link-button'>Next Segment</a></li>\n" % url_next
	context["pagination"] = Markup(pagination_html)
	return context

# --------------------------------------------------------------

def highlight_query(query_string, text):
	if len(query_string) == 0 or query_string == "*":
		return text
	pre_highlight = "<span class='highlight'>"
	post_highlight = "</span>"
	# need to remove quotes
	escaped_query_string = re.escape(query_string.replace( '"', '' ))
	regex = re.compile(r"(\b%s\b)" % escaped_query_string, re.I)
	output = ""
	i, m = 0, None
	for m in regex.finditer(text):
		output += "".join([text[i:m.start()], pre_highlight, text[m.start():m.end()], post_highlight])
		i = m.end()#
	# no matches? just return the original text
	if m is None:
		return text
	return output + text[m.end():]

