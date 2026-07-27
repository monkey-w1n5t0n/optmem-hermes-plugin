"""Tests for the OptMem Hermes memory provider.

Mirrors the shape of tests/agent/test_memory_provider.py (the official
suite) so the provider is validated against the same contract: discovery,
is_available, prefetch, sync, tool routing, and the optional hooks.

Run from the hermes-agent checkout:
    scripts/run_tests.sh tests/agent/test_memory_provider_optmem.py
"""

import json
import os
import sys

import pytest

# Ensure the bundled optmem plugin is importable.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from agent.memory_provider import MemoryProvider
from agent.memory_manager import MemoryManager
from plugins.memory import discover_memory_providers, load_memory_provider


@pytest.fixture
def hermes_home(tmp_path):
    """Isolate HERMES_HOME so we never touch the real profile."""
    d = str(tmp_path / "home")
    os.makedirs(d)
    os.environ["HERMES_HOME"] = d
    yield d
    os.environ.pop("HERMES_HOME", None)


class TestOptMemDiscovery:
    def test_optmem_is_discovered(self):
        names = [n for n, _, _ in discover_memory_providers()]
        assert "optmem" in names

    def test_load_returns_instance(self):
        p = load_memory_provider("optmem")
        assert p is not None
        assert p.name == "optmem"
        assert p.is_available()

    def test_load_unknown_returns_none(self):
        assert load_memory_provider("does_not_exist_xyz") is None


