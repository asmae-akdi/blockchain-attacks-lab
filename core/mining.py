"""Deux modes de minage.

- Mode reel : vraie recherche de nonce SHA-256 (demonstration, comme pow.cpp).
- Mode statistique : le temps pour trouver un bloc suit une loi exponentielle.
  Un mineur ayant la fraction p du hash total trouve un bloc au taux p / T
  (T = intervalle moyen entre blocs du reseau). Modele standard de la
  litterature (Rosenfeld, Eyal & Sirer). Rapide et reproductible (graine).
"""
import random

from core.block import Block, coinbase


def mine_real(block: Block) -> Block:
    """Cherche un nonce tel que le hash commence par `difficulty` zeros."""
    while True:
        block.hash = block.compute_hash()
        if block.meets_target():
            return block
        block.nonce += 1


def sample_mining_time(hash_share: float, mean_interval: float,
                       rng: random.Random) -> float:
    """Temps (simule) avant qu'un mineur de part `hash_share` trouve un bloc."""
    if hash_share <= 0:
        return float("inf")
    return rng.expovariate(hash_share / mean_interval)


def make_stat_block(parent: Block, miner: str, timestamp: float,
                    rng: random.Random, transactions=()) -> Block:
    """Bloc 'mine' en mode statistique (difficulte 0, nonce aleatoire pour
    garantir l'unicite du hash)."""
    index = parent.index + 1
    txs = (coinbase(miner, index),) + tuple(transactions)
    return Block(index=index, prev_hash=parent.hash, transactions=txs,
                 miner=miner, difficulty=0, timestamp=timestamp,
                 nonce=rng.getrandbits(48))
