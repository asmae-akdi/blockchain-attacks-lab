"""Reseau P2P simule (graphe complet) avec latence aleatoire et perte de messages.

Chaque bloc publie est journalise avec ses heures d'arrivee sur chaque noeud :
ces journaux servent a mesurer les delais de propagation.
"""
import random


class Network:
    def __init__(self, sim, rng: random.Random, latency_mean: float = 2.0,
                 latency_min: float = 0.05, loss_prob: float = 0.0):
        self.sim = sim
        self.rng = rng
        self.latency_mean = latency_mean
        self.latency_min = latency_min
        self.loss_prob = loss_prob
        self.nodes: dict = {}
        self.mempool: list = []          # transactions en attente
        self.invalid_txs: set = set()    # transactions invalidees (conflit de depense)
        # hash -> {"block", "time", "miner", "arrivals": {noeud: temps}}
        self.published: dict = {}

    def add_node(self, node) -> None:
        self.nodes[node.name] = node

    def delay(self) -> float:
        return self.latency_min + self.rng.expovariate(1.0 / self.latency_mean)

    def publish(self, sender, block) -> None:
        """Diffuse un bloc a tous les autres noeuds."""
        if block.hash in self.published:
            return
        self.published[block.hash] = {
            "block": block, "time": self.sim.now, "miner": sender.name,
            "arrivals": {sender.name: self.sim.now},
        }
        for node in self.nodes.values():
            if node is sender:
                continue
            if self.rng.random() < self.loss_prob:
                continue                      # message perdu
            self.sim.schedule(self.delay(), self._deliver, node, block, sender.name)

    def _deliver(self, node, block, sender_name: str) -> None:
        rec = self.published.get(block.hash)
        if rec is not None:
            rec["arrivals"].setdefault(node.name, self.sim.now)
        node.receive(block, sender_name)

    def request_block(self, requester, peer_name: str, block_hash: str) -> None:
        """Demande d'un bloc manquant (parent) a un pair : aller-retour."""
        peer = self.nodes.get(peer_name)
        block = peer.chain.blocks.get(block_hash) if peer else None
        if block is None:
            return
        self.sim.schedule(self.delay() + self.delay(),
                          self._deliver, requester, block, peer_name)
