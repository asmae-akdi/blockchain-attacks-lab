from defense.overhead import measure_overhead


def test_overhead_sans_moniteur():
    r = measure_overhead(with_monitor=False, n_blocks=120)
    assert r["windows"] == 0
    assert r["frac_time_alarm"] == 0.0
    assert r["extra_delay_blocks"] == 0.0


def test_overhead_avec_moniteur_et_garde():
    r = measure_overhead(n_blocks=300, defense={"max_reorg_depth": 4})
    assert r["windows"] > 40
    assert 0.0 <= r["frac_time_alarm"] <= 1.0
    assert r["extra_delay_blocks"] <= 4.0 + 1e-9    # borne : z_alarm - z_base
    assert r["rejected_reorgs"] >= 0