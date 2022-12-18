import re
import logging as log
from pathlib import Path

# --------------------------------------------------------------

token_pattern = re.compile(r"\b\w\w+\b", re.U)

def simple_tokenizer(s):
	return [x.lower() for x in token_pattern.findall(s) ]

def custom_tokenizer(s, min_term_length=2):
	"""
	Tokenizer to split text based on any whitespace, keeping only terms of at least a certain length which start with an alphabetic character.
	"""
	return [x.lower() for x in token_pattern.findall(s) if (len(x) >= min_term_length and x[0].isalpha() ) ]

# --------------------------------------------------------------

class BookContentGenerator:
	""" Iterator class for easily accessing full-text volumes files """
	def __init__(self, root_path, book_ids):
		self.root_path = Path(root_path)
		self.book_ids = book_ids

	def __iter__(self):
		for book_id in self.book_ids:
			# construct the path for the full text file
			prefix = book_id[:4]
			dir_parent = self.root_path / prefix
			if not dir_parent.exists():
				log.warning("Skipping book %s, No such directory of fulltexts: %s" % (book_id, dir_parent.absolute()))
				continue
			# read the content for one or more volumes
			volume_number = 0
			book_tokens = set()
			full_content = ""
			while True:
				volume_number += 1
				# does it exist? or have we processed all the volumes for this book?
				fname =  "%s_%02d_text.txt" % (book_id, volume_number)
				volume_path = dir_parent / fname
				if not volume_path.exists():
					break
				# read the full text for one or more volumes for this book
				with open(volume_path, 'r', encoding="utf8", errors='ignore') as fin:
					content = fin.read().strip().lower()
					full_content += "\n" + content
			yield (book_id,full_content)

class BookTokenGenerator:
	""" Iterator class for easily accessing raw tokens for full-text volumes files """
	def __init__(self, root_path, book_ids, stopwords=[], stop_stategy=2):
		self.root_path = root_path
		self.book_ids = book_ids
		self.min_term_length = 2
		# stopword strategy - 0=keep, 1=remove, 2=replace, 3=replace_unique
		self.stop_stategy = stop_stategy
		self.stopwords = stopwords
		self.stopword_index = 0

	def __iter__(self):
		content_gen = BookContentGenerator(self.root_path, self.book_ids)
		# processs the full-text content of each book
		for doc_id, content in content_gen:
			content = content.lower().strip()
			tokens = []
			for tok in simple_tokenizer(content):
				# How to handle stopwords, short tokens and numbers?
				if self.stop_stategy > 0 and (tok in self.stopwords or tok[0].isdigit() or len(tok) < self.min_term_length):
					if self.stop_stategy == 2:
						tokens.append( "<stopword>" )
					elif self.stop_stategy == 3:
						self.stopword_index += 1
						tokens.append( "<stopword%d>" % self.stopword_index )
				else:
					tokens.append(tok)
			yield tokens
