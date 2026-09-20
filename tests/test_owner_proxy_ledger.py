"""Hash-chain integrity units for ``authority.owner_proxy.ledger``.

Spec §7/§8: the ledger is append-only and hash-chained so truncation, insertion,
deletion and reordering are detectable; a damaged chain refuses BOTH to sign and to
append. The append is the commit point. Tail truncation is intentionally NOT caught by
the chain alone (a shorter valid chain is still valid) -- that is caught by the CI
audit's cross-check (every signed record has a row), documented here honestly.
"""

from __future__ import annotations

import json
from pathlib import Path

from authority.owner_proxy.ledger import append_entry, head_seq, verify_chain, _row_sha

PIN = "dc5d7a94f333908abf09aebe1ca1dbf08f965e604eb2919d0b7a9ca70e149762"


def _kw(**over):
    base = dict(
        ts="2026-09-20T12:00:00+00:00",
        actor="agent:owner-authority",
        principal="JonasAbde <147070826+JonasAbde@users.noreply.github.com>",
        delegation_ref="ref-" + "0" * 60,
        action="SIGN_CALIBRATION_GATE",
        tier="routine",
        target="data/jar_exp_0015_calibration_gate_v01.json",
        approval_record="data/jar_exp_0015_calibration_approval_20260920.json",
        bindings={"manifest": PIN, "model": "jev-1.13.0", "calls": 1952, "cost_usd": 5.38},
    )
    base.update(over)
    return base


def _rows(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_first_append_is_seq_one_with_null_prev(tmp_path: Path):
    led = tmp_path / "delegation_ledger.jsonl"
    res = append_entry(led, **_kw())
    assert res.ok and res.seq == 1
    ok, reason = verify_chain(led)
    assert ok, reason
    row = _rows(led)[0]
    assert row["prev_sha256"] is None
    assert row["entry_sha256"] == _row_sha(row)


def test_second_append_chains_to_first(tmp_path: Path):
    led = tmp_path / "delegation_ledger.jsonl"
    a = append_entry(led, **_kw())
    b = append_entry(led, **_kw(approval_record="data/x.json"))
    assert a.ok and b.ok and b.seq == 2
    rows = _rows(led)
    assert rows[1]["prev_sha256"] == rows[0]["entry_sha256"]
    ok, reason = verify_chain(led)
    assert ok, reason
    assert head_seq(led) == 2


def test_modifying_a_middle_row_breaks_the_chain(tmp_path: Path):
    led = tmp_path / "delegation_ledger.jsonl"
    append_entry(led, **_kw())
    append_entry(led, **_kw(approval_record="data/x.json"))
    append_entry(led, **_kw(approval_record="data/y.json"))
    rows = _rows(led)
    # Tamper row 2's bindings but keep its stored entry_sha256 -> hash mismatch at 2.
    rows[1]["bindings"]["cost_usd"] = 999.0
    led.write_text(
        "".join(json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n" for r in rows),
        encoding="utf-8",
    )
    ok, reason = verify_chain(led)
    assert not ok
    assert "at_2" in (reason or "")


def test_recomputing_a_tampered_hash_then_leaving_next_prev_stale_breaks_chain(tmp_path: Path):
    led = tmp_path / "delegation_ledger.jsonl"
    append_entry(led, **_kw())
    append_entry(led, **_kw(approval_record="data/x.json"))
    rows = _rows(led)
    rows[0]["bindings"]["cost_usd"] = 999.0
    rows[0]["entry_sha256"] = _row_sha(rows[0])  # attacker fixes row 1's own hash
    # ...but row 2's prev_sha256 still points at the OLD row-1 hash -> chain break at 2.
    led.write_text(
        "".join(json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n" for r in rows),
        encoding="utf-8",
    )
    ok, reason = verify_chain(led)
    assert not ok
    assert "chain_break_at_2" in (reason or "")


def test_tail_truncation_leaves_a_valid_shorter_chain_by_design(tmp_path: Path):
    # Honest documentation: dropping the LAST row yields a still-valid chain. The
    # chain detects middle tamper/insert/reorder; tail truncation is caught by the CI
    # audit cross-check (a signed record with no row), not by verify_chain.
    led = tmp_path / "delegation_ledger.jsonl"
    append_entry(led, **_kw())
    append_entry(led, **_kw(approval_record="data/x.json"))
    rows = _rows(led)[:-1]
    led.write_text(
        "".join(json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n" for r in rows),
        encoding="utf-8",
    )
    ok, reason = verify_chain(led)
    assert ok, reason


def test_append_refuses_onto_a_damaged_chain(tmp_path: Path):
    led = tmp_path / "delegation_ledger.jsonl"
    append_entry(led, **_kw())
    rows = _rows(led)
    rows[0]["tier"] = "tampered"  # break row 1's hash
    led.write_text(
        "".join(json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n" for r in rows),
        encoding="utf-8",
    )
    res = append_entry(led, **_kw(approval_record="data/x.json"))
    assert not res.ok
    assert res.reason is not None and "ledger_" in res.reason
    # The damaged file was not appended to (still one row).
    assert len(_rows(led)) == 1


def test_expected_seq_race_aborts_append(tmp_path: Path):
    led = tmp_path / "delegation_ledger.jsonl"
    res = append_entry(led, **_kw(), expected_seq=99)
    assert not res.ok
    assert "ledger_seq_race" in (res.reason or "")
    assert not led.exists() or _rows(led) == []


def test_missing_required_field_is_caught_by_verify(tmp_path: Path):
    led = tmp_path / "delegation_ledger.jsonl"
    append_entry(led, **_kw())
    rows = _rows(led)
    del rows[0]["principal"]
    led.write_text(
        "".join(json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n" for r in rows),
        encoding="utf-8",
    )
    ok, reason = verify_chain(led)
    assert not ok
    assert "missing" in (reason or "")