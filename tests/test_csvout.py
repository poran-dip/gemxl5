"""Results CSVs merge reruns instead of overwriting; stale workload binaries are caught."""

import os
import time

from tiered_memory.csvout import ResultsFile, merge, read_rows, write_rows
from tiered_memory.workloads import stale_binaries

KEY = ("workload", "ws_mb")


def test_merge_replaces_only_rerun_keys():
    old = [
        {"workload": "stream", "ws_mb": "64", "limit_mb": "none"},
        {"workload": "kvdecode", "ws_mb": "64", "limit_mb": "none"},
        {"workload": "kvdecode", "ws_mb": "64", "limit_mb": "48"},
    ]
    new = [{"workload": "kvdecode", "ws_mb": 64, "limit_mb": "none"}]  # int vs str still matches
    out = merge(old, new, KEY)
    assert [r["workload"] for r in out] == ["stream", "kvdecode"]
    assert out[-1] is new[0]


def test_results_file_keeps_other_workloads(tmp_path):
    path = tmp_path / "sub" / "sweep.csv"
    first = ResultsFile(path, KEY)
    first.add({"workload": "stream", "ws_mb": 64, "slowdown": 1.0})
    first.add({"workload": "kvdecode", "ws_mb": 64, "slowdown": 1.0})
    second = ResultsFile(path, KEY)  # e.g. sweep_ram.py --workloads kvdecode
    second.add({"workload": "kvdecode", "ws_mb": 64, "slowdown": 2.0, "new_col": "x"})
    rows = read_rows(path)
    assert [(r["workload"], r["slowdown"]) for r in rows] == [
        ("stream", "1.0"),
        ("kvdecode", "2.0"),
    ]
    assert rows[0]["new_col"] == ""  # blank, not missing
    assert not path.with_suffix(".csv.tmp").exists()


def test_fresh_overwrites(tmp_path):
    path = tmp_path / "s.csv"
    write_rows(path, [{"workload": "stream", "ws_mb": "64"}])
    ResultsFile(path, KEY, fresh=True).add({"workload": "sort", "ws_mb": 64})
    assert [r["workload"] for r in read_rows(path)] == ["sort"]


def test_stale_binaries(tmp_path):
    src, bindir = tmp_path / "src", tmp_path / "bin"
    src.mkdir()
    bindir.mkdir()
    for f in ("common.h", "a.cpp", "b.cpp"):
        (src / f).write_text("")
    past = time.time() - 100
    os.utime(src / "common.h", (past, past))
    os.utime(src / "a.cpp", (past, past))
    (bindir / "a").write_text("")  # built after its source
    (bindir / "b").write_text("")
    os.utime(bindir / "b", (past - 50, past - 50))  # built before b.cpp changed
    assert stale_binaries(bindir, ["a", "b", "c"], src_dir=src) == ["b", "c"]
