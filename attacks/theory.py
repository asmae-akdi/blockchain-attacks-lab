"""Probabilite theorique de succes d'un double spending (modele de Nakamoto /
Rosenfeld, adapte a notre regle : l'attaquant doit etre STRICTEMENT plus long).

Pendant que les honnetes minent z blocs, l'attaquant (part q) en mine k
(loi binomiale negative). Il lui reste alors un retard z-k et il doit gagner
z-k+1 blocs nets : probabilite (q/p)^(z-k+1) si q < p, sinon 1.
"""


def double_spend_success_prob(q: float, z: int) -> float:
    p = 1.0 - q
    if q >= p:
        return 1.0
    r = q / p
    total, pk = 0.0, p ** z            # pk = P(k = 0)
    for k in range(0, 5000):
        total += pk * min(1.0, r ** (z - k + 1))
        pk *= (k + z) / (k + 1) * q    # P(k+1) a partir de P(k)
        if k > z and pk < 1e-15:
            break
    return total


def eyal_sirer_revenue(alpha: float, gamma: float = 0.5) -> float:
    """Part relative des blocs de la chaine principale gagnee par un mineur
    selfish mining de part de hash alpha (Eyal & Sirer, 2013,
    "Majority is not Enough"). gamma = fraction des noeuds honnetes qui,
    lors d'un ex-aequo, minent ensuite sur le bloc de l'attaquant
    (propagation/position reseau de l'attaquant)."""
    if alpha <= 0:
        return 0.0
    if alpha >= 0.5:
        return 1.0
    denom = 1 - alpha * (1 + (2 - alpha) * alpha)
    numer = alpha * (1 - alpha) ** 2 * (4 * alpha + gamma * (1 - 2 * alpha)) - alpha ** 3
    return numer / denom


def selfish_mining_threshold(gamma: float = 0.5) -> float:
    """Part de hash minimale au-dela de laquelle le selfish mining devient
    plus rentable que le minage honnete."""
    return (1 - gamma) / (3 - 2 * gamma)


# ---------------------------------------------------------------------------
# Selfish mining (Eyal & Sirer, 2014)
# ---------------------------------------------------------------------------
def selfish_revenue(alpha: float, gamma: float) -> float:
    """Part relative des recompenses du selfish miner (part de hash alpha).
    gamma = fraction du hash honnete qui mine sur le bloc du selfish miner
    lors d'une egalite (course entre deux branches de meme longueur)."""
    num = alpha * (1 - alpha) ** 2 * (4 * alpha + gamma * (1 - 2 * alpha)) - alpha ** 3
    den = 1 - alpha * (1 + (2 - alpha) * alpha)
    return num / den


def selfish_threshold(gamma: float) -> float:
    """Seuil de rentabilite : au-dela, le selfish mining bat le minage honnete."""
    return (1 - gamma) / (3 - 2 * gamma)
