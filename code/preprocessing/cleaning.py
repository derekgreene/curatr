""" 
Functions for cleaning various fields in metadata associated with the British Library Digital Collection dataset.
"""
import logging as log
import re
import ftfy

re_brackets = re.compile("(\[.*\])")

title_remove_suffixes = ["selected and arranged by", "collected and arranged with notes by", "collected and arranged by",
	"with. lllustrations", " with two maps", "with. diagrams",
	"selected and edited by", "with illustrations", "illustrated. With map", ". illustrated", "illustrated, etc", "edited by", ", etc", ",etc"]
title_remove_suffixes.sort(key=len)
title_remove_suffixes.reverse()

def clean(s, default_value=None):
	if s is None or type(s) is float:
		return default_value
	s = ftfy.fix_text(s)
	s = s.replace("-"," ").replace("?"," ")
	s = re.sub("\s+", " ", s).strip()
	if len(s) < 2:
		return default_value
	return s
	
def clean_title(title, default_title=None):
	if title is None or type(title) is float:
		return default_title
	title = ftfy.fix_text(title)
	title = title.replace("…", "...")
	title = title.replace(" ... ", ". ")
	title = title.replace("... ", ". ")
	title = title.replace("...", ".")
	title = re.sub("\s+", " ", title).strip()
	matches = re_brackets.findall(title)
	if len(matches) > 0:
		for m in matches:
			title = title.replace(m, " ")
	title = re.sub("\s+", " ", title).strip()
	for removal in title_remove_suffixes:
		pos = title.lower().find(removal)
		if pos > 0:
			title = title[0:pos].strip()
	if len(title) < 2:
		return default_title
	if title[-1] == ".":
		title = title[0:len(title)-1]
	if title[-1] == ",":
		title = title[0:len(title)-1]
	if len(title) < 2:
		return default_title
	return title.strip()

def clean_location(location, default_location=None):
	if location is None or type(location) is float:
		return default_location
	location = ftfy.fix_text(location)
	location = location.replace("-"," ").replace("?"," ")
	location = re.sub("\s+", " ", location).strip()
	if len(location) < 2:
		return default_location
	# NB: convert to title case
	return location.title()

def clean_content(content):
	if content is None or type(content) is float:
		return ""
	content = ftfy.fix_text(content)
	content = content.replace("<", " ").replace(">", " ")
	content = content.replace("\t"," ")
	content = content.replace("\r","\n")
	return content.strip()

def clean_shelfmarks(shelfmarks):
	if shelfmarks is None:
		return None
	cleaned = []
	for shelfmark in shelfmarks:
		shelfmark = shelfmark.replace("British Library", "")
		shelfmark = re.sub("\s+", " ", shelfmark).strip()
		cleaned.append(shelfmark)
	return cleaned
	

def extract_authors(authors, default_value = None):
	if authors is None or type(authors) is float:
		return default_value
	author_list = []
	for fullname_list in authors.values():
		for fullname in fullname_list:
			fullname = ftfy.fix_text(fullname)
			fullname = fullname.strip().replace(";","").strip()
			if len(fullname) < 2:
				continue
			name_parts = []
			for part in re.split("\s+",fullname):
				if part == "-":
					break
				if part[0] == "(":
					part = part[1:]
				if part[0] == "[":
					part = part[1:]
				if part[-1] == "]":
					part = part[0:len(part)-1]
				if part[-1] == ")":
					part = part[0:len(part)-1]
				if len(part) > 3 and part[-1] == ".":
					part = part[0:len(part)-1]
				name_parts.append(part.capitalize())
			if len(name_parts) == 0:
				log.warning("Could not parse name '%s'" % fullname)
			else:
				author_list.append(" ".join(name_parts))
	if len(author_list) == 0:
		return default_value
	return author_list

def extract_shelf_ids(shelf_marks):
	if shelf_marks is None or type(shelf_marks) is float:
		return None
	shelf_list = []
	for shelf_mark in shelf_marks:
		shelf_list.append(shelf_mark.replace("British Library ","").replace(";",":").strip())
	return shelf_list


place_map = {"Calcutta":"India", "Springfield, Massachusetts": "United States of America", "Oxford":"England", 
	"Lancaster":"England", "Dublin":"Ireland", "Eton":"England", "Quebec":"Canada", "Beaumaris":"Wales",
	"Boston": "United States of America", "Meadville, Pennsylvania":"United States of America",
	"Newcastle upon Tyne":"England", "Brussels":"Belgium", "Melbourne":"Australia", "Philadelphia":"United States of America",
	"Toronto":"Canada", "Cologne":"Germany", 'Cape Town':"South Africa", "Ottawa":"Candata",
	"Ithaca, New York":"United States of America", "Providence, Rhode Island":"United States of America", 
	"Albany, New York":"United States of America", "Providence":"United States of America",
	"Adelaide":"Australia", "Perth":"Australia", "Great Totham":"England", "Montreal":"Canada", "Berlin":"Germany",
	"Detroit":"United States of America", "Madras": "India", "Bombay":"India", "York":"England",
	'San Francisco':"United States of America", "Cork":"Ireland", "Sydney":"Australia", "Manchester":"England",
	"Paris":"France", 'Hartford, Connecticut':"United States of America", "Allahabad":"India",
	"Cheltenham":"England", 'Richmond, Virginia':"United States of America", "Doncaster":"England",
	'Salisbury':'England', 'Bury St Edmunds':"England", 'Great Yarmouth':"England", "Whitby":"England",
	"Concord": "United States of America", "Rome":"Italy", "Leipzig":"Germany", "Yokohama":"Japan", 
	"Shanghai":"China", 'Halifax, N S':"Canada", "Newcastle": "England", 'Durham':"England",
	'Cambridge, Massachusetts':"United States of America", 'Madison, Wisconsin':"United States of America",
	"Dover":"England", "Galway":"Ireland",'Brooklyn':"United States of America",
	"Wigan":"England", "Bolton":"England"}

def extract_publication_location(place_str, country_str):
	place_str = str(place_str)
	country_str = str(country_str)
	places_na = place_str.lower() == "nan"
	countries_na = country_str.lower() == "nan"
	out_places, out_countries = None, None
	if not places_na:
		out_places = [clean_location(x) for x in place_str.strip().split(";")]
		if None in out_places:
			out_places.remove(None)
	if not countries_na:
		out_countries = [clean_location(x)for x in country_str.strip().split(";")]
		if None in out_countries:
			out_countries.remove(None)
	elif not places_na and len(out_places) == 1:
		if out_places[0] in place_map:
			out_countries = [place_map[out_places[0]]]
	# missing country?
	return out_places, out_countries
