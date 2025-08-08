# visualizer.py
"""
visualizer.py
Offers ASCII and PNG visualizations via networkx + matplotlib.
"""

import networkx as nx
import matplotlib.pyplot as plt
import os
from .logger import get_logger

log = get_logger("visualizer")
os.makedirs("output", exist_ok=True)


def draw_topology(G, path="output/topology.png"):
    plt.figure(figsize=(8, 6))
    pos = nx.spring_layout(G, seed=42)
    # node coloring: red if degree==1
    node_colors = ["red" if G.degree(n) == 1 else "green" for n in G.nodes()]
    nx.draw(G, pos, with_labels=True, node_color=node_colors, node_size=800)
    # annotate edge labels
    edge_labels = {}
    for u, v, a in G.edges(data=True):
        bw = a.get("bandwidth", "")
        up = a.get("up", True)
        label = f"{bw}Mb/s" + ("" if up else " (down)")
        edge_labels[(u, v)] = label
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_color='blue')
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
    log.info(f"Saved topology image to {path}")


def ascii_topology(G):
    s = []
    for n in G.nodes():
        s.append(f"{n} -> {list(G.neighbors(n))}")
    return "\n".join(s)
