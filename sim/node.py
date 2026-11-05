"""Noeud honnete : mine sur sa chaine la plus longue et publie immediatement.

Les attaquants (etapes 3 et 4) heriteront de cette classe et redefiniront
`on_block_mined` et `on_block_received`.
"""
import random

from core.blockchain import Blockchain
from core.mining import sample_mining_time, make_stat_block


class Node:
    honest = True

    def __init__(self, name: str, hash_share: float, sim, net,
                 rng: random.Random, block_interval: float):
        self.name = name
        self.hash_share = hash_share
        self.sim = sim
        self.net = net
        self.rng = rng
        self.block_interval = block_interval
        self.chain = Blockchain()
        self._token = 0            # invalide les evenements de minage perimes
        self._requested: set = set()

    # ---------- minage ----------
    def start(self) -> None:
        self.restart_mining()

    def restart_mining(self) -> None:
        """(Re)lance le minage sur le tip courant. Grace a la propriete sans
        memoire de la loi exponentielle, retirer un nouveau temps est exact."""
        if self.hash_share <= 0:
            return
        self._token += 1
        dt = sample_mining_time(self.hash_share, self.block_interval, self.rng)
        self.sim.schedule(dt, self._mining_fired, self._token)

    def _mining_fired(self, token: int) -> None:
        if token != self._token:
            return                 # le tip a change entre-temps
        block = self.create_block()
        self.on_block_mined(block)

    def create_block(self):
        txs = [t for t in self.net.mempool
               if t.tx_id not in self.net.invalid_txs
               and self.chain.confirmations(t.tx_id) == 0]
        return make_stat_block(self.chain.tip_block, self.name, self.sim.now,
                               self.rng, txs)

    # ---------- comportement (redefinissable par les attaquants) ----------
    def on_block_mined(self, block) -> None:
        self.chain.add_block(block, self.sim.now)
        self.net.publish(self, block)
        self.restart_mining()

    def on_block_received(self, block, result) -> None:
        if result.new_tip:
            self.restart_mining()

    # ---------- reception ----------
    def receive(self, block, sender_name: str) -> None:
        result = self.chain.add_block(block, self.sim.now)
        if result.status == "pending" and block.prev_hash not in self._requested:
            self._requested.add(block.prev_hash)
            self.net.request_block(self, sender_name, block.prev_hash)
        self.on_block_received(block, result)
