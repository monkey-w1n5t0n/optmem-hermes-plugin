"""Backend that talks to the canonical OptMem ``memo`` CLI.

This backend is for deployments where ``~/.optmem/memo`` is a client wrapper
(for example blooper's SSH shim) rather than a local Python store.  It never
opens ``LOG.txt`` or creates a fallback directory locally.
"""

from __future__ import annotations

import re
import shlex
import subprocess
from pathlib import Path

_MEMORY_LINE = re.compile(r"^#(\d+)\s+(\d{4}-\d{2}-\d{2})\s+(.*)$")
_SAVED = re.compile(r"Saved as #(\d+)")
_NAP = re.compile(r"Compress memories #(\d+)-(\d+) into one line")
_CONFIG = re.compile(r"^(\w+)\s+(\d+)\s+")


class MemoCliError(RuntimeError):
    """The canonical memo command failed."""


class MemoCliBackend:
    """Small structured adapter over the existing human-readable memo CLI."""

    def __init__(self, command: str = "~/.optmem/memo", timeout: float = 30):
        parts = shlex.split(command)
        if not parts:
            raise ValueError("memo_command must not be empty")
        if parts[0].startswith("~/"):
            parts[0] = str(Path.home() / parts[0][2:])
        self.command = parts
        self.timeout = timeout

    def _run(self, *args: str) -> str:
        try:
            proc = subprocess.run(
                [*self.command, *args],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise MemoCliError(f"canonical OptMem unavailable: {exc}") from exc
        if proc.returncode:
            detail = (proc.stderr or proc.stdout).strip()
            raise MemoCliError(detail or f"memo exited with status {proc.returncode}")
        return proc.stdout

    @staticmethod
    def _memory_lines(output: str) -> list[tuple[int, str, str]]:
        rows = []
        for line in output.splitlines():
            match = _MEMORY_LINE.match(line.strip())
            if match:
                rows.append((int(match.group(1)), match.group(2), match.group(3)))
        return rows

    def append(self, text: str) -> int:
        output = self._run("note", text)
        match = _SAVED.search(output)
        if not match:
            raise MemoCliError(f"could not parse memo note response: {output!r}")
        return int(match.group(1))

    def wake_lines(self) -> list[str]:
        return [line for line in self._run("wake").splitlines() if line.startswith("#")]

    def recall(
        self, query: str, topk: int = 5, mode: str = "regex"
    ) -> list[tuple[float, int, str, str]]:
        if mode != "regex":
            raise ValueError(
                "memo CLI backend supports regex recall only; use the local backend for BM25"
            )
        rows = self._memory_lines(self._run("recall", query))
        return [(0.0, mid, date, text) for mid, date, text in rows[:topk]]

    def next_nap(self) -> tuple[tuple[int, int], str] | None:
        output = self._run("wake")
        match = _NAP.search(output)
        if not match:
            return None
        lo, hi_inclusive = int(match.group(1)), int(match.group(2))
        return (lo, hi_inclusive + 1), output[match.end() :].splitlines()[0].strip()

    def apply_nap(self, lo: int, hi: int, summary: str) -> bool:
        # The CLI's displayed block is inclusive; the provider API is exclusive.
        self._run("nap", f"{lo}-{hi - 1}", summary)
        return True

    def block_lines(self, lo: int, hi: int) -> list[str]:
        rows = self._memory_lines(self._run("zoom", f"{lo}-{hi - 1}"))
        return [text for _mid, _date, text in rows]

    def forget(self, lo: int, hi: int) -> None:
        self._run("forget", f"{lo}-{hi - 1}")

    def read_config(self) -> dict[str, int]:
        matches = (_CONFIG.match(line) for line in self._run("config").splitlines())
        return {m.group(1): int(m.group(2)) for m in matches if m}

    def write_config(self, values: dict[str, int]) -> None:
        # Only pass values that changed; the CLI owns the defaults and validation.
        for key, value in values.items():
            self._run("config", f"{key}={value}")

    def import_lines(self, lines: list[str]) -> int:
        raise MemoCliError(
            "remote memo import requires a VPS-visible file; use optmem_import on the VPS"
        )

    def init_store(self) -> None:
        raise MemoCliError(
            "refusing remote optmem_init; the canonical store must be initialized administratively"
        )

    def log_len(self) -> int:
        # The provider only uses this for local diagnostics; do not invent a count.
        return -1

    def zoom_halves(self, lo: int, hi: int) -> list[str]:
        return [
            line
            for line in self._run("zoom", f"{lo}-{hi - 1}").splitlines()
            if line.startswith("#")
        ]
