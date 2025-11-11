#!/usr/bin/env python
"""
This module provides advanced semantic network visualisation using Dash and Dash Cytoscape.
The Dash app is integrated into the main Curatr Flask application.

Adapted from the legacy standalone Dash application to work within the Flask/Curatr infrastructure.
"""
import io, re
import logging as log
from pathlib import Path
import dash
from dash import html, dcc, Input, Output, State, no_update, ClientsideFunction
import dash_bootstrap_components as dbc
import dash_cytoscape as cyto
import networkx as nx
from semantic import find_neighbors, neighborhood_sizes, default_num_k, default_num_hops

# --------------------------------------------------------------
# Configuration
# --------------------------------------------------------------

# default visualisation settings
DEFAULT_SETTINGS = {
    "node_size": 56,
    "node_border_width": 1.5,
    "node_border": "#3B3B3B",
    "label_font_size": 18,
    "edge_opacity": 0.5,
    "edge_color": "#444444",
    "edge_width": 2.5,
    "background_color": "#ECF0F1",
    "node_colors": ["#FFFF00", "#97C2FC", "#C5FCB5", "#FCC8E8", "#F2D2BD"]
}

# default CoSE layout settings
DEFAULT_LAYOUT_COSE = {
    "name": "cose",
    "animate": True,
    "animationDuration": 250,
    "idealEdgeLength": 95,
    "nodeOverlap": 2,
    "refresh": 20,
    "fit": True,
    "padding": 30,
    "randomize": False,
    "componentSpacing": 40,
    "nodeRepulsion": 9000,
    "edgeElasticity": 120,
    "nestingFactor": 1.2,
    "gravity": 0.4,
    "numIter": 1200,
    "initialTemp": 700,
    "coolingFactor": 0.96,
    "minTemp": 1.0,
    "handleDisconnected": True
}

external_stylesheets = [
    dbc.themes.MATERIA,
    "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css",
    "https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap"
]

# --------------------------------------------------------------
# Helper functions
# --------------------------------------------------------------

def parse_seed_text(text):
    """
    Parse seed text into a unique, ordered list of words (dedup, keep order).
    """
    if not text:
        return []
    text = text.lower()
    cleaned = re.sub(r"[,;\t]+", " ", text)
    parts = re.split(r"\s+", cleaned.strip())
    seen, out = set(), []
    for p in parts:
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return out

def build_network_from_core(core, model_id, seeds, K, N):
    """
    Build semantic network using Curatr core infrastructure.

    Args:
        core: CoreCuratr instance
        model_id: Embedding model ID to use
        seeds: List of seed words
        K: Number of neighbours per node
        N: Number of hops

    Returns:
        (nodes, edges, hop_dict, diagnostics)
    """
    try:
        # use the semantic.find_neighbors function with Curatr core
        all_words, edges, hop_dict = find_neighbors(core, model_id, seeds, K, N)

        diagnostics = {
            "nodes": len(all_words),
            "edges": len(edges),
            "K": K,
            "N": N,
            "seeds": seeds
        }

        return all_words, edges, hop_dict, diagnostics
    except Exception as e:
        log.error(f"Error building network: {e}")
        raise

