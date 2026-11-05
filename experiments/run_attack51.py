"""Experience : attaque des 51 % + double spending.
Fait varier la part de hash de l'attaquant (alpha) et le nombre de confirmations
exigees par le marchand (z). Compare a la theorie.

Usage : python experiments/run_attack51.py [nb_essais]   (defaut 300)
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from attacks.attack_51 import run_double_spend
from attacks.theory import double_spend_success_prob

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
ALPHAS = [0.10, 0.20, 0.30, 0.35, 0.40, 0.45, 0.51]
ZS = [1, 2, 4, 6]


def wilson(k, n, z=1.96):
    """Intervalle de confiance de Wilson a 95 % pour une proportion."""
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def main(n_trials=300):
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for alpha in ALPHAS:
        for z in ZS:
            for s in range(n_trials):
                rows.append(run_double_spend(alpha, z, seed=1000 + s))
        print(f"alpha={alpha:.2f} termine")
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "attack51_trials.csv"), index=False)

    summ = []
    for (a, z), g in df.groupby(["alpha", "z"]):
        k, n = int(g.success.sum()), len(g)
        lo, hi = wilson(k, n)
        ok = g[g.success == 1]
        summ.append({
            "alpha": a, "z": z, "n_trials": n,
            "success_rate": k / n, "ci_low": lo, "ci_high": hi,
            "theory": double_spend_success_prob(a, z),
            "mean_reorg_depth": ok.reorg_depth.mean() if len(ok) else 0.0,
            "mean_merchant_loss": g.merchant_loss.mean(),
            "mean_attacker_profit": g.attacker_profit.mean(),
            "mean_honest_orphans": g.honest_blocks_orphaned.mean(),
        })
    sm = pd.DataFrame(summ)
    sm.to_csv(os.path.join(OUT, "attack51_summary.csv"), index=False)
    print("\n", sm.round(3).to_string(index=False))

    # Figure 1 : taux de reussite vs alpha
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for z, c in zip(ZS, ["C0", "C1", "C2", "C3"]):
        g = sm[sm.z == z]
        ax.errorbar(g.alpha, g.success_rate,
                    yerr=[g.success_rate - g.ci_low, g.ci_high - g.success_rate],
                    fmt="o-", color=c, capsize=3, label=f"simulation z={z}")
        xs = [i / 100 for i in range(5, 52)]
        ax.plot(xs, [double_spend_success_prob(x, z) for x in xs], "--", color=c, alpha=.6)
    ax.set_xlabel("part de hash de l'attaquant (alpha)")
    ax.set_ylabel("taux de reussite du double spending")
    ax.set_title("Attaque 51 % : simulation (points) vs theorie (pointilles)")
    ax.grid(alpha=.3); ax.legend(); fig.tight_layout()
    fig.savefig(os.path.join(OUT, "attack51_success_vs_alpha.png"), dpi=150)

    # Figure 2 : pertes du marchand et profit de l'attaquant (z = 2)
    g = sm[sm.z == 2]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(g.alpha, g.mean_merchant_loss, "o-", label="perte moyenne du marchand")
    ax.plot(g.alpha, g.mean_attacker_profit, "s-", label="profit moyen de l'attaquant")
    ax.axhline(0, color="k", lw=.8)
    ax.set_xlabel("part de hash de l'attaquant (alpha)")
    ax.set_ylabel("montant simule (coins)")
    ax.set_title("Impact economique (z=2, montant double-depense = 1000)")
    ax.grid(alpha=.3); ax.legend(); fig.tight_layout()
    fig.savefig(os.path.join(OUT, "attack51_economics.png"), dpi=150)
    print("\nFichiers ecrits dans experiments/results/")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 300)
