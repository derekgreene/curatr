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
neighborhood_sizes = [1, 3, 5, 10, 12, 15, 20]
""" default number of neighbors for smenatic networks """
default_num_k = 5

# --------------------------------------------------------------

def create_network(core, embed_id, queries, k, expand = True):
	""" Construct a semantic network representation based on a set of query words and their
	neighbors """
	# add the seed_nodes
	seed_nodes = set(queries)
	edges = []
	# add the other nodes, based on the recommendations
	other_nodes = set()
	for seed in queries:
		seed_recs = core.similar_words(embed_id, seed, k)
		for neighbor in seed_recs:
			if not (neighbor in other_nodes or neighbor in seed_nodes):
				other_nodes.add(neighbor)
			edges.append([seed,neighbor])
	# add edges between alters?
	if expand:
		extra_recommendations = {}
		for word in other_nodes:
			extra_recommendations[word]	= core.similar_words(embed_id, word, k)
		for word1, word2 in itertools.combinations(other_nodes, r=2):
			if word1 in extra_recommendations[word2] and word2 in extra_recommendations[word1]:
				edges.append([word1,word2])	
	return seed_nodes, other_nodes, edges

def populate_networks_page(context):
	""" populate the parameters for the template for the semantic networks page """
	# populate the template parameters
	try:
		default_k = context.core.config["networks"].getint("default_k", default_num_k)
		k = max(1, parse_arg_int(context.request, "neighbors", default_k))
	except:
		k = default_num_k
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
	seed_nodes, other_nodes, edges = create_network(context.core, embed_id, queries, k, True)
	# convert to JavaScript
	nodes_js, edges_js = "", ""
	for node in seed_nodes:
		if len(nodes_js) > 0:
			nodes_js += ",\n"
		nodes_js += "\t\t{id: '%s', label: '%s'" % (node, node)
		nodes_js += ", group: 1, size : %d, font: { size : %d }"  % (seed_node_size, seed_font_size)
		nodes_js += "}"
	for node in other_nodes:
		if len(nodes_js) > 0:
			nodes_js += ",\n"
		nodes_js += "\t\t{id: '%s', label: '%s'" % (node, node)
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
	context["export_url"] = Markup("%s/exportnetworks?neighbors=%s&embedding=%s&qwords=%s" % (context.prefix, k, embed_id, quoted_query_string))
	return context

def export_network(context):
	""" Export this semantic network to a directed network in GEXF """
	default_k = context.core.config["networks"].getint("default_k", 5)
	k = max(1, parse_arg_int(context.request, "neighbors", default_k))
	embed_id = context.request.args.get("embedding", default=context.core.default_embedding_id)
	# parse the query
	raw_query_string = context.request.args.get("qwords", default = "").lower()
	queries = parse_keyword_query(raw_query_string)
	if len(queries) == 0:
		return None
	# build the network
	seed_nodes, other_nodes, edges = create_network(context.core, embed_id, queries, k, True)
	# suggested filename
	filename = "network-%d-%s.gexf" % (k, "_".join(queries))
	log.info("Exporting network in GEXF format to %s" % filename) 
	# create the response
	out = io.StringIO()
	create_gexf(out, seed_nodes, other_nodes, edges)
    # Creating the byteIO object from the StringIO Object
	mem = io.BytesIO()
	mem.write(out.getvalue().encode('utf-8'))
	mem.seek(0)
	out.close()	
	return send_file(mem, mimetype='text/xml', as_attachment=True, download_name=filename)

def create_gexf(out, seed_nodes, other_nodes, edges):
	""" Write out the specified graph in GEXF 1.3 format """
	# header
	out.write('<?xml version="1.0" encoding="UTF-8"?>\n')
	out.write('<gexf xmlns="http://gexf.net/1.3" xmlns:viz="http://gexf.net/1.3/viz" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://gexf.net/1.3 http://gexf.net/1.3/gexf.xsd" version="1.3">\n')
	# metadata
	out.write('\t<meta>\n')
	out.write('\t\t<creator>Curatr</creator>\n')
	s_seeds = ", ".join(sorted(seed_nodes))
	out.write('\t\t<description>Semantic Network: %s</description>\n' % escape(s_seeds))
	out.write('\t</meta>\n')
	# start the graph - note we are using directed here
	out.write('\t<graph mode="static" defaultedgetype="directed">\n')
	# define attribute to state whether a node is a seed or not
	out.write('\t\t<attributes class="node" mode="static">\n')
	out.write('\t\t\t<attribute id="seed" title="seed" type="boolean"/>\n')
	out.write('\t\t</attributes>\n')
	# add the nodes
	out.write('\t\t<nodes>\n')
	for node in seed_nodes:
		out.write('\t\t\t<node id="%s" label="%s">\n' % (escape(node), escape(node)))
		out.write('\t\t\t\t<attvalues><attvalue for="seed" value="true"/></attvalues>\n')
		out.write('\t\t\t</node>\n')
	for node in other_nodes:
		out.write('\t\t\t<node id="%s" label="%s">\n' % (escape(node), escape(node)))
		out.write('\t\t\t\t<attvalues><attvalue for="seed" value="false"/></attvalues>\n')
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
