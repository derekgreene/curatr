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
		"""
		Initialize a User object.

		Args:
			user_id: Unique identifier for the user
			email: User's email address
			hashed_passwd: SHA256 hashed password
			admin: Whether the user has administrator privileges (default: False)
			guest: Whether the user is a guest account (default: False)
			created_at: Timestamp when the account was created (default: None)
			last_login: Timestamp of the user's last login (default: None)
			log_queries: Whether to log this user's queries (default: False)
			num_logins: Total number of times the user has logged in (default: 0)
		"""
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
		""" False, as anonymous users are not supported. """
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
		""" Return a string representation of the User object. """
		return f"User (id={self.id} email={self.email})"

# --------------------------------------------------------------
# User Utility Functions
# --------------------------------------------------------------

def dict_to_user(d):
	"""
	Convert a dictionary to a User object.

	Args:
		d: Dictionary containing user data with keys: id, email, hash, admin, guest,
		   created_at, last_login, log_queries, num_logins

	Returns:
		User object initialized with the dictionary data
	"""
	is_admin = (d["admin"] == 1) or (d["admin"] == True)
	is_guest = (d["guest"] == 1) or (d["guest"] == True)
	is_log_queries = (d["log_queries"] == 1) or (d["log_queries"] == True)
	return User(d["id"], email=d["email"], hashed_passwd=d["hash"], admin=is_admin, guest=is_guest,
		created_at=d["created_at"], last_login=d["last_login"], log_queries=is_log_queries, num_logins=d["num_logins"])

def password_to_hash(passwd):
	"""
	Convert a password string to its hashed equivalent using SHA256.

	Args:
		passwd: The plain text password to hash

	Returns:
		SHA256 hashed password string
	"""
	return sha256_crypt.hash(passwd)

def validate_email(email):
	"""
	Check whether a string is a valid email address.

	Args:
		email: The email address string to validate

	Returns:
		Match object if valid, None if invalid
	"""
	pattern = '^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$'
	return re.search(pattern, email)

def generate_password(length=8):
	"""
	Generate a random password of the specified length.

	The generated password contains a mix of letters and digits to meet
	the password validation requirements.

	Args:
		length: The desired password length (default: 8)

	Returns:
		Random password string containing letters and at least 2 digits
	"""
	# add some letters
	selected = [secrets.choice(string.ascii_letters) for i in range(length-2)]
	# add some digits
	selected += [secrets.choice(string.digits) for i in range(2)]
	# randomise the order
	random.shuffle(selected)
	return ''.join(selected)

def validate_password(passwd, current_password=None):
	"""
	Validate a password against security requirements.

	Password validation rules:
	1. Must be at least 8 characters long
	2. Must not be longer than 20 characters
	3. Must contain at least one numeric character
	4. Must not contain spaces
	5. If current_password is provided, new password must be different

	Args:
		passwd: The password string to validate
		current_password: Optional current password to check against (for password changes)

	Returns:
		Tuple of (is_valid: bool, error_message: str or None)
		Returns (True, None) if password is valid
		Returns (False, error_message) if password is invalid
	"""
	# Rule 1: Minimum length for security
	if len(passwd) < 8:
		return (False, "Password must be at least 8 characters long.")

	# Rule 2: Maximum length to prevent potential buffer issues
	if len(passwd) > 20:
		return (False, "Password must not be longer than 20 characters.")

	# Rule 3: Require at least one digit for stronger passwords
	if not any(char.isdigit() for char in passwd):
		return (False, "Password must contain at least one numeric character.")

	# Rule 4: Disallow spaces as they can cause issues with authentication
	if any(char.isspace() for char in passwd):
		return (False, "Password must not contain spaces.")

	# Rule 5: If changing password, new password must be different from current
	if current_password is not None and passwd == current_password:
		return (False, "New password must be different from your current password.")

	return (True, None)
