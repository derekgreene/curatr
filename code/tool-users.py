#!/usr/bin/env python
"""
Utility tool for working with Curatr user accounts.

Sample usage:
``` python code/tool-users.py core list ```
"""
import sys, getpass, random, string
from pathlib import Path
import logging as log
from optparse import OptionParser
from core import CoreCuratr
from user import password_to_hash, validate_email, generate_password

# --------------------------------------------------------------

def validate_password(passwd):
	"""Check if the specified password string meets our required criteria."""
	if len(passwd) < 6:
		log.error("Password should be at least 6 characters long")
		return False
	if len(passwd) > 20:
		log.error("Password should not be longer than 20 characters")
		return False
	if not any(char.isdigit() for char in passwd):
		log.error("Password should have at least one numeric character")
		return False
	if any(char.isspace() for char in passwd):
		log.error("Password should not contain spaces")
		return False
	return True

def user_add(db):
	"""Add a new user to the database."""
	# prompt for details
	try:
		# request & validate new email address
		while True:
			email = input("Email: ").strip().lower()
			# does this email already exist in the DB?
			if db.has_user_email(email):
				log.warning(f"User with email address '{email}' already exists")
				continue
			if validate_email(email):
				break
			log.error("Invalid email address")
		# request & validate new password
		log.info(f"Suggestion: {generate_password()}")
		while True:
			passwd = getpass.getpass(prompt="Password: ", stream=None).strip()
			if validate_password(passwd):
				break
		# double check password
		while True:
			passwd2 = getpass.getpass(prompt="Re-enter Password: ", stream=None).strip()
			if passwd == passwd2:
				break
			else:
				log.warning("Passwords do not match")
	except Exception as e:
		log.warning(f"Cancelling user addition - {e}")
		return
	# hash the password
	hashed_passwd = password_to_hash(passwd)
	# actually add the user
	user_id = db.add_user(email, hashed_passwd)
	if user_id == -1:
		log.error("Failed to add new user")
		return False
	log.info(f"Added new user: email={email} user_id={user_id}")
	return True

def user_list(db):
	"""Print a list of all current users."""
	users = db.get_all_users()
	log.info(f"Database has {len(users)} user(s)")
	for user in users:
		log.info(f"{str(user)} (admin={user.admin}, guest={user.guest})")
	return True

def user_change_password(db):
	"""Change a user's existing password."""
	log.info("Changing user password ...")
	email = input("Enter Email: ").strip()
	user = db.get_user_by_email(email)
	if user is None:
		log.warning(f"No such user '{email}'")
		return False
	# request & validate new password
	log.info(f"Suggestion: {generate_password()}")
	while True:
		passwd = getpass.getpass(prompt="Password: ", stream=None).strip()
		if validate_password(passwd):
			break
	# double check password
	while True:
		passwd2 = getpass.getpass(prompt="Re-enter Password: ", stream=None).strip()
		if passwd == passwd2:
			break
		else:
			log.warning("Passwords do not match")
	# hash the password
	hashed_passwd = password_to_hash(passwd)
	return db.update_user_password(user.get_id(), hashed_passwd)

def user_verify_password(db):
	"""Verify a user's password."""
	log.info("Verifying user password ...")
	email = input("Enter Email: ").strip()
	user = db.get_user_by_email(email)
	if user is None:
		log.warning(f"No such user '{email}'")
		return False
	while True:
		passwd = getpass.getpass(prompt="Enter Password: ", stream=None).strip()
		if user.verify(passwd):
			log.info("Password verified")
			break
		log.info("Password does not match")
	return True

def user_remove(db):
	"""Delete an existing user from the database."""
	log.info("Removing user ...")
	email = input("Enter Email: ").strip()
	user = db.get_user_by_email(email)
	if user is None:
		log.warning(f"No such user '{email}'")
		return False
	return db.delete_user(user.get_id())

def user_lexicons(db):
	"""List lexicons for each user."""
	users = db.get_all_users()
	for user in users:
		lexicons = db.get_user_lexicons(user.id)
		log.info(f"User {user.email}: {len(lexicons)} lexicon(s)")
		for lex in lexicons:
			log.info(f"  - {lex['id']}: {lex['name']}")
	return True

def user_subcorpora(db):
	"""List subcorpora for each user."""
	users = db.get_all_users()
	for user in users:
		corpora = db.get_user_subcorpora(user.id)
		log.info(f"User {user.email}: {len(corpora)} sub-corpora")
		for corpus in corpora:
			log.info(f"  - {corpus['id']}: {corpus['name']}")
	return True

# --------------------------------------------------------------

def main():
	"""
	Manage Curatr user accounts via command-line interface.

	Provides functionality for user account management including:
	- Adding new users
	- Removing existing users
	- Changing passwords
	- Verifying passwords
	- Listing users
	- Viewing user lexicons and subcorpora
	"""
	actions = ["list", "add", "remove", "password", "verify", "lexicons", "corpora"]
	parser = OptionParser(usage="usage: %prog [options] dir_core action")
	(options, args) = parser.parse_args()
	if(len(args) != 2):
		sactions = ", ".join(actions)
		parser.error(f"Must specify core directory and action ({sactions})")
	log.basicConfig(level=log.INFO, format="%(message)s")
	action = args[1].lower()

	# valid action?
	if not action in actions:
		log.warning(f"Invalid action '{action}'")
		log.warning(f"Valid actions are: {str(actions)}")
		sys.exit(1)

	# set up the Curatr core
	dir_core = Path(args[0])
	if not dir_core.exists():
		log.error(f"Invalid core directory: {dir_core.absolute()}")
		sys.exit(1)
	core = CoreCuratr(dir_core)

	# only need a single DB connection
	core.config.set("db", "pool_size", "1")
	# connect to the database
	if not core.init_db():
		sys.exit(1)
	db = core.get_db()

	# Perform the required action
	if action == "add":
		user_add(db)
	elif action == "verify":
		user_verify_password(db)
	elif action == "list":
		user_list(db)
	elif action == "password":
		user_change_password(db)
	elif action == "remove":
		user_remove(db)
	elif action == "lexicons":
		user_lexicons(db)
	elif action == "corpora":
		user_subcorpora(db)

	# Finished
	db.close()
	core.shutdown()
	
# --------------------------------------------------------------

if __name__ == "__main__":
	main()
