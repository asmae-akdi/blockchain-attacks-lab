"""Blockchain PROTEGEE (Etape 6) : contre-mesures au niveau du consensus.

Herite de Blockchain sans la modifier (core/ reste intact) et redefinit _insert.
Deux defenses, independantes et combinables :
  - garde anti-reorg : un bloc qui obligerait a retirer plus de `max_reorg_depth`
    blocs de la chaine principale est STOCKE mais n'est pas adopte (contre 51 %).
  - choix aleatoire : a hauteur egale, on bascule vers le bloc concurrent avec une
    probabilite 1/2 au lieu de garder le premier recu (contre selfish mining).
"""
import random

from core.blockchain import Blockchain


class ProtectedBlockchain(Blockchain):
    def __init__(self, max_reorg_depth=None, tiebreak="first_seen", rng=None):
        super().__init__()
        assert tiebreak in ("first_seen", "random")
        self.max_reorg_depth = max_reorg_depth      # None = pas de garde
        self.tiebreak = tiebreak
        self.rng = rng or random.Random(0)
        self.rejected_reorgs: list[dict] = []       # reorgs refusees par la garde
        self.coin_flips = 0                         # nb de departages aleatoires

    def _insert(self, b, now: float):
        self.blocks[b.hash] = b
        old_tip = self.tip
        old_h = self.blocks[old_tip].index

        if b.index > old_h:
            switch = True
        elif b.index == old_h and self.tiebreak == "random":
            self.coin_flips += 1
            switch = self.rng.random() < 0.5
        else:
            switch = False
        if not switch:
            return False, 0

        anc = self._common_ancestor(old_tip, b.hash)
        depth = old_h - self.blocks[anc].index
        if self.max_reorg_depth is not None and depth > self.max_reorg_depth:
            self.rejected_reorgs.append({"time": now, "depth": depth,
                                         "new_tip": b.hash, "old_tip": old_tip})
            return False, 0                          # bloc garde, tip inchange

        self.tip = b.hash
        if depth > 0:
            self.reorgs.append({"time": now, "depth": depth,
                                "new_tip": b.hash, "old_tip": old_tip})
        return True, depth


def protect(nodes, max_reorg_depth=None, tiebreak="first_seen", seed=0) -> int:
    """Remplace la chaine des noeuds HONNETES par une ProtectedBlockchain.
    A appeler au demarrage (chaine = genesis seul). Retourne le nb de noeuds protege."""
    done = 0
    for n in nodes:
        if not n.honest:
            continue
        if n.chain.height != 0:
            raise RuntimeError("protect() doit etre appele avant le premier bloc")
        n.chain = ProtectedBlockchain(max_reorg_depth, tiebreak,
                                      random.Random(f"{seed}-{n.name}"))
        done += 1
    return done