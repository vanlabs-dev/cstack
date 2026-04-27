from cstack_audit_core import Finding


def test_compute_id_is_deterministic() -> None:
    a = Finding.compute_id("t1", "rule.x", ["obj-1", "obj-2"])
    b = Finding.compute_id("t1", "rule.x", ["obj-1", "obj-2"])
    assert a == b


def test_compute_id_changes_with_inputs() -> None:
    base = Finding.compute_id("t1", "rule.x", ["o1"])
    assert Finding.compute_id("t2", "rule.x", ["o1"]) != base
    assert Finding.compute_id("t1", "rule.y", ["o1"]) != base
    assert Finding.compute_id("t1", "rule.x", ["o1", "o2"]) != base


def test_compute_id_is_order_invariant() -> None:
    a = Finding.compute_id("t1", "rule.x", ["o-a", "o-b", "o-c"])
    b = Finding.compute_id("t1", "rule.x", ["o-c", "o-a", "o-b"])
    assert a == b


def test_compute_id_length_is_thirty_two() -> None:
    fid = Finding.compute_id("t1", "rule.x", ["o1"])
    assert len(fid) == 32
    int(fid, 16)  # all hex; raises if not
