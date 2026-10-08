#!/usr/bin/env python3
"""Fixed working set, shrinking RAM limit (cgroup v2 via systemd-run). Run with sudo.
Usage: sudo python3 sweep_ram.py --ws 1024 --limits 256 512 1024 none

Quick way to find where each workload starts to hurt (small working sets, limit lowered until
the slowdown passes --stop-slowdown, then stops):
       sudo python3 sweep_ram.py --descend
"""

import argparse
import csv
import os
import resource
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gemxl.descend import (  # noqa: E402
    DEFAULT_FACTORS,
    DEFAULT_WS,
    Knee,
    bottleneck,
    limits_mb,
    run_timeout,
    slowdown,
)
from gemxl.linuxstats import cpu_columns, delta_columns, snapshot  # noqa: E402
from gemxl.result import parse_result, throughput_cols  # noqa: E402

ITERS = {"stream": 3, "sort": 1, "gemm": 1, "chase": 2, "kvdecode": 8}


def run(binary, ws, iters, seed, limit_mb, timeout):
    cmd = [binary, "-s", str(ws), "-i", str(iters), "-r", str(seed)]
    if limit_mb is not None:
        cmd = [
            "systemd-run",
            "--scope",
            "--quiet",
            "-p",
            f"MemoryMax={limit_mb}M",
            "-p",
            "MemorySwapMax=infinity",
        ] + cmd
    ru0, snap0 = resource.getrusage(resource.RUSAGE_CHILDREN), snapshot()
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        status = "ok" if p.returncode == 0 else f"exit{p.returncode}"  # -9/137 = OOM killed
        out = p.stdout
    except subprocess.TimeoutExpired:
        status, out = "timeout", ""
    wall = time.time() - t0
    ru1, snap1 = resource.getrusage(resource.RUSAGE_CHILDREN), snapshot()
    row = {
        "workload": os.path.basename(binary),
        "ws_mb": ws,
        "limit_mb": "none" if limit_mb is None else limit_mb,
        "status": status,
        "wall_sec": f"{wall:.2f}",
    }
    row.update(cpu_columns(ru0, ru1, wall))
    # Whole-run window (allocation + ROI), where spill, swap and migration actually happen.
    row.update(delta_columns(snap0, snap1))
    d = parse_result(out)
    if d:
        row.update(roi_sec=d["roi_sec"], work=d["work"], checksum=d["checksum"])
        row.update(throughput_cols(row["workload"], d["work"], d["roi_sec"]))
    return row


def write_csv(path, rows):
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=keys, restval="")
        wr.writeheader()
        wr.writerows(rows)


def descend(binary, ws, iters, a, rows):
    """Unlimited baseline, then lower the limit until the workload is clearly bottlenecked."""

    def record(r):
        print(r, file=sys.stderr)
        rows.append(r)
        write_csv(a.out, rows)  # saved after every run, so Ctrl-C loses nothing

    base_runs = [run(binary, ws, iters, a.seed, None, a.timeout) for _ in range(a.baseline_reps)]
    good = [r for r in base_runs if r["status"] == "ok" and "roi_sec" in r]
    if not good:
        for r in base_runs:
            record({**r, "bottleneck": "baseline failed"})
        return
    base = min(good, key=lambda r: float(r["roi_sec"]))  # fastest of the reps, least noisy
    base.update(factor="none", slowdown=1.0, bottleneck="")
    record(base)
    timeout = run_timeout(float(base["wall_sec"]), a.timeout_mult, a.min_timeout, a.timeout)
    knee = Knee(a.past_knee)
    for lim in limits_mb(ws, a.factors):
        r = run(binary, ws, iters, a.seed, lim, timeout)
        r["factor"] = round(lim / ws, 3)
        r["slowdown"] = slowdown(r.get("roi_sec"), base["roi_sec"])
        r["bottleneck"] = bottleneck(r, a.stop_slowdown)
        record(r)
        if knee.should_stop(bool(r["bottleneck"]), r["status"] != "ok"):
            break


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument(
        "--bindir", default=str(Path(__file__).resolve().parents[1] / "workloads/build/native")
    )
    p.add_argument(
        "--ws", type=int, help="working set MiB (default: 1024; per-workload with --descend)"
    )
    p.add_argument("--limits", nargs="+", default=["256", "512", "1024", "none"])
    p.add_argument("--workloads", nargs="+", default=list(ITERS))
    p.add_argument("--timeout", type=int, default=900, help="hard cap per run, seconds")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", default="ram_sweep.csv")
    d = p.add_argument_group("--descend: find the knee, then stop")
    d.add_argument("--descend", action="store_true", help="lower the limit until slowdown hits")
    d.add_argument(
        "--factors",
        type=float,
        nargs="+",
        default=list(DEFAULT_FACTORS),
        help="limit as a multiple of the working set",
    )
    d.add_argument(
        "--stop-slowdown",
        type=float,
        default=1.5,
        help="bottleneck = ROI this many times slower than unlimited",
    )
    d.add_argument("--past-knee", type=int, default=1, help="extra runs after the knee")
    d.add_argument("--baseline-reps", type=int, default=2, help="unlimited runs, fastest is kept")
    d.add_argument("--timeout-mult", type=float, default=30, help="run cap = this x baseline wall")
    d.add_argument("--min-timeout", type=float, default=20, help="never cap below this, seconds")
    a = p.parse_args()
    if os.geteuid() != 0 and (a.descend or any(x != "none" for x in a.limits)):
        sys.exit("run with sudo (system-level cgroup needed)")
    rows = []
    for w in a.workloads:
        if a.descend:
            descend(f"{a.bindir}/{w}", a.ws or DEFAULT_WS[w], ITERS[w], a, rows)
            continue
        for x in a.limits:
            lim = None if x == "none" else int(x)
            r = run(f"{a.bindir}/{w}", a.ws or 1024, ITERS[w], a.seed, lim, a.timeout)
            print(r, file=sys.stderr)
            rows.append(r)
            write_csv(a.out, rows)
