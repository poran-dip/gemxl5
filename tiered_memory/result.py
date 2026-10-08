"""Parsing of the RESULT line every workload prints, plus throughput derived from it."""

from .workloads import WORK_UNIT


def parse_result(text):
    """Fields of the last RESULT line in text (name, ws_mb, iters, roi_sec, work, checksum)."""
    last = None
    for line in text.splitlines():
        if line.startswith("RESULT"):
            last = line
    if last is None:
        return {}
    return dict(kv.split("=", 1) for kv in last.split()[1:] if "=" in kv)


def throughput_cols(name, work, seconds):
    """work, its unit, work/s, and ns per unit of work (ns per hop for chase = latency).

    seconds must be time for the same region the work was counted over (the ROI).
    """
    try:
        work, seconds = float(work), float(seconds)
    except (TypeError, ValueError):
        return {}
    cols = {"work": work, "work_unit": WORK_UNIT.get(name, "")}
    if seconds > 0:
        cols["throughput"] = work / seconds
    if work > 0:
        cols["ns_per_work"] = seconds * 1e9 / work
    return cols
