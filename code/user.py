"""
Classes and functions for representing and handling users in the Curatr platform.
"""
import re, random, secrets, string
from passlib.hash import sha256_crypt
from flask_login import UserMixin

# --------------------------------------------------------------

class User(UserMixin):
	""" Implementation of user properties """
	def __init__(self, user_id, email, hashed_passwd, admin=False, guest=False, created_at=None, 
			  last_login=None, log_queries=False, num_logins=0):
		self.id = user_id
		self.email = email
		self.hashed_passwd = hashed_passwd
		self.admin = admin
		self.guest = guest
		self.created_at = created_at
		self.last_login = last_login
		self.log_queries = log_queries
		self.num_logins = num_logins

	def get_id(self):
		""" Get unique identifier for this user. """
		return self.id

	@property
	def is_anonymous(self):
		""" False, as anonymous users aren't supported. """
		return False

	@property
	def is_active(self):
		""" Assume all users are active. """
		return True

	@property
	def is_authenticated(self):
		""" Assume all users are authenticated. """
		return True

	def verify(self, passwd):
		""" Check whether the specified password matches the hash of the real password. """
		return sha256_crypt.verify(passwd, self.hashed_passwd)

	def __repr__(self):
		return "User (id=%s email=%s)" % (self.id, self.email)

# --------------------------------------------------------------
# User Utility Functions
# --------------------------------------------------------------

def dict_to_user(d):
	""" Convert a dictionary to a User object """
	is_admin = (d["admin"] == 1) or (d["admin"] == True)
	is_guest = (d["guest"] == 1) or (d["guest"] == True)
	is_log_queries = (d["log_queries"] == 1) or (d["log_queries"] == True) 
	return User(d["id"], email=d["email"], hashed_passwd=d["hash"], admin=is_admin, guest=is_guest,
		created_at=d["created_at"], last_login=d["last_login"], log_queries=is_log_queries, num_logins=d["num_logins"])

def password_to_hash(passwd):
	""" Convert a password string to its hashed equivalent """
	return sha256_crypt.hash(passwd)

def validate_email(email):
	""" Checked whether a string is a valid email address """
	pattern = '^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$'
	return re.search(pattern, email)

def generate_password(length=8):
	""" Suggest a random password of the specified length """
	# add some letters
	selected = [secrets.choice(string.ascii_letters) for i in range(length-2)]
	# add some digits
	selected += [secrets.choice(string.digits) for i in range(2)]
	# randomise the order
	random.shuffle(selected)
	return ''.join(selected)
