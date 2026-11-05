import random

from core.crypto import sha256_hex, merkle_root
from core.block import Block, Transaction, coinbase
from core.blockchain import Blockchain
from core.mining import mine_real, sample_mining_time, make_stat_block


def test_sha256_known_vector():
    assert sha256_hex("abc") == \
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_merkle_changes_on_modification():
    txs = ["A->B 100", "B->C 50", "C->D 30", "D->A 20"]
    r1 = merkle_root(txs)
    txs2 = list(txs); txs2[0] = "A->B 500"
    assert r1 != merkle_root(txs2)


def test_merkle_odd_duplicates_last():
    h = sha256_hex
    expected = h(h(h("a") + h("b")) + h(h("c") + h("c")))
    assert merkle_root(["a", "b", "c"]) == expected


def test_real_mining():
    parent = Blockchain().genesis
    b = Block(1, parent.hash, (coinbase("alice", 1),), "alice", difficulty=3)
    mine_real(b)
    assert b.hash.startswith("000") and b.hash == b.compute_hash()


def test_chain_growth_and_integrity():
    rng = random.Random(1)
    bc = Blockchain()
    for i in range(5):
        bc.add_block(make_stat_block(bc.tip_block, "alice", i + 1.0, rng))
    assert bc.height == 5 and bc.verify_integrity()
    assert bc.orphan_rate() == 0.0


def test_tampering_detected():
    rng = random.Random(1)
    bc = Blockchain()
    for i in range(3):
        bc.add_block(make_stat_block(bc.tip_block, "alice", i + 1.0, rng))
    bc.main_chain()[2].transactions = (Transaction("alice", "bob", 900),)
    assert not bc.verify_integrity()


def test_fork_and_reorg():
    rng = random.Random(2)
    bc = Blockchain()
    g = bc.genesis
    a1 = make_stat_block(g, "A", 1.0, rng)
    b1 = make_stat_block(g, "B", 1.1, rng)
    b2 = make_stat_block(b1, "B", 2.0, rng)
    bc.add_block(a1)
    r = bc.add_block(b1)
    assert bc.tip == a1.hash and not r.new_tip       # first-seen
    r = bc.add_block(b2)
    assert bc.tip == b2.hash and r.reorg_depth == 1  # reorg de profondeur 1
    assert [x.hash for x in bc.stale_blocks()] == [a1.hash]
    assert abs(bc.orphan_rate() - 1 / 3) < 1e-9


def test_out_of_order_blocks_wait_for_parent():
    rng = random.Random(3)
    bc = Blockchain()
    b1 = make_stat_block(bc.genesis, "A", 1.0, rng)
    b2 = make_stat_block(b1, "A", 2.0, rng)
    assert bc.add_block(b2).status == "pending"
    bc.add_block(b1)
    assert bc.tip == b2.hash


def test_confirmations_and_double_spend_disappears():
    rng = random.Random(4)
    bc = Blockchain()
    tx = Transaction("attacker", "merchant", 10)
    b1 = make_stat_block(bc.genesis, "H", 1.0, rng, [tx])
    bc.add_block(b1)
    bc.add_block(make_stat_block(b1, "H", 2.0, rng))
    assert bc.confirmations(tx.tx_id) == 2
    # chaine secrete plus longue sans la transaction
    s1 = make_stat_block(bc.genesis, "X", 1.5, rng)
    s2 = make_stat_block(s1, "X", 2.5, rng)
    s3 = make_stat_block(s2, "X", 3.5, rng)
    for s in (s1, s2, s3):
        bc.add_block(s)
    assert bc.confirmations(tx.tx_id) == 0
    assert bc.reorgs and bc.reorgs[-1]["depth"] == 2


def test_mining_time_is_exponential():
    rng = random.Random(0)
    xs = [sample_mining_time(0.25, 600, rng) for _ in range(20000)]
    assert abs(sum(xs) / len(xs) - 2400) / 2400 < 0.05
