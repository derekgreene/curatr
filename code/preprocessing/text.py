import re, unicodedata
import logging as log
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from gensim.parsing.porter import PorterStemmer
from preprocessing.cleaning import clean_content

# --------------------------------------------------------------

token_pattern = re.compile(r"\b\w\w+\b", re.U)

def simple_tokenizer(s):
	""" 
	Implements the most basic word tokenizer used by Curatr
	"""
	return [x.lower() for x in token_pattern.findall(s)]

def custom_tokenizer(s, min_term_length=2):
	"""
	Tokenizer to split text based on any whitespace, keeping only terms of at least a certain length which start with an alphabetic character.
	"""
	return [x.lower() for x in token_pattern.findall(s) if (len(x) >= min_term_length and x[0].isalpha() ) ]

def build_bow(docgen, stopwords=[], min_df=10, apply_tfidf=True, apply_norm=True):
	""" 
	Build the Vector Space Model, apply TF-IDF and normalize lines to unit length all in one call
	"""
	if apply_norm:
		norm_function = "l2"
	else:
		norm_function = None
	tfidf = TfidfVectorizer(stop_words=stopwords, lowercase=True, strip_accents="unicode", tokenizer=custom_tokenizer, 
		use_idf=apply_tfidf, norm=norm_function, min_df=min_df) 
	X = tfidf.fit_transform(docgen)
	terms = []
	# store the vocabulary map
	v = tfidf.vocabulary_
	for i in range(len(v)):
		terms.append("")
	for term in v.keys():
		terms[v[term]] = term
	return (X,terms)

def load_stopwords():
	""" Returns the default set of Curatr stopwords """
	import pkgutil
	data = pkgutil.get_data(__name__, "stopwords.txt")
	stopwords = set()
	for line in data.decode('utf-8').splitlines():
		line = line.strip()
		if len(line) > 0:
			stopwords.add(line.lower())
	return list(stopwords)

# --------------------------------------------------------------

stemmer = PorterStemmer()
def stem_words(words):
	""" Apply English stemming to the specified words """
	word_stems = []
	for word in words:
		word_stems.append(stemmer.stem(word))
	return word_stems

def stem_word(word):
	""" Apply English stemming to the specified word """
	return stemmer.stem(word)

# --------------------------------------------------------------

def strip_accents_unicode(s):
    """
    Remove diacritics (accent marks) from a Unicode string using NFKD normalization.
    Mirrors scikit-learn's strip_accents='unicode' behavior.
    """
    if not isinstance(s, str):
        s = str(s)
    # Fast path for ASCII-only strings
    try:
        s.encode("ASCII")
        return s
    except UnicodeEncodeError:
        pass
    normalized = unicodedata.normalize("NFKD", s)
    return "".join(c for c in normalized if not unicodedata.combining(c))

# --------------------------------------------------------------

class BookContentGenerator:
	""" Iterator class for easily accessing full-text content for books """
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

class VolumeGenerator:
	""" Iterator for working with volumes associated with a Curatr Core """
	def __init__(self, core):
		self.core = core

	def __iter__(self):	
		self.volume_ids = []
		db = self.core.get_db()
		# get list of all of the volumes we're going to process
		volumes = db.get_volumes()
		# process eaach volume
		for volume in volumes:
			log.debug("Volume %d/%d: Counting tokens in %s" % (len(self.volume_ids)+1, len(volumes), volume["path"]))
			volume_path = self.core.dir_fulltext / volume["path"]
			if not volume_path.exists():
				log.error("Missing volume file %s" % volume_path)
				continue
			with open(volume_path, 'r', encoding="utf8", errors='ignore') as fin:
				content = clean_content(fin.read())
				self.volume_ids.append(volume["id"])
				yield content
		if len(self.volume_ids) % 1000 == 0:
			log.info("Completed processing %d/%d volumes" % (len(self.volume_ids), len(volumes)))

