""" 
Implementation of the Curatr web API functionality
"""
import re
import logging as log
from flask import request
# project imports
from web.util import parse_arg_int

# --------------------------------------------------------------

def author_list(core):	
	""" End point for author catalogue JSON """
	return {"data" : core.cache["author_catalogue"]}

def ngram_counts(core, db, collection_id="all"):
	""" Endpoint to handle ngram counts, which are returned as JSON. """	
	""" Return API data relating to n-gram counts """
	query = request.args.get("q", default = "").lower()
	# NB: spaces in bigrams get replaced with underscores
	query = query.replace(" ", "_")
	query = re.sub("[^a-zA-Z0-9_]", "", query).strip()
	if len(query) == 0:
		raise Exception("No query specified")
	# handle year parameters
	year_start = parse_arg_int(request, "year_start", core.cache["year_min"]) 
	if year_start < core.cache["year_min"]:
		year_start = core.cache["year_min"]
	year_end = parse_arg_int(request, "year_end", core.cache["year_max"]) 
	if year_end > core.cache["year_max"]:
		year_end = core.cache["year_max"]
	# do we want normalized counts?
	snormalize = request.args.get("normalize", default = "false").lower()
	normalize = (snormalize == "1" or snormalize == "true")
	if normalize:
		total_year_counts = db.get_cached_volume_years(year_start, year_end)
	# retrieve the list of counts
	query_counts = db.get_ngram_count(query, year_start, year_end, collection_id)
	# convert it to a list of pairs
	values = []
	for year in range(year_start, year_end+1):
		# do we have a count for this year?
		if year in query_counts:
			if normalize:
				if year in total_year_counts:
					percentage = round((100.0*query_counts[year])/total_year_counts[year], 3)
					values.append([year, percentage])
				else:
					values.append([year, 0])
			else:
				values.append([year, query_counts[year]])
		else:
			values.append([year, 0])
	return values
