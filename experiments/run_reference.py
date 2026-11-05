"""Scenario de reference : tous les noeuds sont honnetes.
Verifie que le simulateur se comporte comme la theorie :
taux d'orphelins ~ 1 - exp(-delai / intervalle entre blocs)."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sim.simulation import SimConfig, run_simulation
from detection.metrics import compute_metrics

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


def main():
    rows = []
    for lat in [0.5, 1, 2, 5, 10, 20]:
        cfg = SimConfig(n_nodes=20, block_interval=60, duration=60 * 3000,
                        latency_mean=lat, seed=7)
        m = compute_metrics(run_simulation(cfg))
        rows.append({
            "latency_mean_s": lat,
            "height": m["height"],
            "orphan_rate": m["orphan_rate"],
            "theory": 1 - math.exp(-lat / 60),
            "prop_delay_p90_s": m["prop_delay_p90"],
            "mean_block_interval_s": m["mean_block_interval"],
            "max_reorg_depth": m["max_reorg_depth"],
            "agreement": m["consensus_agreement"],
        })
    df = pd.DataFrame(rows)
    os.makedirs(OUT, exist_ok=True)
    df.to_csv(os.path.join(OUT, "reference_latency.csv"), index=False)
    print(df.round(4).to_string(index=False))

    plt.figure(figsize=(6, 4))
    plt.plot(df.latency_mean_s, df.orphan_rate, "o-", label="simulation")
    plt.plot(df.latency_mean_s, df.theory, "s--", label="theorie 1-exp(-d/T)")
    plt.xlabel("latence moyenne (s)")
    plt.ylabel("taux d'orphelins")
    plt.title("Blockchain de reference : orphelins vs latence")
    plt.legend(); plt.grid(alpha=.3); plt.tight_layout()
    plt.savefig(os.path.join(OUT, "reference_orphans_vs_latency.png"), dpi=150)
    print("\nFichiers ecrits dans experiments/results/")


if __name__ == "__main__":
    main()
