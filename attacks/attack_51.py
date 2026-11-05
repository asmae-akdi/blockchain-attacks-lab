"""Attaque des 51 % avec double spending et reorganisation de chaine.

Scenario :
  1. L'attaquant (part de hash alpha) paie un marchand : transaction `victim_tx`.
  2. Il mine EN SECRET, depuis le meme point de depart, une chaine privee qui
     contient une transaction conflictuelle (il se paie lui-meme).
  3. Le marchand livre la marchandise apres z confirmations sur la chaine publique.
  4. Des que sa chaine privee est strictement plus longue que la chaine publique,
     l'attaquant la publie : le reseau adopte la plus longue (reorganisation),
     `victim_tx` disparait : le marchand a perdu la marchandise ET le paiement.
  5. Il abandonne si son retard depasse `max_deficit` blocs (ou apres `timeout`).
"""
from dataclasses import dataclass

from core.block import Transaction, BLOCK_REWARD
from core.mining import make_stat_block
from defense.protected_chain import protect          # [6.2]
from sim.node import Node
from sim.simulation import SimConfig, run_simulation


@dataclass
class DoubleSpendContext:
    z: int                       # confirmations exigees par le marchand
    amount: float                # montant double-depense
    max_deficit: int
    timeout: float               # duree max de l'attaque (s)
    settle: float                # delai d'observation apres publication (s)
    victim_tx: Transaction = None
    conflict_tx: Transaction = None
    attacker: object = None
    merchant: object = None
    sim: object = None
    t_start: float = None
    t_delivery: float = None
    t_publish: float = None
    t_end: float = None
    outcome: str = None          # success | published_failed | gave_up | timeout
    on_finish: object = None     # callback (mode flux) ; sinon la simulation s'arrete

    def finish(self, outcome: str) -> None:
        if self.outcome is None:
            self.outcome = outcome
            self.t_end = self.sim.now
            if self.on_finish:
                self.on_finish(self)
            else:
                self.sim.stop()


class Merchant(Node):
    """Noeud honnete qui livre la marchandise apres z confirmations."""

    def __init__(self, *args, ctx: DoubleSpendContext = None):
        super().__init__(*args)
        self.ctx = ctx
        ctx.merchant = self

    def _watch(self) -> None:
        c = self.ctx
        if (c.t_start is not None and c.t_delivery is None
                and self.chain.confirmations(c.victim_tx.tx_id) >= c.z):
            c.t_delivery = self.sim.now           # marchandise livree
            if c.attacker is not None:
                c.attacker.evaluate()

    def on_block_mined(self, block) -> None:
        super().on_block_mined(block)
        self._watch()

    def on_block_received(self, block, result) -> None:
        super().on_block_received(block, result)
        self._watch()


class Attacker51(Node):
    honest = False

    def __init__(self, *args, ctx: DoubleSpendContext = None):
        super().__init__(*args)
        self.ctx = ctx
        ctx.attacker = self
        self.mode = "honest"            # honest -> attacking -> done
        self.private: list = []
        self.private_tip = None
        self.fork_base = None

    # ---- demarrage de l'attaque ----
    def launch(self) -> None:
        c = self.ctx
        c.t_start = self.sim.now
        self.mode = "attacking"
        self.fork_base = self.chain.tip_block
        self.private_tip = self.fork_base
        self.private = []
        self.net.mempool.append(c.victim_tx)      # le paiement part vers le reseau
        self.restart_mining()                      # tout le hash sert la chaine privee

    # ---- minage prive ----
    def create_block(self):
        if self.mode != "attacking":
            return super().create_block()
        txs = [self.ctx.conflict_tx] if not self.private else []
        return make_stat_block(self.private_tip, self.name, self.sim.now, self.rng, txs)

    def on_block_mined(self, block) -> None:
        if self.mode != "attacking":
            return super().on_block_mined(block)
        self.private.append(block)                 # bloc garde SECRET
        self.private_tip = block
        self.restart_mining()
        self.evaluate()

    def on_block_received(self, block, result) -> None:
        if self.mode != "attacking":
            return super().on_block_received(block, result)
        self.evaluate()                            # ne mine pas sur la chaine publique

    # ---- decision ----
    def evaluate(self) -> None:
        if self.mode != "attacking":
            return
        c = self.ctx
        public_h, private_h = self.chain.height, self.private_tip.index
        if c.t_delivery is not None and private_h > public_h:
            self._publish()
        elif (public_h - private_h >= c.max_deficit
              or self.sim.now - c.t_start > c.timeout):
            self.mode = "done"
            c.finish("gave_up")

    def _publish(self) -> None:
        c = self.ctx
        self.mode = "done"
        c.t_publish = self.sim.now
        for b in self.private:
            self.chain.add_block(b, self.sim.now)
        for b in self.private:
            self.net.publish(self, b)
        self.net.invalid_txs.add(c.victim_tx.tx_id)   # la depense conflictuelle invalide le paiement
        self.restart_mining()
        self.sim.schedule(c.settle, self._settle)

    def _settle(self) -> None:
        c = self.ctx
        lost = c.merchant.chain.confirmations(c.victim_tx.tx_id) == 0
        c.finish("success" if lost else "published_failed")


