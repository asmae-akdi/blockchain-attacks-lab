"""Etape 7.1 : analyse de sensibilite (validation scientifique).

Fait varier, UN facteur a la fois : nombre de noeuds, latence, patience de
l'attaquant (strategie adverse 51 %), strategie de publication (selfish mining).
Compare a la reference sans attaque. Parametres : experiments/configs/final.yaml.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from attacks.attack_51 import run_double_spend
from attacks.selfish import run_selfish, SelfishMiner
from attacks.selfish_variants import GreedySelfishMiner
from detection.metrics import compute_metrics
from sim.simulation import SimConfig, run_simulation

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def ci95(x):
    x = np.asarray(x, float)
    return 1.96 * x.std(ddof=1) / math.sqrt(len(x)) if len(x) > 1 else 0.0


def _kw(base, param, value):
    kw = {"n_nodes": base["n_nodes"], "latency_mean": base["latency_mean"],
          "block_interval": base["block_interval"]}
    if param != "patience":
        kw[param] = value
    return kw


def sweep_reference(cfg):
    base, n = cfg["base"], cfg["trials"]["reference"]
    rows = []
    for param in ("n_nodes", "latency_mean"):
        for v in cfg["sweeps"][param]:
            kw = _kw(base, param, v)
            ms = []
            for i in range(n):
                sc = SimConfig(n_nodes=kw["n_nodes"], block_interval=kw["block_interval"],
                               latency_mean=kw["latency_mean"], loss_prob=base["loss_prob"],
                               duration=kw["block_interval"] * 1500, seed=cfg["seed_base"] + i)
                ms.append(compute_metrics(run_simulation(sc)))
            rows.append({"sweep": param, "value": v,
                         "orphan_rate": np.mean([m["orphan_rate"] for m in ms]),
                         "prop_delay_p90": np.mean([m["prop_delay_p90"] for m in ms])})
    return pd.DataFrame(rows)


def sweep_attack51(cfg):
    base, n = cfg["base"], cfg["trials"]["attack51"]
    z, alphas = cfg["cases"]["attack51"]["z"], cfg["cases"]["attack51"]["alpha"]
    rows = []
    for param in ("n_nodes", "latency_mean", "patience"):
        for v in cfg["sweeps"][param]:
            kw = _kw(base, param, v)
            if param == "patience":
                kw["max_deficit"] = v
            for a in alphas:
                res = [run_double_spend(a, z, seed=cfg["seed_base"] + i, **kw) for i in range(n)]
                k = sum(r["success"] for r in res)
                lo, hi = wilson(k, n)
                rows.append({"sweep": param, "value": v, "alpha": a, "z": z, "n": n,
                             "success": k / n, "ci_low": lo, "ci_high": hi,
                             "mean_loss": np.mean([r["merchant_loss"] for r in res]),
                             "mean_profit": np.mean([r["attacker_profit"] for r in res]),
                             "mean_duration_blocks": np.mean([r["attack_duration"] for r in res])
                                                     / base["block_interval"]})
        print(f"  51 % : balayage '{param}' termine")
    return pd.DataFrame(rows)


def sweep_selfish(cfg):
    base, n, nb = cfg["base"], cfg["trials"]["selfish"], cfg["trials"]["selfish_blocks"]
    rows = []
    for param in ("n_nodes", "latency_mean"):
        for v in cfg["sweeps"][param]:
            kw = _kw(base, param, v)
            for a in cfg["cases"]["selfish"]["alpha"]:
                res = [run_selfish(a, seed=cfg["seed_base"] + i, n_blocks=nb,
                                   loss_prob=base["loss_prob"], **kw) for i in range(n)]
                rs = [r["revenue_share"] for r in res]
                rows.append({"sweep": param, "value": v, "alpha": a, "n": n,
                             "revenue_share": np.mean(rs), "ci95": ci95(rs),
                             "advantage": np.mean(rs) - a,
                             "orphan_rate": np.mean([r["orphan_rate"] for r in res]),
                             "gamma_emp": np.nanmean([r["gamma_emp"] for r in res])})
        print(f"  selfish : balayage '{param}' termine")
    return pd.DataFrame(rows)


def _run_selfish_class(cls, alpha, seed, base, nb):
    n_nodes = base["n_nodes"]
    shares = [alpha] + [(1 - alpha) / (n_nodes - 1)] * (n_nodes - 1)
    sc = SimConfig(n_nodes=n_nodes, hash_shares=shares, block_interval=base["block_interval"],
                   duration=nb * base["block_interval"], latency_mean=base["latency_mean"],
                   loss_prob=base["loss_prob"], seed=seed)
    m = compute_metrics(run_simulation(sc, {0: cls}))
    return m["reward_share"]["N0"], m["orphan_rate"]


def sweep_strategies(cfg):
    base, n, nb = cfg["base"], cfg["trials"]["selfish"], cfg["trials"]["selfish_blocks"]
    rows = []
    for a in cfg["cases"]["selfish"]["alpha"]:
        rows.append({"strategy": "minage honnete", "alpha": a, "revenue_share": a,
                     "ci95": 0.0, "orphan_rate": np.nan})
        for name, cls in (("Eyal-Sirer", SelfishMiner), ("gloutonne", GreedySelfishMiner)):
            out = [_run_selfish_class(cls, a, cfg["seed_base"] + i, base, nb) for i in range(n)]
            rs = [o[0] for o in out]
            rows.append({"strategy": name, "alpha": a, "revenue_share": np.mean(rs),
                         "ci95": ci95(rs), "orphan_rate": np.mean([o[1] for o in out])})
    print("  selfish : comparaison des strategies terminee")
    return pd.DataFrame(rows)


def make_figures(ref, a51, sf, strat):
    # --- 51 % ---
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    for ax, (param, lab) in zip(axes, [("n_nodes", "nombre de noeuds"),
                                       ("latency_mean", "latence moyenne (s)"),
                                       ("patience", "patience de l'attaquant (blocs de retard)")]):
        for a in sorted(a51.alpha.unique()):
            g = a51[(a51.sweep == param) & (a51.alpha == a)]
            ax.errorbar(g.value, g.success, yerr=[g.success - g.ci_low, g.ci_high - g.success],
                        fmt="o-", capsize=3, label=f"alpha={a}")
        ax.set_xlabel(lab); ax.set_ylabel("taux de reussite"); ax.set_ylim(0, 1)
        ax.grid(alpha=.3); ax.legend()
    fig.suptitle("Attaque 51 % : sensibilite (z=2)")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "sensitivity_attack51.png"), dpi=150)

    # --- selfish ---
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    for ax, (param, lab) in zip(axes[:2], [("n_nodes", "nombre de noeuds"),
                                           ("latency_mean", "latence moyenne (s)")]):
        for a in sorted(sf.alpha.unique()):
            g = sf[(sf.sweep == param) & (sf.alpha == a)]
            ax.errorbar(g.value, g.advantage, yerr=g.ci95, fmt="o-", capsize=3, label=f"alpha={a}")
        ax.axhline(0, color="k", lw=.8)
        ax.set_xlabel(lab); ax.set_ylabel("gain vs minage honnete (part de recompenses)")
        ax.grid(alpha=.3); ax.legend()
    ax = axes[2]
    alphas = sorted(strat.alpha.unique())
    x = np.arange(len(alphas))
    for i, s in enumerate(["minage honnete", "Eyal-Sirer", "gloutonne"]):
        g = strat[strat.strategy == s].sort_values("alpha")
        ax.bar(x + (i - 1) * .27, g.revenue_share, .27, yerr=g.ci95, capsize=3, label=s)
    ax.set_xticks(x); ax.set_xticklabels([f"alpha={a}" for a in alphas])
    ax.set_ylabel("part des recompenses"); ax.grid(axis="y", alpha=.3); ax.legend()
    ax.set_title("Strategies de publication")
    fig.suptitle("Selfish mining : sensibilite")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "sensitivity_selfish.png"), dpi=150)


def run(cfg):
    os.makedirs(OUT, exist_ok=True)
    print("Reference...")
    ref = sweep_reference(cfg)
    print("Attaque 51 %...")
    a51 = sweep_attack51(cfg)
    print("Selfish mining...")
    sf = sweep_selfish(cfg)
    strat = sweep_strategies(cfg)
    ref.to_csv(os.path.join(OUT, "sensitivity_reference.csv"), index=False)
    a51.to_csv(os.path.join(OUT, "sensitivity_attack51.csv"), index=False)
    sf.to_csv(os.path.join(OUT, "sensitivity_selfish.csv"), index=False)
    strat.to_csv(os.path.join(OUT, "sensitivity_strategies.csv"), index=False)
    make_figures(ref, a51, sf, strat)
    for name, df in [("REFERENCE", ref), ("ATTAQUE 51 %", a51), ("SELFISH MINING", sf),
                     ("STRATEGIES", strat)]:
        print(f"\n=== {name} ===\n{df.round(3).to_string(index=False)}")
    return ref, a51, sf, strat


if __name__ == "__main__":
    import yaml
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "configs", "final.yaml")
    run(yaml.safe_load(open(path, encoding="utf-8")))
