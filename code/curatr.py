#!/usr/bin/env python
"""
This script implements the embedded web server for Curatr, which provides search functionality for the British library 
corpus via an external Solr server and MySQL database containing metadata.

Sample usage, specifying the core configuration directory:
``` python code/curatr.py core ```

Then access the search interface at:
http://127.0.0.1:5000
"""
import sys, io, json
from pathlib import Path
import logging as log
from optparse import OptionParser
from datetime import datetime
# Flask imports
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from flask import request, Response, render_template, Markup
from flask import redirect, url_for, abort, send_file
# project imports
from server import CuratrServer, CuratrContext
from web.search import parse_search_request, populate_search_results
from web.view import populate_segment, populate_volume
from web.format import format_field_options, format_type_options
from web.format import format_classification_options, format_subclassification_options, format_place_options
from web.format import format_classification_links, format_subclassification_links
from web.features import populate_author_page, populate_bookmark_page, populate_similar_page
from web.ngrams import populate_ngrams_page, export_ngrams
from web.networks import populate_networks_page, export_network
from web.lexicon import populate_lexicon_create, populate_lexicon_delete, format_lexicon_list, populate_lexicon_edit
from web.export import handle_export_download, handle_export_build, format_subcorpus_list
from web.api import author_list, ngram_counts
from web.util import safe_int

# --------------------------------------------------------------
# Application Setup
# --------------------------------------------------------------

print("Creating Curatr server...")
app = CuratrServer(__name__)
app.debug = True
print("Creating login manager...")
login_manager = LoginManager()	
# login_manager.session_protection = None
print("Initializing login manger...")
login_manager.init_app(app)

# --------------------------------------------------------------
# Login Handling
# --------------------------------------------------------------

@login_manager.user_loader
def load_user(user_id):
	""" Code to handle user logins using the flask_login package """
	if user_id is None:
		log.warning("Warning: Login manager had failed login. Cannot log in user empty NULL ID")
		return None
	# retrieve details for the user from the database
	db = app.core.get_db()
	log.info("Login manager: Requesting user with ID %s" % user_id)
	user = db.get_user_by_id(user_id)
	if user is None:
		log.error("Error: Failed login. No user with ID %s" % user_id)
	db.close()
	return user

@app.route('/logout')
@login_required
def handle_logout():
	""" End point for handling users logging out """
	logout_user()
	return redirect(url_for('handle_index'))

@app.route("/login", methods=['POST','GET'])
def handle_login():
	""" End point for handling user logins """
	if request.method == 'GET':
		return redirect(url_for('handle_index'))
	# get form values
	email = request.values.get("email", default = "").strip().lower()
	passwd = request.values.get("password", default = "").strip()
	db = app.core.get_db()
	user = db.get_user_by_email(email)
	# validate form values
	verified = False
	if user is None:
		log.warning("Login: Failed login attempt, no such user '%s'" % email )
	else:
		if user.verify(passwd):
			verified = True
		else:
			log.warning("Login: Failed login, bad password for user '%s'" % email )
	# proceed with login?
	if verified:
		login_user(user, remember = True)
		log.info( "Login: Login ok for user '%s'" % email )
		# update the last login time
		db.record_login(user.id)
		# finished with the database
		db.close()
		return redirect(url_for('handle_index'))
	# finished with the database 
	db.close()
	# invalid login
	# TODO: Display invalid login
	# flash("Invalid username/password combination")
	return redirect(url_for('handle_index'))
	#return redirect(url_for('handle_index')+"?action=invalid")

# --------------------------------------------------------------
# Endpoints: Home & About
# --------------------------------------------------------------

@app.route("/")
@app.route('/index')
def handle_index():
	""" Render the main Curatr home page """
	context = app.get_context(request)
	context["num_books"] =  "{:,}".format(app.core.cache["book_count"])
	context["year_min"] = app.core.cache["year_min"]
	context["year_max"] = app.core.cache["year_max"]
	log.info("Index: current_user.is_anonymous: %s" % current_user.is_anonymous)
	return render_template("index.html", **context)

@app.route("/about")
def handle_about():
	""" Render the Curatr about page """
	context = app.get_context(request)
	return render_template("about.html", **context)

# --------------------------------------------------------------
# Endpoints: Search
# --------------------------------------------------------------

