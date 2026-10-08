from gemxl.descend import Knee, bottleneck, limits_mb, run_timeout, slowdown


def test_limits_descend_and_dedupe():
    assert limits_mb(64, (2.0, 1.0, 0.5)) == [128, 64, 32]
    assert limits_mb(1, (2.0, 1.5, 1.0, 0.25)) == [2, 1]  # 1.5 -> 2 (dup), 0.25 -> 1 (dup)


def test_slowdown():
    assert slowdown("0.5", "0.25") == 2.0
    assert slowdown("x", "0.25") == ""
    assert slowdown("0.5", "0") == ""


def test_bottleneck_reasons():
    assert bottleneck({"status": "ok", "slowdown": 1.2}, 1.5) == ""
    assert bottleneck({"status": "ok", "slowdown": 1.5}, 1.5) == "slowdown>=1.5x"
    assert bottleneck({"status": "exit-9", "slowdown": ""}, 1.5) == "exit-9"
    assert bottleneck({"status": "ok", "slowdown": ""}, 1.5) == ""


def test_run_timeout_is_clamped():
    assert run_timeout(0.2, 30, 20, 900) == 20
    assert run_timeout(10, 30, 20, 900) == 300
    assert run_timeout(100, 30, 20, 900) == 900


def stops(seq, past_knee):
    """Index at which the sweep stops for a sequence of (is_bottleneck, failed) results."""
    k = Knee(past_knee)
    for i, (b, f) in enumerate(seq):
        if k.should_stop(b, f):
            return i
    return None


def test_knee_one_run_past():
    ok, bad = (False, False), (True, False)
    assert stops([ok, ok, bad, bad, bad], past_knee=1) == 3
    assert stops([ok, ok, bad, bad, bad], past_knee=0) == 2
    assert stops([ok, ok, ok], past_knee=1) is None


def test_failure_stops_immediately():
    assert stops([(False, False), (True, True), (True, False)], past_knee=3) == 1
