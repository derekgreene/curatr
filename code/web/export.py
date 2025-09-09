"""
Implementation for corpus export-related features of the Curatr web interface
"""
import json, zipfile, threading, re, time
from pathlib import Path
import logging as log
from flask import Markup, send_file, abort
# project imports
from web.util import safe_int, parse_arg_int, format_year_range
from web.format import type_name_map, field_name_map

# --------------------------------------------------------------

export_format_map = {"text" : "Full Text", "metadata" : "Metadata Only"}

# --------------------------------------------------------------

def populate_export(context, db, spec):
	""" Populate the export page """
	request = context.request
	is_segments = spec.get("type", "volume") == "segment"
	context["format_options"] = Markup(format_export_format_options())
	# format number of documents option
	total_results = parse_arg_int(request, "total_results", 0)
	context["num_options"] = Markup(format_export_num_options(total_results))
	# put together the summary of the sub-corpus
	summary_html = ""
	if spec["lexicon_id"] != "":
		lexicon = db.get_lexicon(spec["lexicon_id"])
		if lexicon is None:
			abort(403, "Cannot find specified lexicon in the database (lexicon_id=%s)" % spec["lexicon_id"])
		context["default_name"] = lexicon.get("name","Untitled").capitalize()
		summary_html += "<li><b>Lexicon:</b> %s</li>" % lexicon["name"]
	query_string = spec["query"]
	summary_html += "<li><b>Query:</b> "
	if len(query_string) == 0 or query_string == "*":
		summary_html += "All matching documents</li>\n"
	else:
		summary_html += "%s</li>\n" % query_string
	summary_html += "<li><b>Search Field:</b> %s" % field_name_map[ spec["field"] ].capitalize()
	s_year = format_year_range(spec["year_start"], spec["year_end"])
	if len(s_year) > 0:
		summary_html += "<li><b>Date Range:</b> %s</li>" % s_year
	else:
		summary_html += "<li><b>Date Range:</b> All years</li>" 
	summary_html += "<li><b>Index:</b>"
	if spec["class"].lower() == "all":
		# do we still have a subclass specified?
		if spec["subclass"].lower() != "all":
			summary_html += " Sub-classification '%s'" % spec["subclass"]
		else:
			summary_html += " All classifications"
	else:
		summary_html += " Classification '%s'" % spec["class"]
		# any subclass?
		if spec["subclass"].lower() != "all":
			summary_html += " ('%s')" % spec["subclass"]
	summary_html += "</li>\n"
	if total_results > 0:
		snum_total_results = "{:,}".format(total_results)
		summary_html += "<li><b>Results:</b> %s matching " % snum_total_results
		if is_segments:
			summary_html += "segments</li>\n" 
		else:
			summary_html += "volumes</li>\n" 
	context["summary"] = Markup(summary_html)
	# pass on the export query parameters
	search_spec = ""
	for arg in request.args:
		# ignore this one
		if arg.lower() == "action":
			continue
		value = request.args.get(arg, None)
		if not value is None:
			search_spec += '<input type="hidden" id="spec_%s" name="spec_%s" value="%s">\n' % (arg, arg, value)
	context["search_spec"] = Markup(search_spec)
	return context