@app.route("/search")
@login_required
def handle_search():
	# Get the basic search specification
	spec = parse_search_request(request)
	# is this just a request for an empty search pages?
	query_string = spec["query"]
	action = request.args.get("action", default = "").strip()
	if len(query_string) == 0:
		# any action?
		if len(action) == 0:
			context = handle_empty_search( spec )
			return render_template("search.html", **context )
		query_string = "*"
	# Dealing with volumes or segments?
	current_solr = app.core.get_solr( spec["type"] )
	db = app.core.get_db()
	# populate the values in template
	context = app.get_navigation_context( request, spec )
	context = populate_search_results( context, db, current_solr, spec )
	# finished with the database
	db.close()
	return render_template("search-results.html", **context )

def handle_empty_search(spec):
	context = app.get_context(request)
	context["num_volumes"] =  "{:,}".format( app.core.cache["volume_count"] )
	context["year_min"] = app.core.cache["year_min"]
	context["year_max"] = app.core.cache["year_max"]
	# use default parameters
	context["field_options"] = Markup(format_field_options())
	context["type_options"] = Markup(format_type_options())
	context["class_options"] = Markup(format_classification_options(context))
	context["subclass_options"] = Markup(format_subclassification_options(context))
	context["location_options"] = Markup(format_place_options( context))
	# TODO: fix
	#context["mudies_options"] = Markup(format_mudies_options())
	return context

@app.route("/segment")
@login_required
def handle_segment():
	""" End point to display the text for a single segment """
	current_solr = app.core.get_solr("segments")
	# Get the basic search specification
	segment_id = request.args.get("id", default = "").strip().lower()
	if len(segment_id) == 0:
		abort(404, description="No segment ID specified")
	volume_id = segment_id.rsplit("_",1)[0]
	# query the document from Solr
	doc = current_solr.query_document(segment_id)
	if doc is None:
		error_msg = "No segment match found for: %s" % segment_id
		abort(404, description=error_msg)
	# populate the template context
	db = app.core.get_db()
	spec = parse_search_request(request)
	context = app.get_navigation_context(request, spec)
	context = populate_segment(context, db, doc, spec, segment_id)
	# do we need to perform a bookmark action here?
	action = request.args.get("action", default = "").strip().lower()
	if action == "addbookmark":
		# ensure we don't have this bookmark already
		if db.has_segment_bookmark(current_user.id, volume_id, segment_id):
			log.warning("Warning: Bookmark already exists for user_id=%s segment_id=%s" % (current_user.id, segment_id))
		else:
			if not db.add_bookmark(current_user.id, volume_id, segment_id):
				log.error("Error: Failed to add bookmark for user_id=%s segment_id=%s" % (current_user.id, segment_id))
	elif action == "deletebookmark":
		if not db.delete_bookmark(current_user.id, volume_id, segment_id):
			log.error("Error: Failed to delete bookmark for user_id=%s segment_id=%s" % (current_user.id, segment_id))
	# bookmark info
	context["is_bookmarked"] = db.has_segment_bookmark(current_user.id, volume_id, segment_id)
	if context["is_bookmarked"]:
		context["url_bookmark"] = "%s/segment?id=%s&action=deletebookmark" % (context.prefix, segment_id)
	else:
		context["url_bookmark"] = "%s/segment?id=%s&action=addbookmark" % (context.prefix, segment_id)
	# finished with db
	db.close()
	# render the template
	return render_template("segment.html", **context)

@app.route("/volume")
@login_required
def handle_volume():
	""" End point to display the text for a single volume """
	current_solr = app.core.get_solr("volumes")
	# Get the basic search specification
	volume_id = request.args.get("id", default = "").strip().lower()
	if len(volume_id) == 0:
		abort(404, description="No volume ID specified")
	# query the document from Solr
	doc = current_solr.query_document(volume_id)
	if doc is None:
		error_msg = "No volume match found for: %s" % volume_id
		abort(404, description=error_msg)
	# populate the template context
	db = app.core.get_db()
	spec = parse_search_request(request)
	context = app.get_navigation_context(request, spec)
	context = populate_volume(context, db, doc, spec, volume_id)
	# do we need to perform a bookmark action here?
	action = request.args.get("action", default = "").strip().lower()
	if action == "addbookmark":
		# ensure we don't have this bookmark already
		if db.has_volume_bookmark(current_user.id, volume_id):
			log.warning("Warning: Bookmark already exists for user_id=%s volume_id=%s" % (current_user.id, volume_id))
		else:
			if not db.add_bookmark(current_user.id, volume_id):
				log.error("Error: Failed to add bookmark for user_id=%s volume_id=%s" % (current_user.id, volume_id))
	elif action == "deletebookmark":
		if not db.delete_bookmark(current_user.id, volume_id):
			log.error("Error: Failed to delete bookmark for user_id=%s volume_id=%s" % (current_user.id, volume_id))
	# add bookmark info
	context["is_bookmarked"] = db.has_volume_bookmark(current_user.id, volume_id)
	if context["is_bookmarked"]:
		context["url_bookmark"] = "%s/volume?id=%s&action=deletebookmark" % (context.prefix, volume_id)
	else:
		context["url_bookmark"] = "%s/volume?id=%s&action=addbookmark" % (context.prefix, volume_id)
	# finished with db
	db.close()
	# render the template
	return render_template("volume.html", **context)

