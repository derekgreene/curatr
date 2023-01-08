#!/usr/bin/env python
"""
This script implements the embedded web server for Curatr, which provides search functionality for the British library 
corpus via an external Solr server and MySQL database containing metadata.

Sample usage, specifying the core configuration directory:
``` python code/curatr.py core ```

Then access the search interface at:
http://127.0.0.1:5000
"""
import sys
from pathlib import Path
import logging as log
from optparse import OptionParser
from datetime import datetime
# Flask imports
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from flask import request, Response, render_template, Markup
from flask import redirect, url_for
# project imports
from server import CuratrServer, CuratrContext

# --------------------------------------------------------------

print("Creating Curatr server...")
app = CuratrServer(__name__)
app.debug = True
print("Creating login manager...")
login_manager = LoginManager()	
# login_manager.session_protection = None
print("Initializing login manger...")
login_manager.init_app(app)

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

# --------------------------------------------------------------
# Endpoints: Home & About

@app.route("/")
@app.route('/index')
def handle_index():
	""" Render the main Curatr home page """
	context = app.get_context(request)
	context["num_books"] =  "{:,}".format( app.core.cache["book_count"] )
	context["year_min"] = app.core.cache["year_min"]
	context["year_max"] = app.core.cache["year_max"]
	log.info("Index: current_user.is_anonymous: %s" % current_user.is_anonymous )
	return render_template("index.html", **context )


@app.route("/about")
def handle_about():
	""" Render the Curatr about page """
	context = app.get_context(request)
	return render_template("about.html", **context )
	

# --------------------------------------------------------------
# Endpoints: Login and Login

@app.route('/logout')
@login_required
def handle_logout():
	logout_user()
	return redirect(url_for('handle_index'))

@app.route("/login", methods=['POST','GET'])
def handle_login():
	""" End point for handling user logins. """
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

def configure_server(dir_core, dir_log = None):
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
	if not app.init_server( dir_core ):
		sys.exit( 1 )

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