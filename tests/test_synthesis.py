import numpy as np
import pandas as pd

from experiments import run_synthesis as syn


def _fake_results(tmp_path):
    rng = np.random.default_rng(0)
    rows = []
    for a in (0.3, 0.4):
        for z in (2, 6):
            for cfg in ("sans defense", "garde D=4"):
                for s in range(12):
                    ok = int(rng.random() < (0.5 if cfg == "sans defense" else 0.2))
                    rows.append(dict(alpha=a, z=z, seed=s, outcome="success" if ok else "gave_up",
                                     success=ok, delivered=1, time_to_delivery=200.0,
                                     attack_duration=900.0, private_blocks=3, reorg_depth=2 * ok,
                                     merchant_loss=1000.0 * ok, honest_blocks_orphaned=ok,
                                     attacker_profit=500.0 * ok - 300, t_start=600.0,
                                     t_publish=1000.0 if ok else np.nan, rejected_reorgs=0,
                                     config=cfg))
    pd.DataFrame(rows).to_csv(tmp_path / "defense_attack51.csv", index=False)
    rows = [dict(alpha=a, config=c, seed=s, share=a + rng.normal(0, .01), orphan_rate=.2, rejected=0)
            for a in (0.3, 0.4) for c in ("sans defense", "depart aleatoire", "garde D=3")
            for s in range(5)]
    pd.DataFrame(rows).to_csv(tmp_path / "defense_selfish.csv", index=False)
    rows = [dict(condition=c, config=m, seed=s, elapsed_s=0.15 if m == "sans moniteur" else 3.0,
                 windows=0, alarm_windows=0, frac_time_alarm=0.0 if m == "sans moniteur" else .1,
                 extra_delay_blocks=0.0 if m == "sans moniteur" else .4, rejected_reorgs=0,
                 orphan_rate=.03)
            for c in ("standard", "degradee") for m in ("sans moniteur", "moniteur")
            for s in range(3)]
    pd.DataFrame(rows).to_csv(tmp_path / "overhead.csv", index=False)
    rows = [dict(alpha=a, config=c, seed=s, success=int(rng.random() < .3), time_to_delivery=180.0)
            for a in (0.3, 0.4) for c in ("z=2 fixe", "z=6 fixe") for s in range(20)]
    pd.DataFrame(rows).to_csv(tmp_path / "adaptive_episodes.csv", index=False)


def test_synthesis_builds_tables_and_figures(tmp_path):
    _fake_results(tmp_path)
    tables = syn.main(str(tmp_path), alpha=0.4)
    for key in ("attack51", "selfish", "overhead", "adaptive", "final"):
        assert key in tables and len(tables[key]) > 0
    assert (tmp_path / "synthesis_tables.md").exists()
    for png in ("synthesis_attack51.png", "synthesis_selfish.png", "synthesis_overhead.png"):
        assert (tmp_path / png).exists()
    ov = tables["overhead"]
    assert (ov[ov.config == "sans moniteur"].surcout_calcul_x == 1.0).all()


def test_missing_adaptive_columns_gives_a_note_not_a_crash(tmp_path):
    _fake_results(tmp_path)
    pd.DataFrame({"foo": [1, 2]}).to_csv(tmp_path / "adaptive_episodes.csv", index=False)
    tables, notes = syn.build(str(tmp_path))
    assert "adaptive" not in tables and notes
