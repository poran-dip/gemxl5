"""Planning and stopping rules for a descending memory-limit sweep (pure logic, no I/O).

Start with plenty of memory, lower the limit step by step, and stop once the workload is
clearly hurting, so the sweep never spends minutes inside a thrashing run.
"""

import math

from .workloads import NATIVE_WS

# memory limit as a multiple of the working set: from roomy down to heavily starved
DEFAULT_FACTORS = (2.0, 1.5, 1.25, 1.0, 0.75, 0.5, 0.375, 0.25)

# small working sets for quick native runs (MiB); see tiered_memory/workloads.py
DEFAULT_WS = NATIVE_WS


def limits_mb(ws_mb, factors=DEFAULT_FACTORS):
    """Descending memory limits in MiB, one per factor, without duplicates."""
    out = []
    for f in sorted(factors, reverse=True):
        mb = max(1, math.ceil(ws_mb * f))
        if mb not in out:
            out.append(mb)
    return out


def slowdown(roi_sec, baseline_roi_sec):
    """ROI time relative to the unlimited baseline (2.0 = twice as slow); blank if unknown."""
    try:
        roi, base = float(roi_sec), float(baseline_roi_sec)
    except (TypeError, ValueError):
        return ""
    return round(roi / base, 2) if base > 0 else ""


def bottleneck(row, stop_slowdown):
    """Why this run counts as a bottleneck ('' if it does not)."""
    if row.get("status") != "ok":
        return str(row.get("status"))
    s = row.get("slowdown", "")
    if s != "" and s >= stop_slowdown:
        return f"slowdown>={stop_slowdown}x"
    return ""


def run_timeout(baseline_wall_sec, mult, floor, ceiling):
    """Time allowed for a limited run: mult x the unlimited run, within [floor, ceiling]."""
    return min(ceiling, max(floor, baseline_wall_sec * mult))


class Knee:
    """Decides when to stop descending: past_knee more runs after the first bottleneck."""

    def __init__(self, past_knee=1):
        self.past_knee = past_knee
        self.left = None  # None until the first bottleneck

    def should_stop(self, is_bottleneck, failed):
        if failed:
            return True
        if self.left is None:
            if not is_bottleneck:
                return False
            self.left = self.past_knee
        else:
            self.left -= 1
        return self.left <= 0
