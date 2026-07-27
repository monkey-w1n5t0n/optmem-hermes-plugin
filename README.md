# OptMem — local memory provider for Hermes Agent

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-%3E%3D3.11-blue.svg)](pyproject.toml)
[![Hermes](https://img.shields.io/badge/Hermes%20Agent-memory%20provider-8A2BE2.svg)](https://github.com/NousResearch/hermes-agent)

A portable, dependency-free **independent reimplementation** of
[Victor Taelin's OptMem](https://github.com/VictorTaelin/OptMem) design, wired
into [Hermes Agent](https://github.com/NousResearch/hermes-agent) as a
**standalone `MemoryProvider`**.

> **License note.** The upstream `VictorTaelin/OptMem` repo currently ships
> **without an explicit license** (all rights reserved by default). This
> repository is an *independent* reimplementation of the published design and
> memory format — it does not copy the upstream source. It is released here
> under MIT (see [LICENSE](LICENSE)). If/once upstream adopts a license, this
> plugin will align with it.

- **Append-only `LOG.txt` + decay `TREE/`** — uses the **same on-disk format**
  as the original `memo` tool (fixed-width 320/288-byte records, identical
  cover/decay math), so logs produced here are byte-compatible and
  interchangeable with Taelin's implementation.
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

## How it differs from upstream

The core design — append-only `LOG.txt`, the binary decay `TREE/`, the
"nap, don't sleep" compression, and the fixed-width record format — is the
same as Taelin's. The differences are about **where it runs and how you query
it**, not the memory model:

| Aspect | `VictorTaelin/OptMem` (upstream) | `optmem-hermes-plugin` (this repo) |
|---|---|---|
| Form factor | A standalone CLI (`memo`) you paste into `AGENTS.md` | A Hermes `MemoryProvider` — no prompt paste, auto-wired |
| Query | `memo recall <regex>` (regex only) | `optmem_recall` — **BM25 ranked** (+ optional regex), accent-normalized |
| Platform locks | `fcntl` only (POSIX/Unix; breaks on Windows) | `msvcrt` on Windows (`LK_NBLCK` + spin/backoff), `fcntl` on Unix |
| Delivery | CLI output you pipe into context | Surfaced via Hermes `prefetch` every turn; `on_memory_write` mirrors builtin `memory` |
| Byte format | `LOG_REC=320`, `TREE_REC=288`, `RAW_MAX=16` | **Identical** — logs are interchangeable on disk |

In short: same durable store, but this repo adds **ranked search**, **native
Windows support**, and **first-class Hermes integration** instead of a prompt
block.

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

### Staying aligned with upstream

`./scripts/sync_upstream.sh` fetches Taelin's `memo`, checks that its on-disk
constants still match this engine's, and re-runs the suite. It does **not**
auto-merge — it alerts you when upstream drifts so you can adapt deliberately.

```bash
./scripts/sync_upstream.sh
```

---

## Credits

- Memory model and on-disk format by **Victor Taelin** —
  [VictorTaelin/OptMem](https://github.com/VictorTaelin/OptMem).
- Standalone Hermes integration, Windows locking, and BM25 search by
  **Ronald (rarf)**.

## License

MIT — see [LICENSE](LICENSE).