# --------------------------------------------------------------
# Endpoints: Authors
# --------------------------------------------------------------

@app.route("/authors")
@login_required
def handle_authors():
	context = app.get_context(request)
	context["author_count"] =  "{:,}".format( app.core.cache["author_count"] )
	context["year_min"] = app.core.cache["year_min"]
	context["year_max"] = app.core.cache["year_max"]
	return render_template("author-list.html", **context )

@app.route("/author")
@login_required
def handle_author():
	""" End point for delivering recommended content """
	sauthor_id = request.args.get("author_id", default = "").strip().lower()
	if len(sauthor_id) == 0:
		abort(404, description="No author ID specified")
	author_id = safe_int(sauthor_id, 0)
	if author_id < 1:
		abort(404, description="Invalid author ID specified")
	# get the relevant author info
	db = app.core.get_db()
	author = db.get_cached_author( author_id )
	if author is None:
		error_msg = "No such author ID: %s" % author_id
		abort(404, description=error_msg)
	# populate the parameters to fill the template
	context = app.get_context(request)
	context = populate_author_page( context, db, author )
	# finished with the database
	db.close()
	return render_template("author.html", **context )
	
# --------------------------------------------------------------
# Endpoints: Classification Index & Catalogue
# --------------------------------------------------------------

@app.route("/classification")
@login_required
def handle_classification():
	context = app.get_context(request)
	context["classification"] = Markup(format_classification_links(context))
	context["subclassification"] = Markup(format_subclassification_links(context))
	context["num_subclasses"] = len( app.core.cache["subclass_names"])
	context["num_top_subsubclassifications"] = len(app.core.cache["top_subclass_counts"])
	return render_template("classification.html", **context)

@app.route("/catalogue")
@login_required
def handle_catalogue():
	context = app.get_context(request)
	context["num_books"] =  "{:,}".format(app.core.cache["book_count"])
	context["year_min"] = app.core.cache["year_min"]
	context["year_max"] = app.core.cache["year_max"]
	return render_template("catalogue.html", **context)

# --------------------------------------------------------------
# Endpoints: Ngrams
# --------------------------------------------------------------

@app.route("/ngrams")
@login_required
def handle_ngrams():
	""" Endpoint for the ngram viewer page. """
	context = app.get_context(request)	
	context = populate_ngrams_page(context, app)
	# render the template
	return render_template("ngrams.html", **context)

@app.route("/exportngrams")
@login_required
def handle_ngram_export():
	""" Handle export a CSV representation of ngram counts. """
	context = app.get_context(request)	
	file = export_ngrams(context, app)
	if file is None:
		abort(404, description="No inputs specified for ngram export")
	return file	

# --------------------------------------------------------------
# Endpoints: Networks
# --------------------------------------------------------------

@app.route("/networks")
@login_required
def handle_networks():
	""" Endpoint for the semantic network visualization page. """
	context = app.get_context(request)	
	context = populate_networks_page(context)
	return render_template("networks.html", **context)

@app.route("/exportnetworks")
@login_required
def handle_network_export():
	""" Handle export a GEXF representation of a semantic network. """
	context = app.get_context(request)	
	file = export_network(context)
	if file is None:
		abort(404, description="No inputs specified for network export")
	return file

# --------------------------------------------------------------
# Endpoints: Lexicons
# --------------------------------------------------------------

