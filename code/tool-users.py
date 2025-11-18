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
from user import password_to_hash, validate_email, generate_password, validate_password

# --------------------------------------------------------------

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
			is_valid, error_msg = validate_password(passwd)
			if is_valid:
				break
			log.error(error_msg)
		# double check password
		# require re-entry to prevent typos
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
	# check if insertion failed (returns -1 on error)
	if user_id == -1:
		log.error("Failed to add new user")
		return False
	log.info(f"Added new user: email={email} user_id={user_id}")
	return True

def user_list(db):
	"""Print a list of all current users."""
	users = db.get_all_users()
	log.info(f"Database has {len(users)} user(s)")
	# display each user with their role information
	for user in users:
		log.info(f"{str(user)} (admin={user.admin}, guest={user.guest})")
	return True

def user_change_password(db):
	"""Change a user's existing password."""
	log.info("Changing user password ...")
	# prompt for and look up the user by email
	email = input("Enter Email: ").strip()
	user = db.get_user_by_email(email)
	if user is None:
		log.warning(f"No such user '{email}'")
		return False
	# request & validate new password
	log.info(f"Suggestion: {generate_password()}")
	while True:
		passwd = getpass.getpass(prompt="Password: ", stream=None).strip()
		is_valid, error_msg = validate_password(passwd)
		if is_valid:
			break
		log.error(error_msg)
	# double check password
	# require re-entry to prevent typos
	while True:
		passwd2 = getpass.getpass(prompt="Re-enter Password: ", stream=None).strip()
		if passwd == passwd2:
			break
		else:
			log.warning("Passwords do not match")
	# hash the password
	hashed_passwd = password_to_hash(passwd)
	# update the password in the database
	return db.update_user_password(user.get_id(), hashed_passwd)

def user_verify_password(db):
	"""Verify a user's password."""
	log.info("Verifying user password ...")
	# prompt for and look up the user by email
	email = input("Enter Email: ").strip()
	user = db.get_user_by_email(email)
	if user is None:
		log.warning(f"No such user '{email}'")
		return False
	# keep prompting until correct password is entered
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
	# prompt for and look up the user by email
	email = input("Enter Email: ").strip()
	user = db.get_user_by_email(email)
	if user is None:
		log.warning(f"No such user '{email}'")
		return False
	# delete the user from the database
	return db.delete_user(user.get_id())

def user_lexicons(db):
	"""List lexicons for each user."""
	users = db.get_all_users()
	# iterate through each user and display their lexicons
	for user in users:
		lexicons = db.get_user_lexicons(user.id)
		log.info(f"User {user.email}: {len(lexicons)} lexicon(s)")
		# display each lexicon with its ID and name
		for lex in lexicons:
			log.info(f"  - {lex['id']}: {lex['name']}")
	return True

def user_subcorpora(db):
	"""List subcorpora for each user."""
	users = db.get_all_users()
	# iterate through each user and display their subcorpora
	for user in users:
		corpora = db.get_user_subcorpora(user.id)
		log.info(f"User {user.email}: {len(corpora)} sub-corpora")
		# display each subcorpus with its ID and name
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
	# require exactly 2 arguments: core directory and action
	if(len(args) != 2):
		sactions = ", ".join(actions)
		parser.error(f"Must specify core directory and action ({sactions})")
	log.basicConfig(level=log.INFO, format="%(message)s")
	# convert to lowercase for case-insensitive action matching
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
	# limit connection pool to 1 since this is a single-user CLI tool
	core.config.set("db", "pool_size", "1")
	# initialize embeddings
	if not core.init_embeddings():
		sys.exit(1)
	# connect to the database
	if not core.init_db():
		sys.exit(1)
	db = core.get_db()

	# perform the required action
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

	# finished
	db.close()
	core.shutdown()
	
# --------------------------------------------------------------

if __name__ == "__main__":
	main()