def handle_export_build(context, core, spec):
	""" Handle an export request by getting the export parameters and starting the bulk exporter thread """
	try:
		request = context.request
		# valid user ID?
		corpus_user_id = context.user_id
		if corpus_user_id is None:
			abort(403, "Cannot create lexicon for anonymous user")
		# start the export process
		export_name = request.args.get("export_name", default="").strip()
		if len(export_name) == 0:
			export_name = "Untitled"
		export_format = request.args.get("export_format", default="").strip()
		if len(export_format) == 0:
			export_format = "text"
		try:
			export_num = int(request.args.get("export_num", default="10"))
		except:
			export_num = -1
		search_context = {}
		for arg in request.args:
			if arg.startswith("spec_"):
				spec_key = arg[5:]
				value = request.args.get(arg, None)
				if not value is None:
					search_context[spec_key] = value
		current_solr = core.get_solr(search_context["type"])
		log.info("Export: Search context %s" % str(search_context))
		# Perform the export
		exp = BulkExporter(core, current_solr, export_name, export_format, export_num, corpus_user_id, search_context)
		# create a background thread for the exporter
		thread = threading.Thread(target=exp.run, args=(), name="bulk-export-thread")
		log.info("Export: Starting bulk export thread ...")
		thread.daemon = True
		# thread.daemon = False
		thread.start()
		# add a message
		url_reload = "%s/corpora" % context.prefix
		context["message"] = Markup("Your sub-corpus is currently being exported and will be available for download from this page in a few minutes. <br>Please do not click 'Refresh' in your browser. Instead, click <a href='%s'>here to reload this page</a>." % url_reload)
	except:
		log.exception("ERROR: Export initial build failed due to unexpected exception")
		context["message"] = Markup("Failed to start sub-corpus export process. Please try again at a later time.")
	return context


def handle_export_download(core, subcorpus_id):
	""" Send an export file for download """
	# get the correct path for the file
	zip_filepath = core.get_subcorpus_zipfile(subcorpus_id)
	log.info("Export: Request to download corpus '%s' from '%s'" %  (subcorpus_id, zip_filepath))
	if zip_filepath is None:
		log.warning("WARNING: No ZIP file path specified for export")
		abort(500, "No ZIP file path specified for export")
	if not zip_filepath.exists():
		log.warning("WARNING: Cannot find ZIP file for export - %s" % zip_filepath)
		abort(500, "Cannot find ZIP file for export - %s" % zip_filepath)
	# need to convert to absolute path string
	abs_filepath = str(zip_filepath.absolute())
	# send it as a ZIP file
	log.info("Export: Sending sub-corpus ZIP file %s" % abs_filepath)
	return send_file(abs_filepath, mimetype='application/zip', as_attachment=True, 
		  download_name=zip_filepath.name)

# --------------------------------------------------------------

def format_export_format_options(selected="text"):
	html = ""
	export_format_keys = list(export_format_map.keys())
	export_format_keys.sort()
	for key in export_format_keys:
		# is this the currently selected option?
		if key == selected:
			html += "<option value='%s' selected>%s</option>\n" % (key, export_format_map[key])
		else:
			html += "<option value='%s'>%s</option>\n" % (key, export_format_map[key])
	return html	

def format_export_num_options(total_results = 100):
	if total_results < 1:
		total_results = 100
	html = ""
	# for limit in [ 10, 20, 50, 100, 250, 500, 1000]:
	for limit in [10, 20, 50, 100, 200, 500]:
		if total_results < limit:
			break
		html += "<option value='%d'" % limit
		if total_results < 100 and limit == 10:
			html += " selected"
		elif total_results >= 100 and limit == 100:
			html += " selected"
		html += ">Top %d Documents</option>\n" % limit
	# html += "<option value='all'>All Documents</option>\n" 
	return html	

