import os

import yaml

from attacks.selfish import SelfishMiner
from attacks.selfish_variants import GreedySelfishMiner
from experiments import run_sensitivity as rs

CFG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "experiments", "configs", "final.yaml")


def test_config_has_required_sections():
    cfg = yaml.safe_load(open(CFG, encoding="utf-8"))
    for key in ("seed_base", "base", "trials", "cases", "sweeps", "detection"):
        assert key in cfg


def test_selfish_strategies_run_and_are_reproducible():
    base = {"n_nodes": 10, "block_interval": 60.0, "latency_mean": 2.0, "loss_prob": 0.0}
    a = rs._run_selfish_class(GreedySelfishMiner, 0.4, 5, base, 600)
    b = rs._run_selfish_class(GreedySelfishMiner, 0.4, 5, base, 600)
    c = rs._run_selfish_class(SelfishMiner, 0.4, 5, base, 600)
    assert a == b and 0 < a[0] < 1 and 0 < c[0] < 1


def test_tiny_attack51_sweep_has_expected_columns():
    cfg = yaml.safe_load(open(CFG, encoding="utf-8"))
    cfg["trials"]["attack51"] = 3
    cfg["cases"]["attack51"]["alpha"] = [0.4]
    cfg["sweeps"].update(n_nodes=[10], latency_mean=[2], patience=[5])
    df = rs.sweep_attack51(cfg)
    assert {"sweep", "value", "alpha", "success", "ci_low", "ci_high"} <= set(df.columns)
    assert len(df) == 3
