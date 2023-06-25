"""
Implementation for corpus system administration-related features of the Curatr web interface
"""

import operator
from flask import Markup

# --------------------------------------------------------------

def format_user_list(context, db):
	""" Produce a HTML formatted table continue details of users registered on the system """
	users = db.get_all_users()
	users.sort(key=operator.attrgetter('last_login'))
	users.reverse()
	html = ""
	for user in users:
		html += "\t<tr class='user'>\n"
		# user id column
		html += "\t\t<td class='text-left user'>%s</td>" % user.id
		# email address column
		if user.admin:
			html += "\t\t<td class='text-left user'>%s **</td>" % user.email
		else:
			html += "\t\t<td class='text-left user'>%s</td>" % user.email
		# user date created column
		html += "\t\t<td class='text-left user'>%s</td>" % user.created_at.strftime('%Y-%m-%d %H:%M')
		# user last login column
		if user.last_login is None or user.created_at == user.last_login:
			html += "\t\t<td class='text-left user'>&mdash;</td>"
		else:
			html += "\t\t<td class='text-left user'>%s</td>" % user.last_login.strftime('%Y-%m-%d %H:%M')
		# number of logins column
		html += "\t\t<td class='text-left user'>%s</td>" % user.num_logins
		# add actions
		url_edit = "%s/useredit?user_id=%d" % (context.prefix, user.id)
		html += "<td class='text-center lex'><a href='%s'><img src='%s/img/edit.png' width='30px' style=''/></a></td>\n" % (url_edit, context.staticprefix)
		html += "</tr>\n"
	return html
