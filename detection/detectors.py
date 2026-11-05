"""Detecteurs d'attaques : regles fixes (reference), regles ADAPTATIVES
(contribution), Isolation Forest et Random Forest (ML)."""
from collections import deque

import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestClassifier

from detection.features import FEATURES

WARMUP = 40   # fenetres sans alarme : apprentissage de la normalite

# Echelle minimale de chaque metrique (evite la division par ~0 quand la
# metrique est presque constante, ex. profondeur de reorg toujours 0 ou 1)
MIN_SCALE = {"fork_rate": 0.03, "reorg_count": 1.0, "max_reorg_depth": 1.0,
             "growth": 0.1, "burst_max": 1.0, "top_share": 0.08, "max_run": 1.0,
             "delay_mean": 0.5, "delay_p90": 1.0}
TWO_SIDED = {"growth"}   # croissance trop lente OU trop rapide est suspecte


class StaticDetector:
    """Mecanisme de REFERENCE : seuils fixes, non adaptatifs."""
    name = "Regles fixes"

    def __init__(self, fork_thr=0.15, depth_thr=4):
        self.fork_thr, self.depth_thr = fork_thr, depth_thr

    def run(self, df):
        return ((df.fork_rate > self.fork_thr) | (df.max_reorg_depth >= self.depth_thr)).values


class AdaptiveRuleDetector:
    """Seuils ADAPTATIFS. Pour chaque metrique, on maintient la mediane et le MAD
    (ecart absolu median, robuste) des dernieres fenetres 'saines'. Le score est
        z = (x - mediane) / max(1.4826*MAD, echelle_min)
    Alarme si au moins `m` metriques depassent `k`, ou une seule depasse `k_hi`,
    pendant `persist` fenetres consecutives.
    Pendant une alarme, la reference n'est PAS mise a jour (sinon le detecteur
    apprendrait l'attaque comme etant normale)."""
    name = "Regles adaptatives"

    def __init__(self, k=4.0, m=2, k_hi=10.0, persist=1, history=100, warmup=WARMUP,
                 features=FEATURES):
        self.k, self.m, self.k_hi, self.persist = k, m, k_hi, persist
        self.history, self.warmup, self.features = history, warmup, features

    def _z(self, buf, x):
        z = np.zeros(len(self.features))
        for j, f in enumerate(self.features):
            arr = np.asarray(buf[f])
            med = np.median(arr)
            mad = 1.4826 * np.median(np.abs(arr - med))
            scale = max(mad, MIN_SCALE[f], 0.05 * abs(med))
            d = x[j] - med
            z[j] = abs(d) / scale if f in TWO_SIDED else d / scale
        return z

    def run_with_scores(self, df):
        X = df[self.features].values
        buf = {f: deque(maxlen=self.history) for f in self.features}
        alarms = np.zeros(len(df), bool)
        zs = np.zeros((len(df), len(self.features)))
        streak = 0                      # alarmes brutes consecutives
        for i, x in enumerate(X):
            alarm = False
            if i >= self.warmup:
                z = self._z(buf, x)
                zs[i] = z
                alarm = bool((z > self.k).sum() >= self.m or z.max() > self.k_hi)
                streak = streak + 1 if alarm else 0
                alarms[i] = streak >= self.persist     # persistance exigee
            if not alarm:
                for f, v in zip(self.features, x):
                    buf[f].append(v)
        return alarms, zs

    def run(self, df):
        return self.run_with_scores(df)[0]


class MLDetector:
    """kind = 'rf' (supervise) ou 'iforest' (non supervise, entraine sur du normal).
    adaptive=True : le modele recoit les scores z adaptatifs au lieu des valeurs brutes."""

    def __init__(self, kind="rf", adaptive=False, seed=0):
        self.kind, self.adaptive, self.seed = kind, adaptive, seed
        self.name = {"rf": "Random Forest", "iforest": "Isolation Forest"}[kind] + \
                    (" + z adaptatifs" if adaptive else "")

    def _X(self, df):
        if self.adaptive:
            return AdaptiveRuleDetector().run_with_scores(df)[1]
        return df[FEATURES].values

    def fit(self, runs):
        X, y = [], []
        for r in runs:
            lab = r["labels"]
            keep = (lab != -1) & (np.arange(len(lab)) >= WARMUP)
            X.append(self._X(r["df"])[keep])
            y.append(lab[keep])
        X, y = np.vstack(X), np.concatenate(y)
        if self.kind == "rf":
            self.model = RandomForestClassifier(n_estimators=200, min_samples_leaf=3,
                                                class_weight="balanced",
                                                random_state=self.seed, n_jobs=-1)
            self.model.fit(X, y)
        else:
            self.model = IsolationForest(n_estimators=200, random_state=self.seed)
            self.model.fit(X[y == 0])
            self.thr = np.quantile(-self.model.decision_function(X[y == 0]), 0.99)
        return self

    def run(self, df):
        X = self._X(df)
        if self.kind == "rf":
            alarms = self.model.predict(X).astype(bool)
        else:
            alarms = (-self.model.decision_function(X)) > self.thr
        alarms[:WARMUP] = False
        return alarms