@app.route("/lexicon")
@login_required
def handle_lexicon():
	lexicon_id = safe_int(request.args.get("lexicon_id", default = "").strip().lower(), 0)
	context = app.get_context(request)
	db = app.core.get_db()
	# What type of action?
	action = request.args.get("action", default = "").strip().lower()
	# Create a new lexicon?
	if action == "create":
		context = populate_lexicon_create(context, db)
	# Delete an existing lexicon?
	elif action == "delete" and lexicon_id > 0:
		context = populate_lexicon_delete(context, db, lexicon_id)
	# Default action - display list of lexicons
	context["lexlist"] = Markup(format_lexicon_list(context, db))
	context["type_options"] = Markup(format_type_options())
	context["class_options"] = Markup(format_classification_options(context))
	# finished with database
	db.close()
	return render_template("lexicon.html", **context)

@app.route("/lexiconedit")
@login_required
def handle_lexicon_edit():
	""" Handle editing an individual word lexicon. """
	lexicon_id = safe_int(request.args.get("lexicon_id", default = "").strip().lower(), 0)
	# any ID specified?
	if lexicon_id < 1:
		abort(404, description="No valid lexicon ID specified")
	context = app.get_context(request)
	db = app.core.get_db()
	# handle the edit / populate parameters
	context = populate_lexicon_edit(context, db, lexicon_id)
	# finished with database
	db.close()	
	return render_template("edit-lexicon.html", **context)

@app.route("/exportlexicon")
@login_required
def handle_lexicon_export():
	""" Handle export a plain text representation of an individual word lexicon. """
	lexicon_id = safe_int(request.args.get("lexicon_id", default = "").strip().lower(), 0)
	# any ID specified?
	if lexicon_id < 1:
		abort(404, description="No valid lexicon ID specified")
	context = app.get_context(request)
	# connect to the database and get the required lexcion
	db = app.core.get_db()
	lexicon = db.get_lexicon(lexicon_id)
	# not a valid lexicon?
	if lexicon is None:
		abort(403, "Cannot find specified lexicon in the database (lexicon_id=%s)" % lexicon_id)
	# not owned by the current user?
	if lexicon["user_id"] != context.user_id:
		abort(403, "You do not own this lexicon (lexicon_id=%s)" % lexicon_id)
	# get the words for this lexicon
	log.info("Running export for lexicon lexicon_id=%s" % lexicon_id) 
	words = db.get_lexicon_words(lexicon_id)
	if words is None or len(words) == 0:
		s_words = ""
	else:
		s_words = "\n".join(sorted(words))
	# finished with database
	db.close()	
	# suggested filename
	filename = "%s.txt" % lexicon.get("name", "untitled").lower().replace(".", "").replace(" ", "_")
	log.info("Exporting lexicon to plain/text to %s" % filename) 
	# send the response
	out = io.StringIO()
	out.write(s_words)
	out.write("\n")
    # Creating the byteIO object from the StringIO Object
	mem = io.BytesIO()
	mem.write(out.getvalue().encode('utf-8'))
	mem.seek(0)
	out.close()	
	return send_file(mem, mimetype='text/plain', as_attachment=True, attachment_filename=filename)

# --------------------------------------------------------------
# Endpoints: Sub-corpora
# --------------------------------------------------------------

@app.route("/corpora")
@login_required
def handle_corpora():
	db = app.core.get_db()
	spec = parse_search_request(request)
	# has the user submitted an action?
	action = request.args.get("action", default = "").strip().lower()
	if action == "download":
		subcorpus_id = request.args.get("subcorpus_id", default = "").strip().lower()
		if len(subcorpus_id) == 0:
			log.warning("Warning: No subcorpus ID specified for download")
		else:
			resp = handle_export_download(app.core, subcorpus_id)
			if resp is None:
				abort(404, description="Unable to download corpus ZIP file")
			return resp
	# populate the template context
	context = app.get_context(request)
	if action == "export":
		context = handle_export_build(context, app.core, spec)
	context["subcorpuslist"] = Markup(format_subcorpus_list(context, db))
	# finished with the db
	db.close()
	return render_template("corpora.html", **context)

# --------------------------------------------------------------
# Endpoints: Bookmarks
# --------------------------------------------------------------