def to_cyto(words, edges, hop_dict, seeds):
    """
    Convert network data to Cytoscape elements format.

    Args:
        words: Set of all words (nodes)
        edges: List of [word1, word2] edge pairs
        hop_dict: Dictionary mapping words to hop distances
        seeds: List of seed words

    Returns:
        List of Cytoscape element dictionaries
    """
    elements = []
    seed_set = set([s.lower() for s in seeds])
    node_ids = set()

    # add nodes
    for word in words:
        is_seed = 1 if word.lower() in seed_set else 0
        hop = hop_dict.get(word, 0)
        node_ids.add(word)

        elements.append({
            "data": {
                "id": word,
                "label": word,
                "is_seed": is_seed,
                "hop": hop
            }
        })

    # add edges with validation and unique IDs
    added_edges = set()
    skipped_edges = 0
    for source, target in edges:
        # skip self-loops
        if source == target:
            skipped_edges += 1
            continue

        # verify both nodes exist
        if source not in node_ids or target not in node_ids:
            log.warning(f"Edge references non-existent node: {source} -> {target}")
            skipped_edges += 1
            continue

        # create unique edge ID based on sorted node pair (for undirected edges)
        edge_pair = tuple(sorted([source, target]))
        if edge_pair in added_edges:
            # duplicate edge, skip
            skipped_edges += 1
            continue

        added_edges.add(edge_pair)
        edge_id = f"{edge_pair[0]}--{edge_pair[1]}"

        elements.append({
            "data": {
                "id": edge_id,
                "source": source,
                "target": target
            }
        })

    if skipped_edges > 0:
        log.info(f"Skipped {skipped_edges} edges (self-loops, duplicates, or invalid references)")

    return elements

def make_gexf_from_elements(elements):
    """
    Create a NetworkX graph from Cytoscape elements and return as GEXF format.

    Args:
        elements: List of Cytoscape element dictionaries

    Returns:
        NetworkX graph object
    """
    g = nx.Graph()

    # add nodes
    for el in elements:
        if "source" not in el.get("data", {}):
            data = el["data"]
            g.add_node(
                data["id"],
                label=data.get("label", data["id"]),
                is_seed=data.get("is_seed", 0),
                hop=data.get("hop", 0)
            )

    # add edges
    for el in elements:
        if "source" in el.get("data", {}):
            data = el["data"]
            g.add_edge(data["source"], data["target"])

    return g

# --------------------------------------------------------------
# Stylesheet functions
# --------------------------------------------------------------

def build_stylesheet(settings, max_hop):
    """Create a Cytoscape stylesheet with labels placed below nodes."""
    bw = float(settings.get("node_border_width", 1.5))
    styles = [
        {"selector": "node", "style": {
            "label": "data(label)",
            "font-size": int(settings.get("label_font_size", 18)),
            "color": "#2E2E2E",
            "width": int(settings.get("node_size", 56)),
            "height": int(settings.get("node_size", 56)),
            "text-halign": "center",
            "text-valign": "bottom",
            "text-margin-y": 8,
            "text-wrap": "wrap",
            "text-max-width": 100,
            "background-color": "#cccccc",
            "border-color": settings.get("node_border", "#3B3B3B"),
            "border-width": bw,
        }},
        {"selector": "[is_seed = 1]", "style": {
            "background-color": (settings.get("node_colors", []) or ["#cccccc"])[0],
            "border-width": bw,
            "border-color": settings.get("node_border", "#3B3B3B")
        }},
        {"selector": "edge", "style": {
            "opacity": float(settings.get("edge_opacity", 0.3)),
            "line-color": settings.get("edge_color", "#444444"),
            "width": float(settings.get("edge_width", 2.0))
        }},
        {"selector": "edge:selected", "style": {
            "width": 3,
            "line-color": "#f4a261"
        }},
        {"selector": "node:selected", "style": {
            "border-width": max(bw, 3),
            "border-color": "#f4a261",
            "background-color": "#1971c2",
            "color": "#000"
        }},
    ]

    node_cols = settings.get("node_colors", []) or []
    for h in range(1, max_hop + 1):
        if node_cols:
            idx = 1 + ((h - 1) % max(1, len(node_cols) - 1))
            idx = min(idx, len(node_cols) - 1)
            colour = node_cols[idx]
        else:
            colour = "#94a3b8"
        styles.append({"selector": f"[hop = {h}]", "style": {"background-color": colour}})

    return styles

