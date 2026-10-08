from types import SimpleNamespace

from gemxl.linuxstats import cpu_columns, delta_columns, read_numastat, read_vmstat, snapshot
from gemxl.result import parse_result, throughput_cols


def write_vmstat(path, **kv):
    path.write_text("".join(f"{k} {v}\n" for k, v in kv.items()))


def write_node(root, n, **kv):
    d = root / f"node{n}"
    d.mkdir(parents=True)
    (d / "numastat").write_text("".join(f"{k} {v}\n" for k, v in kv.items()))


def test_delta_columns(tmp_path):
    vm = tmp_path / "vmstat"
    nodes = tmp_path / "node"
    write_vmstat(
        vm, pswpin=1, pswpout=2, pgpromote_success=10, pgdemote_kswapd=5, pgdemote_direct=1
    )
    write_node(nodes, 0, numa_hit=100, numa_miss=0, local_node=100, other_node=0)
    write_node(nodes, 1, numa_hit=0, numa_miss=0, local_node=0, other_node=0)
    before = snapshot(vm, nodes)
    write_vmstat(
        vm, pswpin=11, pswpout=22, pgpromote_success=14, pgdemote_kswapd=9, pgdemote_direct=3
    )
    write_node(nodes / "x", 9, numa_hit=0)  # ignored: not a node dir
    (nodes / "node0" / "numastat").write_text(
        "numa_hit 160\nnuma_miss 3\nlocal_node 150\nother_node 13\n"
    )
    (nodes / "node1" / "numastat").write_text(
        "numa_hit 40\nnuma_miss 0\nlocal_node 0\nother_node 40\n"
    )
    cols = delta_columns(before, snapshot(vm, nodes))
    assert cols["swap_in_pages"] == 10
    assert cols["swap_out_pages"] == 20
    assert cols["promote_pages"] == 4
    assert cols["demote_pages"] == 6  # kswapd + direct
    assert cols["node0_alloc_hit"] == 60
    assert cols["node1_alloc_hit"] == 40
    assert cols["alloc_local_pages"] == 50
    assert cols["alloc_other_pages"] == 53


def test_missing_counter_is_blank_not_zero(tmp_path):
    vm = tmp_path / "vmstat"
    write_vmstat(vm, pswpin=0)
    snap = snapshot(vm, tmp_path / "nonodes")
    cols = delta_columns(snap, snap)
    assert cols["swap_in_pages"] == 0
    assert cols["promote_pages"] == ""
    assert cols["demote_pages"] == ""
    assert "alloc_local_pages" not in cols


def test_unreadable_vmstat_gives_blanks(tmp_path):
    assert read_vmstat(tmp_path / "nope") is None
    assert read_numastat(tmp_path / "nope") == {}
    snap = snapshot(tmp_path / "nope", tmp_path / "nope")
    assert delta_columns(snap, snap)["swap_out_pages"] == ""


def test_cpu_columns():
    def ru(u, s, maj, mino):
        return SimpleNamespace(ru_utime=u, ru_stime=s, ru_majflt=maj, ru_minflt=mino)

    cols = cpu_columns(ru(1, 1, 0, 10), ru(3, 2, 4, 50), wall_sec=10)
    assert cols["cpu_util"] == 0.3  # 2s user + 1s sys of 10s wall: it spent the rest blocked
    assert (cols["majflt"], cols["minflt"]) == (4, 40)


def test_parse_result_and_throughput():
    out = "noise\nRESULT name=chase ws_mb=8 iters=1 roi_sec=0.5 work=1000 checksum=7\n"
    r = parse_result(out)
    assert r["checksum"] == "7"
    cols = throughput_cols("chase", r["work"], 0.002)
    assert cols["work_unit"] == "hops"
    assert cols["ns_per_work"] == 2000.0  # 2 ms over 1000 hops = 2 us per hop
    assert cols["throughput"] == 500000.0
    assert parse_result("nothing here") == {}
    assert throughput_cols("chase", "x", "y") == {}
