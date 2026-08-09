# OptMem — Permanent Local Memory for Hermes Agent

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-%3E%3D3.11-blue.svg)](pyproject.toml)
[![Hermes](https://img.shields.io/badge/Hermes%20Agent-memory%20provider-8A2BE2.svg)](https://github.com/NousResearch/hermes-agent)
[![Parity](https://img.shields.io/badge/byte--compatible%20with%20memo%20CLI-✅-green.svg)](https://github.com/VictorTaelin/OptMem)

**Permanent, searchable agent memory that never leaves your machine, costs zero
tokens to recall, and is byte-for-byte compatible with Victor Taelin's
`OptMem` `memo` CLI.**

OptMem is a drop-in `MemoryProvider` for [Hermes Agent](https://github.com/NousResearch/hermes-agent)
that gives your agent a durable, decaying memory store — the same design
Taelin ships as a CLI, but wired directly into Hermes. No cloud, no API key, no
per-turn LLM cost. Just memory that survives restarts and stays small.

> **License note.** The upstream `VictorTaelin/OptMem` repo currently ships
> **without an explicit license** (all rights reserved by default). This
> repository is an *independent* reimplementation of the published design and
> memory format — it does not copy the upstream source. It is released here
> under MIT (see [LICENSE](LICENSE)). If/once upstream adopts a license, this
> plugin will align with it.

---

## Why teams choose OptMem over cloud memory

| | OptMem (local) | Cloud providers (Honcho / Mem0) |
|---|---|---|
| Setup | **Zero** — works out of the box | API key + base URL + network |
| Recall latency | Local search, sub-ms | Network round-trip, often an LLM call |
| Recall cost | **0 tokens** | Reasoning-tier LLM every call |
| Data residency | On your disk (`HERMES_HOME`) | Leaves the machine to a 3rd party |
| Code footprint | ~850 LOC, stdlib only | 1500+ LOC + SDK + background threads |

Cloud providers are great for cross-session *user modeling*. OptMem is the
**durable, always-on default** — your agent's long-term memory that never
fails because a key expired or a network blipped.

---

## What you get

- **🔒 Permanent & private** — append-only `LOG.txt` on your disk. Nothing is
  ever deleted; forgotten summaries are rebuilt, never lost.
- **🌳 Self-compressing** — the decay tree ("nap, don't sleep") keeps context
  dense instead of growing unbounded. One line per atomic fact, ≤280 bytes.
- **🔎 Two search modes** — `recall` defaults to the **same regex behavior as
  the `memo` CLI** (case-insensitive, newest-first), with optional
  accent-normalized **BM25 ranking** (`cacula` finds `caçula`).
- **💾 Byte-compatible with `memo`** — same fixed-width 320/288-byte records and
  `.lock` file. Run the CLI and the plugin on the **same store**; they read and
  write each other's memories safely.
- **🪟 Native Windows** — `msvcrt` advisory locks with spin/backoff (no WSL, no
  `Resource deadlock avoided`). `fcntl` on Unix.
- **🧩 Zero-dependency** — pure Python standard library.

---

## Quick start

```bash
# 1. Install
git clone https://github.com/rarf/optmem-hermes-plugin.git
cp -r optmem-hermes-plugin/optmem ~/.hermes/plugins/optmem
# (or: pip install optmem-hermes-plugin)

# 2. Activate in ~/.hermes/config.yaml
memory:
  provider: optmem

# 3. Restart the gateway
hermes gateway restart
```

That's it. The agent now has permanent memory — no migration, no prompt paste.

---

## Tools exposed to the agent

| Tool | Purpose |
|---|---|
| `optmem_note` | Record one durable memory line (≤280 bytes). |
| `optmem_recall` | Search all history — regex by default (matches `memo recall`), or `mode="bm25"` for ranked/accent-tolerant search. |
| `optmem_wake` | Print the current decayed context (permanent memory). |
| `optmem_nap` | Apply a compression the engine requested. |
| `optmem_zoom` | Navigate the decay tree (halve a block to see its parts). |
| `optmem_forget` | Drop a bad summary so the next nap rebuilds it. |
| `optmem_config` | Show or change size knobs (mirrors `memo config`). |
| `optmem_import` | Bulk-load historical `YYYY-MM-DD <text>` memories (bootstrap). |
| `optmem_init` | Create the store deliberately (mirrors `memo init`). |

All nine mirror the `memo` CLI surface — so scripts and habits transfer 1:1.

---

## Parity with upstream `memo`

The memory model is identical: append-only log, binary decay tree, "nap, don't
sleep" compression, fixed-width record format. Logs are interchangeable on disk.

| Aspect | `VictorTaelin/OptMem` (`memo`) | `optmem-hermes-plugin` |
|---|---|---|
| On-disk format | `LOG_REC=320`, `TREE_REC=288`, `RAW_MAX=16` | **Identical** |
| `recall` | regex only | regex by default (**same behavior**); BM25 opt-in |
| `wake` | printed once per session | surfaced once per session via `prefetch` (Option B) |
| Platform locks | `fcntl` only (Unix) | `msvcrt` on Windows, `fcntl` on Unix |
| Coexist on one machine | — | **Yes** — shared store + shared `.lock` (proven by retro-test) |
| Form factor | CLI you paste into `AGENTS.md` | Hermes `MemoryProvider` — auto-wired, no paste |

In short: **same durable store, full CLI parity, plus native Windows and
first-class Hermes integration.**

---

## How it works

- **Append-only log** (`LOG.txt`, fixed-width 320-byte records).
- **Decay tree** (`TREE/<size>`). When a pair of memories forms, a *nap* merges
  the block into one line — old context compresses instead of growing.
- **Search** — regex (default, matches `memo`) or accent-normalized BM25.
- **Portable lock** — `msvcrt` on Windows (`LK_NBLCK` + spin/backoff), `fcntl`
  on Unix. Descriptors are closed on release (no fd leak).

Related upstream fix (Windows `fcntl` → `msvcrt`):
[VictorTaelin/OptMem#2](https://github.com/VictorTaelin/OptMem/pull/2).

---

## Tests

```bash
pip install pytest
pytest tests/
```

18 end-to-end tests run against the **real** engine and provider (temp
`HERMES_HOME`, no mocks): append, regex + BM25 recall, accent normalization,
nap/decay compression, byte-compat reopen, tool roundtrip, prefetch (wake-once
per session), `on_memory_write` mirror, and config/import/init.

A bidirectional retro-compatibility harness also proves the plugin and the
official `memo` CLI read/write the **same store** safely.

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
- Standalone Hermes integration, Windows locking, BM25 search, and CLI parity
  by **Ronald (rarf)**.

## License

MIT — see [LICENSE](LICENSE).
