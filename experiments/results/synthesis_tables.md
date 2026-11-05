# Tableaux de synthese (Etape 7.3)

## Synthese : reference / attaquee / protegee

| scenario | succes_double_spend | perte_marchand | profit_attaquant | part_recompenses | gain_vs_equitable | orphelins | refus_garde |
|---|---|---|---|---|---|---|---|
| Reference (sans attaque) | 0.000 | 0.000 | 0.000 |  | 0.000 | 0.030 | 0.000 |
| 51 % ATTAQUEE, z=2 | 0.630 | 630.000 | -196.136 |  |  |  | 0.000 |
| 51 % PROTEGEE (garde D=4), z=2 | 0.450 | 450.000 | -525.136 |  |  |  | 0.290 |
| 51 % ATTAQUEE, z=6 | 0.480 | 480.000 | -995.874 |  |  |  | 0.000 |
| 51 % PROTEGEE (garde D=4), z=6 | 0.000 | 0.000 | -1772.374 |  |  |  | 1.070 |
| Selfish mining ATTAQUEE |  |  |  | 0.510 | 0.110 | 0.308 | 0.000 |
| Selfish mining PROTEGEE (depart aleatoire) |  |  |  | 0.526 | 0.126 | 0.304 | 0.000 |
| Selfish mining PROTEGEE (garde D=3) |  |  |  | 0.150 | -0.250 | 0.691 | 9306.800 |

## 51 % + double spending : sans defense vs garde anti-reorg

| alpha | z | config | n | succes | ic_bas | ic_haut | perte_marchand | profit_attaquant | refus_garde | variation_vs_sans_defense |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.300 | 2 | garde D=4 | 100 | 0.220 | 0.150 | 0.311 | 220.000 | -531.699 | 0.070 | -0.050 |
| 0.300 | 2 | sans defense | 100 | 0.270 | 0.193 | 0.364 | 270.000 | -465.699 | 0.000 | 0.000 |
| 0.400 | 2 | garde D=4 | 100 | 0.450 | 0.356 | 0.548 | 450.000 | -525.136 | 0.290 | -0.180 |
| 0.400 | 2 | sans defense | 100 | 0.630 | 0.532 | 0.718 | 630.000 | -196.136 | 0.000 | 0.000 |
| 0.450 | 2 | garde D=4 | 100 | 0.440 | 0.347 | 0.538 | 440.000 | -714.211 | 0.580 | -0.250 |
| 0.450 | 2 | sans defense | 100 | 0.690 | 0.594 | 0.772 | 690.000 | -208.211 | 0.000 | 0.000 |
| 0.300 | 6 | garde D=4 | 100 | 0.000 | 0.000 | 0.037 | 0.000 | -1020.491 | 0.150 | -0.090 |
| 0.300 | 6 | sans defense | 100 | 0.090 | 0.048 | 0.162 | 90.000 | -890.991 | 0.000 | 0.000 |
| 0.400 | 6 | garde D=4 | 100 | 0.000 | 0.000 | 0.037 | 0.000 | -1772.374 | 1.070 | -0.480 |
| 0.400 | 6 | sans defense | 100 | 0.480 | 0.385 | 0.577 | 480.000 | -995.874 | 0.000 | 0.000 |
| 0.450 | 6 | garde D=4 | 100 | 0.000 | 0.000 | 0.037 | 0.000 | -1691.054 | 2.190 | -0.720 |
| 0.450 | 6 | sans defense | 100 | 0.720 | 0.625 | 0.799 | 720.000 | -396.054 | 0.000 | 0.000 |

## Selfish mining : sans defense vs depart aleatoire vs garde

