#!/usr/bin/env python
"""
Script to generate a semantic network from embeddings for given seed words. The output is a GEXF file representing the network.

The required command line arguments are the core directory path. followed by one or more seed words.

Additional command line arguments can be used to specify the number of neighbours, number of hops, and name of the embedding model to use.

Sample usage:
``` python code/tool-network.py core contagion disease ```
"""
import sys, itertools
from pathlib import Path
import logging as log
from optparse import OptionParser
import networkx as nx
from core import CoreCuratr
from semantic import find_neighbors, default_num_k, default_num_hops

# --------------------------------------------------------------

def main():
	"""
	Generate a semantic network from word embeddings starting from seed words.

	Creates a graph by finding k-nearest neighbours for seed words, then expanding
	outward for a specified number of hops. The resulting network is exported as
	a GEXF file for visualisation and analysis.
	"""
	parser = OptionParser(usage="usage: %prog [options] dir_core word1 word2...")
	parser.add_option("-k", action="store", type="int", dest="k", help="number of neighbours per word", default=default_num_k)
	parser.add_option("-n", action="store", type="int", dest="hops", help="number of hops", default=default_num_hops)
	parser.add_option("-o", action="store", type="string", dest="out_path", help="output path for network file", default="words.gexf")
	parser.add_option("-e", action="store", type="string", dest="embed_id", help="embedding to use", default="all")
	(options, args) = parser.parse_args()
	if len(args) < 2:
		parser.error("Must specify core directory and at least one word")
	log.basicConfig(level=log.INFO, format="%(message)s")
	# use set to remove duplicates and enable fast membership testing
	seeds = set(args[1:])
	embed_id, k, hops = options.embed_id, options.k, options.hops

	# set up the Curatr core
	dir_core = Path(args[0])
	if not dir_core.exists():
		log.error(f"Invalid core directory: {dir_core.absolute()}")
		sys.exit(1)
	core = CoreCuratr(dir_core)

	log.info(f"Using embedding: {embed_id}")
	log.info(f"Getting {k} neighbours for: {seeds}")

	# find the nodes and neighbours
	nodes, edges, hop_dict = find_neighbors(core, embed_id, seeds, k, hops)

	# create the network
	g = nx.Graph()
	# add all nodes with their hop distance from seed words as an attribute
	for node in nodes:
		g.add_node(node, hop=hop_dict[node])
	# add edges between semantically similar words
	for e in edges:
		g.add_edge(e[0], e[1])

	log.info(f"Built network: {g.number_of_nodes()} nodes, {g.number_of_edges()} edges")
	log.info(f"Network density: {nx.density(g):.2f}")
	log.info(f"Connected components: {nx.number_connected_components(g)}")

	# write the network to file in GEXF format for visualisation tools like Gephi
	log.info(f"Writing {options.out_path} ...")
	nx.write_gexf(g, options.out_path)

	# finished
	core.shutdown()
	log.info("Process complete")


# --------------------------------------------------------------

if __name__ == "__main__":
	main()
