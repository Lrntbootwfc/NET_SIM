"""
topology_builder.py
Builds networkx.Graph from parsed configs and explicit link file.

Graph nodes: hostname (node attribute 'parsed' contains dict)
Graph edges: explicit links from link file, or inferred by description or subnet overlap
Edge attributes: ifaces, mtu, bandwidth, up
"""

import os
import networkx as nx
from typing import Dict, List, Tuple, Optional
from .config_parser import parse_links_file
from .logger import get_logger
from . import utils

log = get_logger("topology_builder")


def build_topology(parsed_configs: Dict[str, Dict], config_dir: Optional[str] = None) -> nx.Graph:
    """
    Build a topology graph from parsed device configs,
    using explicit link file if available, otherwise heuristic inference.
    
    Args:
        parsed_configs: dict of hostname -> parsed config dict
        config_dir: directory to look for links.txt (optional)
    
    Returns:
        networkx.Graph with nodes and edges with attributes
    """
    G = nx.Graph()

    # Add nodes with parsed config as attribute
    for host, pdata in parsed_configs.items():
        G.add_node(host, parsed=pdata)
    log.info(f"Added {len(G.nodes)} device nodes")

    # Parse explicit links from links.txt if config_dir provided
    explicit_links: List[Tuple[str, str, str, str]] = []
    if config_dir:
        links_file = os.path.join(config_dir, "links.txt")
        if os.path.isfile(links_file):
            raw_links = parse_links_file(links_file)  # returns List[Tuple[str, str]]
            for ep1, ep2 in raw_links:
                try:
                    dev1, if1 = ep1.split(":")
                    dev2, if2 = ep2.split(":")
                    explicit_links.append((dev1.strip(), if1.strip(), dev2.strip(), if2.strip()))
                except Exception as e:
                    log.warning(f"Skipping malformed link entry '{ep1} - {ep2}': {e}")
            log.info(f"Parsed {len(explicit_links)} explicit links from {links_file}")
        else:
            log.warning(f"No links.txt file found at {links_file}")

    # Add edges from explicit links
    for dev1, if1, dev2, if2 in explicit_links:
        if dev1 in G.nodes and dev2 in G.nodes:
            # Get interface details for mtu and bandwidth if available
            mtu1 = parsed_configs.get(dev1, {}).get("interfaces", {}).get(if1, {}).get("mtu", 1500)
            mtu2 = parsed_configs.get(dev2, {}).get("interfaces", {}).get(if2, {}).get("mtu", 1500)
            bw1 = parsed_configs.get(dev1, {}).get("interfaces", {}).get(if1, {}).get("bandwidth", 1000)
            bw2 = parsed_configs.get(dev2, {}).get("interfaces", {}).get(if2, {}).get("bandwidth", 1000)
            mtu = min(mtu1, mtu2)
            bw = min(bw1, bw2)
            G.add_edge(
                dev1,
                dev2,
                ifaces=[f"{dev1}:{if1}", f"{dev2}:{if2}"],
                mtu=mtu,
                bandwidth=bw,
                up=True,
                source="explicit"
            )
            log.info(f"Added explicit edge {dev1}({if1}) <-> {dev2}({if2}) mtu={mtu} bw={bw}")
        else:
            log.warning(f"Explicit link skipped, unknown device(s): {dev1}, {dev2}")

    # Heuristic inference for missing edges
    hosts = list(parsed_configs.keys())
    for i in range(len(hosts)):
        for j in range(i + 1, len(hosts)):
            a, b = hosts[i], hosts[j]
            # Skip if edge already exists (explicit link)
            if G.has_edge(a, b):
                continue

            pa, pb = parsed_configs[a], parsed_configs[b]
            linked = False

            # 1) Description hint
            for ifa, ifd in pa.get("interfaces", {}).items():
                desc = ifd.get("description", "")
                if desc and b in desc:
                    mtu = min(ifd.get("mtu", 1500), 1500)
                    bw = ifd.get("bandwidth", 1000)
                    G.add_edge(a, b, ifaces=[f"{a}:{ifa}"], mtu=mtu, bandwidth=bw, up=True, source="desc_hint")
                    linked = True
                    log.info(f"Inferred edge (desc) {a} <-> {b} on iface {ifa}")
                    break
            if linked:
                continue

            # 2) Subnet overlap
            for ifa, ifd in pa.get("interfaces", {}).items():
                if "ip" not in ifd:
                    continue
                for ifb, ifdb in pb.get("interfaces", {}).items():
                    if "ip" not in ifdb:
                        continue
                    try:
                        if utils.is_same_subnet(ifd["ip"], ifd["mask"], ifdb["ip"], ifdb["mask"]):
                            mtu = min(ifd.get("mtu", 1500), ifdb.get("mtu", 1500))
                            bw = min(ifd.get("bandwidth", 1000), ifdb.get("bandwidth", 1000))
                            G.add_edge(a, b, ifaces=[f"{a}:{ifa}", f"{b}:{ifb}"], mtu=mtu, bandwidth=bw, up=True, source="subnet")
                            linked = True
                            log.info(f"Inferred edge (subnet) {a} <-> {b} on ifaces {ifa}, {ifb}")
                            break
                    except Exception as e:
                        log.warning(f"Subnet check failed for {a}:{ifa} and {b}:{ifb} - {e}")
                if linked:
                    break

    log.info(f"Final topology: nodes={G.number_of_nodes()} edges={G.number_of_edges()}")
    return G
