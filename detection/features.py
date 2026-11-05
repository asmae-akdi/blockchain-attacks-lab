"""Extraction de metriques par fenetre glissante, du point de vue d'UN noeud
honnete (l'observateur). Tout est CAUSAL : a l'instant t on n'utilise que ce que
l'observateur a deja recu.

Metriques (fenetre de `w_blocks` intervalles de blocs) :
  fork_rate        part des blocs recus qui ont un 'frere' (fork / futur orphelin)
  reorg_count      nombre de reorganisations vues par l'observateur
  max_reorg_depth  profondeur maximale d'une reorganisation
  growth           croissance de la chaine (blocs par intervalle ; ~1 normalement)
  burst_max        nb max de blocs recus dans un court laps de temps (rafale)
  top_share        part du mineur dominant dans les derniers blocs de la chaine
  max_run          plus longue suite de blocs consecutifs du meme mineur
  delay_mean/p90   delai de propagation (reception - publication)
"""
import bisect
from collections import defaultdict

import numpy as np
import pandas as pd

from core.blockchain import Blockchain

FEATURES = ["fork_rate", "reorg_count", "max_reorg_depth", "growth", "burst_max",
            "top_share", "max_run", "delay_mean", "delay_p90"]
BURST_SPAN = 5.0   # secondes


def _max_run(miners) -> int:
    best = cur = 0
    prev = None
    for m in miners:
        cur = cur + 1 if m == prev else 1
        prev = m
        best = max(best, cur)
    return best


def extract_features(result, observer: str | None = None, w_blocks: int = 20,
                     stride_blocks: int = 5) -> pd.DataFrame:
    T = result.config.block_interval
    observer = observer or result.nodes[-1].name
    recs = []
    for rec in result.net.published.values():
        t = rec["arrivals"].get(observer)
        if t is not None:
            recs.append((t, rec["time"], rec["block"]))
    recs.sort(key=lambda r: r[0])

    W, S = w_blocks * T, stride_blocks * T
    bc, children = Blockchain(), defaultdict(int)
    ev_t, ev_fork, ev_depth, ev_delay = [], [], [], []
    tip_t, tip_h = [0.0], [0]
    rows, i, t_end = [], 0, W
    horizon = result.sim.now

    while t_end <= horizon + 1e-9:
        while i < len(recs) and recs[i][0] <= t_end:
            t, pub_t, b = recs[i]
            i += 1
            res = bc.add_block(b, t)
            if res.status in ("duplicate", "invalid"):
                continue
            children[b.prev_hash] += 1
            ev_t.append(t)
            ev_fork.append(children[b.prev_hash] > 1)
            ev_depth.append(res.reorg_depth)
            ev_delay.append(t - pub_t)
            tip_t.append(t)
            tip_h.append(bc.height)

        lo = bisect.bisect_right(ev_t, t_end - W)
        n = len(ev_t) - lo
        times = ev_t[lo:]
        depths = ev_depth[lo:]
        delays = np.array(ev_delay[lo:]) if n else np.array([0.0])

        best, j = 0, 0
        for a in range(len(times)):
            while times[a] - times[j] > BURST_SPAN:
                j += 1
            best = max(best, a - j + 1)

        idx = bisect.bisect_right(tip_t, t_end - W) - 1
        growth = (bc.height - tip_h[idx]) / w_blocks

        chain = [b.miner for b in bc.main_chain()[-w_blocks:]]
        counts = defaultdict(int)
        for m in chain:
            counts[m] += 1

        rows.append({
            "t_end": t_end, "t_end_blocks": t_end / T,
            "fork_rate": (sum(ev_fork[lo:]) / n) if n else 0.0,
            "reorg_count": sum(1 for d in depths if d > 0),
            "max_reorg_depth": max(depths, default=0),
            "growth": growth,
            "burst_max": best,
            "top_share": max(counts.values()) / len(chain) if chain else 0.0,
            "max_run": _max_run(chain),
            "delay_mean": float(delays.mean()),
            "delay_p90": float(np.percentile(delays, 90)),
        })
        t_end += S
    return pd.DataFrame(rows)
