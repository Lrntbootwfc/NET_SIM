"""
simulator.py
Simple multithreaded simulation:
- Each device is a thread
- A central broker (in-memory) relays metadata messages
- Simulates Day-1: ARP broadcast and OSPF hello (conceptually)
- Supports link failure toggling
"""

import threading
import time
from queue import Queue, Empty
from .logger import get_logger
import networkx as nx

log = get_logger("simulator")
BROKER_QUEUE = Queue()
STOP_EVENT = threading.Event()

class DeviceThread(threading.Thread):
    def __init__(self, name, graph, inbox: Queue):
        super().__init__(daemon=True)
        self.name = name
        self.graph = graph
        self.inbox = inbox
        self.running = True

    def run(self):
        log.info(f"[Sim] Device {self.name} started")
        # initial boot: send ARP/HELLO to neighbors
        neighbors = list(self.graph.neighbors(self.name))
        for n in neighbors:
            msg = {"type": "HELLO", "src": self.name, "dst": n, "time": time.time()}
            BROKER_QUEUE.put(msg)
            log.info(f"[{self.name}] sent HELLO to {n}")
        # event loop
        while self.running and not STOP_EVENT.is_set():
            try:
                msg = self.inbox.get(timeout=0.5)
            except Empty:
                time.sleep(0.1)
                continue
            # process msg
            if msg["type"] == "HELLO":
                log.info(f"[{self.name}] Received HELLO from {msg['src']}")
            elif msg["type"] == "ARP":
                if msg["dst"] == self.name:
                    r = {"type": "ARP_REPLY", "src": self.name, "dst": msg["src"], "time": time.time()}
                    BROKER_QUEUE.put(r)
            time.sleep(0.01)

    def stop(self):
        self.running = False
        log.info(f"[Sim] Device {self.name} stopped")

def broker_dispatch(graph, inbox_map):
    """Dispatch messages from BROKER_QUEUE to appropriate device inboxes."""
    while not STOP_EVENT.is_set():
        try:
            msg = BROKER_QUEUE.get(timeout=0.5)
        except Empty:
            continue
        dst = msg.get("dst")
        if dst in inbox_map:
            inbox_map[dst].put(msg)
        else:
            # broadcast or unknown
            if dst is None:
                src = msg.get("src")
                for n in graph.neighbors(src):
                    inbox_map[n].put(msg)
        time.sleep(0.01)

def run_day1_simulation(G, duration=5):
    """
    Runs the Day-1 simulation for given duration (seconds).
    """
    STOP_EVENT.clear()
    inbox_map = {node: Queue() for node in G.nodes()}
    threads = {}

    for node in G.nodes():
        t = DeviceThread(node, G, inbox_map[node])
        t.start()
        threads[node] = t

    broker = threading.Thread(target=broker_dispatch, args=(G, inbox_map), daemon=True)
    broker.start()

    log.info("Simulation started for Day-1")
    time.sleep(duration)
    STOP_EVENT.set()

    for t in threads.values():
        t.stop()
    log.info("Simulation ended")

def _simulate_link_failure(G, link_key: str):
    try:
        a, b = link_key.split("-")
    except Exception:
        log.error("Invalid link format. Use format like 'R1-R2'.")
        return
    if G.has_edge(a, b):
        G[a][b]["up"] = False
        log.warning(f"Link {a}-{b} brought down")
        comps = list(nx.connected_components(G))
        if len(comps) > 1:
            log.warning("Network partition occurred:")
            for comp in comps:
                log.warning(f"Component: {comp}")
    else:
        log.error("No such edge")

# Public API function for link failure simulation
def simulate_link_failure(G, link_key: str):
    _simulate_link_failure(G, link_key)