def run_double_spend(alpha: float, z: int, seed: int = 0, n_nodes: int = 10,
                     block_interval: float = 60.0, latency_mean: float = 2.0,
                     loss_prob: float = 0.0, amount: float = 1000.0,
                     warmup_blocks: int = 10, max_deficit: int = 30,
                     timeout_blocks: int = 600, settle_blocks: float = 3.0,
                     return_result: bool = False,
                     defense: dict | None = None):          # [6.2]
    """Un essai complet. Noeud 0 = attaquant, noeud 1 = marchand,
    les autres = mineurs honnetes. Retourne un dictionnaire de resultats."""
    T = block_interval
    ctx = DoubleSpendContext(
        z=z, amount=amount, max_deficit=max_deficit,
        timeout=timeout_blocks * T, settle=settle_blocks * T,
        victim_tx=Transaction("attacker_wallet", "merchant_wallet", amount, 1),
        conflict_tx=Transaction("attacker_wallet", "attacker_wallet2", amount, 1))

    shares = [alpha] + [(1 - alpha) / (n_nodes - 1)] * (n_nodes - 1)
    cfg = SimConfig(n_nodes=n_nodes, hash_shares=shares, block_interval=T,
                    duration=(warmup_blocks + timeout_blocks + 30) * T,
                    latency_mean=latency_mean, loss_prob=loss_prob, seed=seed)

    special = {0: lambda *a: Attacker51(*a, ctx=ctx),
               1: lambda *a: Merchant(*a, ctx=ctx)}

    def setup(result):
        ctx.sim = result.sim
        if defense:                                          # [6.2]
            protect(result.nodes, seed=seed, **defense)      # [6.2]
        result.sim.schedule(warmup_blocks * T, result.nodes[0].launch)

    result = run_simulation(cfg, special, setup)
    if ctx.outcome is None:
        ctx.t_end = result.sim.now
        ctx.outcome = "timeout"

    atk, mer = ctx.attacker, ctx.merchant
    fork_h = atk.fork_base.index
    final = mer.chain.main_chain()
    atk_final = sum(1 for b in final if b.miner == atk.name and b.index > fork_h)
    honest_orphans = sum(1 for b in mer.chain.stale_blocks()
                         if b.miner != atk.name and b.index > fork_h)
    reorg_depth = max((r["depth"] for r in mer.chain.reorgs
                       if ctx.t_publish is not None and r["time"] >= ctx.t_publish),
                      default=0)
    success = ctx.outcome == "success"
    duration = ctx.t_end - ctx.t_start
    forgone = alpha * duration / T                   # blocs gagnes en minant honnetement
    out = {
        "alpha": alpha, "z": z, "seed": seed,
        "outcome": ctx.outcome, "success": int(success),
        "delivered": int(ctx.t_delivery is not None),
        "time_to_delivery": (ctx.t_delivery - ctx.t_start) if ctx.t_delivery else None,
        "attack_duration": duration,
        "private_blocks": len(atk.private),
        "reorg_depth": reorg_depth if success else 0,
        "merchant_loss": amount if success else 0.0,
        "honest_blocks_orphaned": honest_orphans if success else 0,
        "attacker_profit": (amount if success else 0.0)
                           + BLOCK_REWARD * (atk_final - forgone),
        "t_start": ctx.t_start, "t_publish": ctx.t_publish,
        "rejected_reorgs": len(getattr(mer.chain, "rejected_reorgs", [])),   # [6.2]
    }
    return (out, result, ctx) if return_result else out


def run_attack51_stream(alpha: float, z: int = 1, seed: int = 0, n_nodes: int = 10,
                        block_interval: float = 60.0, latency_mean: float = 2.0,
                        loss_prob: float = 0.0, n_blocks: int = 1500,
                        start_block: int = 500, cooldown_blocks: int = 5,
                        amount: float = 1000.0, max_deficit: int = 8,
                        timeout_blocks: int = 80, settle_blocks: float = 3.0):
    """Attaquant PERSISTANT : a partir de `start_block`, il enchaine les tentatives
    de double spending. Sert a produire des donnees pour la detection.
    Retourne (result, episodes) ; chaque episode a t_start, t_publish, t_end, outcome."""
    T = block_interval
    episodes, holder, counter = [], {}, [0]

    def make_ctx():
        counter[0] += 1
        k = counter[0]
        return DoubleSpendContext(
            z=z, amount=amount, max_deficit=max_deficit, timeout=timeout_blocks * T,
            settle=settle_blocks * T, on_finish=on_finish,
            victim_tx=Transaction("attacker_wallet", "merchant_wallet", amount, k),
            conflict_tx=Transaction("attacker_wallet", "attacker_wallet2", amount, k))

    def on_finish(c):
        episodes.append({"t_start": c.t_start, "t_publish": c.t_publish,
                         "t_end": c.t_end, "outcome": c.outcome})
        sim = holder["sim"]
        if sim.now + cooldown_blocks * T < holder["duration"]:
            sim.schedule(cooldown_blocks * T, relaunch)

    def relaunch():
        c = make_ctx()
        c.sim = holder["sim"]
        atk, mer = holder["atk"], holder["mer"]
        c.attacker, c.merchant = atk, mer
        atk.ctx, mer.ctx = c, c
        atk.launch()

    ctx0 = make_ctx()
    shares = [alpha] + [(1 - alpha) / (n_nodes - 1)] * (n_nodes - 1)
    cfg = SimConfig(n_nodes=n_nodes, hash_shares=shares, block_interval=T,
                    duration=n_blocks * T, latency_mean=latency_mean,
                    loss_prob=loss_prob, seed=seed)
    special = {0: lambda *a: Attacker51(*a, ctx=ctx0),
               1: lambda *a: Merchant(*a, ctx=ctx0)}

    def setup(result):
        ctx0.sim = result.sim
        holder.update(sim=result.sim, duration=cfg.duration,
                      atk=result.nodes[0], mer=result.nodes[1])
        result.sim.schedule(start_block * T, result.nodes[0].launch)

    result = run_simulation(cfg, special, setup)
    return result, episodes