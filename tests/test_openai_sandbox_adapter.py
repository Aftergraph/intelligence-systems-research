"""Tests for the OpenAI Sandbox Agents spike adapter (Issue #59).

Evidence class: engineering spike only (NOT STUDY-012 confirmatory).
All tests use the real installed SDK (openai-agents) with the local
Unix backend — no network, no credentials. Skipped if SDK unavailable.
"""
import os

import pytest

from src.sdc_b0.worker_sandbox import WorkerSandbox

adapter_mod = pytest.importorskip(
    "src.sdc_b0.openai_sandbox_adapter",
    reason="adapter module missing",
)
OpenAISandboxAdapter = adapter_mod.OpenAISandboxAdapter
OpenAIAdapterConfig = adapter_mod.OpenAIAdapterConfig

needs_sdk = pytest.mark.skipif(
    adapter_mod.SDKUNAVAILABLE,
    reason="openai-agents SDK not installed",
)


def _make_adapter(task_prefix="spike"):
    from agents.sandbox.sandboxes.unix_local import UnixLocalSandboxClient

    client = UnixLocalSandboxClient()
    return OpenAISandboxAdapter(
        client,
        OpenAIAdapterConfig(
            repo_url="",
            base_sha="main",
            branch="",
            task_id=task_prefix,
            worker_id="spike-worker",
        ),
    )


@pytest.fixture
def adapter():
    ad = _make_adapter()
    yield ad
    for tid in ad.list_active():
        ad.teardown(tid)
    for key in [k for k in os.environ if k.startswith("SDC_SANDBOX_")]:
        del os.environ[key]


@needs_sdk
def test_adapter_is_canonical_worker_sandbox():
    assert isinstance(_make_adapter(), WorkerSandbox)


@needs_sdk
def test_sdk_pin_recorded():
    assert adapter_mod.SDK_PKG == "openai-agents"
    assert adapter_mod.SDK_VERSION == "0.22.2"


@needs_sdk
def test_create_execute_teardown_lifecycle(adapter):
    ws = adapter.create("t1", "main")
    assert "t1" in adapter.list_active()
    res = adapter.execute("t1", "echo hello-spike")
    assert res.exit_code == 0
    assert "hello-spike" in res.stdout
    assert res.worktree_path == ws
    assert res.base_sha == "main"
    adapter.teardown("t1")
    assert adapter.list_active() == []


@needs_sdk
def test_double_create_rejected(adapter):
    adapter.create("t2", "main")
    with pytest.raises(ValueError):
        adapter.create("t2", "main")


@needs_sdk
def test_execute_unknown_task_raises(adapter):
    with pytest.raises(KeyError):
        adapter.execute("nope", "echo x")


@needs_sdk
def test_teardown_idempotent(adapter):
    adapter.teardown("ghost")
    adapter.create("t3", "main")
    adapter.teardown("t3")
    adapter.teardown("t3")
    assert adapter.list_active() == []


@needs_sdk
def test_execute_captures_stderr_and_exit_code(adapter):
    adapter.create("t4", "main")
    res = adapter.execute("t4", "ls /nonexistent-spike-dir")
    assert res.exit_code != 0
    assert res.stderr != ""