def format_subcorpus_list(context, db):
	user_id = context.user_id
	if user_id is None:
		log.warning("WARNING: No user specified for lexicons in format_subcorpus_list()")
		abort(403, "Cannot list lexicons for anonymous user")
	subcorpora = db.get_user_subcorpora(user_id)
	if subcorpora is None:
		log.warning("WARNING: No sub-corpora available for user_id=%s" % user_id)
		subcorpora = []
	html = ""
	for subcorpus in subcorpora:
		subcorpus_id = subcorpus["id"]
		properties = db.get_subcorpus_metadata(subcorpus_id)
		html += "<tr class='subcorpus'>\n"
		# create the action URL
		url_download = "%s/corpora?action=download&subcorpus_id=%s&ext=.zip" % (context.prefix, subcorpus_id)
		# create the HTML for the table columns
		html += "<td class='text-left subcorpus'><i>%s</i></td>" % subcorpus.get("name", "Untitled")
		num_documents = subcorpus.get("documents", 0)
		html += "<td class='text-center subcorpus'>%s</td>" % "{:,}".format(num_documents)
		html += "<td class='text-left subcorpus'>%s</td>" % export_format_map.get(subcorpus.get("format", "text"), "Full Text")
		# create the summary column
		summary = ""
		for key in properties:
			if key == "lexicon":
				if db.has_lexicon(properties[key]):
					lex = db.get_lexicon(properties[key])
					if not lex is None:
						summary += "<li>Lexicon: %s</li>\n" % lex.get("name","Untitled")
			elif key == "type" and subcorpus.get("format","") != "metadata":
				summary += "<li>Document Type: %s</li>" % type_name_map.get(properties[key],"Volumes")
			elif key == "search_field":
				summary += "<li>Search Field: %s</li>" % properties[key]
			elif key == "date_range":
				if type(properties[key]) == list and len(properties[key]) == 2:
					s_year = format_year_range(properties[key][0], properties[key][1])
					if len(s_year) > 0:
						summary += "<li>Date Range: %s</li>" % s_year
					else:
						summary += "<li>Date Range: All years</li>" 				
			elif key == "query":
				if type(properties[key]) == list:
					s_query = " ".join(properties[key])
				else:
					s_query = " ".join(properties[key].split(" "))
				summary += "<li>Query: %s</li>" % s_query
			elif key == "classification":
				if properties[key] == "*" or properties[key] == ""  or properties[key] == "all":
					summary += "<li>Classification: All</li>"
				else:
					summary += "<li>Classification: %s</li>" % properties[key]
			elif key == "subclassification":
				if not(properties[key] == "*" or properties[key] == ""):
					summary += "<li>Sub-classification: %s</li>" % properties[key]
		if len(summary) > 0:
			summary = "<ul class='subcorpus'>\n%s</ul>\n" % (summary)
		html += "<td class='text-left subcorpus'>%s</td>" % summary
		# add the result
		html += "<td class='text-center subcorpus'><a href='%s'><img src='%s/img/save.png' width='30px' style=''/></a></td>\n" % (url_download, context.staticprefix)
		html += "</tr>\n"
	return html

# --------------------------------------------------------------

