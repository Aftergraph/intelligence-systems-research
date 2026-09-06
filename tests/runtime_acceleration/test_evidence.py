import hashlib

import pytest

from experiments.runtime_acceleration.evidence import write_run_evidence


def test_evidence_is_append_only_and_hash_attested(tmp_path):
    payloads = {
        "metadata": {"run_id": "r1"},
        "metrics": {"mission_wall_clock_ms": 10},
        "verifier": {"verified": True},
        "stdout": "hello\n",
        "stderr": "",
    }
    first = write_run_evidence(tmp_path, "r1", payloads)
    expected = {"metadata.json", "metrics.json", "stdout.log", "stderr.log", "verifier.json", "artifacts.sha256"}
    assert {p.name for p in first.iterdir()} == expected

    manifest = (first / "artifacts.sha256").read_text(encoding="utf-8").splitlines()
    assert len(manifest) == 5
    for line in manifest:
        digest, name = line.split("  ", 1)
        assert hashlib.sha256((first / name).read_bytes()).hexdigest() == digest

    with pytest.raises(FileExistsError):
        write_run_evidence(tmp_path, "r1", payloads)


def test_evidence_rejects_path_like_run_ids(tmp_path):
    with pytest.raises(ValueError):
        write_run_evidence(tmp_path, "../escape", {"metadata": {}, "metrics": {}, "verifier": {}, "stdout": "", "stderr": ""})
