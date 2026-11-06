# Blockchain Attacks Lab

Plateforme expérimentale de simulation, détection et mitigation d'attaques sur une blockchain Proof of Work, écrite en Python.

Projet réalisé dans le cadre de l'**Atelier 2 – Partie Blockchain** . Il prolonge la blockchain PoW/PoS implémentée from scratch à l'Atelier 1 (SHA-256, blocs, minage, arbre de Merkle).



---

## Ce que fait le projet

| Volet | Contenu |
|---|---|
| **Simulation** | Simulateur à événements discrets : nœuds, latence aléatoire, pertes de messages, forks, orphelins, réorganisations |
| **Attaques** | Attaque des **51 % avec double spending** et réorganisation de chaîne ; **selfish mining** (stratégie d'Eyal & Sirer) |
| **Détection** | Détecteur **adaptatif** fondé sur 9 métriques réseau (médiane et MAD glissants), comparé à des règles fixes, Isolation Forest et Random Forest |
| **Défense** | Garde anti-réorganisation, départage aléatoire des branches, confirmations adaptatives déclenchées par l'alarme |
| **Évaluation** | Référence vs attaquée vs protégée : taux de réussite, précision/rappel, temps de détection, pertes économiques, surcoût |
| **Reproductibilité** | Graines fixées, configuration YAML, manifeste des versions, tests automatisés |

**Périmètre.** Deux attaques sur les quatre de l'énoncé sont implémentées (51 % + double spending, selfish mining). Le Block Withholding et l'attaque Sybil sont laissés en perspective. Seul le consensus PoW est attaqué.

---

## Résultats principaux

Tous les chiffres viennent des expériences de ce dépôt (voir `experiments/results/`).

**Le simulateur reproduit la théorie.** Avec le paramètre γ ≈ 0,21 mesuré dans la simulation, la part de récompenses du selfish mining colle à la formule d'Eyal & Sirer à environ 1 point près ; le seuil de rentabilité observé est α ≈ 0,30.

| α (selfish miner) | Part des récompenses (simulation) | Théorie (γ mesuré) |
|---|---|---|
| 0,25 | 22,0 % | 21,8 % |
| 0,35 | 39,5 % | 38,8 % |
| 0,40 | 51,5 % | 50,2 % |

**Détection adaptative : stable quand le réseau change.** Fausses alarmes sur réseau honnête (détecteurs réglés une seule fois en conditions standard) :

| Latence moyenne | Règles fixes | Règles adaptatives |
|---|---|---|
| 1 s | 1,2 % | 4,5 % |
| 5 s | 22,5 % | 4,0 % |
| 10 s | 53,8 % | 3,8 % |

Le prix est un rappel plus faible (0,35 à 0,77 selon la condition, contre 0,84 à 0,94 pour les règles fixes). Avec 10 % de pertes, l'adaptatif n'améliore presque rien (40,7 % contre 45,5 %).

**Contre-mesures : résultats contrastés.**

- La **garde anti-réorganisation** (D = 4) ramène le succès du double spending à **0 %** pour z = 6 (structurel, D < z) et le réduit pour z = 2.
- « Confirmations adaptatives + garde » offre une protection comparable à z = 6 fixe avec un délai de livraison de 4,3 blocs au lieu de 10,2.
- Le **départage aléatoire** et la **garde D = 3** ne protègent **pas** contre le selfish mining dans notre modèle (résultats négatifs documentés dans le rapport).

---

## Structure du projet

```
blockchain-attacks-lab/
├── core/          SHA-256, Merkle, blocs, arbre de blocs, minage réel et statistique
├── sim/           moteur à événements discrets, réseau, nœud honnête, simulation
├── attacks/       attack_51.py, selfish.py, selfish_variants.py, theory.py
├── detection/     métriques, détecteurs, jeux de données étiquetés, évaluation
├── defense/       chaîne protégée, confirmations adaptatives, mesure du surcoût
├── experiments/   scripts d'expériences, configs/final.yaml, results/
├── tests/         tests automatisés (pytest)
├
└── requirements.txt
```

---

## Installation

Python 3.10 ou plus.

```bash
git clone <https://github.com/asmae-akdi/blockchain-attacks-lab.git>
cd blockchain-attacks-lab
python -m pip install -r requirements.txt
```

Dépendances : `numpy`, `pandas`, `matplotlib`, `scikit-learn`, `pyyaml`, `pytest`.

---

## Utilisation

Toutes les commandes se lancent depuis la racine du projet. Les CSV et figures sont écrits dans `experiments/results/`.

| Commande | Effet |
|---|---|
| `python -m pytest -q` | lance les tests automatisés |
| `python experiments/run_reference.py` | blockchain de référence : orphelins vs latence |
| `python experiments/run_attack51.py 300` | attaque 51 % + double spending (300 essais par cas) |
| `python experiments/run_selfish.py 20` | selfish mining (20 graines par valeur de α) |
| `python experiments/run_detection.py` | comparaison des détecteurs |
| `python experiments/run_defense.py 100 10` | garde anti-réorganisation et départage aléatoire |
| `python experiments/run_adaptive.py 8` | confirmations fixes vs adaptatives |
| `python experiments/run_overhead.py 5` | surcoût des défenses |
| `python experiments/run_all.py` | sensibilité et robustesse (option `--quick` pour un essai rapide) |
| `python experiments/run_synthesis.py` | tableaux et figures de synthèse |

Les expériences complètes sont longues (plusieurs dizaines de minutes pour `run_all.py`). Pour un essai rapide : `python experiments/run_all.py --quick`.

### Exemple minimal

```python
from attacks.attack_51 import run_double_spend
from attacks.selfish import run_selfish

# Attaquant à 40 % du hash, marchand qui exige 2 confirmations
print(run_double_spend(alpha=0.40, z=2, seed=1))

# Selfish mining à 35 % du hash
print(run_selfish(alpha=0.35, seed=1, n_blocks=2000))
```

---

## Reproductibilité

- Toutes les simulations utilisent des générateurs aléatoires initialisés par une **graine** : même graine, mêmes résultats.
- Les paramètres de l'étape finale sont dans [`experiments/configs/final.yaml`](experiments/configs/final.yaml).
- `run_all.py` écrit `experiments/results/manifest.json` (configuration et versions des bibliothèques).
- Environnement des résultats publiés : Python 3.11.9, numpy 2.4.6, pandas 3.1.0, scikit-learn 1.9.1.

---

## Limites

- 2 attaques sur 4 ; PoW uniquement.
- Réseau en graphe complet, sans topologie P2P ; temps de minage modélisé par une loi exponentielle.
- Une attaque 51 % est invisible avant sa publication : l'alarme ne peut pas protéger la première double dépense.
- Le détecteur adaptatif perd du rappel et n'aide presque pas en présence de pertes de messages importantes.
- Le moniteur en ligne recalcule les métriques sur tout l'historique (surcoût de calcul d'environ 20 fois, lié à l'implémentation).
- Certaines explications (scission du réseau avec la garde D = 3, échec du détecteur avec des pertes) sont des **hypothèses non vérifiées**.



---

## Perspectives

Block Withholding dans une pool de minage, attaque Sybil avec topologie P2P explicite, extension au PoS, calcul incrémental des métriques, détection des stratégies de publication optimales.

---

## Références

1. S. Nakamoto, *Bitcoin: A Peer-to-Peer Electronic Cash System*, 2008.
2. M. Rosenfeld, *Analysis of Hashrate-Based Double Spending*, 2014.
3. I. Eyal et E. G. Sirer, *Majority is not Enough: Bitcoin Mining is Vulnerable*, Financial Cryptography, 2014.
4. A. Sapirshtein, Y. Sompolinsky et A. Zohar, *Optimal Selfish Mining Strategies in Bitcoin*, Financial Cryptography, 2016.
5. C. Decker et R. Wattenhofer, *Information Propagation in the Bitcoin Network*, IEEE P2P, 2013.
6. F. T. Liu, K. M. Ting et Z.-H. Zhou, *Isolation Forest*, IEEE ICDM, 2008.
7. L. Breiman, *Random Forests*, Machine Learning, 2001.

---

## Auteur

**[AKDI ASMAE ]** – [IDAI]
Encadrante : Pr. Ikram BEN ADBEL OUAHAB – Année universitaire 2026/2027

## MASTER

