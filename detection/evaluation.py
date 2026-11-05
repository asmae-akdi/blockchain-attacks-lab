"""Metriques d'evaluation : precision, rappel, F1, taux de fausses alarmes,
temps de detection."""
import numpy as np
import pandas as pd

from detection.detectors import WARMUP
from detection.dataset import W_BLOCKS


def window_scores(runs, alarms):
    tp = fp = fn = tn = 0
    for r, al in zip(runs, alarms):
        lab = r["labels"].copy()
        lab[:WARMUP] = -1
        al = np.asarray(al, bool)
        tp += int((al & (lab == 1)).sum()); fn += int((~al & (lab == 1)).sum())
        fp += int((al & (lab == 0)).sum()); tn += int((~al & (lab == 0)).sum())
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {"precision": prec, "recall": rec, "f1": f1,
            "fpr": fp / (fp + tn) if fp + tn else 0.0}


def detection_delays(run, alarm):
    """Delais (en blocs) entre le debut/la publication de l'attaque et la 1re alarme.
    NaN = attaque manquee."""
    te = run["df"].t_end_blocks.values
    al = np.asarray(alarm, bool).copy()
    al[:WARMUP] = False
    out = []
    for ev in run["events"]:
        if run["kind"] == "selfish":
            mask = al & (te >= ev)
        else:                                  # attack51 : alarme dans [pub, pub + 2W]
            mask = al & (te >= ev) & (te <= ev + 2 * W_BLOCKS)
        out.append(float(te[mask][0] - ev) if mask.any() else np.nan)
    return out


def evaluate(detector, runs):
    alarms = [detector.run(r["df"]) for r in runs]
    res = window_scores(runs, alarms)
    normal = [(r, a) for r, a in zip(runs, alarms) if r["kind"] == "normal"]
    nw = sum(len(r["df"]) - WARMUP for r, _ in normal)
    res["false_alarm_rate_normal"] = (sum(int(np.asarray(a)[WARMUP:].sum()) for _, a in normal) / nw
                                      if nw else 0.0)
    for kind in ("selfish", "attack51"):
        d = [x for r, a in zip(runs, alarms) if r["kind"] == kind
             for x in detection_delays(r, a)]
        res[f"{kind}_detected"] = float(np.mean([not np.isnan(x) for x in d])) if d else np.nan
        res[f"{kind}_delay_blocks"] = float(np.nanmedian(d)) if d and not all(np.isnan(d)) else np.nan
    return res, alarms
