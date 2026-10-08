#!/usr/bin/env python3
"""Run workloads at several working-set sizes, collect RESULT lines into a CSV."""
from pathlib import Path
import argparse, csv, subprocess, sys

ITERS = {"stream": 3, "sort": 1, "gemm": 1, "chase": 2, "kvdecode": 8}

def run(binary, ws_mb, iters, seed):
    out = subprocess.run([binary, "-s", str(ws_mb), "-i", str(iters), "-r", str(seed)],
                         capture_output=True, text=True, check=True).stdout
    line = next(l for l in out.splitlines() if l.startswith("RESULT"))
    return dict(kv.split("=") for kv in line.split()[1:])

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--bindir", default=str(Path(__file__).resolve().parents[1] / "workloads/build/native"))
    p.add_argument("--sizes", type=int, nargs="+", default=[64, 256, 1024])
    p.add_argument("--workloads", nargs="+", default=list(ITERS))
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", default="results.csv")
    a = p.parse_args()
    rows = []
    for w in a.workloads:
        for s in a.sizes:
            r = run(f"{a.bindir}/{w}", s, ITERS[w], a.seed)
            print(r, file=sys.stderr); rows.append(r)
    with open(a.out, "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=rows[0].keys()); wr.writeheader(); wr.writerows(rows)
