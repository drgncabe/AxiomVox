from __future__ import annotations

import os
from pathlib import Path

from shared.axiomvox_shared.state import SystemStats


def collect_system_stats() -> SystemStats:
    uptime_seconds = _read_uptime_seconds()
    memory = _read_memory_mb()
    load = _read_load_average()
    return SystemStats(
        uptime_seconds=uptime_seconds,
        load_1m=load[0],
        load_5m=load[1],
        load_15m=load[2],
        memory_total_mb=memory[0],
        memory_available_mb=memory[1],
        memory_used_percent=_memory_used_percent(memory[0], memory[1]),
    )


def _read_uptime_seconds() -> int | None:
    try:
        text = Path("/proc/uptime").read_text(encoding="utf-8")
        return round(float(text.split()[0]))
    except (OSError, IndexError, ValueError):
        return None


def _read_load_average() -> tuple[float | None, float | None, float | None]:
    try:
        load = os.getloadavg()
    except (AttributeError, OSError):
        return (None, None, None)
    return (round(load[0], 2), round(load[1], 2), round(load[2], 2))


def _read_memory_mb() -> tuple[int | None, int | None]:
    values: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0].rstrip(":") in {"MemTotal", "MemAvailable"}:
                values[parts[0].rstrip(":")] = round(int(parts[1]) / 1024)
    except (OSError, ValueError):
        return (None, None)
    return (values.get("MemTotal"), values.get("MemAvailable"))


def _memory_used_percent(total_mb: int | None, available_mb: int | None) -> float | None:
    if not total_mb or available_mb is None:
        return None
    used = max(0, total_mb - available_mb)
    return round((used / total_mb) * 100, 1)
