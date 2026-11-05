"""Fabrique de jeux de donnees etiquetes pour la detection."""
import numpy as np

from attacks.attack_51 import run_attack51_stream
from attacks.selfish import run_selfish
from detection.features import extract_features
from sim.simulation import SimConfig, run_simulation

W_BLOCKS, STRIDE_BLOCKS = 20, 5
CONDITIONS = {
    "standard": dict(n_nodes=10, latency_mean=2.0, loss_prob=0.0),
    "stressed": dict(n_nodes=20, latency_mean=8.0, loss_prob=0.05),
}


def label_selfish(df, t_start_blocks):
    """0 avant l'attaque, 1 une fois la fenetre entierement apres le debut,
    -1 (exclu) pour les fenetres de transition."""
    te = df.t_end_blocks.values
    lab = np.full(len(df), -1)
    lab[te <= t_start_blocks] = 0
    lab[te >= t_start_blocks + W_BLOCKS] = 1
    return lab


def label_attack51(df, episodes, T):
    """1 si la fenetre contient la PUBLICATION d'une chaine d'attaque (effet visible),
    0 si elle ne chevauche aucune tentative, -1 sinon (minage prive invisible)."""
    W = W_BLOCKS * T
    pubs = [e["t_publish"] for e in episodes if e["t_publish"] is not None]
    spans = [(e["t_start"], e["t_end"]) for e in episodes]
    lab = np.zeros(len(df), int)
    for i, te in enumerate(df.t_end.values):
        a, b = te - W, te
        if any(a < p <= b for p in pubs):
            lab[i] = 1
        elif any(max(a, s) < min(b, e) for s, e in spans):
            lab[i] = -1
    return lab


def make_run(kind, cond, seed, alpha=None, z=1, n_blocks=1500, start_block=500):
    c = CONDITIONS[cond]
    T = 60.0
    run = {"kind": kind, "cond": cond, "seed": seed, "alpha": alpha, "z": z,
           "start_block": start_block, "events": []}
    if kind == "normal":
        cfg = SimConfig(block_interval=T, duration=n_blocks * T, seed=seed, **c)
        res = run_simulation(cfg)
        df = extract_features(res, w_blocks=W_BLOCKS, stride_blocks=STRIDE_BLOCKS)
        lab = np.zeros(len(df), int)
    elif kind == "selfish":
        out, res = run_selfish(alpha, seed=seed, n_blocks=n_blocks,
                               start_block=start_block, return_result=True, **c)
        df = extract_features(res, w_blocks=W_BLOCKS, stride_blocks=STRIDE_BLOCKS)
        lab = label_selfish(df, start_block)
        run["events"] = [float(start_block)]               # debut d'attaque (en blocs)
    elif kind == "attack51":
        res, eps = run_attack51_stream(alpha, z, seed=seed, n_blocks=n_blocks,
                                       start_block=start_block, **c)
        df = extract_features(res, w_blocks=W_BLOCKS, stride_blocks=STRIDE_BLOCKS)
        lab = label_attack51(df, eps, T)
        run["events"] = [e["t_publish"] / T for e in eps if e["t_publish"] is not None]
        run["episodes"] = eps
    else:
        raise ValueError(kind)
    run["df"], run["labels"] = df, lab
    return run


def build_runs(cond, seed0, n_normal=6, selfish_alphas=(0.2, 0.3, 0.4, 0.45),
               a51=((0.35, 1), (0.45, 1), (0.51, 1), (0.35, 2), (0.45, 2), (0.51, 2)),
               seeds_per=2):
    runs, s = [], seed0
    for _ in range(n_normal):
        runs.append(make_run("normal", cond, s)); s += 1
    for a in selfish_alphas:
        for _ in range(seeds_per):
            runs.append(make_run("selfish", cond, s, alpha=a)); s += 1
    for a, z in a51:
        for _ in range(seeds_per):
            runs.append(make_run("attack51", cond, s, alpha=a, z=z)); s += 1
    return runs
