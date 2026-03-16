"""
Implementation for system administration-related features of the Curatr web interface
"""

from markupsafe import Markup, escape

# --------------------------------------------------------------

def format_user_list(context, db):
	""" Produce a HTML formatted table containing details of users registered on the system """
	users = db.get_all_users()
	html = ""
	for user in users:
		html += "\t<tr class='user'>\n"
		# user id column
		html += "\t\t<td class='text-left user'>%s</td>" % user.id
		# email address column
		suffix = ""
		if user.admin:
			suffix += " (Admin)"
		if user.guest:
			suffix += " (Guest)"
		html += "\t\t<td class='text-left user'>%s%s</td>" % (escape(user.email), suffix)
		# user date created column
		created_str = user.created_at.strftime('%Y-%m-%d %H:%M')
		html += "\t\t<td class='text-left user' data-order='%s'>%s</td>" % (created_str, created_str)
		# user last login column
		if user.last_login is None or user.created_at == user.last_login:
			html += "\t\t<td class='text-left user' data-order='0'>&mdash;</td>"
		else:
			login_str = user.last_login.strftime('%Y-%m-%d %H:%M')
			html += "\t\t<td class='text-left user' data-order='%s'>%s</td>" % (login_str, login_str)
		# number of logins column
		html += "\t\t<td class='text-left user'>%s</td>" % user.num_logins
		# add Edit action
		url_edit = "%s/useredit?user_id=%d" % (context.prefix, user.id)
		html += "\t\t<td class='text-center lex'><a href='%s'><img src='%s/img/edit.png' width='30px'></a></td>\n" % (url_edit, context.staticprefix)
		html += "</tr>\n"
	return html
