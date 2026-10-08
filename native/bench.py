#!/usr/bin/env python3
"""Run workloads at several working-set sizes, collect RESULT lines into a CSV."""

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tiered_memory.csvout import RESULTS, ResultsFile  # noqa: E402
from tiered_memory.workloads import NATIVE_ITERS as ITERS  # noqa: E402
from tiered_memory.workloads import stale_binaries  # noqa: E402


def run(binary, ws_mb, iters, seed):
    out = subprocess.run(
        [binary, "-s", str(ws_mb), "-i", str(iters), "-r", str(seed)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    line = next(l for l in out.splitlines() if l.startswith("RESULT"))
    return dict(kv.split("=") for kv in line.split()[1:])


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument(
        "--bindir", default=str(Path(__file__).resolve().parents[1] / "workloads/build/native")
    )
    p.add_argument("--sizes", type=int, nargs="+", default=[64, 256, 1024])
    p.add_argument("--workloads", nargs="+", default=list(ITERS))
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", default=str(RESULTS / "native_bench.csv"))
    p.add_argument("--fresh", action="store_true", help="overwrite --out instead of merging")
    a = p.parse_args()
    stale = stale_binaries(a.bindir, a.workloads)
    if stale:
        sys.exit(f"missing or older than source: {' '.join(stale)}; run: make -C workloads native")
    results = ResultsFile(a.out, key=("name", "ws_mb"), fresh=a.fresh)
    for w in a.workloads:
        for s in a.sizes:
            r = run(f"{a.bindir}/{w}", s, ITERS[w], a.seed)
            print(r, file=sys.stderr)
            results.add(r)
    print(f"wrote {a.out}", file=sys.stderr)
