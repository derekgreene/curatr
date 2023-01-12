"""
Implementation for word lexicon-related features of the Curatr web interface
"""
import urllib.parse, re, operator
import logging as log
from collections import defaultdict
from flask import Markup, abort

# --------------------------------------------------------------

def populate_lexicon_create(context, db):
	lexicon_name = context.request.args.get("name", default = "").strip()
	if len(lexicon_name) == 0:
		lexicon_name = "Untitled"
	lexicon_description = context.request.args.get("description", default = "").strip()
	if len(lexicon_description) == 0:
		lexicon_description = "No description"
	lexicon_classification = context.request.args.get("class", default = "").strip()
	# valid user ID?
	lexicon_user_id = context.user_id
	if lexicon_user_id is None:
		abort(403, "Cannot create lexicon for anonymous user")
	s_words = context.request.args.get("words", default = "")
	s_words = re.sub("[,\.;\:]+", " ", s_words)
	s_words = re.sub("\s+", " ", s_words)
	seed_words = set()
	for word in s_words.split(" "):
		# NB: Lowercase the word and remove any commas that were added
		word = word.strip().lower()
		if len(word) > 0:
			seed_words.add(word)
	seed_words = list(seed_words)
	seed_words.sort()
	try:
		if db.add_lexicon(lexicon_name, lexicon_user_id, lexicon_description, lexicon_classification, seed_words):
			log.info("Created new lexicon id=%s" % lexicon_name)
			context["message"] = "Created new lexicon '%s'" % lexicon_name
		else:
			log.error("Error: Failed to create new lexicon '%s'" % lexicon_name)
			context["message"] = "Unable to create new lexicon"
	except Exception as e:
		log.error("Error: Failed to create new lexicon '%s'" % lexicon_name)
		log.error(str(e))
		context["message"] = "Unable to create new lexicon"	
	return context

def populate_lexicon_delete(context, db, lexicon_id):
	try:
		lexicon = db.get_lexicon(lexicon_id)
		# not a valid lexicon?
		if lexicon is None:
			abort(403, "Cannot find specified lexicon in the database (lexicon_id=%s)" % lexicon_id)
		# not owned by the current user?
		if lexicon["user_id"] != context.user_id:
			abort(403, "You do not own this lexicon (lexicon_id=%s)" % lexicon_id)
		if db.delete_lexicon(lexicon_id):
			log.info("Deleted existing lexicon id=%s" % lexicon_id)
			context["message"] = "Deleted lexicon '%s'" % lexicon["name"]
		else:
			log.error("Error: Cannot delete lexicon id=%s" % lexicon_id)
			context["message"] = "Cannot delete lexicon '%s'" % lexicon["name"]
	except Exception as e:
		log.error(str(e))
	return context

def populate_lexicon_edit(context, db, lexicon_id):
	lexicon = db.get_lexicon(lexicon_id)
	# not a valid lexicon?
	if lexicon is None:
		abort(403, "Cannot find specified lexicon in the database (lexicon_id=%s)" % lexicon_id)
	# not owned by the current user?
	if lexicon["user_id"] != context.user_id:
		abort(403, "You do not own this lexicon (lexicon_id=%s)" % lexicon_id)
	context["lexicon_name"] = lexicon["name"]
	context["lexicon_id"] = lexicon_id
	# do we need to delete a word from a lexicon?
	remove_word = context.request.args.get("remove", default = "").strip().lower()
	if len(remove_word) > 0:
		if db.remove_lexicon_word(lexicon_id, remove_word):
			log.info("Removed word '%s' from lexicon %s" % (remove_word, lexicon_id))
		else:
			log.warning("Warning: Failed to remove word '%s' from lexicon %s" % (remove_word, lexicon_id))
	# do we need to handle a recommendation accept?
	accept_word = context.request.args.get("accept", default = "").strip().lower()
	if len(accept_word) > 0:
		if db.add_lexicon_word(lexicon_id, accept_word):
			log.info("Added recommended word '%s' to lexicon %s" % (accept_word, lexicon_id))
		else:
			log.warning("Warning: Failed to add word '%s' to lexicon %s" % (accept_word, lexicon_id))
	# do we need to handle a recommendation reject?
	reject_word = context.request.args.get("reject", default = "").strip().lower()
	if len(reject_word) > 0:
		if db.add_lexicon_ignore(lexicon_id, reject_word):
			log.info("Ignorning recommended word '%s' from lexicon %s" % (reject_word, lexicon_id))	
		else:
			log.warning("Warning: Failed to ignore word '%s' to lexicon %s" % (reject_word, lexicon_id))
	# get word recommendations 
	lexicon_words = db.get_lexicon_words(lexicon_id)
	lexicon_ignores = db.get_lexicon_ignores(lexicon_id)
	recommendations = context.core.recommend_words(lexicon_words, lexicon_ignores)
	if recommendations is None or len(recommendations) == 0:
		context["message"] = "Unable to generate recommended words for lexicon"
	else:
		context["recommendations"] = Markup(format_lexicon_recommendations(context, lexicon_id, recommendations ))
	if len(lexicon_words) == 0:
		context["lexicon_summary"] = "This lexicon currently contains no keywords"
	else:
		context["lexicon_summary"] = "There are currently %d keywords in this lexicon:" % len(lexicon_words)
		context["lexicon_words"] = Markup(format_lexicon_words(context, lexicon_words, lexicon_id))	
	# get the export URL
	context["export_url"] = "%s/exportlexicon?lexicon_id=%d" % (context.prefix, lexicon_id)
	return context

