"""Selfish mining avec la strategie de publication d'Eyal & Sirer (2014).

Le mineur egoiste garde ses blocs secrets (chaine privee). Regle de publication,
appliquee a chaque nouveau bloc honnete recu, avec
    delta = hauteur_privee - hauteur_honnete_apres_ce_bloc :

    delta < 0   -> il est battu : il adopte la chaine publique
    delta = 0   -> egalite : il publie sa chaine privee et tente la course
    delta = 1   -> il publie TOUT : sa chaine depasse, les blocs honnetes sont orphelins
    delta >= 2  -> il publie seulement les blocs jusqu'a la hauteur honnete
                   (il garde de l'avance en reserve)

Et quand il trouve un bloc alors qu'une course est en cours (egalite), il publie
immediatement pour gagner la course.
"""
from core.mining import make_stat_block
from defense.protected_chain import protect          # [6.2]
from detection.metrics import global_chain, compute_metrics
from sim.node import Node
from sim.simulation import SimConfig, run_simulation


class SelfishMiner(Node):
    honest = False

    def __init__(self, *args, start_time: float = 0.0):
        super().__init__(*args)
        self.active = start_time <= 0          # honnete tant que l'attaque n'a pas commence
        if not self.active:
            self.sim.schedule(start_time, self.activate)
        self.private: list = []        # blocs mines depuis le dernier point commun
        self.published = 0             # nb de blocs de self.private deja publies
        self.honest_h = 0              # hauteur de la meilleure chaine honnete connue
        self.ties: list = []           # (bloc egoiste, bloc honnete) pour chaque course
        self.max_lead = 0
        self.blocks_mined = 0

    # ---------- etat ----------
    @property
    def private_tip(self):
        return self.private[-1] if self.private else self.chain.tip_block

    def _in_tie(self) -> bool:
        return bool(self.private) and self.published == len(self.private) \
            and self.private[-1].index == self.honest_h

    def activate(self) -> None:
        self.active = True
        self.private, self.published = [], 0
        self.honest_h = self.chain.height
        self.restart_mining()

    # ---------- minage ----------
    def create_block(self):
        if not self.active:
            return super().create_block()
        return make_stat_block(self.private_tip, self.name, self.sim.now, self.rng)

    def on_block_mined(self, block) -> None:
        if not self.active:
            return super().on_block_mined(block)
        self.blocks_mined += 1
        tie = self._in_tie()
        self.private.append(block)
        self.max_lead = max(self.max_lead, block.index - self.honest_h)
        if tie:                                # il gagne la course : publie tout de suite
            self._publish_upto(block.index)
            self._reset_to_public()
        else:
            self.restart_mining()

    # ---------- reception d'un bloc honnete ----------
    def on_block_received(self, block, result) -> None:
        if not self.active:
            return super().on_block_received(block, result)
        if not self.private:                   # rien de secret : comportement honnete
            self.honest_h = self.chain.height
            if result.new_tip:
                self.restart_mining()
            return
        if block.index <= self.honest_h:       # bloc de cote : sans effet
            return
        self.honest_h = block.index
        delta = self.private_tip.index - self.honest_h
        if delta < 0:
            self._reset_to_public()
        elif delta == 0:                       # course : publie et attend
            self._publish_upto(self.private_tip.index)
            self.ties.append((self.private[-1], block))
        elif delta == 1:                       # victoire : publie tout
            self._publish_upto(self.private_tip.index)
            self._reset_to_public()
        else:                                  # grosse avance : revele un bloc a la fois
            self._publish_upto(self.honest_h)

    # ---------- utilitaires ----------
    def _publish_upto(self, height: int) -> None:
        while self.published < len(self.private) and self.private[self.published].index <= height:
            b = self.private[self.published]
            self.chain.add_block(b, self.sim.now)
            self.net.publish(self, b)
            self.published += 1

    def _reset_to_public(self) -> None:
        """Abandonne (ou integre) la chaine privee et repart de la chaine publique."""
        self.private = []
        self.published = 0
        self.honest_h = self.chain.height
        self.restart_mining()


def run_selfish(alpha: float, seed: int = 0, n_nodes: int = 10,
                block_interval: float = 60.0, latency_mean: float = 2.0,
                loss_prob: float = 0.0, n_blocks: int = 3000,
                start_block: int = 0, return_result: bool = False,
                defense: dict | None = None):               # [6.2]
    """Un essai : noeud 0 = selfish miner, les autres honnetes."""
    shares = [alpha] + [(1 - alpha) / (n_nodes - 1)] * (n_nodes - 1)
    cfg = SimConfig(n_nodes=n_nodes, hash_shares=shares, block_interval=block_interval,
                    duration=n_blocks * block_interval, latency_mean=latency_mean,
                    loss_prob=loss_prob, seed=seed)
    start = start_block * block_interval

    def setup(result):                                       # [6.2]
        if defense:                                          # [6.2]
            protect(result.nodes, seed=seed, **defense)      # [6.2]

    result = run_simulation(cfg, {0: lambda *a: SelfishMiner(*a, start_time=start)},
                            setup)                           # [6.2]
    atk = result.nodes[0]
    obs = result.nodes[-1].chain                   # [6.2] chaine d'un noeud honnete
    rew = obs.rewards_by_miner()                   # [6.2]
    m = compute_metrics(result)
    g = global_chain(result.net)
    main = {b.hash for b in g.main_chain()}

    ties = len(atk.ties)
    wins = sum(1 for s, _ in atk.ties if s.hash in main)
    p_win = wins / ties if ties else float("nan")
    gamma_emp = (p_win - alpha) / (1 - alpha) if ties else float("nan")

    honest_orphans = sum(1 for b in g.stale_blocks() if b.miner != atk.name)
    out = {
        "alpha": alpha, "seed": seed, "t_start": start,
        "revenue_share": m["reward_share"]["N0"],
        "advantage": m["reward_share"]["N0"] - alpha,
        "orphan_rate": m["orphan_rate"],
        "honest_blocks_orphaned": honest_orphans,
        "selfish_blocks_orphaned": sum(1 for b in g.stale_blocks() if b.miner == atk.name),
        "height": m["height"],
        "ties": ties, "gamma_emp": gamma_emp,
        "max_reorg_depth": m["max_reorg_depth"],
        "max_private_lead": atk.max_lead,
        "prop_delay_p90": m["prop_delay_p90"],
        "consensus_agreement": m["consensus_agreement"],
        "obs_revenue_share": rew.get(atk.name, 0) / max(obs.height, 1),   # [6.2]
        "obs_orphan_rate": obs.orphan_rate(),                             # [6.2]
        "rejected_reorgs": sum(len(getattr(n.chain, "rejected_reorgs", []))
                               for n in result.nodes if n.honest),        # [6.2]
    }
    return (out, result) if return_result else out