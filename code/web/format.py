"""
Generall formatting fuctions for display Curatr web content
"""
import urllib.parse
import logging as log
# project imports
from preprocessing.cleaning import tidy_extract, tidy_authors, tidy_location_places

# --------------------------------------------------------------

field_name_map = {  "all" : "Full Text", "title_text" : "Title", "authors_text" : "Author", "location_text" : "Location" }
field_plural_map = {  "title_text" : "titles", "authors_text" : "authors", "location_text" : "locations" }
type_name_map = {  "volume" : "Volumes", "segment" : "Segments" }

# --------------------------------------------------------------

def format_classification_links(context):
	""" Generate HTML formatting for links for book classifications on the classification index page. """
	html = ""
	class_counts = context.core.cache["class_counts"]
	class_names = sorted(list(class_counts.keys()))
	for name in class_names:
		if name.lower() == "all" or class_counts[name] == 0:
			continue
		label = name.replace("?","'")
		escaped_name = urllib.parse.quote_plus(name)
		url = '%s/search?qwords=*&class="%s"&type=volume' % (context.prefix, escaped_name)
		if class_counts[name] == 1:
			html += "\t\t\t<li class='classification'><a href='%s'>%s</a> (1 book)\n" % (url, label)
		else:
			fmt_count = "{:,}".format(class_counts[name])
			html += "\t\t\t<li class='classification'><a href='%s'>%s</a> (%s books)\n" % (url, label, fmt_count)
	return html

def format_subclassification_links(context):
	""" Generate HTML formatting for links for book subclassifications on the classification index page. """
	html = ""
	subclass_counts = context.core.cache["top_subclass_counts"]
	subclass_names = sorted(list(subclass_counts.keys()))
	for name in subclass_names:
		if name.lower() == "all" or subclass_counts[name] == 0:
			continue
		label = name
		escaped_name = urllib.parse.quote_plus(name)
		url = '%s/search?qwords=*&subclass="%s"&type=volume' % (context.prefix, escaped_name)
		if subclass_counts[name] == 1:
			html += "\t\t\t<li class='classification'><a href='%s'>%s</a> (1 book)\n" % (url, label)
		else:
			fmt_count = "{:,}".format(subclass_counts[name])
			html += "\t\t\t<li class='classification'><a href='%s'>%s</a> (%s books)\n" % (url, label, fmt_count)
	return html

def format_classification_options(context, selected = "all"):
	# add the all option
	class_names = [ "all" ] + context.core.cache["class_names"]
	# generate the HTML
	html = ""
	for name in class_names:
		label = name.replace("?","'")
		if name == "all":
			label = "All Classifications"
		# is this the currently selected option?
		if name.lower() == selected.lower():
			html += "<option value='%s' selected>%s</option>\n" % (name, label)
		else:
			html += "<option value='%s'>%s</option>\n" % (name, label)
	return html

def format_subclassification_options(context, selected = "all"):
	# add the all option
	subclass_names =  [ "all" ] + context.core.cache["subclass_names"]
	# generate the HTML
	html = ""
	for name in subclass_names:
		label = name.replace("?","'")
		if name == "all":
			label = "All Sub-classifications"
		# is this the currently selected option?
		if name.lower() == selected.lower():
			html += "<option value='%s' selected>%s</option>\n" % (name, label)
		else:
			html += "<option value='%s'>%s</option>\n" % (name, label)
	return html

def format_place_options(context, selected = "all"):
	place_names = context.core.cache["top_place_names"]
	# add the all option
	place_names = [ "all" ] + place_names
	# generate the HTML
	html = ""
	for name in place_names:
		label = name.replace("?","'")
		if name == "all":
			label = "All Locations"
		# is this the currently selected option?
		if name.lower() == selected.lower():
			html += "<option value='%s' selected>%s</option>\n" % (name, label)
		else:
			html += "<option value='%s'>%s</option>\n" % (name, label)
	return html

def format_field_options(selected = "all"):
	html = ""
	field_keys = list(field_name_map.keys())
	field_keys.sort()
	for key in field_keys:
		# is this the currently selected option?
		if key == selected:
			html += "<option value='%s' selected>%s</option>\n" % (key, field_name_map[key])
		else:
			html += "<option value='%s'>%s</option>\n" % (key, field_name_map[key])
	return html	

def format_type_options(selected = "volume"):
	html = ""
	type_keys = list(type_name_map.keys())
	type_keys.sort()
	for key in type_keys:
		# is this the currently selected option?
		if key == selected:
			html += "<option value='%s' selected>%s</option>\n" % (key, type_name_map[key])
		else:
			html += "<option value='%s'>%s</option>\n" % (key, type_name_map[key])
	return html	

def format_mudies_options(selected = False):
	html = ""
	if selected:
		html += "<option value='true' selected>Yes</option>\n" 
		html += "<option value='false'>No</option>\n" 
	else:
		html += "<option value='true'>Yes</option>\n" 
		html += "<option value='false' selected>No</option>\n" 
	return html	
	
def format_volume_list(context, db, selected_volumes, verbose=True, max_title_length=200):
	html = ""
	result_url_prefix = "%s/volume" % (context.prefix)
	# Generate HTML	for each result
	for volume_id in selected_volumes:
		doc = db.get_volume_metadata(volume_id)
		if doc is None:
			continue
		title = doc["title"]
		if len(title) > max_title_length:
			title = title[0:max_title_length] + "&hellip;"
		year = int(doc["year"])
		volume = int(doc["volume"])
		max_volume = int(doc["volumes"])
		url_result = "%s?id=%s" % (result_url_prefix, volume_id)
		html += "<p class='search-result'>\n"
		html += "<div class='search-result-meta'>\n"
		# add extra metadata?
		if verbose:
			html += "<a href='%s' class='result-title'>%s" % (url_result, title)
			if max_volume > 1:
				html += "&nbsp;&nbsp;&ndash;&nbsp;&nbsp;Volume %d" % (volume)
			html += "</a>\n"
			# format authors
			sauthors = tidy_authors(doc.get("authors", None))
			# format locations
			if "published_locations" in doc:
				locations = []
				# need to extract just the places not the countries
				for pair in doc["published_locations"]:
					if pair[0] == "place":
						locations.append(pair[1])
				html += "<div>%s &ndash; %s &ndash; %s</div>\n" % (sauthors, year, tidy_location_places(locations))
			else:
				html += "<div>%s &ndash; %s</div>\n" % (sauthors, year)
		# just add the primary metadata
		else:
			html += "<a href='%s' class='result-title'>%s&nbsp;&nbsp;(%d)&nbsp;&nbsp;&ndash;&nbsp;&nbspVolume %d</a>\n" % (url_result, title, year, volume)
		html += "</div>\n"
		# add a snippet to the result?
		if verbose:
			extract = db.get_volume_extract(volume_id)		
			if extract is None or len(extract) == 0:
				extract = "No text available."
			else:
				extract = tidy_extract(extract)
			# actually format the snippet
			html += "<ul class='search-snippets'>\n"
			html += "<li class='snippet-text'>%s</li>\n" % extract
			html += "</ul>\n"
		# finished result
		html += "</p>\n"
	return html
