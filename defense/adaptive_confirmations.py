"""Etape 6.3 : confirmations ADAPTATIVES declenchees par l'alarme, EN LIGNE.

- OnlineAdaptiveDetector : meme logique que AdaptiveRuleDetector, mais fenetre par
  fenetre (etat conserve), pour tourner pendant la simulation.
- OnlineMonitor : toutes les `stride_blocks` intervalles, recalcule les metriques de
  l'observateur (extract_features, causal) et alimente le detecteur.
- ConfirmationPolicy / AdaptiveMerchant : le marchand exige z_base confirmations, ou
  z_alarm tant que l'alarme est active.
- run_adaptive_stream : variante de run_attack51_stream avec cette defense.
"""
from collections import deque

from attacks.attack_51 import DoubleSpendContext, Attacker51, Merchant
from core.block import Transaction
from defense.protected_chain import protect
from detection.detectors import AdaptiveRuleDetector
from detection.features import FEATURES, extract_features
from sim.simulation import SimConfig, run_simulation


class OnlineAdaptiveDetector(AdaptiveRuleDetector):
    """Equivalent fenetre-par-fenetre de AdaptiveRuleDetector.run_with_scores."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.buf = {f: deque(maxlen=self.history) for f in self.features}
        self.i = 0
        self.streak = 0

    def step(self, x) -> bool:
        raw = alarm = False
        if self.i >= self.warmup:
            z = self._z(self.buf, x)
            raw = bool((z > self.k).sum() >= self.m or z.max() > self.k_hi)
            self.streak = self.streak + 1 if raw else 0
            alarm = self.streak >= self.persist
        if not raw:                          # reference gelee pendant l'alarme
            for f, v in zip(self.features, x):
                self.buf[f].append(v)
        self.i += 1
        return alarm


class OnlineMonitor:
    def __init__(self, result, observer=None, w_blocks=20, stride_blocks=5,
                 hold_blocks=10, **detector_kw):
        self.result = result
        self.sim = result.sim
        self.T = result.config.block_interval
        self.observer = observer or result.nodes[-1].name
        self.w, self.s = w_blocks, stride_blocks
        self.hold = hold_blocks * self.T
        self.det = OnlineAdaptiveDetector(**detector_kw)
        self.n_seen = 0              # fenetres deja traitees
        self.n_alarm = 0             # fenetres en alarme
        self.last_alarm_t = None
        self.alarm_times: list = []

    def start(self) -> None:
        self.sim.schedule(self.w * self.T, self.tick)

    def tick(self) -> None:
        df = extract_features(self.result, self.observer, self.w, self.s)
        X = df[FEATURES].values
        t_ends = df["t_end"].values
        for j in range(self.n_seen, len(df)):
            if self.det.step(X[j]):
                self.n_alarm += 1
                self.last_alarm_t = float(t_ends[j])
                self.alarm_times.append(self.last_alarm_t)
        self.n_seen = len(df)
        self.sim.schedule(self.s * self.T, self.tick)

    def alarm_active(self, now: float) -> bool:
        return self.last_alarm_t is not None and now - self.last_alarm_t <= self.hold


class ConfirmationPolicy:
    def __init__(self, z_base: int, z_alarm: int | None = None):
        self.z_base = z_base
        self.z_alarm = z_base if z_alarm is None else z_alarm
        self.monitor = None

    def required_z(self, now: float) -> int:
        if self.monitor is not None and self.monitor.alarm_active(now):
            return self.z_alarm
        return self.z_base


class AdaptiveMerchant(Merchant):
    """Comme Merchant, mais le nombre de confirmations exige depend de l'alarme."""

    def __init__(self, *args, ctx: DoubleSpendContext = None, policy=None):
        super().__init__(*args, ctx=ctx)
        self.policy = policy

    def _watch(self) -> None:
        c = self.ctx
        if c.t_start is None or c.t_delivery is not None:
            return
        need = self.policy.required_z(self.sim.now)
        if self.chain.confirmations(c.victim_tx.tx_id) >= need:
            c.t_delivery = self.sim.now
            c.z_at_delivery = need
            if c.attacker is not None:
                c.attacker.evaluate()


