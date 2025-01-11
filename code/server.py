import logging as log
# Flask logins
from flask import Flask, Markup
from flask_login import current_user
# project imports
from core import CoreCuratr
from web.format import format_classification_options, format_subclassification_options
from web.format import format_place_options
from web.format import format_field_options, format_type_options

# --------------------------------------------------------------

class CuratrServer(Flask):
	""" Core Flask server application """
	def __init__(self, import_name):
		super(CuratrServer, self).__init__(import_name)
		self.core = None

	def init_server(self, dir_core):
		# create the Curatr core
		self.core = CoreCuratr(dir_core)

		# get the server config
		core_config = self.core.config
		self.port_number = core_config["app"].getint("port", 5000)
		self.hostname = core_config["app"].get("hostname", "localhost")
		self.server_name = "%s:%d" % (self.hostname, self.port_number)
		log.info("Configuring server %s ..." % self.server_name)

		# Flask settings
		self.config["JSONIFY_PRETTYPRINT_REGULAR"] = True
		#self.config["SERVER_NAME"] = self.server_name
		self.config["SESSION_COOKIE_DOMAIN"] = self.server_name
		# set secret key for sessions
		self.secret_key = core_config["app"].get("secret_key", None)
		if self.secret_key is None:
			log.error("Error: No app secret key specified in configuration file")
			return False

		# Get prefix for web content
		self.prefix = core_config["app"].get("prefix", "" )
		self.staticprefix = core_config["app"].get("staticprefix", self.prefix)
		self.apiprefix = core_config["app"].get("apiprefix", self.prefix )
		log.info("Server configuration: prefix=%s staticprefix=%s" % (self.prefix, self.staticprefix))

		# Login settings
		self.require_login = core_config["app"].getboolean("require_login", True)
		log.info("System requires user login: %s" % self.require_login)

		# Create a connection to the database
		if not self.core.init_db(autocommit = True):
			log.error("Error: Cannot run web server without database connection")
			return False

		# Create connections to Solr
		if not self.core.init_solr():
			log.error("Error: Cannot run web server without Solr connection")
			return False

		# Cache required values from database
		self.core.cache_values()

		# Preload any the embedding model?
		if str( core_config["app"].get("embedding_preload", "false" ) ).lower() == "true":
			log.info("Preloading embedding model ...")
			self.core.get_embedding()	
		# Initalized ok
		return True	

	def run(self, debug=False):
		""" Start the Flask web server """
		return Flask.run(self, port=self.port_number, debug=debug)

	def get_context(self, request=None):
		context = CuratrContext()
		if current_user.is_anonymous:
			context.user_id = None
			context.user_email = None
		else:
			context.user_id = current_user.id
			context.user_email = current_user.email
		context.request = request
		context.core = self.core
		context.prefix = self.prefix
		context.staticprefix = self.staticprefix
		context.apiprefix = self.apiprefix
		context["require_login"] = self.require_login
		context["prefix"] = self.prefix
		context["staticprefix"] = self.staticprefix
		context["apiprefix"] = self.apiprefix
		context["message"] = ""
		return context

	def get_navigation_context(self, request, spec):
		""" Populate search and navigation-related parameters for HTML templates """
		context = self.get_context(request)
		# add the query-specific values
		context["query"] = spec["query"]
		context["type"] = spec["type"]
		context["field"] = spec["field"]
		context["class"] = spec["class"]
		context["subclass"] = spec["subclass"] 
		# specific query fields?
		if spec["field"] == "title_text":
			context["query_titles"] = spec["query"]
		if spec["field"] == "authors_text":
			context["query_authors"] = spec["query"]
		if spec["field"] == "location_places":
			context["query_location"] = spec["query"]
		# date range
		if spec["year_start"] > 0:
			context["year_start"] = spec["year_start"]
		if spec["year_end"] < 2000:
			context["year_end"] = spec["year_end"]
		context["class_options"] = Markup(format_classification_options(context, spec["class"]))
		context["subclass_options"] = Markup(format_subclassification_options(context, spec["subclass"]))
		context["field_options"] = Markup(format_field_options(spec["field"]))
		context["type_options"] = Markup(format_type_options(spec["type"]))
		context["location_options"] = Markup(format_place_options(context, spec["location"]))
		# TODO: fix
		# context["mudies_options"] = Markup(format_mudies_options(spec["mudies_match"]))
		context["mudies_options"] = ""
		return context

# --------------------------------------------------------------

class CuratrContext(dict):
	""" Variable for containing web context information """
	def __init__(self, *args):
		dict.__init__(self, args)
		self.request = None
		self.core = None
