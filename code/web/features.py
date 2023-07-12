"""
Implementation for additional features of the Curatr web interface
"""
import urllib.parse
from flask import Markup
from web.util import parse_arg_int
from web.format import format_volume_list
from preprocessing.cleaning import tidy_authors

# --------------------------------------------------------------

def populate_author_page(context, db, author, author_page_size=10):
	""" Populate information for the Curatr page which displays all books for a given author """
	author_id = author["author_id"]
	# Get the relevant recommendations
	volume_ids = db.get_author_volume_ids(author_id)
	num_total_results = len(volume_ids)
	# paging parameters
	start = max(parse_arg_int(context.request, "start", 0), 0)
	if start >= num_total_results:
		start = 0
	end = start + author_page_size
	if end >= num_total_results:
		end = num_total_results
	current_page = max(int(start / author_page_size) + 1, 1)
	current_volume_ids = volume_ids[start:end]		
	# Populate parameters
	context["author_id"] = author_id
	context["author_name"] = author["author_name"]
	context["results"] = Markup(format_volume_list(context, db, current_volume_ids))
	page_url_prefix = "%s/author?author_id=%s" % (context.prefix, author_id)
	# create the summary
	if num_total_results == 1:
		summary = "<strong>1</strong> matching volume was found for the author <span class='highlight'><b>%s</b></span>" % (author["author_name"])
	else:
		summary = "<strong>%d</strong> matching volumes were found for the author <span class='highlight'><b>%s</b></span>" % (num_total_results, author["author_name"])
	# do we need pagination?
	pagination_html = ""
	if num_total_results > author_page_size:
		max_pages = int(num_total_results/author_page_size)
		if num_total_results % author_page_size > 0:
			max_pages += 1
		if current_page <= 5:
			min_page_index = 1
		else:
			min_page_index = current_page - 5
		max_page_index = min(min_page_index + 9, max_pages)
		# first page of results?
		if current_page == 1:
			pagination_html += "<li class='page-item disabled'><a href='#' class='page-link'>Previous</a></li>\n"
		else:
			page_index = current_page - 1
			page_start = (page_index-1) * author_page_size
			page_url_string = "%s&start=%d" % (page_url_prefix, page_start)
			pagination_html += "<li class='page-item'><a href='%s' class='page-link'>Previous</a></li>\n" % page_url_string
		# numbered links
		for page_index in range(min_page_index,max_page_index+1):
			if current_page == page_index:
				pagination_html += "<li class='page-item active'><a href='#' class='page-link'>%d</a></li>\n" % page_index
			else:
				page_start = (page_index-1) * author_page_size
				page_url_string = "%s&start=%d" % (page_url_prefix, page_start)
				pagination_html += "<li class='page-item'><a href='%s' class='page-link'>%d</a></li>\n" % (page_url_string, page_index)
		# last page of results?
		if current_page == max_pages:
			pagination_html += "<li class='page-item disabled'><a href='#' class='page-link'>Next</a></li>\n"
		else:
			page_index = current_page + 1
			page_start = (page_index-1) * author_page_size
			page_url_string = "%s&start=%d" % (page_url_prefix, page_start)
			pagination_html += "<li class='page-item'><a href='%s' class='page-link'>Next</a></li>\n" % page_url_string
	# generate the HTML template
	context["summary"] = Markup(summary)
	context["pagination"] = Markup(pagination_html)	
	return context

def populate_similar_page(context, db, volume, recommendation_page_size = 10):
	volume_id = volume["id"]
	# get the relevant recommendations
	recs = db.get_volume_recommendations(volume_id)
	num_total_results = len(recs)
	# paging parameters
	start = max(parse_arg_int(context.request, "start", 0), 0)
	if start >= num_total_results:
		start = 0
	end = start + recommendation_page_size
	if end >= num_total_results:
		end = num_total_results
	current_page = max(int(start / recommendation_page_size) + 1, 1)
	current_recs = recs[start:end]
	# populate the parameters
	context["id"] = volume_id
	context["results"] = Markup(format_volume_list(context, db, current_recs))
	# Create the pagination
	page_url_prefix = "%s/similar?volume_id=%s" % (context.prefix, volume_id)
	# do we need pagination?
	pagination_html = ""
	if num_total_results > recommendation_page_size:
		max_pages = int(num_total_results/recommendation_page_size)
		if num_total_results % recommendation_page_size > 0:
			max_pages += 1
		if current_page <= 5:
			min_page_index = 1
		else:
			min_page_index = current_page - 5
		max_page_index = min(min_page_index + 9, max_pages)
		# first page of results?
		summary = "Page <b>%d</b> of <b>%d</b> volumes which are similar to " % (current_page, num_total_results)
		# multi volume? then display the volume number
		if volume["volumes"] > 1:
			summary += "<b>%s&nbsp;&ndash;&nbsp;Volume %d</b> (%s)" % (volume["title"], volume["volume"], volume["year"])
		else:
			summary += "<b>%s</b> (%s)" % (volume["title"], volume["year"])
		if current_page == 1:
			pagination_html += "<li class='page-item disabled'><a href='#' class='page-link'>Previous</a></li>\n"
		else:
			page_index = current_page - 1
			page_start = (page_index-1) * recommendation_page_size
			page_url_string = "%s&start=%d" % (page_url_prefix, page_start)
			pagination_html += "<li class='page-item'><a href='%s' class='page-link'>Previous</a></li>\n" % page_url_string
		# numbered links
		for page_index in range(min_page_index,max_page_index+1):
			if current_page == page_index:
				pagination_html += "<li class='page-item active'><a href='#' class='page-link'>%d</a></li>\n" % page_index
			else:
				page_start = (page_index-1) * recommendation_page_size
				page_url_string = "%s&start=%d" % (page_url_prefix, page_start)
				pagination_html += "<li class='page-item'><a href='%s' class='page-link'>%d</a></li>\n" % (page_url_string, page_index)
		# last page of results?
		if current_page == max_pages:
			pagination_html += "<li class='page-item disabled'><a href='#' class='page-link'>Next</a></li>\n"
		else:
			page_index = current_page + 1
			page_start = (page_index-1) * recommendation_page_size
			page_url_string = "%s&start=%d" % (page_url_prefix, page_start)
			pagination_html += "<li class='page-item'><a href='%s' class='page-link'>Next</a></li>\n" % page_url_string
	else:
		summary = "<b>%d</b> volume(s) which are similar to <b>%s</b>" % (num_total_results, volume["title"])			
	# populate and generate the HTML template
	context["summary"] = Markup(summary)
	context["pagination"] = Markup(pagination_html)	
	return context

