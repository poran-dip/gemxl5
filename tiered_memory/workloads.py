"""The one list of workloads. Everything that runs or reports on them reads this table.

To add a workload: write workloads/<name>.cpp, add it to WL in workloads/Makefile, and add one
row here (tests/test_workloads.py checks the two lists match).
"""

from pathlib import Path
from typing import NamedTuple


class Workload(NamedTuple):
    work_unit: str  # what one unit of the RESULT line's `work` means
    pdf_class: str  # workload class from the project brief (section 7)
    native_ws: int  # MiB, default working set for quick native runs (sweep_ram --descend)
    native_iters: int  # iters for native runs, sized for a ROI of roughly 0.1-0.5 s at native_ws
    gem5_ws: int  # MiB, default working set for gem5 SE runs (keep >> L2 so DRAM is exercised)
    gem5_iters: int


WORKLOADS = {
    "stream": Workload("bytes", "bandwidth", 64, 3, 8, 2),
    "sort": Workload("compares", "random/irregular", 64, 1, 4, 1),
    # gemm's work grows with the cube of its size; it is the cache-resident compute control
    "gemm": Workload("flops", "compute/matrix", 16, 1, 2, 1),
    "chase": Workload("hops", "random/irregular", 64, 2, 8, 1),
    "kvdecode": Workload("bytes", "CPU AI/LLM", 64, 64, 8, 2),
    "graph": Workload("edges", "graph", 64, 4, 8, 1),
    "kvstore": Workload("ops", "database (OLTP)", 64, 4, 8, 1),
    "hashjoin": Workload("tuples", "database (OLAP)", 64, 4, 8, 1),
}

NAMES = list(WORKLOADS)
WORK_UNIT = {k: w.work_unit for k, w in WORKLOADS.items()}
NATIVE_WS = {k: w.native_ws for k, w in WORKLOADS.items()}
NATIVE_ITERS = {k: w.native_iters for k, w in WORKLOADS.items()}
GEM5_DEFAULTS = {k: (w.gem5_ws, w.gem5_iters) for k, w in WORKLOADS.items()}


def stale_binaries(bindir, names, src_dir=None):
    """Names whose binary in bindir is missing or older than its source or common.h."""
    src = Path(src_dir) if src_dir else Path(__file__).resolve().parents[1] / "workloads"
    common = (src / "common.h").stat().st_mtime
    out = []
    for n in names:
        exe = Path(bindir) / n
        if not exe.exists() or exe.stat().st_mtime < max(
            common, (src / f"{n}.cpp").stat().st_mtime
        ):
            out.append(n)
    return out
