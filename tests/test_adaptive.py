"""Tests de la sous-etape 6.3 : confirmations adaptatives."""
import random

import numpy as np

from attacks.attack_51 import DoubleSpendContext
from attacks.selfish import SelfishMiner
from core.block import Transaction
from core.mining import make_stat_block
from defense.adaptive_confirmations import (AdaptiveMerchant, ConfirmationPolicy,
                                            OnlineAdaptiveDetector, OnlineMonitor)
from detection.dataset import make_run
from detection.detectors import AdaptiveRuleDetector
from detection.features import FEATURES, extract_features
from sim.events import Simulator
from sim.network import Network
from sim.simulation import SimConfig, run_simulation


class _AlarmStub:
    """Faux moniteur : alarme toujours active (ou jamais)."""
    def __init__(self, active: bool):
        self.active = active

    def alarm_active(self, now: float) -> bool:
        return self.active


def test_online_detector_gives_same_alarms_as_batch_detector():
    kw = dict(k=3, m=1, k_hi=8, persist=2)
    df = make_run("selfish", "standard", 41, alpha=0.45, n_blocks=900, start_block=400)["df"]
    batch = AdaptiveRuleDetector(**kw).run(df)
    online = OnlineAdaptiveDetector(**kw)
    out = np.array([online.step(x) for x in df[FEATURES].values])
    assert batch.any()                       # le test n'est pas trivial
    assert (out == batch).all()


def test_confirmation_policy_and_alarm_hold_window():
    res = run_simulation(SimConfig(n_nodes=5, block_interval=60.0, duration=600.0, seed=1))
    mon = OnlineMonitor(res, hold_blocks=10)              # maintien = 600 s
    assert mon.alarm_active(100.0) is False               # jamais d'alarme
    mon.last_alarm_t = 1000.0
    assert mon.alarm_active(1600.0) is True               # encore dans le maintien
    assert mon.alarm_active(1600.5) is False              # maintien termine

    pol = ConfirmationPolicy(z_base=2, z_alarm=6)
    assert pol.required_z(1200.0) == 2                    # pas de moniteur relie
    pol.monitor = mon
    assert pol.required_z(1200.0) == 6                    # sous alarme
    assert pol.required_z(2000.0) == 2                    # alarme eteinte
    assert ConfirmationPolicy(z_base=3).z_alarm == 3      # z_alarm absent -> z_base


def _merchant(policy):
    rng = random.Random(0)
    sim = Simulator()
    net = Network(sim, rng)
    tx = Transaction("attacker_wallet", "merchant_wallet", 1000.0, 1)
    ctx = DoubleSpendContext(z=2, amount=1000.0, max_deficit=30, timeout=1e9, settle=1.0,
                             victim_tx=tx, conflict_tx=Transaction("a", "a2", 1000.0, 1))
    ctx.sim, ctx.t_start = sim, 0.0
    m = AdaptiveMerchant("M", 0.1, sim, net, rng, 60.0, ctx=ctx, policy=policy)
    parent = m.chain.genesis
    first = make_stat_block(parent, "H", 1.0, rng, [tx])
    m.chain.add_block(first)
    return m, ctx, first, rng


def _extend(m, tip, n, rng):
    for i in range(n):
        tip = make_stat_block(tip, "H", 2.0 + i, rng)
        m.chain.add_block(tip)
    return tip


def test_adaptive_merchant_waits_longer_under_alarm():
    pol = ConfirmationPolicy(z_base=2, z_alarm=4)
    pol.monitor = _AlarmStub(True)
    m, ctx, tip, rng = _merchant(pol)
    tip = _extend(m, tip, 1, rng)                         # 2 confirmations
    m._watch()
    assert ctx.t_delivery is None                         # sous alarme : 2 ne suffit pas
    _extend(m, tip, 2, rng)                               # 4 confirmations
    m._watch()
    assert ctx.t_delivery is not None and ctx.z_at_delivery == 4


def test_adaptive_merchant_delivers_at_z_base_without_alarm():
    pol = ConfirmationPolicy(z_base=2, z_alarm=4)
    pol.monitor = _AlarmStub(False)
    m, ctx, tip, rng = _merchant(pol)
    _extend(m, tip, 1, rng)
    m._watch()
    assert ctx.t_delivery is not None and ctx.z_at_delivery == 2


def test_online_monitor_matches_batch_on_a_live_simulation():
    """Le moniteur branche dans la simulation donne les memes alarmes que la
    version par lot appliquee a la meme serie de metriques."""
    T = 60.0
    cfg = SimConfig(n_nodes=10, hash_shares=[0.45] + [0.55 / 9] * 9, block_interval=T,
                    duration=700 * T, latency_mean=2.0, seed=17)
    holder = {}

    def setup(res):
        holder["mon"] = OnlineMonitor(res)
        holder["mon"].start()

    res = run_simulation(cfg, {0: lambda *a: SelfishMiner(*a, start_time=300 * T)}, setup)
    mon = holder["mon"]
    df = extract_features(res, mon.observer, 20, 5)
    n = mon.n_seen
    assert n > 40
    batch = AdaptiveRuleDetector().run(df.iloc[:n])
    assert mon.n_alarm == int(batch.sum()) and mon.n_alarm > 0
    assert mon.alarm_times == list(df.t_end.values[:n][batch])