def hop_legend(settings, max_hop):
    """Return a small HTML legend describing colours for seeds and each hop."""
    items = []
    node_cols = settings.get("node_colors", []) or []
    seed_colour = (node_cols or ["#cccccc"])[0]

    items.append(html.Div(className="d-flex align-items-center mb-1", children=[
        html.Div(style={
            "width": "14px",
            "height": "14px",
            "borderRadius": "50%",
            "marginRight": "6px",
            "backgroundColor": seed_colour,
            "border": f"3px solid {settings.get('node_border', '#3B3B3B')}"
        }),
        html.Small("Seed word(s)")
    ]))

    for h in range(1, max_hop + 1):
        if node_cols:
            idx = 1 + ((h - 1) % max(1, len(node_cols) - 1))
            idx = min(idx, len(node_cols) - 1)
            colour = node_cols[idx]
        else:
            colour = "#94a3b8"
        items.append(html.Div(className="d-flex align-items-center mb-1", children=[
            html.Div(style={
                "width": "14px",
                "height": "14px",
                "borderRadius": "50%",
                "marginRight": "6px",
                "backgroundColor": colour,
                "border": f"1px solid {settings.get('node_border', '#3B3B3B')}"
            }),
            html.Small(f"Hop {h}")
        ]))

    return html.Div(items)

# --------------------------------------------------------------
# Dash App Creation
# --------------------------------------------------------------

