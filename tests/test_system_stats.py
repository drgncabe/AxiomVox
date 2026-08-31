from device.axiomvox_device import system_stats


def test_cpu_percent_uses_delta_between_samples(monkeypatch) -> None:
    samples = iter([(100, 80), (200, 120)])
    monkeypatch.setattr(system_stats, "_LAST_CPU_TIMES", None)
    monkeypatch.setattr(system_stats, "_read_cpu_times", lambda: next(samples))

    assert system_stats._read_cpu_used_percent() is None
    assert system_stats._read_cpu_used_percent() == 60.0
