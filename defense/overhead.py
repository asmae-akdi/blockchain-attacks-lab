"""Etape 6.4 : mesure du SURCOUT des defenses sur une blockchain sans attaque.

- fraction du temps en alarme (fausses alarmes) -> delai de confirmation
  supplementaire impose aux clients honnetes ;
- refus abusifs de la garde anti-reorg ;
- temps de calcul du moniteur.
"""
import time

from defense.adaptive_confirmations import OnlineMonitor
from defense.protected_chain import protect
from sim.simulation import SimConfig, run_simulation


def measure_overhead(z_base: int = 2, z_alarm: int = 6, seed: int = 0,
                     n_nodes: int = 10, block_interval: float = 60.0,
                     latency_mean: float = 2.0, loss_prob: float = 0.0,
                     n_blocks: int = 900, with_monitor: bool = True,
                     defense: dict | None = None, monitor_kw: dict | None = None):
    T = block_interval
    cfg = SimConfig(n_nodes=n_nodes, block_interval=T, duration=n_blocks * T,
                    latency_mean=latency_mean, loss_prob=loss_prob, seed=seed)
    holder = {}

    def setup(result):
        if defense:
            protect(result.nodes, seed=seed, **defense)
        if with_monitor:
            mon = OnlineMonitor(result, **(monitor_kw or {}))
            holder["m"] = mon
            mon.start()

    t0 = time.perf_counter()
    result = run_simulation(cfg, None, setup)
    elapsed = time.perf_counter() - t0

    mon = holder.get("m")
    frac_alarm, windows, alarm_windows = 0.0, 0, 0
    if mon is not None:
        windows, alarm_windows = mon.n_seen, mon.n_alarm
        t_first = (mon.w + mon.det.warmup * mon.s) * T      # fin de l'apprentissage
        times = [t_first + k * T for k in range(int((cfg.duration - t_first) / T))]
        if times:
            frac_alarm = sum(mon.alarm_active(t) for t in times) / len(times)

    honest = [n for n in result.nodes if n.honest]
    return {
        "seed": seed, "elapsed_s": elapsed,
        "windows": windows, "alarm_windows": alarm_windows,
        "frac_time_alarm": frac_alarm,
        "extra_delay_blocks": frac_alarm * (z_alarm - z_base),
        "rejected_reorgs": sum(len(getattr(n.chain, "rejected_reorgs", []))
                               for n in honest),
        "orphan_rate": result.nodes[-1].chain.orphan_rate(),
    }