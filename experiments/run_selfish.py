"""Experience : selfish mining (strategie d'Eyal & Sirer).
Fait varier la part de hash alpha du selfish miner et compare sa part de
recompenses a (1) sa part equitable (minage honnete) et (2) la theorie.

Usage : python experiments/run_selfish.py [nb_graines]   (defaut 20)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from attacks.selfish import run_selfish
from attacks.theory import selfish_revenue, selfish_threshold

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
ALPHAS = [0.10, 0.15, 0.20, 0.25, 0.30, 0.33, 0.35, 0.40, 0.45]


def main(n_seeds=20):
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for a in ALPHAS:
        for s in range(n_seeds):
            rows.append(run_selfish(a, seed=2000 + s, n_blocks=3000))
        print(f"alpha={a:.2f} termine")
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "selfish_trials.csv"), index=False)

    def ci(x):
        return 1.96 * x.std(ddof=1) / np.sqrt(len(x))

    g = df.groupby("alpha")
    sm = pd.DataFrame({
        "revenue_share": g.revenue_share.mean(),
        "revenue_ci95": g.revenue_share.apply(ci),
        "advantage": g.advantage.mean(),
        "orphan_rate": g.orphan_rate.mean(),
        "honest_blocks_orphaned": g.honest_blocks_orphaned.mean(),
        "gamma_emp": g.gamma_emp.mean(),
        "max_reorg_depth": g.max_reorg_depth.max(),
        "max_private_lead": g.max_private_lead.max(),
    }).reset_index()
    sm["theory_gamma0"] = [selfish_revenue(a, 0.0) for a in sm.alpha]
    sm["theory_gamma_emp"] = [selfish_revenue(a, gm) for a, gm in zip(sm.alpha, sm.gamma_emp)]
    sm.to_csv(os.path.join(OUT, "selfish_summary.csv"), index=False)
    print("\n", sm.round(3).to_string(index=False))

    gam = float(df.gamma_emp.mean())
    print(f"\ngamma empirique moyen : {gam:.3f}  ->  seuil theorique : {selfish_threshold(gam):.3f}"
          f"   (gamma=0 : {selfish_threshold(0):.3f})")

    # Figure 1 : revenu relatif vs alpha
    fig, ax = plt.subplots(figsize=(7, 4.5))
    xs = np.linspace(0.05, 0.46, 80)
    ax.plot(xs, xs, "k:", label="minage honnete (part equitable)")
    ax.plot(xs, [selfish_revenue(x, 0.0) for x in xs], "--", color="C1", label="theorie gamma=0")
    ax.plot(xs, [selfish_revenue(x, gam) for x in xs], "--", color="C2",
            label=f"theorie gamma={gam:.2f} (mesure)")
    ax.errorbar(sm.alpha, sm.revenue_share, yerr=sm.revenue_ci95, fmt="o-", color="C0",
                capsize=3, label="simulation")
    ax.axvline(selfish_threshold(gam), color="C2", alpha=.3)
    ax.set_xlabel("part de hash du selfish miner (alpha)")
    ax.set_ylabel("part des recompenses (blocs de la chaine principale)")
    ax.set_title("Selfish mining : simulation vs theorie d'Eyal & Sirer")
    ax.grid(alpha=.3); ax.legend(); fig.tight_layout()
    fig.savefig(os.path.join(OUT, "selfish_revenue_vs_alpha.png"), dpi=150)

    # Figure 2 : impact sur le reseau
    fig, ax1 = plt.subplots(figsize=(7, 4.5))
    ax1.plot(sm.alpha, sm.orphan_rate, "o-", color="C3", label="taux d'orphelins")
    ax1.set_xlabel("part de hash du selfish miner (alpha)")
    ax1.set_ylabel("taux d'orphelins", color="C3")
    ax2 = ax1.twinx()
    ax2.plot(sm.alpha, sm.honest_blocks_orphaned, "s--", color="C4",
             label="blocs honnetes orphelins")
    ax2.set_ylabel("blocs honnetes orphelins (par essai)", color="C4")
    ax1.set_title("Selfish mining : impact sur le reseau (reference : ~3 %)")
    ax1.grid(alpha=.3); fig.tight_layout()
    fig.savefig(os.path.join(OUT, "selfish_network_impact.png"), dpi=150)
    print("\nFichiers ecrits dans experiments/results/")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 20)
