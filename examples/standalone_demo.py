#!/usr/bin/env python3
"""Standalone OptMem demo — no Hermes required.

Shows the full memory lifecycle against a throwaway temp store:
  note -> recall (regex) -> recall (BM25) -> auto-nap -> wake.

Run:  python examples/standalone_demo.py
"""
from __future__ import annotations

import os
import tempfile

from optmem.engine import OptMemEngine


def main() -> None:
    store = os.path.join(tempfile.mkdtemp(), "optmem_memory")
    eng = OptMemEngine(store)
    eng.init_store()

    print("=== OptMem standalone demo ===\n")

    # 1. Record durable facts (one atomic line each, <=280 bytes)
    #    Pass (text) only — the engine stamps the date automatically.
    #    To backdate, call eng.append(text, date="YYYY-MM-DD").
    facts = [
        "cliente X aprovou orcamento Q3",
        "deploy em staging autorizado pelo cliente",
        "paywall onboarding (email-confirm) testado em prod",
        "conversao base Diego (200 motoristas) iniciada",
        "churn mensal monitorizado semanalmente",
    ]
    for f in facts:
        eng.append(f)
        print(f"  + note: 2026-08-09 {f}")

    # 2. Recall — regex (default, matches `memo recall`)
    print("\n--- recall('paywall') [regex] ---")
    for r in eng.recall("paywall"):
        print(f"  # {r}")

    # 3. Recall — BM25 with accent normalization
    print("\n--- recall('orcamento', mode=bm25) [accent-tolerant] ---")
    for r in eng.recall("orcamento", mode="bm25"):
        print(f"  # {r}")

    # 4. Auto-compaction (deterministic, LLM-free)
    print("\n--- auto-compaction (drain pending naps) ---")
    naps = 0
    while True:
        nxt = eng.next_nap()
        if not nxt:
            break
        (lo, hi), _prompt = nxt
        lines = eng.block_lines(lo, hi)
        # Mirror provider._local_summary logic (kept inline for the demo)
        summary = _demo_summary(lines)
        if not summary:
            break
        eng.apply_nap(lo, hi, summary)
        print(f"  ~ nap({lo},{hi}): {summary}")
        naps += 1
        if naps > 50:  # safety
            break

    # 5. Wake — the decayed, compressed context
    print("\n--- wake_lines() [decayed context] ---")
    for line in eng.wake_lines():
        print(f"  {line}")

    print("\nDone. All memory stays on disk, zero tokens spent on recall/compaction.")


def _demo_summary(lines: list[str]) -> str:
    """Minimal extractive summary mirroring the provider's local summarizer."""
    durable = ("aprov", "decid", "orcament", "budget", "deploy", "client",
               "paywall", "churn", "gtm", "growth", "staging", "onboard",
               "convers", "base")
    scored = []
    for ln in lines:
        low = ln.lower()
        score = sum(1 for k in durable if k in low)
        if len(ln) >= 10 and ln[0:4].isdigit() and ln[4] == "-":
            score += 2
        scored.append((score, ln.strip()))
    if not any(s > 0 for s, _ in scored):
        return ""
    scored.sort(key=lambda x: x[0], reverse=True)
    return " | ".join(s for _, s in scored[:3])


if __name__ == "__main__":
    main()
