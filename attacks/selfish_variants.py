"""Variante de strategie de publication du selfish mining, pour comparer
plusieurs STRATEGIES ADVERSES (sans toucher a attacks/selfish.py)."""
from attacks.selfish import SelfishMiner


class GreedySelfishMiner(SelfishMiner):
    """Strategie 'gloutonne' : des qu'il a au moins 2 blocs d'avance, il publie
    TOUT immediatement (pas de reserve), au lieu de reveler un bloc a la fois
    comme dans la strategie d'Eyal & Sirer."""

    def on_block_received(self, block, result) -> None:
        if self.active and self.private and block.index > self.honest_h:
            delta = self.private_tip.index - block.index
            if delta >= 2:
                self.honest_h = block.index
                self._publish_upto(self.private_tip.index)
                self._reset_to_public()
                return
        super().on_block_received(block, result)
