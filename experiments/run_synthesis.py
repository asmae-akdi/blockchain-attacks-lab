"""Etape 7.3 : synthese REFERENCE / ATTAQUEE / PROTEGEE.

Lit les CSV deja produits (Etapes 2 a 6) dans experiments/results/ et fabrique :
  - les tableaux finaux (CSV + synthesis_tables.md, pret a copier dans le rapport)
  - les figures de synthese
Aucune simulation n'est relancee.

Usage : python experiments/run_synthesis.py [dossier_resultats]
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from attacks.theory import selfish_revenue

DEFAULT_RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
Z6_FIXED_DELAY = 4.0      # z=6 fixe impose 6-2 = 4 blocs de plus en permanence
GAMMA_NO_DEFENSE = 0.21   # gamma mesure a l'Etape 4 (remplace par selfish_summary.csv si present)


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def ci95(x):
    x = np.asarray(x, float)
    return 1.96 * x.std(ddof=1) / math.sqrt(len(x)) if len(x) > 1 else 0.0


def load(res, name):
    p = os.path.join(res, name)
    return pd.read_csv(p) if os.path.exists(p) else None


# ------------------------------------------------------------------ tableaux
def table_attack51(d):
    rows = []
    for (a, z, cfg), g in d.groupby(["alpha", "z", "config"]):
        n, k = len(g), int(g.success.sum())
        lo, hi = wilson(k, n)
        rows.append({"alpha": a, "z": z, "config": cfg, "n": n, "succes": k / n,
                     "ic_bas": lo, "ic_haut": hi,
                     "perte_marchand": g.merchant_loss.mean(),
                     "profit_attaquant": g.attacker_profit.mean(),
                     "refus_garde": g.rejected_reorgs.mean()})
    t = pd.DataFrame(rows).sort_values(["z", "alpha", "config"]).reset_index(drop=True)
    base = t[t.config == "sans defense"].set_index(["alpha", "z"]).succes
    t["variation_vs_sans_defense"] = [s - base.get((a, z), np.nan)
                                      for a, z, s in zip(t.alpha, t.z, t.succes)]
    return t


def table_selfish(d, gamma_nd):
    rows = []
    for (a, cfg), g in d.groupby(["alpha", "config"]):
        theory = (selfish_revenue(a, gamma_nd) if cfg == "sans defense"
                  else selfish_revenue(a, 0.5) if cfg == "depart aleatoire" else np.nan)
        rows.append({"alpha": a, "config": cfg, "n": len(g), "part": g.share.mean(),
                     "ic95": ci95(g.share), "gain_vs_equitable": g.share.mean() - a,
                     "orphelins": g.orphan_rate.mean(), "refus_garde": g.rejected.mean(),
                     "theorie": theory})
    return pd.DataFrame(rows).sort_values(["alpha", "config"]).reset_index(drop=True)


def table_overhead(d):
    t = (d.groupby(["condition", "config"])
          .agg(temps_calcul_s=("elapsed_s", "mean"), part_temps_en_alarme=("frac_time_alarm", "mean"),
               delai_supp_blocs=("extra_delay_blocks", "mean"), refus_garde=("rejected_reorgs", "mean"),
               orphelins=("orphan_rate", "mean"), n=("seed", "count")).reset_index())
    ref = t[t.config == "sans moniteur"].set_index("condition").temps_calcul_s
    t["surcout_calcul_x"] = [v / ref[c] for c, v in zip(t.condition, t.temps_calcul_s)]
    t["delai_z6_fixe_blocs"] = Z6_FIXED_DELAY
    return t


def pick(d, names, *cands):
    for c in cands:
        if c in d.columns:
            return c
    return None


def table_adaptive(ep):
    """Confirmations adaptatives (episodes). Les noms de colonnes sont detectes."""
    cs = pick(ep, None, "success", "succes")
    cc, ca = pick(ep, None, "config"), pick(ep, None, "alpha")
    if not (cs and cc and ca):
        return None, f"colonnes non reconnues dans adaptive_episodes.csv : {list(ep.columns)}"
    cd = pick(ep, None, "time_to_delivery", "delai_livraison")
    rows = []
    for (a, cfg), g in ep.groupby([ca, cc]):
        n, k = len(g), int(g[cs].sum())
        lo, hi = wilson(k, n)
        row = {"alpha": a, "config": cfg, "episodes": n, "succes": k / n, "ic_bas": lo, "ic_haut": hi}
        if cd:
            row["delai_livraison_blocs"] = g[cd].dropna().mean() / 60.0 if g[cd].max() > 60 \
                else g[cd].dropna().mean()
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["alpha", "config"]).reset_index(drop=True), None


def final_comparison(a51, sf, ov, alpha):
    ref_orph = np.nan
    if ov is not None:
        r = ov[(ov.condition == "standard") & (ov.config == "sans moniteur")]
        ref_orph = float(r.orphelins.iloc[0]) if len(r) else np.nan
    rows = [{"scenario": "Reference (sans attaque)", "succes_double_spend": 0.0, "perte_marchand": 0.0,
             "profit_attaquant": 0.0, "part_recompenses": np.nan, "gain_vs_equitable": 0.0,
             "orphelins": ref_orph, "refus_garde": 0.0}]
    for z in sorted(a51.z.unique()):
        for cfg, lab in (("sans defense", "ATTAQUEE"), ("garde D=4", "PROTEGEE (garde D=4)")):
            r = a51[(a51.alpha == alpha) & (a51.z == z) & (a51.config == cfg)]
            if len(r):
                r = r.iloc[0]
                rows.append({"scenario": f"51 % {lab}, z={z}", "succes_double_spend": r.succes,
                             "perte_marchand": r.perte_marchand, "profit_attaquant": r.profit_attaquant,
                             "part_recompenses": np.nan, "gain_vs_equitable": np.nan,
                             "orphelins": np.nan, "refus_garde": r.refus_garde})
    labs = {"sans defense": "ATTAQUEE", "depart aleatoire": "PROTEGEE (depart aleatoire)",
            "garde D=3": "PROTEGEE (garde D=3)"}
    for cfg, lab in labs.items():
        r = sf[(sf.alpha == alpha) & (sf.config == cfg)]
        if len(r):
            r = r.iloc[0]
            rows.append({"scenario": f"Selfish mining {lab}", "succes_double_spend": np.nan,
                         "perte_marchand": np.nan, "profit_attaquant": np.nan,
                         "part_recompenses": r.part, "gain_vs_equitable": r.gain_vs_equitable,
                         "orphelins": r.orphelins, "refus_garde": r.refus_garde})
    return pd.DataFrame(rows)


def table_detection(det):
    if det is None:
        return None
    keep = det[det.detecteur.isin(["Regles fixes", "Regles adaptatives"])]
    cols = [c for c in ["condition", "detecteur", "precision", "recall", "false_alarm_rate_normal",
                        "selfish_detected", "selfish_delay_blocks", "attack51_detected",
                        "attack51_delay_blocks"] if c in keep.columns]
    return keep[cols].reset_index(drop=True)


# ------------------------------------------------------------------ markdown
def to_md(df, nd=3):
    if df is None or df.empty:
        return "_(donnees indisponibles)_\n"
    def f(v):
        if isinstance(v, (float, np.floating)):
            return "" if np.isnan(v) else f"{v:.{nd}f}"
        return str(v)
    out = ["| " + " | ".join(df.columns) + " |", "|" + "|".join("---" for _ in df.columns) + "|"]
    out += ["| " + " | ".join(f(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ figures
def fig_attack51(a51, res):
    zs = sorted(a51.z.unique())
    fig, axes = plt.subplots(1, len(zs), figsize=(5.5 * len(zs), 4), sharey=True, squeeze=False)
    for ax, z in zip(axes[0], zs):
        alphas = sorted(a51.alpha.unique())
        x = np.arange(len(alphas))
        for i, cfg in enumerate(["sans defense", "garde D=4"]):
            g = a51[(a51.z == z) & (a51.config == cfg)].set_index("alpha").reindex(alphas)
            ax.bar(x + (i - .5) * .38, g.succes, .38, label=cfg,
                   yerr=[g.succes - g.ic_bas, g.ic_haut - g.succes], capsize=3)
        ax.set_xticks(x); ax.set_xticklabels([f"{a:.2f}" for a in alphas])
        ax.set_xlabel("part de hash de l'attaquant"); ax.set_title(f"z = {z}")
        ax.set_ylim(0, 1); ax.grid(axis="y", alpha=.3)
    axes[0][0].set_ylabel("taux de reussite du double spending"); axes[0][0].legend()
    fig.suptitle("51 % : attaquee vs protegee (garde anti-reorg D=4)")
    fig.tight_layout(); fig.savefig(os.path.join(res, "synthesis_attack51.png"), dpi=150)


def fig_selfish(sf, res):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    xs = np.linspace(sf.alpha.min(), sf.alpha.max(), 60)
    ax.plot(xs, xs, "k:", label="part equitable (minage honnete)")
    for cfg, c in (("sans defense", "C0"), ("depart aleatoire", "C1"), ("garde D=3", "C3")):
        g = sf[sf.config == cfg]
        ax.errorbar(g.alpha, g.part, yerr=g.ic95, fmt="o-", color=c, capsize=3, label=cfg)
    ax.plot(xs, [selfish_revenue(x, 0.5) for x in xs], "--", color="C1", alpha=.5,
            label="theorie gamma=0,5")
    ax.set_xlabel("part de hash du selfish miner"); ax.set_ylabel("part des recompenses")
    ax.set_title("Selfish mining : attaquee vs protegee")
    ax.grid(alpha=.3); ax.legend(fontsize=8); fig.tight_layout()
    fig.savefig(os.path.join(res, "synthesis_selfish.png"), dpi=150)


def fig_overhead(ov, res):
    t = ov[ov.config != "sans moniteur"]
    conds = list(t.condition.unique())
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for ax, col, lab in ((axes[0], "delai_supp_blocs", "delai de confirmation supplementaire (blocs)"),
                         (axes[1], "surcout_calcul_x", "surcout de calcul (x)")):
        cfgs = list(t.config.unique())
        for i, cfg in enumerate(cfgs):
            vals = [t[(t.condition == c) & (t.config == cfg)][col].mean() for c in conds]
            ax.bar(np.arange(len(conds)) + (i - (len(cfgs) - 1) / 2) * .35, vals, .35, label=cfg)
        ax.set_xticks(range(len(conds))); ax.set_xticklabels(conds); ax.set_ylabel(lab)
        ax.grid(axis="y", alpha=.3)
    axes[0].axhline(Z6_FIXED_DELAY, color="r", ls="--", label="z=6 fixe (4 blocs en permanence)")
    axes[0].legend(fontsize=8)
    fig.suptitle("Surcout des defenses (sans attaque)")
    fig.tight_layout(); fig.savefig(os.path.join(res, "synthesis_overhead.png"), dpi=150)


def fig_adaptive(ad, res):
    if "delai_livraison_blocs" not in ad.columns:
        return
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    for cfg, g in ad.groupby("config"):
        ax.scatter(g.delai_livraison_blocs, g.succes, s=60, label=cfg)
    ax.set_xlabel("delai de livraison moyen (blocs)"); ax.set_ylabel("taux de succes de l'attaque")
    ax.set_title("Compromis protection / delai (confirmations)")
    ax.grid(alpha=.3); ax.legend(fontsize=8); fig.tight_layout()
    fig.savefig(os.path.join(res, "synthesis_adaptive_tradeoff.png"), dpi=150)


# ------------------------------------------------------------------ main
def build(res, alpha=0.40):
    out, notes = {}, []
    d51, dsf = load(res, "defense_attack51.csv"), load(res, "defense_selfish.csv")
    dov, dep = load(res, "overhead.csv"), load(res, "adaptive_episodes.csv")
    if d51 is not None:
        out["attack51"] = table_attack51(d51)
    if dsf is not None:
        gam = GAMMA_NO_DEFENSE
        s4 = load(res, "selfish_summary.csv")
        if s4 is not None and "gamma_emp" in s4.columns:
            gam = float(s4.gamma_emp.mean())
        out["selfish"] = table_selfish(dsf, gam)
    if dov is not None:
        out["overhead"] = table_overhead(dov)
    if dep is not None:
        t, err = table_adaptive(dep)
        if t is not None:
            out["adaptive"] = t
        else:
            notes.append(err)
    if "attack51" in out and "selfish" in out:
        out["final"] = final_comparison(out["attack51"], out["selfish"], out.get("overhead"), alpha)
    det = table_detection(load(res, "detection_results.csv"))
    if det is not None:
        out["detection"] = det
    return out, notes


TITLES = {"final": "Synthese : reference / attaquee / protegee",
          "attack51": "51 % + double spending : sans defense vs garde anti-reorg",
          "selfish": "Selfish mining : sans defense vs depart aleatoire vs garde",
          "adaptive": "Confirmations fixes vs adaptatives",
          "overhead": "Surcout des defenses (sans attaque)",
          "detection": "Detection (Etape 5) : regles fixes vs adaptatives"}


def main(res=DEFAULT_RES, alpha=0.40):
    tables, notes = build(res, alpha)
    md = ["# Tableaux de synthese (Etape 7.3)\n"]
    for key, title in TITLES.items():
        if key in tables:
            tables[key].to_csv(os.path.join(res, f"synthesis_{key}.csv"), index=False)
            md.append(f"## {title}\n\n{to_md(tables[key])}")
            print(f"\n=== {title} ===\n{tables[key].round(3).to_string(index=False)}")
    with open(os.path.join(res, "synthesis_tables.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    if "attack51" in tables:
        fig_attack51(tables["attack51"], res)
    if "selfish" in tables:
        fig_selfish(tables["selfish"], res)
    if "overhead" in tables:
        fig_overhead(tables["overhead"], res)
    if "adaptive" in tables:
        fig_adaptive(tables["adaptive"], res)
    for n in notes:
        print("\nATTENTION :", n)
    print(f"\nFichiers ecrits dans {res}")
    return tables


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_RES)
