"""Etape 6.4 : surcout des defenses (sans attaque).

Usage : python experiments/run_overhead.py [n_graines]
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from defense.overhead import measure_overhead

OUT = Path(__file__).resolve().parent / "results"
OUT.mkdir(exist_ok=True)

N_SEEDS = int(sys.argv[1]) if len(sys.argv) > 1 else 5

CONDITIONS = [
    ("standard", dict(n_nodes=10, latency_mean=2.0, loss_prob=0.0)),
    ("degradee", dict(n_nodes=20, latency_mean=8.0, loss_prob=0.05)),
]
CONFIGS = [
    ("sans moniteur", dict(with_monitor=False)),
    ("moniteur", dict(with_monitor=True)),
    ("moniteur + garde D=4", dict(with_monitor=True, defense={"max_reorg_depth": 4})),
]

rows = []
for cond, ckw in CONDITIONS:
    for label, kw in CONFIGS:
        for s in range(N_SEEDS):
            r = measure_overhead(seed=s, **ckw, **kw)
            rows.append({"condition": cond, "config": label, **r})
        print(f"{cond} / {label} : fait", flush=True)

df = pd.DataFrame(rows)
df.to_csv(OUT / "overhead.csv", index=False)

keys = ["condition", "config"]
tab = df.groupby(keys).agg(
    temps_calcul_s=("elapsed_s", "mean"),
    part_temps_en_alarme=("frac_time_alarm", "mean"),
    delai_supp_blocs=("extra_delay_blocs", "mean") if False else ("extra_delay_blocks", "mean"),
    refus_garde=("rejected_reorgs", "mean"),
    orphelins=("orphan_rate", "mean"))
base = tab.xs("sans moniteur", level="config")["temps_calcul_s"]
tab["surcout_calcul_x"] = [tab.loc[(c, k), "temps_calcul_s"] / base[c] for c, k in tab.index]

print(f"\n=== Surcout des defenses, sans attaque ({N_SEEDS} graines) ===")
print("(delai_supp_blocs : attente moyenne ajoutee a un client honnete, en intervalles de blocs ;")
print(" reference : z=6 fixe impose 4 blocs de plus en permanence)")
print(tab.round(3).to_string())
print(f"\nCSV ecrit dans {OUT}")