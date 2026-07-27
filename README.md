# OptMem — local memory provider for Hermes Agent

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-%3E%3D3.11-blue.svg)](pyproject.toml)
[![Hermes](https://img.shields.io/badge/Hermes%20Agent-memory%20provider-8A2BE2.svg)](https://github.com/NousResearch/hermes-agent)

A portable, dependency-free reimplementation of
[Victor Taelin's OptMem](https://github.com/VictorTaelin/OptMem), wired into
[Hermes Agent](https://github.com/NousResearch/hermes-agent) as a **standalone
`MemoryProvider`**.

- **Append-only `LOG.txt` + decay `TREE/`** — byte-compatible with the original
  `memo` tool, so your logs are interchangeable with Taelin's implementation.
- **Accent-normalized BM25 recall** — `recall("cacula")` finds the `caçula` memory.
- **Zero dependencies** — pure Python standard library.
- **Native Windows** — uses `msvcrt` advisory locks (with spin/backoff), no WSL.
- **Cheap, always-on** — local BM25, no network round-trip, no per-call LLM cost.

> Published as a **standalone plugin repo** per Hermes `CONTRIBUTING.md`:
> third-party memory providers no longer land under `plugins/memory/` in the
> core tree. Install via `~/.hermes/plugins/` or pip.

---

## Why OptMem

Hermes ships cloud-backed memory providers (Honcho, Mem0, Hindsight). They are
powerful for cross-session *user modeling*, but they impose a network
round-trip and — on reasoning tiers — an LLM call on every recall.

OptMem is the **cheap, always-available local layer**: permanent, searchable
memory that survives restarts, costs zero tokens, and never leaves your
machine. Hermes allows **one** external provider at a time, so the two are
complementary — OptMem is the durable default; a cloud provider is selected
when richer modeling is wanted.

| Dimension | OptMem (local) | Cloud providers (e.g. Honcho) |
|---|---|---|
| Startup dependency | None — `is_available()` is always `True` | Needs API key / base URL |
| Per-call latency | Local BM25 (sub-ms to ms) | Network, sometimes an LLM |
| Per-call cost | Zero tokens | Reasoning tier runs an LLM |
| Data residency | On disk in `HERMES_HOME` | Leaves the machine to a 3rd party |
| Code footprint | ~840 LOC (provider + engine) | 1500+ LOC + SDK + background threads |

---

## Install

**Option A — copy into your Hermes plugins dir (simplest):**

```bash
git clone https://github.com/rarf/optmem-hermes-plugin.git
mkdir -p ~/.hermes/plugins
cp -r optmem-hermes-plugin/optmem ~/.hermes/plugins/optmem
```

**Option B — pip (entry point registered):**

```bash
pip install optmem-hermes-plugin
```

Hermes discovers it from `~/.hermes/plugins/optmem/` or the
`hermes.plugins` entry point.

---

## Activate

In `~/.hermes/config.yaml`:

```yaml
memory:
  provider: optmem
plugins:
  optmem:
    memory_dir: $HERMES_HOME/optmem_memory   # optional; this is the default
```

Restart the Hermes gateway (`hermes gateway restart`). The provider exposes
four tools: `optmem_note`, `optmem_recall`, `optmem_nap`, `optmem_wake`
(surfaced automatically via `prefetch` each turn). It also mirrors builtin
`memory` writes through `on_memory_write`, so existing memory keeps feeding
permanent recall with **no migration step**.

---

## How it works

- **Append-only log** (`LOG.txt`, fixed-width 320-byte records). Nothing is ever deleted.
- **Decay tree** (`TREE/<size>`). When a pair of memories forms, the agent
  performs a *nap*: it merges the block into one line. Old context compresses
  instead of growing unbounded — Taelin's *"nap, don't sleep"*.
- **BM25 search** with accent normalization (`caçula` ≈ `cacula`).
- **Portable lock** — `msvcrt` on Windows (with `LK_NBLCK` + spin/backoff to
  avoid the `Resource deadlock avoided` failure under contention), `fcntl` on
  Unix. The lock file is always opened in append mode.

Related engine fix (Windows `fcntl` → `msvcrt`):
[VictorTaelin/OptMem#2](https://github.com/VictorTaelin/OptMem/pull/2).

---

## Tools

| Tool | Purpose |
|---|---|
| `optmem_note` | Record one durable memory line (≤280 chars). |
| `optmem_recall` | Accent-normalized BM25 search across all history. |
| `optmem_nap` | Apply a compression the engine asked for. |
| `optmem_wake` | Print the current decayed context (permanent memory). |

---

## Tests

```bash
pip install pytest
pytest tests/
```

18 end-to-end tests over the **real** engine and provider against a temp
`HERMES_HOME` (no mocks of the store): append, accent-normalized BM25,
nap/decay compression, byte-compat reopen, tool roundtrip, prefetch, and the
`on_memory_write` mirror.

---

## Credits

- Memory model and on-disk format by **Victor Taelin** —
  [VictorTaelin/OptMem](https://github.com/VictorTaelin/OptMem).
- Standalone Hermes integration, Windows locking, and BM25 search by
  **Ronald (rarf)**.

## License

MIT — see [LICENSE](LICENSE).
