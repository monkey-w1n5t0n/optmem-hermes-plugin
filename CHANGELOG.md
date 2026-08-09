# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-08-09

### Added
- Full byte-compatible reimplementation of Victor Taelin's OptMem (LOG.txt + TREE/ decay)
- 9 tools exposed to Hermes: `optmem_note`, `optmem_recall`, `optmem_nap`, `optmem_wake`, `optmem_zoom`, `optmem_forget`, `optmem_config`, `optmem_import`, `optmem_init`
- Native Windows locking (`msvcrt`) + Unix (`fcntl`) — no WSL required
- Two search modes: regex (default, = `memo` CLI behavior) and accent-normalized BM25
- Prefetch with "wake once per session" (Option B): wake injected only on first turn, subsequent turns do recall-only
- Parity with upstream `memo` CLI commands: note, recall, nap, wake, zoom, forget, config, import, init
- Lock file (`.lock`) compatible with original — safe coexistence on same store
- Entry size limit 280 bytes (matches original)
- Decay tree compression ("nap, don't sleep") with configurable `nap_prompt`
- 18 passing tests (engine + provider + integration)
- Comprehensive README with 3-way comparison table (Built-in / Honcho / OptMem)

### Fixed
- Lock file descriptor leak closed (fd closed in `__exit__`)
- `memory_dir` → `dir` alignment across engine
- Import atomicity: validate all lines before any write (matches original behavior)
- BM25 index rebuild only when `mode="bm25"` requested
- Prefetch changed from full wake every turn → wake-once + recall subsequent

### Security
- Rejects entries >280 bytes (matches upstream)
- No network calls, no external dependencies beyond stdlib + PyYAML

[0.1.0]: https://github.com/rarf/optmem-hermes-plugin/releases/tag/v0.1.0