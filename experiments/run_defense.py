"""Etape 6.2 : blockchain de reference / attaquee / PROTEGEE.

Usage : python experiments/run_defense.py [n_essais_51] [n_graines]
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from attacks.attack_51 import run_double_spend
from attacks.selfish import run_selfish
from defense.protected_chain import protect
from sim.simulation import SimConfig, run_simulation

OUT = Path(__file__).resolve().parent / "results"
OUT.mkdir(exist_ok=True)

N_TRIALS = int(sys.argv[1]) if len(sys.argv) > 1 else 100
N_SEEDS = int(sys.argv[2]) if len(sys.argv) > 2 else 10


def eyal_sirer(a, g):
    """Part de recompenses theorique du selfish miner (Eyal & Sirer 2014)."""
    return (a * (1 - a) ** 2 * (4 * a + g * (1 - 2 * a)) - a ** 3) / \
           (1 - a * (1 + (2 - a) * a))


# ---------- A. faux refus de la garde sans aucune attaque ----------
def part_reference():
    rows = []
    for lat in (2.0, 10.0, 20.0):
        for D in (2, 3, 4):
            for s in range(N_SEEDS):
                cfg = SimConfig(n_nodes=10, block_interval=60.0, duration=1500 * 60.0,
                                latency_mean=lat, seed=s)
                res = run_simulation(
                    cfg, None,
                    lambda r, D=D, s=s: protect(r.nodes, max_reorg_depth=D, seed=s))
                honest = [n for n in res.nodes if n.honest]
                rows.append({"latency": lat, "D": D, "seed": s,
                             "rejected": sum(len(n.chain.rejected_reorgs) for n in honest)})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "defense_reference.csv", index=False)
    summ = df.groupby(["latency", "D"]).agg(
        refus_moyens=("rejected", "mean"),
        part_runs_touches=("rejected", lambda x: (x > 0).mean())).round(3)
    print("\n=== A. Faux refus de la garde (reference, sans attaque) ===")
    print(summ.to_string())


# ---------- B. 51 % + double spending ----------
def part_attack51():
    D = 4
    configs = [("sans defense", None), (f"garde D={D}", {"max_reorg_depth": D})]
    rows = []
    for alpha in (0.30, 0.40, 0.45):
        for z in (2, 6):
            for label, d in configs:
                for s in range(N_TRIALS):
                    r = run_double_spend(alpha, z, seed=s, defense=d)
                    r["config"] = label
                    rows.append(r)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "defense_attack51.csv", index=False)
    g = df.groupby(["alpha", "z", "config"]).agg(
        succes=("success", "mean"), perte_marchand=("merchant_loss", "mean"),
        profit_attaquant=("attacker_profit", "mean"),
        refus_moyens=("rejected_reorgs", "mean")).round(3)
    print(f"\n=== B. 51 % + double spending ({N_TRIALS} essais par cas) ===")
    print(g.to_string())

    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, z in zip(axes, (2, 6)):
        for label, _ in configs:
            sub = g.xs((z, label), level=("z", "config"))
            ax.plot(sub.index, sub["succes"], "o-", label=label)
        ax.set_title(f"z = {z} confirmations")
        ax.set_xlabel("part de hash de l'attaquant (alpha)")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("taux de succes du double spending")
    axes[0].legend()
    fig.tight_layout()
    fig.savefig(OUT / "defense_attack51.png", dpi=150)


# ---------- C. selfish mining ----------
def part_selfish():
    configs = [("sans defense", None),
               ("depart aleatoire", {"tiebreak": "random"}),
               ("garde D=3", {"max_reorg_depth": 3})]
    rows = []
    for alpha in (0.25, 0.30, 0.35, 0.40):
        for label, d in configs:
            for s in range(N_SEEDS):
                r = run_selfish(alpha, seed=s, defense=d)
                rows.append({"alpha": alpha, "config": label, "seed": s,
                             "share": r["obs_revenue_share"],
                             "orphan_rate": r["obs_orphan_rate"],
                             "rejected": r["rejected_reorgs"]})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "defense_selfish.csv", index=False)
    g = df.groupby(["alpha", "config"]).agg(
        part=("share", "mean"), orphelins=("orphan_rate", "mean"),
        refus_moyens=("rejected", "mean")).reset_index()
    g["gain"] = g["part"] - g["alpha"]
    g["theorie"] = [eyal_sirer(a, 0.21) if c == "sans defense"
                    else eyal_sirer(a, 0.5) if c == "depart aleatoire" else float("nan")
                    for a, c in zip(g["alpha"], g["config"])]
    print(f"\n=== C. Selfish mining ({N_SEEDS} graines par cas) ===")
    print("(theorie : gamma=0.21 sans defense, gamma=0.5 avec depart aleatoire)")
    print(g.round(3).to_string(index=False))

    fig, ax = plt.subplots(figsize=(6, 4.5))
    for label, _ in configs:
        sub = g[g["config"] == label]
        ax.plot(sub["alpha"], sub["part"], "o-", label=label)
    xs = sorted(g["alpha"].unique())
    ax.plot(xs, xs, "k--", label="part equitable")
    ax.set_xlabel("part de hash de l'attaquant (alpha)")
    ax.set_ylabel("part des recompenses")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "defense_selfish.png", dpi=150)


if __name__ == "__main__":
    part_reference()
    part_attack51()
    part_selfish()
    print(f"\nCSV et figures ecrits dans {OUT}")