def populate_bookmark_page(context, db, user_id):
	""" Populate the context for a user's bookmark page """
	# check the numbers
	context["numvolumebookmarks"] = db.volume_bookmark_count(user_id)
	context["numsegmentbookmarks"] = db.segment_bookmark_count(user_id)
	context["segmentbookmarks"] = ""
	# get the user's volume bookmarks
	s_volumes = ""
	volume_bookmarks = db.get_volume_bookmarks(user_id)
	for b in volume_bookmarks:
		# get the associated volume & book
		volume = db.get_volume(b["volume_id"])
		if volume is None:
			continue
		book = db.get_book_by_volume(b["volume_id"])
		if book is None:
			continue
		# create the link URL
		url_link = "%s/volume?id=%s" % (context.prefix, b["volume_id"])
		# create the action URLs
		# url_download = "%s/bookmarks?action=download&bookmark_id=%d" % (context.prefix, b["id"])
		url_delete = "%s/bookmarks?action=delete&bookmark_id=%d" % (context.prefix, b["id"])
		# create the HTML
		row = "<tr>"
		row += "<td>%s</td>" % b["created_at"].strftime("%Y-%m-%d %H:%M")
		s_title = book["title"]
		s_title_suffix = ""
		if book["volumes"] > 1:
			s_title_suffix = "&nbsp;&mdash;&nbsp(Volume %d/%d)" % (volume["num"], book["volumes"])
		row += "<td><a href='%s'>%s</a>%s</td>" % (url_link, s_title, s_title_suffix)
		# row += "<td class='text-center lex'><a href='%s'><img src='%s/img/download.png' width='30px' style=''/></a></td>\n" % (url_download, context.staticprefix)
		row += "<td class='text-center lex'><a href='%s'><img src='%s/img/delete.png' width='30px' style=''/></a></td>\n" % (url_delete, context.staticprefix)
		row += "</tr>"
		s_volumes += "\n\t\t" + row
	context["volumebookmarks"] = Markup(s_volumes)
	# get the user's segment bookmarks
	s_segments = ""
	segment_bookmarks = db.get_segment_bookmarks(user_id)
	for b in segment_bookmarks:
		# get the associated volume & book
		volume = db.get_volume(b["volume_id"])
		if volume is None:
			continue
		book = db.get_book_by_volume(b["volume_id"])
		if book is None:
			continue
		# create the link URL
		url_link = "%s/segment?id=%s" % (context.prefix, b["segment_id"])
		# create the action URLs
		url_download = "%s/bookmarks?action=download&bookmark_id=%d" % (context.prefix, b["id"])
		url_delete = "%s/bookmarks?action=delete&bookmark_id=%d" % (context.prefix, b["id"])
		# create the HTML
		row = "<tr>"
		row += "<td>%s</td>" % b["created_at"].strftime("%Y-%m-%d %H:%M")
		s_title = book["title"]
		s_title_suffix = ""
		if book["volumes"] > 1:
			s_title_suffix = " (Volume %d/%d)" % (volume["num"], book["volumes"])
		segment_num = int(b["segment_id"].rsplit("_")[-1])
		s_title_suffix = "&nbsp;&mdash;&nbsp" + s_title_suffix + " (Segment %d)" % segment_num
		row += "<td><a href='%s'>%s</a>%s</td>" % (url_link, s_title, s_title_suffix)
		# row += "<td class='text-center lex'><a href='%s'><img src='%s/img/download.png' width='30px' style=''/></a></td>\n" % (url_download, context.staticprefix)
		row += "<td class='text-center lex'><a href='%s'><img src='%s/img/delete.png' width='30px' style=''/></a></td>\n" % (url_delete, context.staticprefix)
		row += "</tr>"
		s_segments += "\n\t\t" + row	
	context["segmentbookmarks"] = Markup(s_segments)
	return context