class TestOptMemProvider:
    def test_initialize_sets_memory_dir(self, hermes_home):
        p = load_memory_provider("optmem")
        p.initialize(session_id="s1", platform="cli", hermes_home=hermes_home)
        assert p._engine is not None
        assert os.path.isdir(p._memory_dir)
        assert p._memory_dir.startswith(hermes_home)

    def test_note_triggers_pending_nap(self, hermes_home):
        p = load_memory_provider("optmem")
        p.initialize(session_id="s1", platform="cli", hermes_home=hermes_home)
        json.loads(p.handle_tool_call("optmem_note", {"text": "Ronald mora em Aguas Santas"}))
        r1 = json.loads(p.handle_tool_call("optmem_note", {"text": "Marina cacula da familia"}))
        assert "nap_due" in r1
        lo, hi = r1["nap_due"]["lo"], r1["nap_due"]["hi"]
        assert hi - lo == 2

    def test_prefetch_surfaces_nap(self, hermes_home):
        p = load_memory_provider("optmem")
        p.initialize(session_id="s1", platform="cli", hermes_home=hermes_home)
        p.handle_tool_call("optmem_note", {"text": "Ronald mora em Aguas Santas"})
        p.handle_tool_call("optmem_note", {"text": "Marina cacula da familia"})
        pf = p.prefetch("anything")
        assert "optmem_nap" in pf

    def test_prefetch_empty_query_surfaces_context(self, hermes_home):
        """OptMem can fully replace builtin memory (memory_enabled=False):
        prefetch with an empty query still returns the decayed context."""
        p = load_memory_provider("optmem")
        p.initialize(session_id="s1", platform="cli", hermes_home=hermes_home)
        p.handle_tool_call("optmem_note", {"text": "AllDrivers paywall em curso"})
        pf = p.prefetch("")
        assert "OptMem context" in pf
        assert "AllDrivers paywall" in pf

    def test_system_prompt_block_stays_stable(self, hermes_home):
        """system_prompt_block must not dump the full log (would break the
        cached system prompt). It reports status only."""
        p = load_memory_provider("optmem")
        p.initialize(session_id="s1", platform="cli", hermes_home=hermes_home)
        p.handle_tool_call("optmem_note", {"text": "facto longo para testar"})
        block = p.system_prompt_block()
        assert "OptMem (permanent memory)" in block
        assert "facto longo" not in block

    def test_prefetch_with_query_adds_recall(self, hermes_home):
        p = load_memory_provider("optmem")
        p.initialize(session_id="s1", platform="cli", hermes_home=hermes_home)
        p.handle_tool_call("optmem_note", {"text": "AllDrivers paywall em curso"})
        pf = p.prefetch("paywall")
        assert "OptMem context" in pf
        assert "recall" in pf

    def test_nap_compresses_block(self, hermes_home):
        p = load_memory_provider("optmem")
        p.initialize(session_id="s1", platform="cli", hermes_home=hermes_home)
        p.handle_tool_call("optmem_note", {"text": "Ronald mora em Aguas Santas"})
        r1 = json.loads(p.handle_tool_call("optmem_note", {"text": "Marina cacula da familia"}))
        lo, hi = r1["nap_due"]["lo"], r1["nap_due"]["hi"]
        r = json.loads(p.handle_tool_call("optmem_nap",
            {"lo": lo, "hi": hi, "summary": "Ronald e Marina sao da familia"}))
        assert r["status"] == "compressed"

    def test_recall_accent_normalized_bm25(self, hermes_home):
        p = load_memory_provider("optmem")
        p.initialize(session_id="s1", platform="cli", hermes_home=hermes_home)
        p.handle_tool_call("optmem_note", {"text": "Marina cacula da familia"})
        p.handle_tool_call("optmem_note", {"text": "Casa opera Telegram grupo Casa"})
        r = json.loads(p.handle_tool_call("optmem_recall", {"query": "caçula", "topk": 3}))
        assert r["count"] >= 1
        assert any("cacula" in h["text"] for h in r["results"])

    def test_recall_ranks_relevant(self, hermes_home):
        p = load_memory_provider("optmem")
        p.initialize(session_id="s1", platform="cli", hermes_home=hermes_home)
        p.handle_tool_call("optmem_note", {"text": "Casa opera Telegram grupo Casa"})
        p.handle_tool_call("optmem_note", {"text": "Ronald mora em Aguas Santas"})
        r = json.loads(p.handle_tool_call("optmem_recall", {"query": "telegram", "topk": 3}))
        assert r["count"] >= 1
        assert any("Telegram" in h["text"] for h in r["results"])

    def test_wake_returns_context(self, hermes_home):
        p = load_memory_provider("optmem")
        p.initialize(session_id="s1", platform="cli", hermes_home=hermes_home)
        p.handle_tool_call("optmem_note", {"text": "Ronald mora em Aguas Santas"})
        p.handle_tool_call("optmem_note", {"text": "Marina cacula da familia"})
        w = json.loads(p.handle_tool_call("optmem_wake", {}))
        assert w["count"] >= 2

    def test_system_prompt_block_reports_status(self, hermes_home):
        p = load_memory_provider("optmem")
        p.initialize(session_id="s1", platform="cli", hermes_home=hermes_home)
        block = p.system_prompt_block()
        assert "OptMem" in block

    def test_on_memory_write_mirrors_builtin(self, hermes_home):
        p = load_memory_provider("optmem")
        p.initialize(session_id="s1", platform="cli", hermes_home=hermes_home)
        p.on_memory_write("add", "memory", "Márcia tem endoscopia pendente")
        mirror = p._engine.recall("endoscopia", topk=1)
        assert any("endoscopia" in t for _, _, _, t in mirror)

    def test_shutdown_is_safe(self, hermes_home):
        p = load_memory_provider("optmem")
        p.initialize(session_id="s1", platform="cli", hermes_home=hermes_home)
        p.shutdown()
        assert p._engine is None

    def test_manager_integrates_provider(self, hermes_home):
        mgr = MemoryManager()
        mgr.add_provider(load_memory_provider("optmem"))
        mgr.initialize_all(session_id="s1", platform="cli", hermes_home=hermes_home)
        schemas = mgr.get_all_tool_schemas()
        names = {s["name"] for s in schemas}
        assert "optmem_note" in names
        out = mgr.prefetch_all("test query")
        assert isinstance(out, str)
        mgr.shutdown_all()
