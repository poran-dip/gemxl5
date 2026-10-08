#!/usr/bin/env python3
"""Shrink simulated local DRAM per workload; record gem5-native stats for the ROI.
  python3 configs/sweep.py        # from the repo root, or anywhere
Status 'OOM' = working set no longer fits in simulated DRAM (the 'limit').
Metrics come from the FIRST stats block in stats.txt = the ROI (reset at ROI begin,
dumped at ROI end by common.h); the trailing block is post-ROI teardown, ignored.
"""
import argparse, csv, os, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

# workload -> (ws_mb, iters); sized for gem5 speed, keep ws >> L2 so DRAM is exercised
DEFAULTS = {"stream": (8, 2), "sort": (4, 1), "gemm": (2, 1), "chase": (8, 1), "kvdecode": (8, 2)}

def first_block(path):
    st, started = {}, False
    for line in open(path):
        if line.startswith("---------- Begin"):
            if started: break
            started = True; continue
        if line.startswith("---------- End"): break
        f = line.split()
        if started and len(f) >= 2 and not line.startswith("#"):
            try: st[f[0]] = float(f[1])
            except ValueError: pass
    return st

def summarize(st):
    tot = lambda suf: sum(v for k, v in st.items() if k.endswith(suf))
    insts = st.get("simInsts") or tot(".committedInsts") or tot(".numInsts")
    cyc = tot(".numCycles")
    mx = lambda suf: max([v for k, v in st.items() if k.endswith(suf)] or [""])
    lat = [v for k, v in st.items() if k.endswith("avgMemAccLat")]
    l2m = [v for k, v in st.items() if "l2" in k and k.endswith("overallMisses::total")]
    return {"sim_sec": st.get("simSeconds", ""), "insts": insts, "cycles": cyc,
            "ipc": round(insts / cyc, 4) if cyc else "",
            "dram_rd_bursts": mx(".readBursts"), "dram_wr_bursts": mx(".writeBursts"),
            "avg_mem_lat_ns": round(lat[0] / 1000, 2) if lat else "",  # ticks=ps
            "l2_misses": sum(l2m) if l2m else ""}

def pow2_mib(x):
    m = 1
    while m < x: m *= 2
    return m

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--gem5-bin", default=str(REPO / "third_party/gem5/build/X86/gem5.opt"))
    p.add_argument("--bindir", default=str(REPO / "workloads/build/m5"))
    p.add_argument("--workloads", nargs="+", default=list(DEFAULTS))
    p.add_argument("--ratios", type=float, nargs="+", default=[8, 4, 2, 1],
                   help="simulated DRAM = ws * ratio, rounded up to power-of-2 MiB")
    p.add_argument("--mem", nargs="+", help="explicit sizes (MiB) overriding --ratios")
    p.add_argument("--cpu", default="timing")
    p.add_argument("--timeout", type=int, default=3600)
    p.add_argument("--reparse", action="store_true", help="re-parse existing m5out dirs, no simulation")
    p.add_argument("--out", default=str(REPO / "results/gem5_sweep.csv"))
    p.add_argument("--outroot", default=str(REPO / "m5out"))
    a = p.parse_args()
    rows = []
    for w in a.workloads:
        ws, it = DEFAULTS[w]
        mems = [int(m) for m in a.mem] if a.mem else [pow2_mib(ws * r) for r in a.ratios]
        for m in mems:
            od = f"{a.outroot}/{w}_{m}MiB_{a.cpu}"
            cmd = [a.gem5_bin, "-d", od, str(HERE / "run.py"), "--binary", f"{a.bindir}/{w}",
                   "--mem-size", f"{m}MiB", "--cpu", a.cpu, "--", "-s", str(ws), "-i", str(it)]
            row = {"workload": w, "ws_mb": ws, "dram_mib": m, "ratio": round(m / ws, 2), "cpu": a.cpu}
            if a.reparse:
                sp, lg = os.path.join(od, "stats.txt"), os.path.join(od, "run.log")
                if os.path.exists(lg) and "Out of memory" in open(lg).read():
                    row["status"] = "OOM"
                elif os.path.exists(sp):
                    row.update(summarize(first_block(sp)))
                    row["status"] = "ok" if row.get("insts") else "OOM"  # OOM runs leave an all-zero stats.txt
                else:
                    row["status"] = "not-run"
                print(row, file=sys.stderr); rows.append(row); continue
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=a.timeout)
                log = r.stdout + r.stderr
                os.makedirs(od, exist_ok=True); open(os.path.join(od, "run.log"), "w").write(log)
                if "Out of memory" in log: row["status"] = "OOM"
                elif r.returncode != 0: row["status"] = f"exit{r.returncode}"
                else: row["status"] = "ok"
                sp = os.path.join(od, "stats.txt")
                if row["status"] == "ok" and os.path.exists(sp):
                    row.update(summarize(first_block(sp)))
                m_ = re.search(r"checksum=(\d+)", log)
                if m_: row["checksum"] = m_.group(1)
            except subprocess.TimeoutExpired:
                row["status"] = "timeout"
            print(row, file=sys.stderr); rows.append(row)
    keys = list(dict.fromkeys(k for r in rows for k in r))
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=keys, restval=""); wr.writeheader(); wr.writerows(rows)
