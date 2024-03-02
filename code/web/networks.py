"""
Implementation for semantic network-related features of the Curatr web interface
"""
import itertools, urllib.parse, io
import logging as log
from flask import Markup, send_file
from xml.sax.saxutils import escape
from web.util import parse_keyword_query, parse_arg_int

# --------------------------------------------------------------

""" list of available neighborhood sizes for construction semantic networks """
neighborhood_sizes = [3, 5, 10, 12, 15, 20]
""" default number of neighbors for semnatic networks """
default_num_k = 10
""" default number of hops for semnatic networks """
default_num_hops = 1

# --------------------------------------------------------------

def find_neighbors(core, embed_id, queries, k, hops):
	""" Use an embedding to find all neighbors of the specified query words, and repeat the process
	recursively for the specified number of hops """
	# add the seed words
	edges, hop_dict = [], {}
	input_words = set(queries)
	all_words = set()
	next_words = set()
	for hop in range(1, hops+1):
		for input_word in input_words:
			# have we checked it before?
			if input_word in all_words:
				continue
			if input_word in hop_dict:
				hop_dict[input_word] = min(hop-1, hop_dict[input_word])
			else:
				hop_dict[input_word] = hop-1
			all_words.add(input_word)
			# find its neighbours
			neighbors = core.similar_words(embed_id, input_word, k)
			if len(neighbors) == 0:
				log.warning("Warning: No neighbors for '%s'" % word)
				continue
			for neighbor in neighbors[0:k]:
				if not neighbor in hop_dict:
					hop_dict[neighbor] = hop
				next_words.add(neighbor)
				log.debug("Edge: %s, %s" % (input_word, neighbor))
				edges.append([input_word, neighbor])
		# tidy up for next hop?
		if hop < hops:
			input_words = next_words
			next_words = set()
		else:
			# make sure we add the final set of words
			all_words = all_words.union(next_words)
	# now check all pairs
	extra_neighbors = {}
	for word in all_words:
		extra_neighbors[word] = core.similar_words(embed_id, word, k)
	for word1, word2 in itertools.combinations(all_words, r=2):
		if word1 in extra_neighbors[word2] and word2 in extra_neighbors[word1]:
			edges.append([word1, word2])	
	return all_words, edges, hop_dict
	

def populate_networks_page(context):
	""" populate the parameters for the template for the semantic networks page """
	# populate the template parameters
	try:
		default_k = context.core.config["networks"].getint("default_k", default_num_k)
		k = max(1, parse_arg_int(context.request, "k", default_k))
		default_hops = context.core.config["networks"].getint("default_hops", default_num_hops)
		hops = max(1, parse_arg_int(context.request, "hops", default_hops))
	except:
		k = default_num_k
		hops = default_num_hops
	embed_id = context.request.args.get("embedding", default=context.core.default_embedding_id)
	seed_font_size = context.core.config["networks"].getint("seed_font_size", 30)
	neighbor_font_size = context.core.config["networks"].getint("neighbor_font_size", 23)
	seed_node_size = context.core.config["networks"].getint("seed_node_size", 30)
	neighbor_node_size = context.core.config["networks"].getint("neighbor_node_size", 20)
	# parse the query
	raw_query_string = context.request.args.get("qwords", default = "").lower()
	queries = parse_keyword_query(raw_query_string)
	# if nothing specified, use the default query
	if len(queries) > 0:
		query_string = ", ".join(queries)
	else:
		query_string = context.core.config["networks"].get("default_query", "contagion")
		queries = parse_keyword_query(query_string)
	context["query"] = query_string
	context["querylist"] = Markup(str(queries))	
	# build the network
	nodes, edges, hop_dict = find_neighbors(context.core, embed_id, queries, k, hops)
	# convert to JavaScript
	nodes_js, edges_js = "", ""
	for node in nodes:
		if len(nodes_js) > 0:
			nodes_js += ",\n"
		nodes_js += "\t\t{id: '%s', label: '%s'" % (node, node)
		# first hop => seed node
		if hop_dict[node] == 0:
			nodes_js += ", group: 1, size : %d, font: { size : %d }"  % (seed_node_size, seed_font_size)
		else:
			nodes_js += ", group: 2, size : %d, font: { size : %d }" % (neighbor_node_size, neighbor_font_size)
		nodes_js += "}"
	for e in edges:
		if len(edges_js) > 0:
			edges_js += ",\n"
		edges_js += "\t\t{from: '%s', to: '%s'}" % (e[0], e[1])		
	# populate drop-down menus
	context["neighbor_options"] = Markup(format_neighbor_options(k))
	context["embedding_options"] = Markup(format_embedding_options(context.core, embed_id))
	# render the template
	context["nodedata"] = Markup(nodes_js)
	context["edgedata"] = Markup(edges_js)
	# add export URL
	quoted_query_string = urllib.parse.quote_plus(query_string)
	context["export_url"] = Markup("%s/exportnetworks?k=%s&embedding=%s&qwords=%s" % (context.prefix, k, embed_id, quoted_query_string))
	return context

