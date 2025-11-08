"""
Implementation for basic semantic network-related features of the Curatr web interface
"""
import urllib.parse
import io
import logging as log
from flask import Markup, send_file
from xml.sax.saxutils import escape
from web.util import parse_keyword_query, parse_arg_int
from semantic import find_neighbors, neighborhood_sizes, default_num_k, default_num_hops

# --------------------------------------------------------------
	
def populate_networks_page(context):
	"""
	Populate the parameters for the template for the semantic networks page.

	This function retrieves network configuration parameters, parses the query words,
	builds a semantic network using the find_neighbors function, and formats the
	network data as JavaScript objects for visualisation in the web interface.

	Args:
		context: Dictionary containing core, request, and other template parameters

	Returns:
		Updated context dictionary with network data, visualisation parameters, and export URL
	"""
	# Populate the template parameters
	try:
		default_k = context.core.config["networks"].getint("default_k", default_num_k)
		k = max(1, parse_arg_int(context.request, "k", default_k))
		default_hops = context.core.config["networks"].getint("default_hops", default_num_hops)
		hops = max(1, parse_arg_int(context.request, "hops", default_hops))
	except Exception as e:
		log.warning(f"Error parsing network parameters: {e}")
		k = default_num_k
		hops = default_num_hops
	embed_id = context.request.args.get("embedding", default=context.core.default_embedding_id)
	seed_font_size = context.core.config["networks"].getint("seed_font_size", 30)
	neighbor_font_size = context.core.config["networks"].getint("neighbor_font_size", 23)
	seed_node_size = context.core.config["networks"].getint("seed_node_size", 30)
	neighbor_node_size = context.core.config["networks"].getint("neighbor_node_size", 20)

	# Parse the query
	raw_query_string = context.request.args.get("qwords", default="").lower()
	queries = parse_keyword_query(raw_query_string)
	# If nothing specified, use the default query
	if len(queries) > 0:
		query_string = ", ".join(queries)
	else:
		query_string = context.core.config["networks"].get("default_query", "contagion")
		queries = parse_keyword_query(query_string)
	context["query"] = query_string
	context["querylist"] = Markup(str(queries))

	# Build the network
	nodes, edges, hop_dict = find_neighbors(context.core, embed_id, queries, k, hops)
	log.info(
		f"Basic network built: |V|={len(nodes)} |E|={len(edges)} "
		f"k={k} hops={hops} seeds={','.join(queries)}"
	)

	# Convert to JavaScript
	nodes_js, edges_js = "", ""
	for node in nodes:
		if len(nodes_js) > 0:
			nodes_js += ",\n"
		nodes_js += f"\t\t{{id: '{node}', label: '{node}'"
		# First hop => seed node
		if hop_dict[node] == 0:
			nodes_js += f", group: 1, size : {seed_node_size}, font: {{ size : {seed_font_size} }}"
		else:
			nodes_js += f", group: 2, size : {neighbor_node_size}, font: {{ size : {neighbor_font_size} }}"
		nodes_js += "}"
	for e in edges:
		if len(edges_js) > 0:
			edges_js += ",\n"
		edges_js += f"\t\t{{from: '{e[0]}', to: '{e[1]}'}}"

	# Populate drop-down menus
	context["neighbor_options"] = Markup(format_neighbor_options(k))
	context["embedding_options"] = Markup(format_embedding_options(context.core, embed_id))

	# Render the template
	context["nodedata"] = Markup(nodes_js)
	context["edgedata"] = Markup(edges_js)

	# Add export URL
	quoted_query_string = urllib.parse.quote_plus(query_string)
	context["export_url"] = Markup(f"{context.prefix}/exportnetworks?k={k}&embedding={embed_id}&qwords={quoted_query_string}")
	return context

