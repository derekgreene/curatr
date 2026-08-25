""" 
Functions for cleaning various fields in the raw metadata associated with the British Library 
Digital Collection.
"""
import logging as log
import re
import ftfy

# --------------------------------------------------------------

re_brackets = re.compile(r"(\[.*\])")

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
	s = re.sub(r"\s+", " ", s).strip()
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
	title = re.sub(r"\s+", " ", title).strip()
	matches = re_brackets.findall(title)
	if len(matches) > 0:
		for m in matches:
			title = title.replace(m, " ")
	title = re.sub(r"\s+", " ", title).strip()
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
	location = re.sub(r"\s+", " ", location).strip()
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
		shelfmark = re.sub(r"\s+", " ", shelfmark).strip()
		cleaned.append(shelfmark)
	return cleaned

def _clean_name_token(part):
	""" Clean a single whitespace-delimited token from a raw author name/qualifier """
	if not part:
		return ""
	if part[0] == "(":
		part = part[1:]
	if part and part[0] == "[":
		part = part[1:]
	if part and part[-1] == "]":
		part = part[0:len(part)-1]
	if part and part[-1] == ")":
		part = part[0:len(part)-1]
	if len(part) > 3 and part[-1] == ".":
		part = part[0:len(part)-1]
	return part.capitalize().strip()

# Qualifiers that reveal gender (Mrs/Lady/Miss and their peerage equivalents), distinguish
# otherwise-identical names across generations (the Elder/Younger, Junior/Senior, numbered
# peerage titles), or preserve a life-date range (also disambiguating). Generic, non-
# distinguishing honorifics/occupations (Sir, Dr, Novelist, of Somewhere, etc.) are still
# discarded, as they were before.
_qualifier_keep_patterns = [
	re.compile(r"^mrs\.?$", re.IGNORECASE),
	re.compile(r"^lady(\s|$)", re.IGNORECASE),
	re.compile(r"^miss$", re.IGNORECASE),
	re.compile(r"^baroness(\s|$)", re.IGNORECASE),
	re.compile(r"^countess(\s|$)", re.IGNORECASE),
	re.compile(r"^duchess(\s|$)", re.IGNORECASE),
	re.compile(r"^viscountess(\s|$)", re.IGNORECASE),
	re.compile(r"^marchioness(\s|$)", re.IGNORECASE),
	re.compile(r"^the elder\.?$", re.IGNORECASE),
	re.compile(r"^the younger\.?$", re.IGNORECASE),
	re.compile(r"^(junior|jr|jnr)\.?$", re.IGNORECASE),
	re.compile(r"^(senior|sr|snr)\.?$", re.IGNORECASE),
	re.compile(r"^\d+(st|nd|rd|th)\s+(bart|baronet|earl|duke|viscount|marquis|marquess|baron|lord)", re.IGNORECASE),
	re.compile(r"^\d{3,4}\??\s*-\s*\d{3,4}\??\.?$"),  # life-date range, e.g. '1821-1890'
]

_peerage_title_re = re.compile(r"^(lord|baron|earl|viscount|duke|marquis|marquess)\b\s*(.*)$", re.IGNORECASE)
_peerage_connector_re = re.compile(r"^(of|de|d['’]|von|del)\s*", re.IGNORECASE)

def _has_attached_peerage_title(component):
	""" True if component is a peerage/office title WITH a specific attached name
	(e.g. 'Lord Hailes', 'Earl of Dorset', 'Lord Mayor of London'), rather than a bare,
	non-distinguishing honorific (e.g. 'Lord' alone) """
	m = _peerage_title_re.match(component.strip())
	if not m:
		return False
	remainder = _peerage_connector_re.sub("", m.group(2).strip()).strip()
	remainder = remainder.rstrip(" .,").strip()
	return len(remainder) > 0

def _qualifies_component(component):
	""" Decide whether a single comma-separated qualifier component should be preserved """
	component = component.strip()
	if not component:
		return False
	if re.search(r"\bafterwards\b", component, re.IGNORECASE):
		return True
	for pattern in _qualifier_keep_patterns:
		if pattern.match(component):
			return True
	return _has_attached_peerage_title(component)

_lowercase_connector_re = re.compile(r"\b(Of|De|Von|Del)\b")

def _clean_qualifier_component(component):
	""" Apply the same per-token cleanup used for names to a kept qualifier component """
	tokens = [_clean_name_token(w) for w in re.split(r"\s+", component.strip())]
	joined = " ".join(t for t in tokens if t).strip()
	return _lowercase_connector_re.sub(lambda m: m.group(1).lower(), joined)

