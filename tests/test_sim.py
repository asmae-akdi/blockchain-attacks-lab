from sim.simulation import SimConfig, run_simulation
from detection.metrics import compute_metrics


def run(**kw):
    cfg = SimConfig(**{"n_nodes": 10, "block_interval": 60,
                       "duration": 60 * 1500, "latency_mean": 2.0, "seed": 1, **kw})
    return run_simulation(cfg), cfg


def test_reproducible_with_same_seed():
    m1 = compute_metrics(run()[0])
    m2 = compute_metrics(run()[0])
    assert m1 == m2


def test_block_interval_close_to_target():
    m = compute_metrics(run()[0])
    assert abs(m["mean_block_interval"] - 60) / 60 < 0.1


def test_rewards_proportional_to_hashrate():
    res, cfg = run(hash_shares=[40, 20, 10, 10, 5, 5, 4, 3, 2, 1], duration=60 * 4000)
    m = compute_metrics(res)
    assert abs(m["reward_share"]["N0"] - 0.40) < 0.05


def test_orphans_increase_with_latency():
    low = compute_metrics(run(latency_mean=0.5)[0])["orphan_rate"]
    high = compute_metrics(run(latency_mean=15)[0])["orphan_rate"]
    assert high > low


def test_nodes_converge_and_chain_valid():
    res, _ = run()
    m = compute_metrics(res)
    assert m["consensus_agreement"] >= 0.8
    assert all(n.chain.verify_integrity() for n in res.nodes)


def test_packet_loss_recovers_via_parent_requests():
    res, _ = run(loss_prob=0.2)
    m = compute_metrics(res)
    assert m["consensus_agreement"] >= 0.7
