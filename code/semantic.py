"""
Implementation of techniques for building semantic networks from word embeddings
"""
import itertools
import logging as log

# --------------------------------------------------------------

""" list of available neighbourhood sizes for constructing semantic networks """
neighborhood_sizes = [3, 5, 10, 12, 15, 20]
""" default number of neighbours for semantic networks """
default_num_k = 10
""" default number of hops for semantic networks """
default_num_hops = 1

# --------------------------------------------------------------
# Helper Functions

def _only_words(sim_result):
	"""
	Normalise outputs of core.word_similarity to a list of neighbour tokens.
	Accepts either ["w1","w2",...] or [("w1", score), ...].
	"""
	if not sim_result:
		return []
	words = []
	for x in sim_result:
		if isinstance(x, tuple) and len(x) >= 1:
			words.append(x[0])
		else:
			words.append(x)
	return words

# --------------------------------------------------------------
# Original Implementations

def find_neighbors(core, embed_id, queries, k, hops):
	"""
	Build a semantic network from word embeddings using BFS expansion and mutual neighbour detection.

	Network construction process:
		Phase 1 - BFS Expansion:
			1. Start with seed query words
			2. For each word in the current frontier, find its k-nearest neighbours in the embedding space
			3. Create edges between the word and all its k-nearest neighbours
			4. Add neighbours to the next frontier
			5. Repeat for the specified number of hops

		Phase 2 - Mutual Neighbour Detection:
			1. Query k-nearest neighbours for ALL words discovered in Phase 1
			2. Check all possible pairs of words
			3. If two words are mutual k-nearest neighbours (each appears in the other's top-k list),
			   add an edge between them
			4. This densifies the network by discovering semantic relationships not found during BFS

	The resulting network contains edges from both phases, providing a more complete representation
	of semantic relationships than BFS alone.

	Args:
		core: CoreCuratr instance providing word_similarity queries
		embed_id: Identifier for the embedding to use
		queries: Set or list of seed words to start network construction
		k: Number of nearest neighbours to consider for each word
		hops: Number of BFS hops from seed words

	Returns:
		all_words: Set of all words (nodes) in the network
		edges: List of [word1, word2] undirected edge pairs
		hop_dict: Dictionary mapping each word to its minimum hop distance from seed queries
	"""
	# Add the seed words
	edges, hop_dict = [], {}
	input_words = set(queries)
	all_words = set()
	next_words = set()
	for hop in range(1, hops+1):
		for input_word in input_words:
			# Have we checked it before?
			if input_word in all_words:
				continue
			if input_word in hop_dict:
				hop_dict[input_word] = min(hop-1, hop_dict[input_word])
			else:
				hop_dict[input_word] = hop-1
			all_words.add(input_word)
			# Find its neighbours
			neighbors_raw = core.word_similarity(input_word, k=k, embed_id=embed_id)
			neighbors = _only_words(neighbors_raw)
			if len(neighbors) == 0:
				log.warning(f"Warning: No neighbours for \"{input_word}\"")
				continue
			for neighbor in neighbors[0:k]:
				if not neighbor in hop_dict:
					hop_dict[neighbor] = hop
				next_words.add(neighbor)
				log.debug(f"Edge: {input_word}, {neighbor}")
				edges.append([input_word, neighbor])
		# Tidy up for next hop?
		if hop < hops:
			input_words = next_words
			next_words = set()
		else:
			# Make sure we add the final set of words
			all_words = all_words.union(next_words)
	# Now check all pairs
	extra_neighbors = {}
	for word in all_words:
		neighbors_raw = core.word_similarity(word, k=k, embed_id=embed_id)
		extra_neighbors[word] = _only_words(neighbors_raw)
	for word1, word2 in itertools.combinations(all_words, r=2):
		if word1 in extra_neighbors[word2] and word2 in extra_neighbors[word1]:
			edges.append([word1, word2])
	# Now ensure that we only have unique edges (undirected)
	unique_edges = set()
	for e in edges:
		unique_edges.add(tuple(sorted(e)))
	edges = [list(e) for e in unique_edges]
	return all_words, edges, hop_dict

# --------------------------------------------------------------
# Optimised Implementation