def clean_author_name(fullname):
	""" Clean a single raw author name string as found in the British Library Digital
	Collection metadata (e.g. 'PEEL, Augustus - Mrs' -> 'Peel, Augustus, Mrs'). Qualifiers
	that reveal gender or distinguish otherwise-identical names are preserved; generic
	non-distinguishing titles (Sir, Dr, occupations, etc.) are discarded as before. """
	fullname = ftfy.fix_text(fullname)
	fullname = fullname.strip().replace(";","").strip()
	if len(fullname) < 2:
		return None
	parts = re.split(r"\s+", fullname)
	if "-" in parts:
		idx = parts.index("-")
		name_part = " ".join(parts[:idx]).strip()
		qualifier_part = " ".join(parts[idx+1:]).strip()
	else:
		name_part = fullname
		qualifier_part = ""
	name_tokens = [t for t in (_clean_name_token(p) for p in re.split(r"\s+", name_part) if p) if t]
	if len(name_tokens) == 0:
		log.warning("Could not parse name '%s'" % fullname)
		return None
	cleaned_name = " ".join(name_tokens).strip()
	if not qualifier_part:
		return cleaned_name
	kept = [_clean_qualifier_component(c) for c in qualifier_part.split(",") if _qualifies_component(c)]
	kept = [c for c in kept if c]
	if not kept:
		return cleaned_name
	return cleaned_name + ", " + ", ".join(kept)

def parse_holdings_personal_name(raw):
	""" Convert holdings_author_personal's 'Surname, Firstname, Title, dates.' convention
	(e.g. 'Burton, Richard Francis, Sir, 1821-1890.') into the 'Name - qualifier' form used
	elsewhere in authors_full, so it flows through clean_author_name() unchanged """
	if raw is None or type(raw) is float:
		return None
	raw = raw.strip()
	if raw.endswith("."):
		raw = raw[:-1].strip()
	if not raw:
		return None
	segments = [s.strip() for s in raw.split(",")]
	segments = [s for s in segments if s.lower().rstrip(".") != "pseud"]
	if len(segments) < 2:
		return segments[0] if segments else None
	name_part = "%s, %s" % (segments[0], segments[1])
	qualifier_part = ", ".join(s for s in segments[2:] if s)
	if qualifier_part:
		return "%s - %s" % (name_part, qualifier_part)
	return name_part

def extract_authors(authors, default_value = None):
	""" Extract a list of formatted author names from the string originally provided in
	the metadata from the British Library Digital Collection """
	if authors is None or type(authors) is float:
		return default_value
	author_list = []
	for fullname_list in authors.values():
		for fullname in fullname_list:
			cleaned = clean_author_name(fullname)
			if cleaned is not None:
				author_list.append(cleaned)
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
	s = re.sub(r"\[.*\]", "", author).strip()
	# handle case
	parts = re.split(r"[ ,\.'']", s)
	parts = sorted(parts, key=lambda x: len(x))[::-1]
	for word in parts:
		if len(word) > 2 and word.isupper():
			s = s.replace(word, word.capitalize())
	# manual replacements
	if len(s) > 10 and s[-1] in "., -_?":
		s = s[0:len(s)-1]
	return s.strip()

# --------------------------------------------------------------

def tidy_title( title ):
	""" Tidy a text title for display in search results """
	if title is None:
		return "Untitled"
	title = title.replace("[", " ").replace("]", " ").replace(" ?", " ").replace("? ", " ")
	title = re.sub( r"\s+", " ", title ).strip()
	if len(title) < 2:
		return "Untitled"
	return title	

def tidy_author_list(author_list):
	""" Tidy an author list, reversing the order of lastname and firstname """
	if author_list is None or len(author_list) == 0 or (len(author_list) == 1 and author_list[0].lower() == "unknown"):
		return ["Author Unknown"]
	# change to firstname, last name
	reversed_authors = []
	for author in author_list:
		author = ftfy.fix_text(author)
		parts = author.split(",", 1)
		if len(parts) == 1:
			reversed_authors.append(parts[0])
		else:
			reversed_authors.append("%s %s" % (parts[1].strip(), parts[0].strip()))
	return reversed_authors		

def tidy_authors(author_list):
	""" Tidy an author list, turning it into a string for display in search results """
	return ", ".join(tidy_author_list(author_list))

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
	return re.sub(r"\s+", " ", edition).strip()

def tidy_description(descr):
	""" Tidy book physical description string """
	if descr is None or len(descr) == 0 or descr.lower() == "unknown":
		return "Unknown"
	descr = ftfy.fix_text(descr)
	descr = descr.replace("-"," ").replace("?"," ")
	return re.sub(r"\s+", " ", descr).strip()
	
def tidy_publisher(publisher):
	""" Tidy a string containing publisher information """
	if publisher is None or len(publisher) == 0 or publisher.lower() == "unknown":
		return "Unknown"
	publisher = ftfy.fix_text(publisher)
	publisher = publisher.replace("-"," ").replace("?"," ")
	publisher = re.sub(r"\s+", " ", publisher).strip()
	# remove trailing full-stop
	if publisher.endswith("."):
		publisher = publisher[0:len(publisher)-1]
	return publisher
