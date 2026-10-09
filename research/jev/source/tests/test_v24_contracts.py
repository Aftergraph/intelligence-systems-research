from __future__ import annotations

import json
from importlib.resources import files

import jsonschema

from jev_engineering.physical_pair import generate_physical_pair_template
from jev_engineering.relay_resilience import JournalCheckpoint


def _schema(name: str):
    return json.loads((files("jev_engineering") / "schemas" / name).read_text(encoding="utf-8"))


def test_physical_pair_template_conforms_to_packaged_schema():
    jsonschema.validate(generate_physical_pair_template(), _schema("physical-pair-manifest.v1.schema.json"))


def test_journal_checkpoint_shape_conforms():
    row = JournalCheckpoint("worker:a", "stream:1", 0, "", False)
    payload = {
        "version": 1,
        "worker_id": row.worker_id,
        "stream_id": row.stream_id,
        "cursor": row.cursor,
        "last_event_sha256": row.last_event_sha256,
        "complete": row.complete,
    }
    jsonschema.validate(payload, _schema("journal-checkpoint.v1.schema.json"))
