""" 
Functions for cleaning various fields in the raw metadata associated with the British Library 
Digital Collection.
"""
import logging as log
import re
import ftfy

# --------------------------------------------------------------

re_brackets = re.compile("(\[.*\])")

title_remove_suffixes = ["selected and arranged by", "collected and arranged with notes by", "collected and arranged by",
	"with. lllustrations", " with two maps", "with. diagrams",
	"selected and edited by", "with illustrations", "illustrated. With map", ". illustrated", "illustrated, etc", "edited by", ", etc", ",etc"]
title_remove_suffixes.sort(key=len)
title_remove_suffixes.reverse()

def clean(s, default_value=None):
	""" General string cleaning function """
	if s is None or type(s) is float:
		return default_value
	s = ftfy.fix_text(s)
	s = s.replace("-"," ").replace("?"," ")
	s = re.sub("\s+", " ", s).strip()
	if len(s) < 2:
		return default_value
	return s
	
def clean_title(title, default_title=None):
	""" Clean a string containing a book title as originally provided in
	the metadata from the British Library Digital Collection """
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
	location = location.title()
	return location.replace(" Of ", " of ")

def clean_content(content):
	if content is None or type(content) is float:
		return ""
	content = ftfy.fix_text(content)
	content = content.replace("<", " ").replace(">", " ")
	content = content.replace("\t"," ")
	content = content.replace("\r","\n")
	return content.strip()

def clean_shelfmarks(shelfmarks):
	""" Extract a list of formatted library shelfmarks from the string originally provided in
	the metadata from the British Library Digital Collection """
	if shelfmarks is None or type(shelfmarks) is float:
		return None
	cleaned = []
	for shelfmark in shelfmarks:
		shelfmark = shelfmark.replace("British Library", "").replace(";",":")
		shelfmark = re.sub("\s+", " ", shelfmark).strip()
		cleaned.append(shelfmark)
	return cleaned

def extract_authors(authors, default_value = None):
	""" Extract a list of formatted author names from the string originally provided in
	the metadata from the British Library Digital Collection """
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
				name_parts.append(part.capitalize().strip())
			if len(name_parts) == 0:
				log.warning("Could not parse name '%s'" % fullname)
			else:
				author_list.append(" ".join(name_parts).strip())
	if len(author_list) == 0:
		return default_value
	return author_list

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

def format_author_sortname(author):
	""" Convert an author name to a sortable format string 'Lastname, Firstname' with extra
	title words removed """
	if author is None or type(author) is float or author.lower() == "unknown":
		return "Unknown"
	s = re.sub("\[.*\]", "", author).strip()
	# handle case
	parts = re.split("[ ,\.'']", s)
	parts = sorted(parts, key=lambda x: len(x))[::-1]
	for word in parts:
		if len(word) > 2 and word.isupper():
			s = s.replace(word, word.capitalize())
	# manual replacements
	s = re.sub(" \- Sir$", "", s, re.IGNORECASE)
	s = re.sub(" \- Mrs$", "", s, re.IGNORECASE)
	s = re.sub(" \- Mr$", "", s, re.IGNORECASE)
	s = re.sub(" \- Dr$", "", s, re.IGNORECASE)
	s = re.sub(" \- Esq$", "", s, re.IGNORECASE)
	s = re.sub(" \- Lord$", "", s, re.IGNORECASE)
	s = re.sub(" \- Lady$", "", s, re.IGNORECASE)
	s = re.sub(" \- Esquire$", "", s, re.IGNORECASE)
	s = re.sub(" \- Esq\.,.*$", "", s, re.IGNORECASE)
	s = re.sub(" \- M\.P$", "", s, re.IGNORECASE)
	s = re.sub(" \- M\.P\.$", "", s, re.IGNORECASE)
	s = re.sub(" \- Esq\.$", "", s, re.IGNORECASE)
	s = re.sub(" \- Right Hon.*$", "", s, re.IGNORECASE)
	s = re.sub(" \- Artist$", "", s, re.IGNORECASE)
	s = re.sub(" \- Missionary$", "", s, re.IGNORECASE)
	s = re.sub(" \- the Poet$", "", s, re.IGNORECASE)
	s = re.sub(" \- a Poet$", "", s, re.IGNORECASE)
	s = re.sub(" \- Poet$", "", s, re.IGNORECASE)
	s = re.sub(" \- Anthropologist$", "", s, re.IGNORECASE)
	s = re.sub(" \- Minister at Etal$", "", s, re.IGNORECASE)
	s = re.sub(" \- Lecturer$", "", s, re.IGNORECASE)
	s = re.sub(" \- Esq\., of .*$", "", s, re.IGNORECASE)
	s = re.sub(" \- Author of .*$", "", s, re.IGNORECASE)
	s = re.sub(" \- Fellow of .*$", "", s, re.IGNORECASE)
	s = re.sub(" \- Late Fellow of .*$", "", s, re.IGNORECASE)
	s = re.sub(" \- Late of .*$", "", s, re.IGNORECASE)
	s = re.sub(" \- of .*$", "", s, re.IGNORECASE)
	s = re.sub(" \- Vicar of .*$", "", s, re.IGNORECASE)
	s = re.sub(" \- Earl of .*$", "", s, re.IGNORECASE)
	s = re.sub(" \- Mayor of .*$", "", s, re.IGNORECASE)
	s = re.sub(" \- Baron of .*$", "", s, re.IGNORECASE)
	s = re.sub(" \- Lord Protector.*$", "", s, re.IGNORECASE)
	s = re.sub(" \- Baron$", "", s, re.IGNORECASE)
	s = re.sub(" \- Novelist$", "", s, re.IGNORECASE)
	s = re.sub(" \- Author$", "", s, re.IGNORECASE)
	s = re.sub(" \- B\.A\.. *$", "", s, re.IGNORECASE)
	s = re.sub("\(Margaret\)", "Margaret", s)
	s = re.sub(" \- of the 62nd Regiment$", "", s, re.IGNORECASE)
	s = s.replace(", the Historian","")
	s = re.sub("\s+", " ", s)
	if len(s) > 10 and s[-1] in "., -_?":
		s = s[0:len(s)-1]
	return s.strip()

