#!/usr/bin/env python3
"""Fixed working set, shrinking RAM limit (cgroup v2 via systemd-run). Run with sudo.
Usage: sudo python3 sweep_ram.py --ws 1024 --limits 256 512 1024 none
"""
from pathlib import Path
import argparse, csv, os, resource, subprocess, sys, time

ITERS = {"stream": 3, "sort": 1, "gemm": 1, "chase": 2, "kvdecode": 8}

def run(binary, ws, iters, seed, limit_mb, timeout):
    cmd = [binary, "-s", str(ws), "-i", str(iters), "-r", str(seed)]
    if limit_mb is not None:
        cmd = ["systemd-run", "--scope", "--quiet",
               "-p", f"MemoryMax={limit_mb}M", "-p", "MemorySwapMax=infinity"] + cmd
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        status = "ok" if p.returncode == 0 else f"exit{p.returncode}"  # -9/137 = OOM killed
        out = p.stdout
    except subprocess.TimeoutExpired:
        status, out = "timeout", ""
    wall = time.time() - t0
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    row = {"workload": os.path.basename(binary), "ws_mb": ws,
           "limit_mb": "none" if limit_mb is None else limit_mb,
           "status": status, "wall_sec": f"{wall:.2f}",
           "majflt": after.ru_majflt - before.ru_majflt,
           "minflt": after.ru_minflt - before.ru_minflt}
    for l in out.splitlines():
        if l.startswith("RESULT"):
            d = dict(kv.split("=") for kv in l.split()[1:])
            row.update(roi_sec=d["roi_sec"], work=d["work"], checksum=d["checksum"])
    return row

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--bindir", default=str(Path(__file__).resolve().parents[1] / "workloads/build/native"))
    p.add_argument("--ws", type=int, default=1024, help="working set MB (fixed)")
    p.add_argument("--limits", nargs="+", default=["256", "512", "1024", "none"])
    p.add_argument("--workloads", nargs="+", default=list(ITERS))
    p.add_argument("--timeout", type=int, default=900)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", default="ram_sweep.csv")
    a = p.parse_args()
    if os.geteuid() != 0 and any(l != "none" for l in a.limits):
        sys.exit("run with sudo (system-level cgroup needed)")
    rows = []
    for w in a.workloads:
        for l in a.limits:
            lim = None if l == "none" else int(l)
            r = run(f"{a.bindir}/{w}", a.ws, ITERS[w], a.seed, lim, a.timeout)
            print(r, file=sys.stderr); rows.append(r)
    keys = sorted({k for r in rows for k in r}, key=lambda k: list(rows[0]).index(k) if k in rows[0] else 99)
    with open(a.out, "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=keys, restval=""); wr.writeheader(); wr.writerows(rows)
