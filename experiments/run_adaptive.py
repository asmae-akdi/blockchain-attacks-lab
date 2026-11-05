"""Etape 6.3 : confirmations fixes vs ADAPTATIVES face a un attaquant 51 % persistant.

Usage : python experiments/run_adaptive.py [n_graines]
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from defense.adaptive_confirmations import run_adaptive_stream

OUT = Path(__file__).resolve().parent / "results"
OUT.mkdir(exist_ok=True)

N_SEEDS = int(sys.argv[1]) if len(sys.argv) > 1 else 5

CONFIGS = [
    ("z=2 fixe", dict(z_base=2)),
    ("z=6 fixe", dict(z_base=6)),
    ("adaptatif 2->6", dict(z_base=2, z_alarm=6)),
    ("adaptatif 2->6 + garde D=4", dict(z_base=2, z_alarm=6,
                                        defense={"max_reorg_depth": 4})),
]

ep_rows, run_rows = [], []
for alpha in (0.30, 0.40):
    for label, kw in CONFIGS:
        for s in range(N_SEEDS):
            episodes, mon, _ = run_adaptive_stream(alpha, seed=s, **kw)
            run_rows.append({"alpha": alpha, "config": label, "seed": s,
                             "windows": mon.n_seen if mon else 0,
                             "alarm_windows": mon.n_alarm if mon else 0})
            for k, e in enumerate(episodes):
                ep_rows.append({"alpha": alpha, "config": label, "seed": s, "idx": k, **e})
        print(f"alpha={alpha} {label} : fait", flush=True)

ep = pd.DataFrame(ep_rows)
ep["success"] = (ep["outcome"] == "success").astype(int)
ep.to_csv(OUT / "adaptive_episodes.csv", index=False)
runs = pd.DataFrame(run_rows)
runs.to_csv(OUT / "adaptive_runs.csv", index=False)

keys = ["alpha", "config"]
tab = ep.groupby(keys).agg(
    episodes=("success", "size"),
    succes=("success", "sum"),
    taux_succes=("success", "mean"),
    delai_livraison_blocs=("delivery_delay", "mean"),
    part_sous_alarme=("alarm_at_start", "mean"))
tab["episodes"] = tab["episodes"] / N_SEEDS
tab["succes"] = tab["succes"] / N_SEEDS                 # par simulation
tab["taux_1er_episode"] = ep[ep.idx == 0].groupby(keys)["success"].mean()
tab["taux_episodes_suivants"] = ep[ep.idx > 0].groupby(keys)["success"].mean()
tab["fenetres_en_alarme"] = runs.groupby(keys)["alarm_windows"].mean()
print(f"\n=== Confirmations fixes vs adaptatives ({N_SEEDS} graines) ===")
print("(episodes et succes : moyenne par simulation)")
print(tab.round(3).to_string())
print(f"\nCSV ecrits dans {OUT}")