"""S1 — the cover's counts (I-31), now the engine's own arithmetic.

~~This file used to carry its own `cover_counts(matters, **counts)` —
the whole K=2 anonymity-gate arithmetic, vendored here with no `by_matter`
parameter.~~ (struck 2026-09-11, L5-sync, per the E4-cover-distribution
audit's finding, 2026-09-11 — "law carries a vendored `app/cover.py` with the
old signature"): the implementation now lives where the rest of Wave 4's
cover work landed, engine #58's `homestead.app.cover.cover_counts`, which
adds the `by_matter` distribution parameter Gate 2 needed to close the gap
the L2c audit found (`docs/DECISION-cover-re-identification.md`): a roster
of two truthfully open matters could still satisfy the old, roster-only
Gate 2 with a `(2, 0)` distribution — both items in one of them — and the
number would simply appear.

This module is now a thin re-export, so every existing
`from homestead_law.app.cover import cover_counts` import here keeps
working unchanged. `homestead_law.queue.cover` is the one caller, and it now
passes `by_matter` — built from the queue's own per-matter overdue/due_soon
counts — so Gate 2 reads the household's real spread instead of trusting the
roster's shape. `test_invariants_chokepoint.py` still scans this file with
the rest of `homestead_law/app/`; it imports a name and reflects over
nothing.
"""
from __future__ import annotations

from homestead.app.cover import K, cover_counts

__all__ = ["cover_counts", "K"]