@app.route("/bookmarks")
@login_required
def handle_bookmarks():
	""" End point for showing a user's bookmarks """
	db = app.core.get_db()
	# has the user submitted an action?
	action = request.args.get("action", default = "").strip().lower()
	if action == "delete":
		bookmark_id = request.args.get("bookmark_id", default = "").strip().lower()
		if len(bookmark_id) == 0:
			log.warning("Warning: No bookmark ID specified for deletion")
		else:
			if not db.delete_bookmark_by_bookmark_id(bookmark_id, current_user.id):
				log.error("Error: Failed to delete bookmark '%s' for user '%s'" % (bookmark_id, current_user.id))
	# populate the template context
	context = app.get_context(request)
	context = populate_bookmark_page(context, db, current_user.id)
	# finished with the db
	db.close()
	return render_template("bookmarks.html", **context)

# --------------------------------------------------------------
# Endpoints: Volume Recommendations
# --------------------------------------------------------------

@app.route("/similar")
@login_required
def handle_similar():
	""" End point for delivering recommended content """
	volume_id = request.args.get("volume_id", default = "").strip().lower()
	if len(volume_id) == 0:
		abort(404, description="No volume ID specified")
	db = app.core.get_db()
	# get the relevant book info
	volume = db.get_volume_metadata(volume_id)
	if volume is None:
		db.close()
		error_msg = "No such volume ID: %s" % volume_id
		abort(404, description=error_msg)
	# populate the template parameters
	context = app.get_context(request)
	context = populate_similar_page(context, db, volume)
	# finished with DB
	db.close()
	return render_template("similar.html", **context)		

# --------------------------------------------------------------
# Endpoints: API
# --------------------------------------------------------------

@app.route("/api/authors")
def handle_api_authors():	
	""" Return API data relating to complete list of authors """
	data = author_list(app.core)
	# return the author catalogue as JSON
	return Response(json.dumps(data), mimetype="application/json")

@app.route("/api/ngrams")
def handle_counts():
	db = app.core.get_db()
	try:
		values = ngram_counts(app.core, db)
	except Exception as e:
		db.close()
		abort(404, description=str(e))
	db.close()
	# return the counts as JSON
	return Response(json.dumps(values), mimetype="application/json")

# --------------------------------------------------------------
# Error Handling
# --------------------------------------------------------------

@app.errorhandler(404)
def page_not_found(e):
	""" Handle HTTP 404 errors """
	context = app.get_context()
	# note that we set the status explicitly
	return render_template('error-404.html', **context), 404

@app.errorhandler(500)
def internal_server_error(e):
	""" Handle HTTP 500 errors """
	context = app.get_context()
	context["message"] = e.description
	if context["message"] is None:
		context["message"] = "Unknown error on server"
	# note that we set the status explicitly
	return render_template('error-500.html', **context), 500    

@app.errorhandler(403)
def page_forbidden(e):
	""" Handle HTTP 403 errors """
	context = app.get_context()
	context["message"] = e.description
	if context["message"] is None:
		context["message"] = "Resource does not belong to current user"
	# note that we set the status explicitly
	return render_template('error-403.html', **context), 403   
	
# --------------------------------------------------------------

def configure_server(dir_core, dir_log=None):
	""" Configure server directories, logging output, and initialize the web server. """
	# get core configuration and read the metadata
	if not (dir_core.exists() and dir_core.is_dir()):
		sys.exit("Error: invalid core directory %s" % dir_core)

	# track startup time
	app.start_time = datetime.now()
	# configure logging
	if dir_log is None:
		# use the default log file directory
		dir_log = dir_core / "log"
	dir_log.mkdir( exist_ok=True )
	log_prefix = app.start_time.strftime('%Y%m%d-%H%M')
	log_fname = log_prefix + ".log"
	log_path = dir_log / log_fname
	handlers = [log.FileHandler(log_path), log.StreamHandler()]
	log.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=log.INFO, handlers=handlers, datefmt='%Y-%m-%d %H:%M')
	log.info("+++ Starting Curatr: %s" % log_prefix)
	log.info("Log files will be stored in %s" % dir_log )

	# Initialize and start the web server
	log.info("Initializing server ...")
	if not app.init_server(dir_core):
		sys.exit(1)

def main():
	parser = OptionParser(usage="usage: %prog [options] dir_core")
	(options, args) = parser.parse_args()
	if len(args) != 1:
		parser.error("Must specify core directory")
	# configure the Curatr server
	configure_server(Path(args[0]))
	# start the server
	app.run()

# --------------------------------------------------------------

if __name__ == "__main__":
	main()