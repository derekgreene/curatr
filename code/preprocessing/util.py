"""
Various utlity code used for data preprocessing tasks when running Curatr setup.
"""
import json
import logging as log
from core import CoreBase
from pathlib import Path
import pandas as pd
import numpy as np
from preprocessing.text import load_stopwords

# --------------------------------------------------------------

class CorePrep(CoreBase):
	def __init__(self, dir_root):
		super().__init__(dir_root)
		self.dir_raw = self.dir_metadata / "raw"
		# file paths for raw data
		self.original_path = self.dir_raw / "ucd_digitised_books_2021.json"
		self.bl_path = self.dir_raw / "ms_digitised_books_2021-01-09.csv"
		self.alston_path = self.dir_raw / "alston-classifications-annotated.json"
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

	def get_alston_rawdata(self):
		""" Load and return the raw Alston classification data as a list of records, one per book """
		log.info("Reading raw data from %s" % self.alston_path)
		with open(self.alston_path, "r", encoding="utf-8") as f:
			records = json.load(f)
		log.info("Read %d records" % len(records))
		return records

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
		df_classifications = pd.read_json(self.meta_classifications_path, orient="records", dtype={'book_id':object})
		df_classifications = df_classifications.set_index("book_id")
		# make sure we don't have any np.nan values as these won't work with MySQL
		# (df.replace({np.nan: None}) is unreliable across pandas versions for this)
		df_classifications = df_classifications.where(df_classifications.notna(), None)
		log.info("Read %d rows, %d columns" % df_classifications.shape)
		return df_classifications		

	def get_volumes_metadata(self):
		""" Return the book volumes metadata as a Pandas DataFrame """
		log.info("Reading volume metadata from %s" % self.meta_volumes_path)
		df_volumes = pd.read_csv(self.meta_volumes_path, sep="\t", dtype={'book_id':object}).set_index("volume_id")
		log.info("Read %d rows, %d columns" % df_volumes.shape)
		return df_volumes	

	def get_stopwords(self):
		""" Returns the default set of Curatr stopwords """
		return load_stopwords()
	