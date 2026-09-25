from experiments.study015.dry_run import build_matrix


def test_dry_run_matrix_covers_all_conditions_and_is_never_live():
    rows = build_matrix()
    assert len(rows) == 22
    assert {r["condition"] for r in rows} == {f"S{i}" for i in range(10)} | {"FULL"}
    assert all(r["execution_class"] == "DRY_RUN" for r in rows)
    assert all(r["is_live"] is False for r in rows)


def test_dry_run_uses_single_implementation_fingerprint():
    rows = build_matrix()
    assert len({r["implementation_fingerprint"] for r in rows}) == 1
