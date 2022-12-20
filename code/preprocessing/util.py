"""
Various utlity code used for data preprocessing tasks when running Curatr setup.
"""
import logging as log
from core import CoreBase
from pathlib import Path
import pandas as pd
import numpy as np

# --------------------------------------------------------------

class CorePrep(CoreBase):
	def __init__(self, dir_root):
		super().__init__(dir_root)
		self.dir_raw = self.dir_metadata / "raw"
		# file paths for raw data
		self.original_path = self.dir_raw / "ucd_digitised_books_2021.json"
		self.bl_path = self.dir_raw / "ms_digitised_books_2021-01-09.csv"
		self.ark_path = self.dir_raw / "MicrosoftBooks_FullIndex_27_09_2018.xlsx"
		self.filter_path = self.dir_raw / "books-filter.txt"
		# ensure the key Core directories exist
		self.ensure_directories_exists([self.dir_fulltext, self.dir_metadata, self.dir_embeddings, self.dir_export])

	def ensure_directories_exists(self, paths):
		for dir_path in paths:
			if not dir_path.exists():
				try:
					log.info("Creating directory %s" % dir_path)
					dir_path.mkdir( parents=True, exist_ok=True )
				except Exception as e:
					log.error("Failed to create directory %s" % dir_path)
					log.error(str(e))

	def get_original_rawdata(self):
		""" Load and return raw UCD Curatr metadata as a Pandas DataFrame """
		log.info("Reading raw data from %s" % self.original_path)
		df_original = pd.read_json(self.original_path, dtype={'identifier':object}).set_index("identifier").sort_index()
		log.info("Read %d rows, %d columns" % (len(df_original), len(df_original.columns)))
		return df_original

	def get_bl_rawdata(self):
		""" Load and return raw British Library metadata as a Pandas DataFrame """
		log.info("Reading raw data from %s" % self.bl_path)
		blindex_col = 'BL record ID for physical resource'
		df_bl = pd.read_csv(self.bl_path, dtype={blindex_col:object}).set_index(blindex_col).sort_index()
		log.info("Read %d rows, %d columns" % (len(df_bl), len(df_bl.columns)))
		return df_bl

	def get_ark_rawdata(self):
		""" Load and return raw Ark-related British Library metadata as a Pandas DataFrame """
		log.info("Reading raw data from %s" % self.ark_path)
		df_ark = pd.read_excel(self.ark_path)
		df_ark = df_ark.sort_index()
		log.info("Read %d rows, %d columns" % (len(df_ark), len(df_ark.columns)))
		return df_ark

	def get_book_metadata(self):
		""" Load and return the key book metadata as a Pandas DataFrame """
		log.info("Reading book metadata from %s" % self.meta_books_path)
		df_books = pd.read_json(self.meta_books_path, orient="records", dtype={'book_id':object})
		df_books.set_index("book_id", inplace=True)
		log.info("Read %d rows, %d columns" % df_books.shape)
		return df_books

	def get_book_classifications(self):
		""" Return the book classification metadata as a Pandas DataFrame """
		log.info("Reading classification metadata from %s" % self.meta_classifications_path)
		df_classifications = pd.read_csv(self.meta_classifications_path, sep="\t", dtype={'book_id':object})
		# make sure we don't have any np.nan values as these won't work with MySQL
		df_classifications = df_classifications.replace({np.nan: None})
		log.info("Read %d rows, %d columns" % df_classifications.shape)
		return df_classifications		

	def get_book_links(self):
		""" Return the book external link metadata as a Pandas DataFrame """
		log.info("Reading link metadata from %s" % self.meta_links_path)
		df_links = pd.read_csv(self.meta_links_path, sep="\t", dtype={'book_id':object})
		log.info("Read %d rows, %d columns" % df_links.shape)
		return df_links	

	def get_volumes_metadata(self):
		""" Return the book volumes metadata as a Pandas DataFrame """
		log.info("Reading volume metadata from %s" % self.meta_volumes_path)
		df_volumes = pd.read_csv(self.meta_volumes_path, sep="\t", dtype={'book_id':object}).set_index("volume_id")
		log.info("Read %d rows, %d columns" % df_volumes.shape)
		return df_volumes	

	def get_filter_book_ids(self):
		""" Get list of book identifiers which are to be excluded from Curatr """
		if not self.filter_path.exists():
			log.warning("Filter list file does not exist: %s" % self.filter_path.absolute())
			return set()
		filter_book_ids = set()
		with open(self.filter_path, "r") as fin:
			for line in fin.readlines():
				line = line.strip()
				if len(line) > 0:
					filter_book_ids.add(line)
		log.info("Read filter list of %d book IDs from %s" % (len(filter_book_ids), self.filter_path.absolute()) )
		return filter_book_ids

	def get_stopwords(self):
		""" Returns the default set of Curatr stopwords """
		import pkgutil
		data = pkgutil.get_data(__name__, "stopwords.txt")
		stopwords = set()
		for line in data.decode('utf-8').splitlines():
			line = line.strip()
			if len(line) > 0:
				stopwords.add(line.lower())
		return stopwords