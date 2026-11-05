"""Metriques du reseau (utilisees ensuite par la detection)."""
from collections import Counter

import numpy as np

from core.blockchain import Blockchain


def global_chain(net) -> Blockchain:
    """Vue globale : tous les blocs publies, dans l'ordre de publication."""
    bc = Blockchain()
    for rec in net.published.values():
        bc.add_block(rec["block"], rec["time"])
    return bc


def propagation_delays(net) -> dict:
    """Delai median et 90e percentile de propagation, moyennes sur les blocs."""
    med, p90 = [], []
    for rec in net.published.values():
        d = [t - rec["time"] for n, t in rec["arrivals"].items() if n != rec["miner"]]
        if d:
            med.append(np.percentile(d, 50))
            p90.append(np.percentile(d, 90))
    return {"prop_delay_median": float(np.mean(med)) if med else 0.0,
            "prop_delay_p90": float(np.mean(p90)) if p90 else 0.0}


def compute_metrics(result) -> dict:
    cfg, net = result.config, result.net
    g = global_chain(net)
    height = g.height
    shares = cfg.shares()
    hash_share = {f"N{i}": s for i, s in enumerate(shares)}

    blocks = g.rewards_by_miner()
    reward_share = {m: blocks.get(m, 0) / height if height else 0.0 for m in hash_share}

    tips = Counter(n.chain.tip for n in result.nodes)
    agreement = tips.most_common(1)[0][1] / len(result.nodes)

    node_reorgs = [r["depth"] for n in result.nodes for r in n.chain.reorgs]
    out = {
        "blocks_published": len(net.published),
        "height": height,
        "orphan_rate": g.orphan_rate(),
        "mean_block_interval": g.tip_block.timestamp / height if height else 0.0,
        "fork_count": len(g.stale_blocks()),
        "reorg_count_per_node": len(node_reorgs) / len(result.nodes),
        "max_reorg_depth": max(node_reorgs, default=0),
        "consensus_agreement": agreement,
        "reward_share": reward_share,
        "hash_share": hash_share,
    }
    out.update(propagation_delays(net))
    return out
