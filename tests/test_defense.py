import random
from types import SimpleNamespace

from core.blockchain import Blockchain
from core.mining import make_stat_block
from defense.protected_chain import ProtectedBlockchain, protect
from attacks.attack_51 import run_double_spend
from attacks.selfish import run_selfish


def branch(parent, miner, n, rng):
    out, p = [], parent
    for _ in range(n):
        p = make_stat_block(p, miner, float(p.index + 1), rng)
        out.append(p)
    return out


def test_garde_refuse_reorg_profonde():
    rng = random.Random(1)
    ch = ProtectedBlockchain(max_reorg_depth=3)
    for b in branch(ch.genesis, "H", 5, rng):
        ch.add_block(b)
    tip = ch.tip
    for b in branch(ch.genesis, "A", 6, rng):    # branche privee plus longue
        ch.add_block(b)
    assert ch.tip == tip                         # reorg de profondeur 5 refusee
    assert len(ch.rejected_reorgs) == 1
    assert ch.rejected_reorgs[0]["depth"] == 5


def test_sans_garde_la_reorg_passe():
    rng = random.Random(1)
    ch = ProtectedBlockchain(max_reorg_depth=None)
    for b in branch(ch.genesis, "H", 5, rng):
        ch.add_block(b)
    atk = branch(ch.genesis, "A", 6, rng)
    for b in atk:
        ch.add_block(b)
    assert ch.tip == atk[-1].hash
    assert ch.reorgs[-1]["depth"] == 5


def test_garde_accepte_reorg_peu_profonde():
    rng = random.Random(2)
    ch = ProtectedBlockchain(max_reorg_depth=3)
    honest = branch(ch.genesis, "H", 5, rng)
    for b in honest:
        ch.add_block(b)
    fork = branch(honest[2], "A", 3, rng)        # fork au bloc 3, profondeur 2
    for b in fork:
        ch.add_block(b)
    assert ch.tip == fork[-1].hash
    assert not ch.rejected_reorgs


def test_first_seen_garde_le_premier():
    rng = random.Random(3)
    ch = ProtectedBlockchain(tiebreak="first_seen")
    h1 = branch(ch.genesis, "H", 1, rng)[0]
    a1 = branch(ch.genesis, "A", 1, rng)[0]
    ch.add_block(h1)
    ch.add_block(a1)
    assert ch.tip == h1.hash


def test_tiebreak_aleatoire_environ_50_50():
    rng = random.Random(4)
    h1 = branch(Blockchain().genesis, "H", 1, rng)[0]
    a1 = branch(Blockchain().genesis, "A", 1, rng)[0]
    wins = 0
    for i in range(400):
        ch = ProtectedBlockchain(tiebreak="random", rng=random.Random(i))
        ch.add_block(h1)
        ch.add_block(a1)
        wins += ch.tip == a1.hash
    assert 0.4 < wins / 400 < 0.6


def test_protect_ne_touche_que_les_honnetes():
    nodes = [SimpleNamespace(name="N0", honest=False, chain=Blockchain()),
             SimpleNamespace(name="N1", honest=True, chain=Blockchain())]
    assert protect(nodes, max_reorg_depth=4) == 1
    assert type(nodes[0].chain) is Blockchain
    assert isinstance(nodes[1].chain, ProtectedBlockchain)


def test_garde_bloque_le_double_spending_quand_D_inferieur_a_z():
    # un double spending reussi retire au moins z blocs : avec D < z c'est impossible
    for seed in (0, 1):
        r = run_double_spend(0.45, 6, seed=seed, defense={"max_reorg_depth": 4})
        assert r["success"] == 0


def test_run_selfish_avec_defense_aleatoire():
    r = run_selfish(0.35, seed=0, n_blocks=300, defense={"tiebreak": "random"})
    assert 0.0 <= r["obs_revenue_share"] <= 1.0
    assert r["rejected_reorgs"] == 0        # pas de garde : aucun refus