def create_dash_app(flask_app):
    """
    Create and configure a Dash app instance integrated with the existing Flask server.

    Args:
        flask_app: The Flask application instance to integrate with

    Returns:
        Configured Dash application instance
    """
    log.info("Creating Dash app for advanced semantic network visualisation...")

    # get core and available embeddings
    core = flask_app.core
    embedding_ids = core.get_embedding_ids()

    # create embedding model options for dropdown
    model_options = [{"label": embed_id, "value": embed_id} for embed_id in embedding_ids]

    # load settings from config if available
    settings = DEFAULT_SETTINGS.copy()
    if hasattr(core, "config") and "networkvis" in core.config:
        config_section = core.config["networkvis"]
        settings["node_size"] = config_section.getint("node_size", DEFAULT_SETTINGS["node_size"])
        settings["node_border_width"] = config_section.getfloat("node_border_width", DEFAULT_SETTINGS["node_border_width"])
        settings["label_font_size"] = config_section.getint("label_font_size", DEFAULT_SETTINGS["label_font_size"])
        settings["edge_opacity"] = config_section.getfloat("edge_opacity", DEFAULT_SETTINGS["edge_opacity"])
        settings["edge_width"] = config_section.getfloat("edge_width", DEFAULT_SETTINGS["edge_width"])
        if "node_border" in config_section:
            settings["node_border"] = config_section.get("node_border")
        if "edge_color" in config_section:
            settings["edge_color"] = config_section.get("edge_color")
        # parse node colours if provided
        if "node_colors" in config_section:
            colors_str = config_section.get("node_colors")
            settings["node_colors"] = [c.strip() for c in colors_str.split(",")]

    # create Dash app instance using the existing Flask server
    app_name = "Curatr Advanced Semantic Network Explorer"
    dash_app = dash.Dash(
        __name__,
        server=flask_app,
        url_base_pathname="/advanced/",
        title="Curatr - Advanced Semantic Networks",
        assets_folder="assets",
        external_stylesheets=external_stylesheets,
        suppress_callback_exceptions=True
    )

    # load custom HTML template
    template_path = Path(__file__).parent / "templates" / "advanced.html"
    try:
        fin = open(template_path, "r", encoding="utf-8")
        dash_app.index_string = fin.read().strip()
        fin.close()
    except Exception as e:
        log.error(f"Failed to load Dash app HTML template: {e}")

    # define the left panel controls
    controls = dbc.Card(
        dbc.CardBody([
            html.H5(app_name, className="app-title-left mb-3", id="title_app"),
            dbc.Label("Enter one or more keywords"),
            dbc.Input(
                id="seeds",
                type="text",
                placeholder="e.g. contagion, disease",
                className="mb-2"
            ),
            dbc.Label("Collection"),
            dcc.Dropdown(
                id="model_id",
                options=model_options,
                value=(model_options[0]["value"] if model_options else None),
                clearable=False,
                className="mb-2"
            ),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Related Words"),
                    dcc.Dropdown(
                        id="K",
                        options=[{"label": str(x), "value": x} for x in neighborhood_sizes],
                        value=default_num_k,
                        clearable=False
                    ),
                ], width=6),
                dbc.Col([
                    dbc.Label("Hops"),
                    dcc.Dropdown(
                        id="N",
                        options=[{"label": str(x), "value": x} for x in [1, 2, 3, 4]],
                        value=default_num_hops,
                        clearable=False
                    ),
                ], width=6),
            ], className="g-2 mb-2"),
            dbc.Button(
                "Visualise",
                id="explore",
                color="primary",
                className="w-100 mt-2"
            ),
            html.Div(id="loading_status", className="text-muted small mt-2"),
            html.Div(id="oov_warning", className="text-danger small mt-2"),
            html.Hr(),
            html.Div(id="graph_stats", className="text-muted small mb-1"),
            html.Div(id="legend", className="mt-1"),
            dbc.ButtonGroup([
                dbc.Button("Download PNG", id="btn_export_png", color="primary", size="sm"),
                dbc.Button("Download GEXF", id="btn_export_gexf", color="primary", size="sm"),
            ], className="w-100 mt-1 btn-group-gap"),
            dcc.Store(id="current_elements"),
            dcc.Store(id="seed_slug"),
            dcc.Store(id="fit_seq", data=0),
            dcc.Store(id="busy", data=False),
            dcc.Download(id="download"),
        ]),
        className="left-top",
    )

    # define the main layout
    dash_app.layout = dbc.Container(
        fluid=True,
        className="p-0",
        style={"minHeight": "100vh"},
        children=[
            dbc.Row(className="app-shell g-0", children=[
                dbc.Col(md=3, children=[
                    html.Div(className="left-panel", children=[controls])
                ]),
                dbc.Col(md=9, className="right-pane d-flex flex-column", children=[
                    html.Div(className="cy-wrap flex-grow-1 position-relative", children=[
                        html.Div(className="cy-toolbar", children=[
                            html.Button(
                                id="btn_zoom_in",
                                className="btn btn-light btn-sm me-1",
                                title="Zoom in",
                                children=[html.I(className="bi bi-plus")]
                            ),
                            html.Button(
                                id="btn_zoom_out",
                                className="btn btn-light btn-sm me-1",
                                title="Zoom out",
                                children=[html.I(className="bi bi-dash")]
                            ),
                            html.Button(
                                id="btn_fit",
                                className="btn btn-light btn-sm",
                                title="Fit to graph",
                                children=[html.I(className="bi bi-arrows-fullscreen")]
                            ),
                        ]),
                        cyto.Cytoscape(
                            id="cy",
                            layout={"name": "cose"},
                            elements=[],
                            minZoom=0.2,
                            maxZoom=4,
                            wheelSensitivity=0.2,
                            style={
                                "width": "100%",
                                "height": "100%",
                                "backgroundColor": settings.get("background_color", "#ECF0F1")
                            },
                            stylesheet=[],
                        )
                    ])
                ])
            ])
        ]
    )

    # --------------------------------------------------------------
    # Callback Functions
    # --------------------------------------------------------------

    @dash_app.callback(
        Output("legend", "children"),
        Output("cy", "stylesheet"),
        Output("graph_stats", "children"),
        Input("cy", "elements"),
    )
    def update_legend_and_stylesheet(elements):
        if not elements:
            return hop_legend(settings, 0), build_stylesheet(settings, 0), "No seed words selected"

        nodes = [el for el in elements if "source" not in el.get("data", {})]
        edges = [el for el in elements if "source" in el.get("data", {})]
        hops = [el.get("data", {}).get("hop") for el in nodes]
        max_hop = max([h for h in hops if isinstance(h, int)], default=0)
        stats = f"{len(nodes)} nodes, {len(edges)} edges"

        return hop_legend(settings, max_hop), build_stylesheet(settings, max_hop), stats

    @dash_app.callback(
        Output("cy", "elements"),
        Output("current_elements", "data"),
        Output("oov_warning", "children"),
        Output("cy", "layout"),
        Output("seed_slug", "data"),
        Output("busy", "data", allow_duplicate=True),
        Input("explore", "n_clicks"),
        State("model_id", "value"),
        State("seeds", "value"),
        State("K", "value"),
        State("N", "value"),
        prevent_initial_call=True
    )
    def build_graph(n, model_id, typed_seeds, K, N):
        # parse seed words and force lowercase
        seeds = parse_seed_text(typed_seeds or "")
        seeds = [s.lower() for s in seeds]

        if not seeds:
            return no_update, no_update, dbc.Alert(
                "Please provide seed words (type keywords).",
                color="warning",
                className="py-1 px-2"
            ), no_update, "network", False

        if model_id is None or not core.has_embedding(model_id):
            return no_update, no_update, dbc.Alert(
                "No valid embedding model selected.",
                color="danger",
                className="py-1 px-2"
            ), no_update, "network", False

        # check which seeds are in vocabulary
        embedding = core.get_embedding(model_id)
        if embedding is None:
            log.warning(f"Advanced network viwewer: Failed to access embedding model '{model_id}'")
            return no_update, no_update, dbc.Alert(
                "Failed to load embedding model.",
                color="danger",
                className="py-1 px-2"
            ), no_update, "network", False

        # get key_to_index if available
        oov, in_vocab = [], []
        for s in seeds:
            if embedding.in_vocab(s):
                in_vocab.append(s)
            else:
                oov.append(s)

        # no valid seed words at all?
        if len(in_vocab) == 0:
            log.warning(f"Advanced network viwewer: None of the seed words are in the selected model '{model_id}': {seeds}")
            return [], [], dbc.Alert(
                "None of the seed words are in the selected model.",
                color="danger",
                className="py-1 px-2"
            ), {"name": "cose"}, "network", False

        try:
            # build the network
            all_words, edges, hop_dict, diag = build_network_from_core(
                core, model_id, in_vocab, int(K or 10), int(N or 1)
            )
            # turn it into the Cytoscape format
            elements = to_cyto(all_words, edges, hop_dict, in_vocab)
            log.info(
                f"Advanced network built: |V|={diag.get('nodes')} |E|={diag.get('edges')} "
                f"k={diag.get('K')} hops={diag.get('N')} seeds={','.join(diag.get('seeds', []))}"
            )
        except Exception as e:
            log.serve(f"Advanced network viwewer: Error generating network for model '{model_id}': {e}")
            return no_update, no_update, dbc.Alert(
                f"Error while generating network: {e}",
                color="danger",
                className="py-1 px-2"
            ), no_update, "network", False
        # need to display a warning message?
        warn = ""
        if oov:
            warn = dbc.Alert(
                f"Not in the vocabulary: {', '.join(oov)}",
                color="warning",
                className="py-1 px-2"
            )
        # create slug for export filenames
        seed_slug = re.sub(
            r"_+", "_",
            re.sub(r"[^a-z0-9_]+", "_", "_".join(in_vocab).lower())
        ).strip("_") or "network"

        return elements, elements, warn, DEFAULT_LAYOUT_COSE, seed_slug, False

    @dash_app.callback(
        Output("cy", "generateImage"),
        Input("btn_export_png", "n_clicks"),
        State("seed_slug", "data"),
        State("K", "value"),
        State("N", "value"),
        State("model_id", "value"),
        prevent_initial_call=True,
    )
    def export_png(n, seed_slug, K, N, model_id):
        if not n:
            return no_update

        k_part = f"K{int(K):02d}" if K is not None else "K00"
        n_part = f"H{int(N)}" if N is not None else "H0"
        model_part = (
            re.sub(r"_+", "_", re.sub(r"[^a-z0-9_]+", "_", str(model_id).lower())) or "model"
        ).strip("_")
        base = f"curatr_{seed_slug or 'network'}-{model_part}-{k_part}{n_part}"

        return {
            "type": "png",
            "action": "download",
            "scale": 2,
            "full": True,
            "bg": "#ffffff",
            "filename": base
        }

    @dash_app.callback(
        Output("download", "data"),
        Input("btn_export_gexf", "n_clicks"),
        State("current_elements", "data"),
        State("seed_slug", "data"),
        State("K", "value"),
        State("N", "value"),
        State("model_id", "value"),
        prevent_initial_call=True
    )
    def export_gexf(n, elements, seed_slug, K, N, model_id):
        if not n or not elements:
            return no_update

        g = make_gexf_from_elements(elements)
        bio = io.BytesIO()
        nx.write_gexf(g, bio, encoding="utf-8")

        k_part = f"K{int(K):02d}" if K is not None else "K00"
        n_part = f"H{int(N)}" if N is not None else "H0"
        model_part = (
            re.sub(r"_+", "_", re.sub(r"[^a-z0-9_]+", "_", str(model_id).lower())) or "model"
        ).strip("_")
        fname = f"curatr_{seed_slug or 'network'}-{model_part}-{k_part}{n_part}.gexf"

        return dcc.send_bytes(bio.getvalue(), fname)

    @dash_app.callback(
        Output("cy", "zoom"),
        Output("cy", "layout", allow_duplicate=True),
        Output("fit_seq", "data"),
        Input("btn_zoom_in", "n_clicks"),
        Input("btn_zoom_out", "n_clicks"),
        Input("btn_fit", "n_clicks"),
        State("cy", "zoom"),
        State("fit_seq", "data"),
        prevent_initial_call=True,
    )
    def on_zoom_buttons(zin, zout, fit, current_zoom, fit_seq):
        ctx = dash.callback_context
        if not ctx.triggered:
            return no_update, no_update, fit_seq or 0

        tid = ctx.triggered[0]["prop_id"].split(".")[0]

        if tid == "btn_zoom_in":
            try:
                z = float(current_zoom or 1.0)
            except Exception:
                z = 1.0
            return max(0.1, min(10.0, z * 1.2)), no_update, fit_seq or 0

        if tid == "btn_zoom_out":
            try:
                z = float(current_zoom or 1.0)
            except Exception:
                z = 1.0
            return max(0.1, min(10.0, z / 1.2)), no_update, fit_seq or 0

        if tid == "btn_fit":
            seq = (fit_seq or 0) + 1
            pad = 30 + (0.01 if (seq % 2) == 1 else 0.0)
            return no_update, {"name": "preset", "fit": True, "padding": pad}, seq

        return no_update, no_update, fit_seq or 0

    # clientside: set busy flag when 'Visualise' is clicked
    dash_app.clientside_callback(
        ClientsideFunction(namespace="clientside", function_name="setBusyOnExplore"),
        Output("busy", "data"),
        Input("explore", "n_clicks"),
        prevent_initial_call=True
    )

    # clientside: double-tap a node to append it as a seed word (no duplicates)
    dash_app.clientside_callback(
        ClientsideFunction(namespace="clientside", function_name="addSeedOnDoubleTap"),
        Output("seeds", "value"),
        Input("cy", "tapNodeData"),
        State("seeds", "value"),
    )

    @dash_app.callback(
        Output("explore", "disabled"),
        Output("loading_status", "children"),
        Input("busy", "data"),
    )
    def show_busy(busy):
        if busy:
            spinner = dbc.Spinner(
                size="sm",
                color="secondary",
                fullscreen=False,
                spinner_style={"marginRight": "6px"}
            )
            return True, html.Span([spinner, "Building network…"])
        return False, ""

    log.info("Dash app created successfully at /advanced/")
    return dash_app
