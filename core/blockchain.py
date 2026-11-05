"""Blockchain sous forme d'ARBRE de blocs (necessaire pour les forks).

Regle de choix : chaine la plus longue ; en cas d'egalite, le premier bloc
recu est conserve (first-seen), comme dans Bitcoin.
"""
from collections import defaultdict
from dataclasses import dataclass

from core.block import Block, Transaction, COINBASE


def make_genesis() -> Block:
    tx = Transaction(COINBASE, "GENESIS", 0.0)
    return Block(index=0, prev_hash="0", transactions=(tx,), miner="genesis",
                 difficulty=0, timestamp=0.0, nonce=0)


@dataclass
class AddResult:
    status: str            # accepted | duplicate | invalid | pending
    new_tip: bool = False
    reorg_depth: int = 0   # nb de blocs retires de l'ancienne chaine principale


class Blockchain:
    def __init__(self):
        g = make_genesis()
        self.genesis = g
        self.blocks: dict[str, Block] = {g.hash: g}
        self.tip: str = g.hash
        self.pending: dict[str, list[Block]] = defaultdict(list)  # parent -> blocs
        self.reorgs: list[dict] = []     # historique des reorganisations
        self._cache_tip = None
        self._cache_chain: list[Block] = []

    # ---------- ajout de blocs ----------
    def add_block(self, block: Block, now: float = 0.0) -> AddResult:
        if block.hash in self.blocks:
            return AddResult("duplicate")
        if block.hash != block.compute_hash() or not block.meets_target():
            return AddResult("invalid")
        if block.prev_hash not in self.blocks:
            self.pending[block.prev_hash].append(block)
            return AddResult("pending")
        parent = self.blocks[block.prev_hash]
        if block.index != parent.index + 1:
            return AddResult("invalid")

        res = AddResult("accepted")
        queue = [block]
        while queue:                       # traite aussi les blocs en attente
            b = queue.pop()
            if b.hash in self.blocks:
                continue
            tip_changed, depth = self._insert(b, now)
            if b is block:
                res.new_tip, res.reorg_depth = tip_changed, depth
            else:
                res.new_tip |= tip_changed
                res.reorg_depth = max(res.reorg_depth, depth)
            queue.extend(self.pending.pop(b.hash, []))
        return res

    def _insert(self, b: Block, now: float):
        self.blocks[b.hash] = b
        old_tip = self.tip
        if b.index > self.blocks[old_tip].index:
            self.tip = b.hash
            anc = self._common_ancestor(old_tip, b.hash)
            depth = self.blocks[old_tip].index - self.blocks[anc].index
            if depth > 0:
                self.reorgs.append({"time": now, "depth": depth,
                                    "new_tip": b.hash, "old_tip": old_tip})
            return True, depth
        return False, 0

    def _common_ancestor(self, h1: str, h2: str) -> str:
        a, b = self.blocks[h1], self.blocks[h2]
        while a.hash != b.hash:
            if a.index >= b.index:
                a = self.blocks[a.prev_hash]
            else:
                b = self.blocks[b.prev_hash]
        return a.hash

    # ---------- lecture ----------
    @property
    def tip_block(self) -> Block:
        return self.blocks[self.tip]

    @property
    def height(self) -> int:
        return self.tip_block.index

    def main_chain(self) -> list[Block]:
        """Chaine principale, du genesis au tip."""
        if self._cache_tip == self.tip:
            return self._cache_chain
        chain, b = [], self.tip_block
        while True:
            chain.append(b)
            if b.index == 0:
                break
            b = self.blocks[b.prev_hash]
        chain.reverse()
        self._cache_tip, self._cache_chain = self.tip, chain
        return chain

    def stale_blocks(self) -> list[Block]:
        """Blocs orphelins (hors chaine principale), genesis exclu."""
        main = {b.hash for b in self.main_chain()}
        return [b for b in self.blocks.values() if b.hash not in main]

    def orphan_rate(self) -> float:
        total = len(self.blocks) - 1
        return len(self.stale_blocks()) / total if total > 0 else 0.0

    def confirmations(self, tx_id: str) -> int:
        """Nb de confirmations d'une transaction sur la chaine principale
        (0 si elle n'y figure pas)."""
        h = self.height
        for b in self.main_chain():
            if any(t.tx_id == tx_id for t in b.transactions):
                return h - b.index + 1
        return 0

    def balances(self) -> dict[str, float]:
        bal: dict[str, float] = defaultdict(float)
        for b in self.main_chain():
            for t in b.transactions:
                if t.sender != COINBASE:
                    bal[t.sender] -= t.amount
                bal[t.receiver] += t.amount
        return dict(bal)

    def rewards_by_miner(self) -> dict[str, int]:
        """Nombre de blocs de la chaine principale par mineur."""
        out: dict[str, int] = defaultdict(int)
        for b in self.main_chain()[1:]:
            out[b.miner] += 1
        return dict(out)

    # ---------- integrite (port de verifierIntegrite) ----------
    def verify_integrity(self) -> bool:
        chain = self.main_chain()
        for i, b in enumerate(chain):
            if b.hash != b.compute_hash() or not b.meets_target():
                return False
            if b.merkle != Block(b.index, b.prev_hash, b.transactions, b.miner,
                                 b.difficulty, b.timestamp, b.nonce).merkle:
                return False
            if i > 0 and (b.prev_hash != chain[i - 1].hash
                          or b.index != chain[i - 1].index + 1):
                return False
        return True
