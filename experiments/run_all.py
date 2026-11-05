"""Point d'entree unique des experiences finales (reproductibilite).

    python experiments/run_all.py                 # configuration complete
    python experiments/run_all.py --quick         # essai rapide (quelques minutes)
    python experiments/run_all.py --only sensitivity   (ou : detection)

Ecrit aussi results/manifest.json : configuration + versions des bibliotheques.
"""
import argparse
import copy
import json
import os
import platform
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy
import pandas
import sklearn
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results")


def quick_config(cfg):
    c = copy.deepcopy(cfg)
    c["trials"].update(attack51=20, selfish=2, selfish_blocks=800, reference=2)
    c["sweeps"].update(n_nodes=[10, 20], latency_mean=[2, 10], patience=[3, 30])
    c["cases"]["selfish"]["alpha"] = [0.25, 0.40]
    c["detection"]["conditions"] = c["detection"]["conditions"][:2]
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=os.path.join(HERE, "configs", "final.yaml"))
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--only", choices=["sensitivity", "detection"])
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config, encoding="utf-8"))
    if args.quick:
        cfg = quick_config(cfg)
    os.makedirs(OUT, exist_ok=True)
    manifest = {"date": time.strftime("%Y-%m-%d %H:%M:%S"), "quick": args.quick,
                "python": platform.python_version(), "numpy": numpy.__version__,
                "pandas": pandas.__version__, "sklearn": sklearn.__version__, "config": cfg}
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    t0 = time.time()
    if args.only in (None, "sensitivity"):
        print("##### 7.1 Analyse de sensibilite #####")
        from experiments import run_sensitivity
        run_sensitivity.run(cfg)
    if args.only in (None, "detection"):
        print("\n##### 7.2 Robustesse de la detection #####")
        from experiments import run_detection_robustness
        run_detection_robustness.run(cfg, quick=args.quick)
    print(f"\nTermine en {time.time() - t0:.0f} s. Resultats dans experiments/results/")


if __name__ == "__main__":
    main()