def run_adaptive_stream(alpha: float, z_base: int = 2, z_alarm: int | None = None,
                        seed: int = 0, n_nodes: int = 10, block_interval: float = 60.0,
                        latency_mean: float = 2.0, loss_prob: float = 0.0,
                        n_blocks: int = 900, start_block: int = 300,
                        cooldown_blocks: int = 5, amount: float = 1000.0,
                        max_deficit: int = 8, timeout_blocks: int = 80,
                        settle_blocks: float = 3.0, defense: dict | None = None,
                        monitor_kw: dict | None = None):
    """Attaquant persistant (comme run_attack51_stream) contre un marchand dont
    l'exigence de confirmations est fixe (z_alarm=None) ou adaptative.
    Retourne (episodes, monitor, result) ; monitor vaut None si z_alarm est None."""
    T = block_interval
    adaptive = z_alarm is not None
    policy = ConfirmationPolicy(z_base, z_alarm)
    episodes, holder, counter = [], {}, [0]

    def make_ctx():
        counter[0] += 1
        k = counter[0]
        return DoubleSpendContext(
            z=z_base, amount=amount, max_deficit=max_deficit,
            timeout=timeout_blocks * T, settle=settle_blocks * T, on_finish=on_finish,
            victim_tx=Transaction("attacker_wallet", "merchant_wallet", amount, k),
            conflict_tx=Transaction("attacker_wallet", "attacker_wallet2", amount, k))

    def start_episode(c):
        c.alarm_at_start = policy.required_z(holder["sim"].now) > policy.z_base
        holder["atk"].launch()

    def on_finish(c):
        episodes.append({
            "t_start": c.t_start, "t_publish": c.t_publish, "t_end": c.t_end,
            "outcome": c.outcome,
            "delivered": c.t_delivery is not None,
            "delivery_delay": ((c.t_delivery - c.t_start) / T
                               if c.t_delivery is not None else None),
            "z_at_delivery": getattr(c, "z_at_delivery", None),
            "alarm_at_start": getattr(c, "alarm_at_start", False)})
        sim = holder["sim"]
        if sim.now + cooldown_blocks * T < holder["duration"]:
            sim.schedule(cooldown_blocks * T, relaunch)

    def relaunch():
        c = make_ctx()
        c.sim = holder["sim"]
        atk, mer = holder["atk"], holder["mer"]
        c.attacker, c.merchant = atk, mer
        atk.ctx, mer.ctx = c, c
        start_episode(c)

    ctx0 = make_ctx()
    shares = [alpha] + [(1 - alpha) / (n_nodes - 1)] * (n_nodes - 1)
    cfg = SimConfig(n_nodes=n_nodes, hash_shares=shares, block_interval=T,
                    duration=n_blocks * T, latency_mean=latency_mean,
                    loss_prob=loss_prob, seed=seed)
    special = {0: lambda *a: Attacker51(*a, ctx=ctx0),
               1: lambda *a: AdaptiveMerchant(*a, ctx=ctx0, policy=policy)}
    mon_holder = {}

    def setup(result):
        ctx0.sim = result.sim
        holder.update(sim=result.sim, duration=cfg.duration,
                      atk=result.nodes[0], mer=result.nodes[1])
        if defense:
            protect(result.nodes, seed=seed, **defense)
        if adaptive:
            mon = OnlineMonitor(result, **(monitor_kw or {}))
            policy.monitor = mon
            mon_holder["m"] = mon
            mon.start()
        result.sim.schedule(start_block * T, lambda: start_episode(ctx0))

    result = run_simulation(cfg, special, setup)
    return episodes, mon_holder.get("m"), result