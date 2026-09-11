"""What a document still *asserts*, for the grep guards that scan prose.

House style keeps history struck through rather than deleting it, so a stale
sentence quoted inside `~~...~~` is not a live claim and must not trip a
drift guard. Two guards need that reading — `tests/test_docs_drift.py` (the
README status banner and the `rules.accept` wording) and
`tests/test_plan_affairs_face.py` (a struck bite's own predicted PR/release
must not stand in for the PR/release that actually shipped it) — and two
copies of it would drift apart, which is the same failure those guards exist
to catch. One helper, imported by both. Ported from the engine's own
`tests/_strikethrough.py` (X7-drift-engine) rather than rewritten, for the
same reason `homestead_law.packs.custody` copies a derived-form sentence
verbatim instead of retyping it: one definition of "what counts as a live
claim," not two that can disagree.

`live()` does two things:

* drops every `~~...~~` span, `re.DOTALL` because a struck span wraps lines;
* collapses runs of whitespace to single spaces, because the prose it scans
  is hard-wrapped — a phrase split across a line break must still match as
  one string.
"""
from __future__ import annotations

import re

_STRUCK = re.compile(r"~~.*?~~", re.DOTALL)
_WHITESPACE = re.compile(r"\s+")


def live(text: str) -> str:
    """The still-asserted text: struck spans removed, whitespace flattened."""
    return _WHITESPACE.sub(" ", _STRUCK.sub("", text)).strip()
