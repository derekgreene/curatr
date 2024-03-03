"""
Various utility functions used as part of the Curatr web search implementation.
"""
import re
import logging as log

# --------------------------------------------------------------

def safe_int(value, default=0):
	""" Make sure the specified value is a valid integer """
	if value is None:
		return default
	if type(value) == int:
		return value
	svalue = str(value)
	if len(svalue) == 0:
		return default
	try:
		return int(svalue)
	except:
		return default

def parse_arg_int(request, param_name, default=0):
	svalue = request.args.get(param_name, default="").strip().lower()
	if len(svalue) == 0:
		return default
	try:
		return int(svalue)
	except:
		return default

def parse_arg_bool(request, param_name, default=False):
	svalue = request.args.get(param_name, default="").strip().lower()
	return svalue == "1" or svalue == "true"

def format_year_range(ystart, yend):
	""" Nicely format a pair of years as a range string """
	# make sure start year is valid
	if ystart is None or ystart == "*":
		ystart = 0
	elif type(ystart) == str:
		try:
			ystart = int(ystart)
		except:
			ystart = 0
	# make sure end year is valid
	if yend is None or yend == "*":
		yend = 0
	elif type(yend) == str:
		try:
			yend = int(yend)
		except:
			yend = 0
	# now build the format string
	s_year = ""
	if ystart > 0:
		s_year = "From %d" % ystart
	if yend > 0 and yend < 2000:
		if len(s_year) == 0:
			s_year = "Until %d" % yend
		else:
			s_year += " until %d" % yend
	elif len(s_year) > 0:
		s_year += " onwards" 
	return s_year

def parse_keyword_query(raw_query_string):
	""" Query parsing where the user inputs a list of comma-separated keywords """
	if raw_query_string == "*":
		return ""
	raw_query_string = re.sub("\s+", " ", raw_query_string).strip().lower()
	queries = []
	for query in raw_query_string.split(","):
		query = re.sub("[^a-zA-Z0-9 ]", "", query).strip()
		if len(query) > 1 and not query in queries:
			queries.append(query)
	return queries