| alpha | config | n | part | ic95 | gain_vs_equitable | orphelins | refus_garde | theorie |
|---|---|---|---|---|---|---|---|---|
| 0.250 | depart aleatoire | 10 | 0.251 | 0.006 | 0.001 | 0.200 | 0.000 | 0.250 |
| 0.250 | garde D=3 | 10 | 0.169 | 0.032 | -0.081 | 0.558 | 7175.400 |  |
| 0.250 | sans defense | 10 | 0.218 | 0.007 | -0.032 | 0.197 | 0.000 | 0.219 |
| 0.300 | depart aleatoire | 10 | 0.330 | 0.012 | 0.030 | 0.229 | 0.000 | 0.327 |
| 0.300 | garde D=3 | 10 | 0.186 | 0.055 | -0.114 | 0.646 | 9232.000 |  |
| 0.300 | sans defense | 10 | 0.310 | 0.008 | 0.010 | 0.233 | 0.000 | 0.296 |
| 0.350 | depart aleatoire | 10 | 0.412 | 0.010 | 0.062 | 0.259 | 0.000 | 0.416 |
| 0.350 | garde D=3 | 10 | 0.145 | 0.062 | -0.205 | 0.717 | 9292.300 |  |
| 0.350 | sans defense | 10 | 0.390 | 0.008 | 0.040 | 0.260 | 0.000 | 0.388 |
| 0.400 | depart aleatoire | 10 | 0.526 | 0.012 | 0.126 | 0.304 | 0.000 | 0.526 |
| 0.400 | garde D=3 | 10 | 0.150 | 0.128 | -0.250 | 0.691 | 9306.800 |  |
| 0.400 | sans defense | 10 | 0.510 | 0.020 | 0.110 | 0.308 | 0.000 | 0.502 |

## Confirmations fixes vs adaptatives

| alpha | config | episodes | succes | ic_bas | ic_haut |
|---|---|---|---|---|---|
| 0.300 | adaptatif 2->6 | 239 | 0.234 | 0.185 | 0.292 |
| 0.300 | adaptatif 2->6 + garde D=4 | 230 | 0.183 | 0.138 | 0.238 |
| 0.300 | z=2 fixe | 239 | 0.234 | 0.185 | 0.292 |
| 0.300 | z=6 fixe | 203 | 0.153 | 0.110 | 0.209 |
| 0.400 | adaptatif 2->6 | 210 | 0.462 | 0.396 | 0.529 |
| 0.400 | adaptatif 2->6 + garde D=4 | 214 | 0.322 | 0.263 | 0.388 |
| 0.400 | z=2 fixe | 216 | 0.491 | 0.425 | 0.557 |
| 0.400 | z=6 fixe | 163 | 0.350 | 0.281 | 0.426 |

## Surcout des defenses (sans attaque)

| condition | config | temps_calcul_s | part_temps_en_alarme | delai_supp_blocs | refus_garde | orphelins | n | surcout_calcul_x | delai_z6_fixe_blocs |
|---|---|---|---|---|---|---|---|---|---|
| degradee | moniteur | 3.040 | 0.473 | 1.892 | 0.000 | 0.152 | 5 | 18.618 | 4.000 |
| degradee | moniteur + garde D=4 | 3.138 | 0.473 | 1.892 | 0.000 | 0.152 | 5 | 19.220 | 4.000 |
| degradee | sans moniteur | 0.163 | 0.000 | 0.000 | 0.000 | 0.152 | 5 | 1.000 | 4.000 |
| standard | moniteur | 3.214 | 0.000 | 0.000 | 0.000 | 0.030 | 5 | 21.222 | 4.000 |
| standard | moniteur + garde D=4 | 3.004 | 0.000 | 0.000 | 0.000 | 0.030 | 5 | 19.835 | 4.000 |
| standard | sans moniteur | 0.151 | 0.000 | 0.000 | 0.000 | 0.030 | 5 | 1.000 | 4.000 |

## Detection (Etape 5) : regles fixes vs adaptatives

| condition | detecteur | precision | recall | false_alarm_rate_normal | selfish_detected | selfish_delay_blocks | attack51_detected | attack51_delay_blocks |
|---|---|---|---|---|---|---|---|---|
| standard | Regles fixes | 0.956 | 0.861 | 0.052 | 1.000 | 10.000 | 0.967 | 3.026 |
| standard | Regles adaptatives | 0.900 | 0.703 | 0.091 | 1.000 | 10.000 | 0.889 | 3.315 |
| stressed | Regles fixes | 0.627 | 0.945 | 0.671 | 1.000 | 5.000 | 0.998 | 2.787 |
| stressed | Regles adaptatives | 0.758 | 0.452 | 0.136 | 1.000 | 17.500 | 0.768 | 3.787 |