def export_network(context):
	"""
	Export a semantic network to an undirected network in GEXF format.

	Builds a semantic network from the query parameters and exports it as a
	GEXF XML file for download. The file can be imported into network analysis
	tools like Gephi. The network is exported as undirected to match the
	semantic network structure from find_neighbors().

	Args:
		context: Dictionary containing core, request, and other parameters

	Returns:
		Flask send_file response with GEXF XML data, or None if no queries provided
	"""
	# Get the various parameter values for the network
	try:
		default_k = context.core.config["networks"].getint("default_k", default_num_k)
		k = max(1, parse_arg_int(context.request, "k", default_k))
		default_hops = context.core.config["networks"].getint("default_hops", default_num_hops)
		hops = max(1, parse_arg_int(context.request, "hops", default_hops))
	except Exception as e:
		log.warning(f"Error parsing network parameters: {e}")
		k = default_num_k
		hops = default_num_hops
	embed_id = context.request.args.get("embedding", default=context.core.default_embedding_id)

	# Parse the query
	raw_query_string = context.request.args.get("qwords", default="").lower()
	queries = parse_keyword_query(raw_query_string)
	if len(queries) == 0:
		return None

	# Build the network
	nodes, edges, hop_dict = find_neighbors(context.core, embed_id, queries, k, hops)

	# Suggested filename
	filename = f"network-{k}-{'_'.join(queries)}.gexf"
	log.info(f"Exporting network in GEXF format to {filename}")

	# Create the response
	out = io.StringIO()
	create_gexf(out, queries, nodes, edges, hop_dict)
	# Creating the BytesIO object from the StringIO object
	mem = io.BytesIO()
	mem.write(out.getvalue().encode("utf-8"))
	mem.seek(0)
	out.close()
	return send_file(mem, mimetype="text/xml", as_attachment=True, download_name=filename)

def create_gexf(out, queries, nodes, edges, hop_dict):
	"""
	Write out the specified network in GEXF 1.3 format.

	GEXF (Graph Exchange XML Format) is an XML-based file format for describing
	complex network structures, their associated data, and dynamics.

	Args:
		out: Output stream to write the GEXF XML data to
		queries: List of seed query words
		nodes: Set of all nodes (words) in the network
		edges: List of edges as [source, target] pairs
		hop_dict: Dictionary mapping each node to its hop distance from seeds
	"""
	# Header
	out.write('<?xml version="1.0" encoding="UTF-8"?>\n')
	out.write('<gexf xmlns="http://gexf.net/1.3" xmlns:viz="http://gexf.net/1.3/viz" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://gexf.net/1.3 http://gexf.net/1.3/gexf.xsd" version="1.3">\n')

	# Metadata
	out.write('\t<meta>\n')
	out.write('\t\t<creator>Curatr</creator>\n')
	s_seeds = ", ".join(sorted(queries))
	out.write(f'\t\t<description>Semantic Network: {escape(s_seeds)}</description>\n')
	out.write('\t</meta>\n')

	# Start the network - using undirected edges to match semantic network structure
	out.write('\t<graph mode="static" defaultedgetype="undirected">\n')

	# Define attribute to state the hop distance for each node
	out.write('\t\t<attributes class="node" mode="static">\n')
	out.write('\t\t\t<attribute id="0" title="hop" type="long"/>\n')
	out.write('\t\t</attributes>\n')

	# Add the nodes
	out.write('\t\t<nodes>\n')
	for node in nodes:
		out.write(f'\t\t\t<node id="{escape(node)}" label="{escape(node)}">\n')
		# Add the hop attribute
		out.write(f'\t\t\t\t<attvalues><attvalue for="0" value="{hop_dict[node]}"/></attvalues>\n')
		out.write('\t\t\t</node>\n')
	out.write('\t\t</nodes>\n')

	# Add the edges
	out.write('\t\t<edges>\n')
	for edge_id, e in enumerate(edges):
		out.write(f'\t\t\t<edge id="{edge_id}" source="{escape(e[0])}" target="{escape(e[1])}"/>\n')
	out.write('\t\t</edges>\n')

	# Finished network
	out.write('\t</graph>\n')

	# Footer
	out.write('</gexf>\n')

# --------------------------------------------------------------

def format_neighbor_options(selected=10):
	"""
	Populate the list of options for the neighbourhood size drop-down list.

	Generates HTML <option> elements for the k-nearest neighbours parameter,
	marking the currently selected value.

	Args:
		selected: The currently selected k value (default: 10)

	Returns:
		HTML string containing <option> elements for each neighbourhood size
	"""
	html = ""
	for k in neighborhood_sizes:
		if k == selected:
			html += f"<option value='{k}' selected>{k}</option>\n"
		else:
			html += f"<option value='{k}'>{k}</option>\n"
	return html

def format_embedding_options(core, selected="all"):
	"""
	Populate the list of options for the embedding drop-down list.

	Generates HTML <option> elements for available embeddings,
	marking the currently selected embedding.

	Args:
		core: CoreCuratr instance providing access to available embeddings
		selected: The currently selected embedding ID (default: "all")

	Returns:
		HTML string containing <option> elements for each embedding
	"""
	html = ""
	for embed_id in core.get_embedding_ids():
		if embed_id == selected:
			html += f"<option value='{embed_id}' selected>{embed_id.title()}</option>\n"
		else:
			html += f"<option value='{embed_id}'>{embed_id.title()}</option>\n"
	return html	
