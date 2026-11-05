from attacks.attack_51 import run_double_spend
from attacks.theory import double_spend_success_prob


def rate(alpha, z, n, **kw):
    return sum(run_double_spend(alpha, z, seed=s, **kw)["success"] for s in range(n)) / n


def test_theory_basic_values():
    assert double_spend_success_prob(0.51, 6) == 1.0
    assert double_spend_success_prob(0.1, 6) < 1e-3
    assert double_spend_success_prob(0.3, 1) > double_spend_success_prob(0.3, 6)


def test_majority_attacker_wins_and_tx_disappears():
    out, res, ctx = run_double_spend(0.6, 2, seed=3, return_result=True)
    assert out["outcome"] == "success"
    assert ctx.merchant.chain.confirmations(ctx.victim_tx.tx_id) == 0   # tx disparue
    assert out["delivered"] == 1                                         # marchandise livree
    assert out["reorg_depth"] >= 2                                       # reorg profonde
    assert out["merchant_loss"] == 1000.0


def test_minority_attacker_with_many_confirmations_fails():
    assert rate(0.10, 6, 30) <= 0.05


def test_success_rate_close_to_theory():
    sim = rate(0.30, 2, 150)
    th = double_spend_success_prob(0.30, 2)
    assert abs(sim - th) < 0.12


def test_reproducible():
    a = run_double_spend(0.4, 2, seed=5)
    b = run_double_spend(0.4, 2, seed=5)
    assert a == b