def find_neighbors_fast(core, embed_id, queries, k, hops):
	"""
	Build a semantic network from word embeddings using BFS expansion and mutual neighbour detection.
	Optimised version of find_neighbors() that produces identical output with improved performance.

	Network construction process:
		Phase 1 - BFS Expansion:
			1. Start with seed query words
			2. For each word in the current frontier, find its k-nearest neighbours in the embedding space
			3. Create edges between the word and all its k-nearest neighbours
			4. Cache the neighbour results for use in Phase 2
			5. Add neighbours to the next frontier
			6. Repeat for the specified number of hops

		Phase 2 - Mutual Neighbour Detection:
			1. Query k-nearest neighbours for any words not cached in Phase 1
			2. Convert all neighbour lists to sets for O(1) membership testing
			3. Check all possible pairs of words
			4. If two words are mutual k-nearest neighbours (each appears in the other's top-k list),
			   add an edge between them
			5. This densifies the network by discovering semantic relationships not found during BFS

	Performance improvements over original:
		- Caches neighbour queries from BFS phase to avoid redundant word_similarity calls
		- Uses sets for O(1) membership testing during all-pairs mutual neighbour check
		- Deduplicates edges during construction (frozenset) instead of sorting at the end
		- Better error handling with try/except blocks
		- Normalises word_similarity output to handle both string and tuple formats

	Args:
		core: CoreCuratr instance providing word_similarity queries
		embed_id: Identifier for the embedding to use
		queries: Set or list of seed words to start network construction
		k: Number of nearest neighbours to consider for each word
		hops: Number of BFS hops from seed words

	Returns:
		all_words: Set of all words (nodes) in the network
		edges: List of [word1, word2] undirected edge pairs
		hop_dict: Dictionary mapping each word to its minimum hop distance from seed queries
	"""
	edges = set()  # Use frozenset for efficient undirected edge deduplication
	hop_dict = {}
	all_words = set()
	frontier = set(queries)
	next_frontier = set()
	neighbor_cache = {}  # Cache word -> neighbours to avoid redundant queries

	# Phase 1: BFS neighbour discovery (same as original)
	for hop in range(1, hops + 1):
		for input_word in frontier:
			# Have we checked it before?
			if input_word in all_words:
				continue

			# Update hop distance
			if input_word in hop_dict:
				hop_dict[input_word] = min(hop - 1, hop_dict[input_word])
			else:
				hop_dict[input_word] = hop - 1

			all_words.add(input_word)

			# Find neighbours and cache the result (KEY OPTIMISATION)
			try:
				neighbors_raw = core.word_similarity(input_word, k=k, embed_id=embed_id)
				neighbors = _only_words(neighbors_raw)
				neighbor_cache[input_word] = neighbors  # Cache for Phase 2
			except Exception as e:
				log.warning(f"No neighbours for \"{input_word}\": {e}")
				neighbor_cache[input_word] = []
				continue

			if len(neighbors) == 0:
				log.warning(f"No neighbours for \"{input_word}\"")
				continue

			# Add edges and update frontier
			for neighbor in neighbors[0:k]:
				if neighbor not in hop_dict:
					hop_dict[neighbor] = hop
				next_frontier.add(neighbor)
				# Use frozenset for automatic deduplication of undirected edges
				edges.add(frozenset([input_word, neighbor]))

		# Prepare for next hop
		if hop < hops:
			frontier = next_frontier
			next_frontier = set()
		else:
			# Make sure we add the final set of words
			all_words = all_words.union(next_frontier)

	# Phase 2: All-pairs mutual neighbour check
	# Query neighbours ONLY for words not already cached (KEY OPTIMISATION)
	for word in all_words:
		if word not in neighbor_cache:
			try:
				neighbors_raw = core.word_similarity(word, k=k, embed_id=embed_id)
				neighbor_cache[word] = _only_words(neighbors_raw)
			except Exception as e:
				log.warning(f"No neighbours for \"{word}\": {e}")
				neighbor_cache[word] = []

	# Convert neighbour lists to sets for O(1) membership testing (KEY OPTIMISATION)
	neighbor_sets = {word: set(nbrs[0:k]) for word, nbrs in neighbor_cache.items()}

	# Check all pairs for mutual k-nearest neighbours
	for word1, word2 in itertools.combinations(all_words, 2):
		if (word1 in neighbor_sets.get(word2, set()) and
		    word2 in neighbor_sets.get(word1, set())):
			edges.add(frozenset([word1, word2]))

	# Convert to same format as original (list of 2-element lists)
	edges = [list(e) for e in edges]
	return all_words, edges, hop_dict