def export_network(context):
	""" Export this semantic network to a directed network in GEXF """
	# get the various parameter value for the network
	try:
		default_k = context.core.config["networks"].getint("default_k", default_num_k)
		k = max(1, parse_arg_int(context.request, "k", default_k))
		default_hops = context.core.config["networks"].getint("default_hops", default_num_hops)
		hops = max(1, parse_arg_int(context.request, "hops", default_hops))
	except:
		k = default_num_k
		hops = default_num_hops	
	embed_id = context.request.args.get("embedding", default=context.core.default_embedding_id)
	# parse the query
	raw_query_string = context.request.args.get("qwords", default = "").lower()
	queries = parse_keyword_query(raw_query_string)
	if len(queries) == 0:
		return None
	# build the network
	nodes, edges, hop_dict = find_neighbors(context.core, embed_id, queries, k, hops)
	# suggested filename
	filename = "network-%d-%s.gexf" % (k, "_".join(queries))
	log.info("Exporting network in GEXF format to %s" % filename) 
	# create the response
	out = io.StringIO()
	create_gexf(out, queries, nodes, edges, hop_dict)
    # Creating the byteIO object from the StringIO Object
	mem = io.BytesIO()
	mem.write(out.getvalue().encode('utf-8'))
	mem.seek(0)
	out.close()	
	return send_file(mem, mimetype='text/xml', as_attachment=True, download_name=filename)

def create_gexf(out, queries, nodes, edges, hop_dict):
	""" Write out the specified graph in GEXF 1.3 format """
	# header
	out.write('<?xml version="1.0" encoding="UTF-8"?>\n')
	out.write('<gexf xmlns="http://gexf.net/1.3" xmlns:viz="http://gexf.net/1.3/viz" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://gexf.net/1.3 http://gexf.net/1.3/gexf.xsd" version="1.3">\n')
	# metadata
	out.write('\t<meta>\n')
	out.write('\t\t<creator>Curatr</creator>\n')
	s_seeds = ", ".join(sorted(queries))
	out.write('\t\t<description>Semantic Network: %s</description>\n' % escape(s_seeds))
	out.write('\t</meta>\n')
	# start the graph - note we are using directed here
	out.write('\t<graph mode="static" defaultedgetype="directed">\n')
	# define attribute to state whether a node is a seed or not
	out.write('\t\t<attributes class="node" mode="static">\n')
	out.write('\t\t\t<attribute id="0" title="hop" type="long"/>\n')
	out.write('\t\t</attributes>\n')
	# add the nodes
	out.write('\t\t<nodes>\n')
	for node in nodes:
		out.write('\t\t\t<node id="%s" label="%s">\n' % (escape(node), escape(node)))
		# add the hop attribute
		out.write('\t\t\t\t<attvalues><attvalue for="0" value="%d"/></attvalues>\n' % hop_dict[node])
		out.write('\t\t\t</node>\n')
	out.write('\t\t</nodes>\n')
	# add the edges
	out.write('\t\t<edges>\n')
	for e in edges:
		out.write('\t\t\t<edge source="%s" target="%s"/>\n' % (escape(e[0]), escape(e[1])))
	out.write('\t\t</edges>\n')
	# finished graph
	out.write('\t</graph>\n')
	# footer
	out.write('</gexf>\n')

# --------------------------------------------------------------

def format_neighbor_options(selected=10):
	""" Populate the list of options for the neighborhood size drop-down list """
	html = ""
	for k in neighborhood_sizes:
		if k == selected:
			html += "<option value='%s' selected>%s</option>\n" % (k, k)
		else:
			html += "<option value='%s'>%s</option>\n" % (k, k)
	return html	

def format_embedding_options(core, selected="all"):
	""" Populate the list of options for the embedding drop-down list """
	html = ""
	for embed_id in core.get_embedding_ids():
		if embed_id == selected:
			html += "<option value='%s' selected>%s</option>\n" % (embed_id, embed_id.title())
		else:
			html += "<option value='%s'>%s</option>\n" % (embed_id, embed_id.title())
	return html	
