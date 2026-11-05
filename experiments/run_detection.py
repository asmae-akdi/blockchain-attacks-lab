"""Experience de detection.

1. Genere des simulations etiquetees : reference, selfish mining, attaque 51 %
   persistante, dans deux conditions reseau (standard / degradee).
2. REGLE les detecteurs sur le jeu d'entrainement (conditions standard uniquement).
3. EVALUE sur des simulations jamais vues, en conditions standard ET degradees
   (latence x4, 2x plus de noeuds, 5 % de pertes) : test de robustesse.

Usage : python experiments/run_detection.py
"""
import itertools
import os
import pickle
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from detection.dataset import build_runs
from detection.detectors import (StaticDetector, AdaptiveRuleDetector, MLDetector, WARMUP)
from detection.evaluation import evaluate, window_scores
from detection.features import FEATURES

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
CACHE = os.path.join(OUT, "detection_cache.pkl")


def get_data():
    if os.path.exists(CACHE):
        with open(CACHE, "rb") as f:
            return pickle.load(f)
    print("Generation des simulations (quelques minutes)...")
    data = {"train": build_runs("standard", 100),
            "test_standard": build_runs("standard", 500),
            "test_stressed": build_runs("stressed", 900)}
    os.makedirs(OUT, exist_ok=True)
    with open(CACHE, "wb") as f:
        pickle.dump(data, f)
    return data


def tune(make, grid, train):
    best, best_f1 = None, -1
    for params in grid:
        det = make(**params)
        f1 = window_scores(train, [det.run(r["df"]) for r in train])["f1"]
        if f1 > best_f1:
            best, best_f1 = params, f1
    return best, best_f1


def main():
    data = get_data()
    train = data["train"]
    print({k: len(v) for k, v in data.items()}, "simulations")

    # ---- reglage sur l'entrainement ----
    sp, sf = tune(StaticDetector,
                  [dict(fork_thr=a, depth_thr=b) for a, b in
                   itertools.product([0.10, 0.15, 0.20, 0.25, 0.30], [2, 3, 4, 5, 6])], train)
    ap, af = tune(AdaptiveRuleDetector,
                  [dict(k=k, m=m, k_hi=h, persist=p) for k, m, h, p in
                   itertools.product([3, 4, 5, 6], [1, 2, 3], [8, 12], [1, 2, 3])], train)
    print(f"Regles fixes      : {sp}  (F1 train = {sf:.3f})")
    print(f"Regles adaptatives: {ap}  (F1 train = {af:.3f})")

    detectors = [StaticDetector(**sp), AdaptiveRuleDetector(**ap),
                 MLDetector("iforest").fit(train),
                 MLDetector("rf").fit(train),
                 MLDetector("rf", adaptive=True).fit(train)]

    # ---- evaluation ----
    rows, alarms_store = [], {}
    for cond in ("test_standard", "test_stressed"):
        for det in detectors:
            res, al = evaluate(det, data[cond])
            alarms_store[(cond, det.name)] = al
            rows.append({"condition": cond.replace("test_", ""), "detecteur": det.name, **res})
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "detection_results.csv"), index=False)
    show = df[["condition", "detecteur", "precision", "recall", "f1",
               "false_alarm_rate_normal", "selfish_detected", "selfish_delay_blocks",
               "attack51_detected", "attack51_delay_blocks"]]
    print("\n", show.round(3).to_string(index=False))

    # ---- figure 1 : F1 par detecteur et condition ----
    fig, ax = plt.subplots(figsize=(8, 4.5))
    names = [d.name for d in detectors]
    x = np.arange(len(names))
    for i, cond in enumerate(("standard", "stressed")):
        vals = [df[(df.condition == cond) & (df.detecteur == n)].f1.iloc[0] for n in names]
        ax.bar(x + (i - .5) * .38, vals, .38,
               label="conditions standard" if cond == "standard" else "conditions degradees")
    ax.set_xticks(x); ax.set_xticklabels(names, rotation=18, ha="right", fontsize=8)
    ax.set_ylabel("F1 (fenetres)"); ax.set_ylim(0, 1.05)
    ax.set_title("Detection : robustesse aux conditions reseau")
    ax.legend(); ax.grid(axis="y", alpha=.3); fig.tight_layout()
    fig.savefig(os.path.join(OUT, "detection_f1.png"), dpi=150)

    # ---- figure 2 : exemple de serie temporelle (selfish mining, alpha=0.4) ----
    run = next(r for r in data["test_standard"] if r["kind"] == "selfish" and r["alpha"] == 0.4)
    ada = detectors[1]
    al, zs = ada.run_with_scores(run["df"])
    te = run["df"].t_end_blocks
    fig, axes = plt.subplots(3, 1, figsize=(8, 7), sharex=True)
    axes[0].plot(te, run["df"].fork_rate, color="C3"); axes[0].set_ylabel("fork_rate")
    axes[1].plot(te, run["df"].burst_max, color="C4"); axes[1].set_ylabel("burst_max")
    axes[2].plot(te, zs.max(axis=1), color="C0", label="score z maximal")
    axes[2].axhline(ada.k, color="gray", ls="--", label=f"seuil k={ada.k}")
    axes[2].fill_between(te, 0, zs.max(axis=1).max(), where=al, color="red", alpha=.15, label="alarme")
    axes[2].set_ylabel("score adaptatif"); axes[2].set_xlabel("temps (en intervalles de blocs)")
    for a in axes:
        a.axvline(run["start_block"], color="k", ls=":"); a.grid(alpha=.3)
    axes[2].legend(fontsize=8)
    axes[0].set_title("Selfish mining (alpha=0,4) : debut a t=500 (ligne pointillee)")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "detection_timeseries.png"), dpi=150)
    print("\nFichiers ecrits dans experiments/results/")


if __name__ == "__main__":
    main()
