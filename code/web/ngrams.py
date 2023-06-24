"""
Implementation for ngram-related features of the Curatr web interface
"""
import urllib.parse, io
import logging as log
from flask import Markup, send_file, abort
# project imports
from web.util import parse_keyword_query, parse_arg_int

# --------------------------------------------------------------

def format_ngram_normalize_options(normalize=False):
	html = ""
	if normalize:
		html += "<option value='false'>Number of Volumes</option>"
		html += "<option value='true' selected>Relative Percentage of Volumes</option>"
	else:
		html += "<option value='false' selected>Number of Volumes</option>"
		html += "<option value='true'>Relative Percentage of Volumes</option>"
	return html	

# --------------------------------------------------------------

def populate_ngrams_page(context, app, collection_id="all"):
	# handle year parameters
	ngram_default_year_min = app.core.config["ngrams"].getint("default_year_min", 0)
	ngram_default_year_max = app.core.config["ngrams"].getint("default_year_max", 0)
	year_start = max(0, parse_arg_int(context.request, "year_start", ngram_default_year_min))
	year_end = max(0, parse_arg_int(context.request, "year_end", ngram_default_year_max))
	# invalid years?
	if year_start < 1:
		year_start = app.core.cache["year_min"]	
	if year_end < 1:
		year_end = app.core.cache["year_max"]	
	# do we want normalized counts?
	snormalize = context.request.args.get("normalize", default = "false").lower()
	normalize = ( snormalize == "1" or snormalize == "true" )
	# parse the query
	raw_query_string = context.request.args.get("qwords", default = "").lower()
	queries = parse_keyword_query(raw_query_string)
	# if nothing specified, use the default query
	if len(queries) > 0:
		query_string = ", ".join(queries)
	else:
		query_string = app.core.config["ngrams"].get("default_query", "contagion")
		queries = parse_keyword_query(query_string)
	context["query"] = query_string
	context["querylist"] = Markup(str(queries))
	context["yearstart"] = year_start
	context["yearend"] = year_end
	if normalize:
		context["yaxis"] = "Percentage of Volumes (%)"
		context["allowdecimals"] = "true"
	else:
		context["yaxis"] = "Number of Volumes"
		context["allowdecimals"] = "false"
	context["normalize_options"] = Markup(format_ngram_normalize_options(normalize))
	# add the API data URL
	context["jsonurlprefix"] = Markup("%s/ngrams?year_start=%s&year_end=%s&normalize=%s&q=" % (app.apiprefix, year_start, year_end, normalize))
	# add the export URL
	quoted_query_string = urllib.parse.quote_plus(query_string)
	context["export_url"] = Markup("%s/exportngrams?year_start=%s&year_end=%s&normalize=%s&qwords=%s" % (context.prefix, year_start, year_end, normalize, quoted_query_string))
	return context

def export_ngrams(context, app, collection_id="all"):
	""" Export ngram counts in CSV format """
	# handle year parameters
	ngram_default_year_min = app.core.config["ngrams"].getint("default_year_min", 0)
	ngram_default_year_max = app.core.config["ngrams"].getint("default_year_max", 0)
	year_start = max(0, parse_arg_int(context.request, "year_start", ngram_default_year_min))
	year_end = max(0, parse_arg_int(context.request, "year_end", ngram_default_year_max))
	# invalid years?
	if year_start < 1:
		year_start = app.core.cache["year_min"]	
	if year_end < 1:
		year_end = app.core.cache["year_max"]	
	# do we want normalized counts?
	snormalize = context.request.args.get("normalize", default = "false").lower()
	normalize = ( snormalize == "1" or snormalize == "true" )
	# parse the query
	raw_query_string = context.request.args.get("qwords", default = "").lower()
	queries = parse_keyword_query(raw_query_string)
	# if nothing specified, use the default query
	if len(queries) == 0:
		abort(404, description="No valid query string specified")
	# get the counts
	db = app.core.get_db()
	all_query_counts = {}
	for query in queries:
		all_query_counts[query] = db.get_ngram_count(query, year_start, year_end, collection_id)
	if normalize:
		total_year_counts = db.get_cached_volume_years(year_start, year_end)
	# finish with the database	
	db.close()
	# suggested filename
	filename = "ngrams-%s.csv" % "_".join(queries)
	log.info("Exporting ngram counts in CSV format to %s" % filename) 
	# export the counts
	out = io.StringIO()
	# header line
	out.write("year")
	for query in queries:
		out.write(",%s" % query)
	out.write("\n")
	# each row, one per year
	for year in range(year_start,year_end+1):
		out.write("%d" % year)
		for query in queries:
			if year in all_query_counts[query]:
				if normalize:
					if year in total_year_counts:
						percentage = (100.0*all_query_counts[query][year])/total_year_counts[year]
						out.write(",%.3f" % percentage)
					else:
						out.write(",0")
				else:
					out.write(",%d" % all_query_counts[query][year])
		out.write("\n")
    # Creating the byteIO object from the StringIO Object
	mem = io.BytesIO()
	mem.write(out.getvalue().encode('utf-8'))
	mem.seek(0)
	out.close()
	return send_file(mem, mimetype='text/plain', as_attachment=True, attachment_filename=filename)
