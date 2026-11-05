"""Assemble une simulation complete a partir d'une configuration."""
import random
from dataclasses import dataclass, field, asdict

from sim.events import Simulator
from sim.network import Network
from sim.node import Node


@dataclass
class SimConfig:
    n_nodes: int = 20
    hash_shares: list | None = None      # None -> parts egales
    block_interval: float = 60.0         # intervalle moyen entre blocs (s)
    duration: float = 60.0 * 2000        # duree simulee (s)
    latency_mean: float = 2.0            # latence moyenne d'un message (s)
    loss_prob: float = 0.0               # probabilite de perte d'un message
    seed: int = 42

    def shares(self) -> list[float]:
        s = self.hash_shares or [1.0] * self.n_nodes
        total = sum(s)
        return [x / total for x in s]


@dataclass
class SimResult:
    config: SimConfig
    sim: Simulator
    net: Network
    nodes: list = field(default_factory=list)


def run_simulation(cfg: SimConfig, special_nodes: dict | None = None,
                   setup=None) -> SimResult:
    """special_nodes : {indice: fabrique(name, share, sim, net, rng, interval)}
    permet de remplacer un noeud honnete par un attaquant (etapes 3 et 4)."""
    rng = random.Random(cfg.seed)
    sim = Simulator()
    net = Network(sim, rng, cfg.latency_mean, loss_prob=cfg.loss_prob)
    nodes = []
    for i, share in enumerate(cfg.shares()):
        name = f"N{i}"
        factory = (special_nodes or {}).get(i, Node)
        node = factory(name, share, sim, net, rng, cfg.block_interval)
        net.add_node(node)
        nodes.append(node)
    result = SimResult(cfg, sim, net, nodes)
    for node in nodes:
        node.start()
    if setup:
        setup(result)          # permet de planifier des evenements (lancement d'attaque)
    sim.run(cfg.duration)
    return result