# --------------------------------------------------------------

def tidy_title( title ):
	""" Tidy a text title for display in search results """
	if title is None:
		return "Untitled"
	title = title.replace("[", " ").replace("]", " ").replace(" ?", " ").replace("? ", " ")
	title = re.sub( "\s+", " ", title ).strip()
	if len(title) < 2:
		return "Untitled"
	return title	

def tidy_authors(author_list):
	""" Tidy an author list for display in search results """
	if author_list is None or len(author_list) == 0 or ( len(author_list) == 1 and author_list[0].lower() == "unknown" ):
		return "Author Unknown"
	# change to firstname, last name
	reversed_authors = []
	for author in author_list:
		# TODO: remove ftfy
		author = ftfy.fix_text( author )
		parts = author.split(",", 1)
		if len(parts) == 1:
			reversed_authors.append( parts[0] )
		else:
			reversed_authors.append( "%s %s" % ( parts[1].strip(), parts[0].strip() ) )
	return ", ".join( reversed_authors )

def tidy_content(text):
	""" Tidy the body text for display for close reading """
	if text is None:
		return ""
	return text.strip()

def tidy_snippet(snippet):
	""" Tidy a text snippet for display in search results """
	if snippet is None:
		return ""
	# trim the start of the snippet
	c = snippet[0]
	while not (c.isalnum() or c == "<"):
		if len(snippet) < 2:
			break
		snippet = snippet[1:]
		c = snippet[0]
	# TODO: better fix for inaccurate tags.
	snippet = snippet.replace("<i ", " ")
	snippet = snippet.replace("<b ", " ")
	if not snippet[-1] == ".":
		snippet += "&hellip;"
	return snippet

def tidy_extract(extract):
	""" Tidy a document extract for display in search results """
	if extract is None:
		return ""
	extract_ignores = "^/\\$£~*@«»"
	# remove unwanted characters
	for c in extract_ignores:
		extract = extract.replace(c,"")
	return tidy_snippet(extract.strip())

def tidy_location_places(places):
	""" Tidy a location place information for display in the Curatr interface """
	if places is None or len(places) == 0:
		return "Unknown"
	tidy_place_list = []
	for x in places:
		tidy_place_list.append(ftfy.fix_text(x).strip().title())
	return "; ".join(tidy_place_list)

def tidy_shelfmarks(shelf_list):
	""" Tidy a string containing one or more BL shelfmark codes """
	if shelf_list is None or len(shelf_list) == 0:
		return "Unavailable"
	tidy_shelf_list = []
	for x in shelf_list:
		tidy_shelf_list.append(ftfy.fix_text(x).strip())
	return ", ".join(tidy_shelf_list)

def tidy_edition(edition):
	""" Tidy book edition string """
	if edition is None or len(edition) == 0 or edition.lower() == "unknown":
		return "Unknown"
	edition = ftfy.fix_text(edition)
	edition = edition.replace("-"," ").replace("?"," ")
	return re.sub("\s+", " ", edition).strip()

def tidy_description(descr):
	""" Tidy book physical description string """
	if descr is None or len(descr) == 0 or descr.lower() == "unknown":
		return "Unknown"
	descr = ftfy.fix_text(descr)
	descr = descr.replace("-"," ").replace("?"," ")
	return re.sub("\s+", " ", descr).strip()
	
def tidy_publisher(publisher):
	""" Tidy a string containing publisher information """
	if publisher is None or len(publisher) == 0 or publisher.lower() == "unknown":
		return "Unknown"
	publisher = ftfy.fix_text(publisher)
	publisher = publisher.replace("-"," ").replace("?"," ")
	return re.sub("\s+", " ", publisher).strip()
