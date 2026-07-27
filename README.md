# OptMem — local memory provider for Hermes Agent

A portable reimplementation of [Victor Taelin's OptMem](https://github.com/VictorTaelin/OptMem),
wired into [Hermes Agent](https://github.com/NousResearch/hermes-agent) as a standalone
`MemoryProvider`. Append-only `LOG.txt` + decay `TREE/`, byte-compatible with the original
`memo` tool. Accent-normalized BM25 recall (`caçula` finds `cacula`), zero dependencies,
native Windows (msvcrt advisory lock — no WSL).

> Published as a **standalone plugin repo** per Hermes `CONTRIBUTING.md` — memory providers
> no longer land under `plugins/memory/` in the core tree. Install via `~/.hermes/plugins/`
> or pip.

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

Hermes discovers it from `~/.hermes/plugins/optmem/` or the `hermes.plugins` entry point.

## Activate

In `~/.hermes/config.yaml`:

```yaml
memory:
  provider: optmem
plugins:
  optmem:
    memory_dir: $HERMES_HOME/optmem_memory   # optional; this is the default
```

The provider exposes four tools: `optmem_note`, `optmem_recall`, `optmem_nap`, `optmem_wake`.
It mirrors builtin `memory` writes via `on_memory_write`, so existing memory files keep
feeding permanent recall without a separate migration path.

## How it works

- **Append-only log** (`LOG.txt`, fixed-width 320-byte records). Nothing is ever deleted.
- **Decay tree** (`TREE/<size>`). When a pair of memories forms, the agent performs a
  "nap": merges the block into one line. Old context compresses instead of growing unbounded
  — "nap, don't sleep".
- **BM25 search** with accent normalization. `recall("cacula")` hits the `caçula` memory.
- **Local lock** — `msvcrt` on Windows, `fcntl` on Unix. No WSL needed.

Related engine fix (Windows `fcntl` → `msvcrt`): [VictorTaelin/OptMem#2](https://github.com/VictorTaelin/OptMem/pull/2).

## Why a local provider (vs cloud memory backends)

Hermes ships cloud-backed memory providers (Honcho, Mem0, Hindsight). They are powerful for
cross-session *user modeling* but impose a network round-trip and, on reasoning tiers, an LLM
call per recall. OptMem is the cheap, always-available default:

| Dimension | OptMem (local) | Cloud providers (e.g. Honcho) |
|---|---|---|
| Startup dependency | None — `is_available()` always True | Needs API key / base URL |
| Per-call latency | Local BM25 (sub-ms to ms) | Network, sometimes an LLM |
| Per-call cost | Zero tokens | Reasoning tier runs an LLM |
| Data residency | On disk in `HERMES_HOME` | Leaves the machine to a 3rd party |
| Code footprint | ~840 LOC (provider + engine) | 1500+ LOC + SDK + background threads |

Hermes enforces one external provider at a time, so the two are complementary: OptMem is the
local durable layer; a cloud provider is selected when richer user modeling is wanted.

## Tests

```bash
pytest tests/
```

18 E2E tests over the real engine and provider against a temp `HERMES_HOME`
(no mocks of the store): append, accent-normalized BM25, nap/decay compression,
byte-compat reopen, tool roundtrip, prefetch, and the `on_memory_write` mirror.

## License

MIT