# --------------------------------------------------------------

def format_lexicon_list(context, db, max_words=20):
	""" Display a list of all lexicons as a table. """
	user_id = context.user_id
	if user_id is None:
		log.warning("No user specified for lexicons")
		return None
	lexicons = db.get_user_lexicons(user_id)
	html = ""
	for lex in lexicons:
		lex_id = lex["id"]
		words = db.get_lexicon_words(lex_id)
		if len(words) > max_words:
			s_words = ", ".join(words[0:max_words])
			s_words += "... (and %d more)" % (len(words) - max_words)
		else:
			s_words = ", ".join(words)
		html += "<tr class='lexicon'>\n"
		# create the action URLs
		url_edit = "%s/lexiconedit?lexicon_id=%d" % (context.prefix, lex_id)
		url_delete = "%s/lexicon?action=delete&lexicon_id=%d" % (context.prefix, lex_id)
		escaped_words = urllib.parse.quote_plus(" ".join(words))
		url_search = '%s/search?qwords=%s&type=volume&lexicon_id=%d' % (context.prefix, escaped_words, lex_id)
		if "classification" in lex and len(lex["classification"]) > 0:
			url_search += "&class=%s" % urllib.parse.quote_plus(lex["class_name"])
		default_k = context.core.config["networks"].getint("default_k", 5)
		escaped_network_words = urllib.parse.quote_plus(", ".join(words))
		url_network = '%s/networks?qwords=%s&neighbors=%d' % (context.prefix, escaped_network_words, default_k)
		# create the HTML
		html += "<td class='text-left lex'><i>%s</i></td><td class='text-left'>%s</td><td class='text-left'>%s</td>\n" % (lex.get("name", "Untitled"), lex.get("description", "No description"), s_words)
		html += "<td class='text-center lex'><a href='%s'><img src='%s/img/edit.png' width='30px' style=''/></a></td>\n" % (url_edit, context.staticprefix)
		html += "<td class='text-center lex'><a href='%s'><img src='%s/img/delete.png' width='30px' style=''/></a></td>\n" % (url_delete, context.staticprefix)
		html += "<td class='text-center lex'><a href='%s'><img src='%s/img/search.png' width='30px' style=''/></a></td>\n" % (url_search, context.staticprefix)
		html += "<td class='text-center lex'><a href='%s'><img src='%s/img/network.png' width='30px' style=''/></a></td>\n" % (url_network, context.staticprefix)
		html += "</tr>\n"
	return html

def format_lexicon_words(context, words, lexicon_id, cols = 5):
	if words is None or len(words) == 0:
		return ""
	html = ""
	s_col_width = "%0.f%%" % (100.0/cols)
	for i, word in enumerate(words):
		# new row?
		if i % cols == 0:
			if len(html) > 0:
				html += "</tr>\n"
			html += "<tr>"
		html += "<td width='%s' class='text-left lex-word'>%s" % (s_col_width, word)
		url_remove = "%s/lexiconedit?lexicon_id=%d&remove=%s" % (context.prefix, lexicon_id, urllib.parse.quote_plus(word))
		html += "<a href='%s'><img src='%s/img/reject.png' width='26px' style='float: right;'/></a></td>\n" % (url_remove, context.staticprefix)
		html += "</td>"
	if len(html) > 0:
		html += "</tr>\n"
	return html

def format_lexicon_recommendations(context, lexicon_id, recommendations, top = 15):
	html = ""
	scores = defaultdict(float)
	similar_to = defaultdict(list)
	for word in recommendations:
		for i, neighbor in enumerate(recommendations[word]):
			rank = i+1
			score = 0.5 + (1.0/rank)
			scores[neighbor] += score
			similar_to[neighbor].append("<i>%s</i>" % word.replace("_","-"))
	# Rank the suggested terms
	sx = sorted(scores.items(), key=operator.itemgetter(1), reverse=True)
	actual_top = min(top, len(sx))
	for i in range(actual_top):
		# tidy the word
		neighbor = sx[i][0].replace("_", "-")
		if len(similar_to[neighbor]) == 0:
			explanation = "Word is not present in current lexicon"
		elif len(similar_to[neighbor]) == 1:
			explanation = "Similar to existing lexicon word %s" % similar_to[neighbor][0]
		elif len(similar_to[neighbor]) == 2:
			explanation = "Similar to existing lexicon words %s and %s" % (similar_to[neighbor][0], similar_to[neighbor][1])
		else:
			explanation = "Similar to existing lexicon words "
			explanation += ", ".join(similar_to[neighbor])
		html += "<tr class='lexicon'>\n"
		html += "<td class='text-left lex'><i>%s</i></td><td class='text-left lex'>%s</td>\n" % (neighbor.replace("_"," "), explanation)
		url_accept = "%s/lexiconedit?lexicon_id=%d&accept=%s" % (context.prefix, lexicon_id, urllib.parse.quote_plus(neighbor))
		url_reject = "%s/lexiconedit?lexicon_id=%d&reject=%s" % (context.prefix, lexicon_id, urllib.parse.quote_plus(neighbor))
		html += "<td class='text-center lex'><a href='%s'><img src='%s/img/accept.png' width='26px' style=''/></a></td>\n" % (url_accept, context.staticprefix)
		html += "<td class='text-center lex'><a href='%s'><img src='%s/img/reject.png' width='26px' style=''/></a></td>\n" % (url_reject, context.staticprefix)
		html += "</tr>\n"
	return html
