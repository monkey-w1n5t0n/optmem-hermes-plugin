"""Tests for the canonical memo CLI transport."""

import json
import sys

from optmem import OptMemProvider

_FAKE_MEMO = r"""
import sys
args = sys.argv[1:]
if args[:1] == ["note"]:
    print("Saved as #42.")
elif args[:1] == ["wake"]:
    print("#40-41 durable context")
    print("Compress memories #42-43 into one line")
elif args[:1] == ["recall"]:
    print("#42 2026-08-10 canonical remote fact")
elif args[:1] == ["zoom"]:
    print("#42 2026-08-10 canonical remote fact")
elif args[:1] == ["nap"]:
    print("Compressed #42-43")
elif args[:1] == ["config"]:
    print("WAKE_LINES   96      the memory context")
else:
    raise SystemExit("unexpected command: " + repr(args))
"""


def _provider(tmp_path):
    script = tmp_path / "memo.py"
    script.write_text(_FAKE_MEMO, encoding="utf-8")
    p = OptMemProvider(
        {
            "backend": "memo-cli",
            "memo_command": f"{sys.executable} {script}",
        }
    )
    p.initialize("remote-test", hermes_home=str(tmp_path))
    return p


def test_cli_backend_uses_command_without_creating_local_store(tmp_path):
    provider = _provider(tmp_path)

    note = json.loads(provider.handle_tool_call("optmem_note", {"text": "fact"}))
    recall = json.loads(provider.handle_tool_call("optmem_recall", {"query": "fact"}))
    wake = json.loads(provider.handle_tool_call("optmem_wake", {}))

    assert note["saved_as"] == "#42"
    assert recall["results"][0]["id"] == 42
    assert wake["context"] == ["#40-41 durable context"]
    assert not (tmp_path / "optmem_memory").exists()


def test_cli_backend_nap_uses_inclusive_cli_block(tmp_path):
    provider = _provider(tmp_path)
    result = json.loads(
        provider.handle_tool_call("optmem_nap", {"lo": 42, "hi": 43, "summary": "compressed"})
    )
    assert result["status"] == "compressed"


def test_cli_backend_does_not_fallback_to_local_store(tmp_path):
    provider = OptMemProvider(
        {
            "backend": "memo-cli",
            "memo_command": f"{sys.executable} {tmp_path / 'missing.py'}",
        }
    )
    provider.initialize("unavailable-test", hermes_home=str(tmp_path))

    result = json.loads(provider.handle_tool_call("optmem_note", {"text": "fact"}))

    assert "error" in result
    assert not (tmp_path / "optmem_memory").exists()
