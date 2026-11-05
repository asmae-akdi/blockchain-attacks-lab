import numpy as np

from attacks.attack_51 import run_attack51_stream
from detection.dataset import make_run
from detection.detectors import AdaptiveRuleDetector, StaticDetector, WARMUP
from detection.features import extract_features, FEATURES
from sim.simulation import SimConfig, run_simulation


def test_features_shape_and_causality():
    res = run_simulation(SimConfig(n_nodes=10, block_interval=60, duration=60 * 400, seed=1))
    df = extract_features(res)
    assert list(df[FEATURES].columns) == FEATURES
    assert len(df) > 50 and df.notna().all().all()
    assert abs(df.growth.mean() - 1.0) < 0.15          # ~1 bloc par intervalle


def test_stream_attack_produces_several_episodes():
    res, eps = run_attack51_stream(0.45, z=1, seed=3, n_blocks=1200, start_block=300)
    assert len(eps) >= 3 and any(e["t_publish"] for e in eps)


def test_labels_selfish_and_51():
    r = make_run("selfish", "standard", 11, alpha=0.4, n_blocks=900, start_block=400)
    assert set(np.unique(r["labels"])) <= {-1, 0, 1} and (r["labels"] == 1).any()
    r2 = make_run("attack51", "standard", 12, alpha=0.51, z=1, n_blocks=900, start_block=300)
    assert (r2["labels"] == 1).any() and (r2["labels"] == 0).any()


def test_adaptive_detector_quiet_on_honest_and_alarms_on_selfish():
    ok = make_run("normal", "standard", 21, n_blocks=900)
    sf = make_run("selfish", "standard", 22, alpha=0.45, n_blocks=900, start_block=400)
    det = AdaptiveRuleDetector()
    far = det.run(ok["df"])[WARMUP:].mean()
    pos = det.run(sf["df"])[sf["labels"] == 1]
    assert far < 0.10 and pos.mean() > 0.5


def test_static_detector_returns_boolean_per_window():
    ok = make_run("normal", "standard", 31, n_blocks=500)
    assert StaticDetector().run(ok["df"]).dtype == bool
