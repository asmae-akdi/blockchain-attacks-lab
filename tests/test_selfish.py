from attacks.selfish import run_selfish
from attacks.theory import selfish_revenue, selfish_threshold
from sim.simulation import SimConfig, run_simulation
from detection.metrics import compute_metrics


def test_theory_threshold_values():
    assert abs(selfish_threshold(0.0) - 1 / 3) < 1e-9
    assert abs(selfish_threshold(0.5) - 0.25) < 1e-9
    assert abs(selfish_threshold(1.0) - 0.0) < 1e-9
    # au seuil, le revenu relatif egale la part de hash
    a = selfish_threshold(0.0)
    assert abs(selfish_revenue(a, 0.0) - a) < 1e-9


def test_big_selfish_miner_gains_more_than_fair_share():
    out = run_selfish(0.40, seed=1, n_blocks=3000)
    assert out["revenue_share"] > 0.40 + 0.04


def test_small_selfish_miner_loses():
    out = run_selfish(0.10, seed=1, n_blocks=3000)
    assert out["revenue_share"] < 0.10


def test_selfish_creates_more_orphans_than_honest_network():
    cfg = SimConfig(n_nodes=10, block_interval=60, duration=60 * 3000,
                    latency_mean=2.0, seed=1)
    base = compute_metrics(run_simulation(cfg))["orphan_rate"]
    atk = run_selfish(0.35, seed=1, n_blocks=3000)["orphan_rate"]
    assert atk > 3 * base


def test_network_stays_consistent_and_valid():
    out, res = run_selfish(0.30, seed=2, n_blocks=1500, return_result=True)
    assert out["consensus_agreement"] >= 0.7
    assert all(n.chain.verify_integrity() for n in res.nodes)


def test_unpublished_blocks_never_leak():
    out, res = run_selfish(0.40, seed=3, n_blocks=1000, return_result=True)
    atk = res.nodes[0]
    published = set(res.net.published)
    hidden = [b for b in atk.private[atk.published:]]
    assert all(b.hash not in published for b in hidden)


def test_reproducible():
    assert run_selfish(0.3, seed=7, n_blocks=800) == run_selfish(0.3, seed=7, n_blocks=800)