class BulkExporter:
	""" Class for handling bulk export of a set of volumes or segments from Curatr """

	def __init__(self, core, solr, export_name, export_format, export_num, user_id, search_params):
		self.core = core
		self.current_solr = solr
		self.export_name = export_name
		self.export_format = export_format
		self.export_num = export_num
		self.user_id = user_id
		self.search_params = search_params

	def run(self):
		log.info("Export: Starting export for export_name '%s'" % self.export_name)
		# Step 1: Get DB & Perform the search
		db, export_id = None, "untitled"
		try:
			db = self.core.get_db()
			base_export_id = re.sub(r'[^a-zA-Z0-9]', '', self.export_name.lower().strip())
			if len(base_export_id) == 0:
				base_export_id = "untitled"
			# add the user id
			base_export_id = "%s_%s" % (self.user_id, base_export_id)
			export_id = base_export_id
			num = 0
			existing_ids = set(db.get_all_subcorpus_ids())
			while export_id in existing_ids:
				num += 1
				export_id = base_export_id + str(num)
			log.info("Export: Starting export for export_id '%s'" % export_id)
			# perform the search
			results = self.search()
			if len(results) == 0:
				log.warning("Warning: No results found for export_id '%s'" % export_id)
				db.close()
				return
			log.info("Export: Found %d results for export_id '%s'" % (len(results), export_id))
		except Exception:
			log.exception("ERROR: Export failed for export_id '%s' due to unhandled exception in Step 1 of exp.run" % export_id)
			if db:
				db.close()
			return

		# Step 2: File creation
		try:
			# create the metadata file
			is_segments = self.search_params.get("type", "volume") == "segment"
			meta_fname = base_export_id + ".meta.json"
			meta_path = self.core.dir_export / meta_fname
			self.write_metadata(results, meta_path, is_segments)
			# create the JSON file
			description_fname = base_export_id + ".json"
			description_path = self.core.dir_export / description_fname
			self.write_description(results, description_path)
			# create the ZIP file
			zip_fname = base_export_id + ".zip"
			zip_path = self.core.dir_export / zip_fname
			log.info("Export: Preparing to write ZIP file: %s" % zip_path)
			# only write the metadata
			if self.export_format == "metadata":
				results = []
			if self.write_zip(results, zip_path, meta_path, description_path, is_segments):
				log.info("Export: Export complete for export_id '%s'" % export_id)
			else:
				log.error("ERROR: Export failed for export_id '%s' when writing ZIP file" % export_id)
				# need to delete the JSON description file after the failed export
				if description_path.exists():
					description_path.unlink()
				db.close()
				return
			# always delete the metadata file
			if meta_path.exists():
				meta_path.unlink()
			# read back in the description, and tidy it
			fin = open(description_path, "r")
			desc = json.load(fin)		
			fin.close()
			desc["export_format"] = self.export_format
			if not "type" in desc:
				desc["type"] = "volume"
			if not "field" in desc:
				desc["field"] = "Full text"
			if not "name" in desc:
				desc["name"] = "Untitled"
			for key in desc["properties"]:
				desc[key] = desc["properties"][key]
			del desc["properties"]
			if len(desc["lexicon"].strip()) == 0:
				del desc["lexicon"]		
			# now add to the database
			log.info("Export: Adding corpus: %s - %s" % (export_id, desc["name"]))
			subcorpus_id = db.add_subcorpus(desc, zip_fname, self.user_id)
			if subcorpus_id == -1:
				log.exception("ERROR: Export failed for export_id '%s' when add sub-corpus to database" % export_id)
			else:
				log.info("Export: Added subcorpus with ID=%s" % subcorpus_id)	
		except Exception:
			log.exception("ERROR: Export failed for export_id '%s' due to unhandled exception in Step 2 of exp.run" % export_id)
		# finished
		if db:
			db.close()	

	def write_metadata(self, results, meta_path, is_segments):
		log.info("Writing sub-corpus metadata file to %s" % meta_path)
		export_metadata = []
		ignores = [ "content", "_version_" ]
		if not is_segments:
			ignores += [ "segment", "max_segment", "book_id", "cat_start", "cat_end" ]
		for doc in results:
			doc_metadata = {}
			for key in doc:
				if not key in ignores:
					doc_metadata[key] = doc[key]
			if not is_segments:
				doc_metadata["id"] = doc["book_id"]
			export_metadata.append(doc_metadata)
		with open(meta_path, "w", encoding="utf-8", errors="ignore") as fout:
			fout.write(json.dumps(export_metadata, indent=4))

	def write_description(self, results, description_path):
		log.info("Writing sub-corpus description file to %s" % description_path)
		data = { "name" : self.export_name, "format" : self.export_format, "documents" : len(results) }
		# create the properties
		properties = { "date_range" : [0,2000] }
		spec = self.parse_search_params(self.search_params)
		for key in spec:
			# note we need to remove the prefix, if it's applied
			if key.startswith("spec_"):
				key = key[5:]
			if key == "lexicon_id":
				properties["lexicon"] = spec[key]
			elif key == "class":
				properties["classification"] = spec[key]
			elif key == "subclass":
				properties["subclassification"] = spec[key]
			elif key == "type":
				properties["type"] = spec[key]
			elif key == "location":
				properties["location"] = spec[key]
			elif key == "field":
				properties["search_field"] = field_name_map.get(spec[key], "Full text")
			# TODO: more nuanced parsing of query string
			elif key == "query":
				properties["query"] = spec[key].split(" ")
			elif key == "year_start":
				properties["date_range"][0] = int(spec[key])
			elif key == "year_end":
				properties["date_range"][1] = int(spec[key])
		# write the data
		data["properties"] = properties
		with open(description_path, "w", encoding="utf-8", errors="ignore") as fout:
			fout.write(json.dumps(data, indent=4))

	def write_zip(self, results, zip_path, meta_path, description_path, is_segments):
		""" Actually create a ZIP file for export """
		log.info("Creating sub-corpus zip file %s ..." % zip_path)
		try:
			zip = zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED)
			zip.write(meta_path.absolute(), "metadata.json")
			zip.write(description_path.absolute(), "description.json")
			for doc in results:
				fname = "%s.txt" % doc["id"]
				if is_segments:
					arc_path = Path("volumes") / fname
				else:
					arc_path = Path("segments") / fname
				zip.writestr(str(arc_path), doc["content"])
			zip.close()
		except Exception as e:
			log.error("ERROR: Export failed when writing ZIP file %s" % zip_path)
			log.error(str(e))
			return False
		return True

	def search(self):
		# Get the basic search specification
		spec = self.parse_search_params(self.search_params)
		query_string = spec["query"]		
		filters = {}
		# year range for search
		filters["year"] = "[%d TO %d]" % (spec["year_start"], spec["year_end"])
		# has a particular classification or subclassification been specified?
		if spec["class"].lower() != "all":
			filters["classification"] = spec["class"]
		if spec["subclass"].lower() != "all":
			filters["subclassification"] = spec["subclass"]
		# has any specific book_id been specified?
		if spec["book_id"] != "":
			filters["book_id"] = spec["book_id"]		
		# Perform the actual search
		if self.export_num < 1:
			page_size = 100
		else:
			page_size = min(100, self.export_num)
		start = 0
		all_results = []
		if self.export_num > 0:
			log.info("Export: Starting to export up to %d documents for query '%s' ..." % (self.export_num, query_string))
		else:
			log.info("Export: Starting to export all documents for query '%s' ..." % query_string) 
		while True:
			res = self.current_solr.query(query_string, spec["field"], filters, start, False, 0, page_size)	
			# no results?
			if res is None or len(res.docs) == 0:
				break
			all_results += res.docs
			num_total_results = res.get_num_found()
			log.info("Export: Export query returned %d/%d results (start=%d)" % (len(res.docs), num_total_results, start))
			start += page_size
			# reached the end?
			if self.export_num > 0 and start >= min(num_total_results, self.export_num):
				break
		if self.export_num > 0 and len(all_results) > self.export_num:
			return all_results[0:self.export_num]
		return all_results

	def parse_search_params(self, params):
		spec = {}
		spec["query"] = params.get("qwords", "").strip()
		# TODO: more nuanced way of doing this?
		spec["type"] = params.get("type", "volume").strip().lower()
		spec["field"] = params.get("field", "all").strip().lower()
		if spec["field"] != "all" and spec["query"].startswith(spec["field"] +":"):
			spec["query"] = spec["query"][len(spec["field"])+1:]
		spec["year_start"] = max(0, safe_int(params.get("year_start", ""), 0))
		spec["year_end"] = max(0, safe_int(params.get("year_end", ""), 2000))
		# just in case the user has specified these in the wrong order, swap them
		if spec["year_start"] > spec["year_end"]:
			spec["year_start"], spec["year_end"] = spec["year_end"], spec["year_start"]
		spec["class"] = params.get("class", "all").strip()
		if spec["class"] is None or len(spec["class"]) < 2:
			spec["class"] = "All"
		spec["subclass"] = params.get("subclass", "all").strip()
		if spec["subclass"] is None or len(spec["subclass"]) < 2:
			spec["subclass"] = "All"
		# just in case a specific book_id was specified
		spec["book_id"] = params.get("book_id", "").strip()
		# lexicon id?
		spec["lexicon_id"] = params.get("lexicon_id", "").strip()
		return spec
