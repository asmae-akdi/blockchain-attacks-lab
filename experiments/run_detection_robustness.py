"""Etape 7.2 : robustesse de la detection a des conditions reseau JAMAIS vues.

Les detecteurs sont regles une seule fois (conditions standard, jeu 'train' de
l'Etape 5), puis evalues dans de nouvelles conditions (latence, taille, pertes).
"""
import itertools
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from detection import dataset
from detection.detectors import StaticDetector, AdaptiveRuleDetector, MLDetector
from detection.evaluation import evaluate
from experiments.run_detection import get_data, tune

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


def run(cfg, quick=False):
    os.makedirs(OUT, exist_ok=True)
    train = get_data()["train"]
    sp, _ = tune(StaticDetector,
                 [dict(fork_thr=a, depth_thr=b) for a, b in
                  itertools.product([0.10, 0.15, 0.20, 0.25, 0.30], [2, 3, 4, 5, 6])], train)
    ap, _ = tune(AdaptiveRuleDetector,
                 [dict(k=k, m=m, k_hi=h, persist=p) for k, m, h, p in
                  itertools.product([3, 4, 5, 6], [1, 2, 3], [8, 12], [1, 2, 3])], train)
    print(f"Regles fixes : {sp}\nRegles adaptatives : {ap}")
    dets = [StaticDetector(**sp), AdaptiveRuleDetector(**ap),
            MLDetector("rf").fit(train), MLDetector("rf", adaptive=True).fit(train)]

    build_kw = (dict(n_normal=3, selfish_alphas=(0.3, 0.45), a51=((0.45, 1), (0.51, 2)),
                     seeds_per=1) if quick else dict(seeds_per=cfg["detection"]["seeds_per"]))
    rows, seed0 = [], 7000
    for c in cfg["detection"]["conditions"]:
        dataset.CONDITIONS[c["name"]] = dict(n_nodes=c["n_nodes"], latency_mean=c["latency_mean"],
                                             loss_prob=c["loss_prob"])
        runs = dataset.build_runs(c["name"], seed0, **build_kw)
        seed0 += 100
        for det in dets:
            res, _ = evaluate(det, runs)
            rows.append({"condition": c["name"], "detecteur": det.name, **res})
        print(f"  condition {c['name']} terminee ({len(runs)} simulations)")
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "robustness_detection.csv"), index=False)

    names = [d.name for d in dets]
    conds = [c["name"] for c in cfg["detection"]["conditions"]]
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    for ax, col, lab in zip(axes, ["false_alarm_rate_normal", "recall"],
                            ["fausses alarmes (reseau honnete)", "rappel (fenetres d'attaque)"]):
        for i, n in enumerate(names):
            vals = [df[(df.condition == c) & (df.detecteur == n)][col].iloc[0] for c in conds]
            ax.bar([x + (i - 1.5) * .2 for x in range(len(conds))], vals, .2, label=n)
        ax.set_xticks(range(len(conds))); ax.set_xticklabels(conds)
        ax.set_ylabel(lab); ax.set_ylim(0, 1.05); ax.grid(axis="y", alpha=.3)
    axes[0].legend(fontsize=8)
    fig.suptitle("Detection : robustesse a de nouvelles conditions reseau")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "robustness_detection.png"), dpi=150)
    show = df[["condition", "detecteur", "false_alarm_rate_normal", "recall", "precision",
               "selfish_detected", "selfish_delay_blocks", "attack51_detected",
               "attack51_delay_blocks"]]
    print("\n", show.round(3).to_string(index=False))
    return df


if __name__ == "__main__":
    import yaml
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "configs", "final.yaml")
    run(yaml.safe_load(open(path, encoding="utf-8")))
