"""I-33 — each pane shows at most one status indicator.

Two levels, matching where the badge is actually produced:

1. **The composer's own data shape.** Every `app.panes` composer returns a
   single `"indicator"` key — `None` or one of a closed three-word set —
   never a list. A scalar cannot become two badges no matter how many
   overdue dates fed into it; `tests/test_panes.py` already covers the
   arithmetic (the "worst" date wins), and this file adds the structural
   half: the returned value is never a list or tuple, across every pane
   shape, including one deliberately built to have two candidate overdue
   dates at once.

2. **The page's own JS.** `server._PAGE`'s `renderPane(data)` calls
   `renderIndicator(data.indicator)` exactly once, regardless of which pane
   shape it drew — so no matter how the markup around it changes, the badge
   itself is emitted from one call site. The scan below extracts that
   function's body by name and counts the call, and the plant test proves
   the counter would catch a second one if a future edit duplicated it —
   the house rule that a scan which has never fired has not been shown to
   check anything.
"""
from __future__ import annotations

import re

import pytest

from homestead.keep.rungs import Classified, Rung
from homestead_law import instances
from homestead_law.app import panes
from homestead_law.packs import bankruptcy, custody, workers_comp
from homestead_law.store import Sidecar

TODAY = "2026-08-10"


# ── level 1: the composer's own shape ───────────────────────────────────────

@pytest.mark.parametrize("mt", [custody.MATTER, bankruptcy.MATTER, workers_comp.MATTER, "unregistered"])
def test_every_pane_shape_carries_a_single_scalar_indicator(mt, tmp_path, monkeypatch):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    pane = panes.pane_for(Sidecar(), mt, "primary", today=TODAY)
    assert "indicator" in pane
    assert not isinstance(pane["indicator"], (list, tuple, set, dict))
    assert pane["indicator"] is None or isinstance(pane["indicator"], str)


def test_two_overdue_candidates_still_yield_one_indicator_not_two(tmp_path, monkeypatch):
    """The plant, at the data level: both bar dates are overdue at once, and
    the pane still names exactly one indicator — the worst of the two,
    never a pair."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    store.put(bankruptcy.MATTER, "claims_bar_date", "primary", Classified(Rung.L1, "2026-01-01"))
    store.put(bankruptcy.MATTER, "governmental_claims_bar_date", "primary", Classified(Rung.L1, "2025-01-01"))

    pane = panes.pane_for(store, bankruptcy.MATTER, "primary", today=TODAY)
    assert pane["indicator"] == "overdue"
    assert not isinstance(pane["indicator"], (list, tuple))


def test_two_overdue_children_related_dates_still_one_custody_indicator(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    store.put(custody.MATTER, "registration_contest_deadline", "primary", Classified(Rung.L1, "2020-01-01"))
    store.put(custody.MATTER, "mediation_date", "primary", Classified(Rung.L1, "2019-01-01"))
    store.put(
        custody.MATTER, "child.name", instances.item_id("primary", "c1"),
        Classified(Rung.L4, "A", custody.SCHEMA["child.name"]["derived"]),
    )
    store.put(
        custody.MATTER, "child.name", instances.item_id("primary", "c2"),
        Classified(Rung.L4, "B", custody.SCHEMA["child.name"]["derived"]),
    )
    pane = panes.pane_for(store, custody.MATTER, "primary", today=TODAY)
    assert pane["indicator"] == "overdue"
    assert len(pane["children"]) == 2                 # two cards, still one indicator


# ── level 2: the page's JS ───────────────────────────────────────────────────

from homestead_law import server  # noqa: E402  (after the fixtures above)


def _extract_function(source: str, name: str) -> str:
    """The body of a top-level `function <name>(...) { ... }` in `source` —
    matched non-greedily up to the first `\\n}\\n`, which is safe here
    because every nested closure in this page's functions closes on an
    indented line (`  });`), never a bare `}` flush against a newline until
    the function's own end."""
    match = re.search(
        r"function " + re.escape(name) + r"\([^)]*\)\s*\{(.*?)\n\}\n",
        source, re.S,
    )
    assert match, f"{name} not found in the page"
    return match.group(1)


def _count_indicator_calls(js_source: str) -> int:
    """How many times a pane-render function invokes the one indicator
    helper — the guard I-33 rests on at the page layer."""
    return len(re.findall(r"renderIndicator\(", js_source))


def test_render_pane_calls_the_indicator_helper_exactly_once():
    body = _extract_function(server._PAGE, "renderPane")
    assert _count_indicator_calls(body) == 1


def test_the_indicator_call_site_is_outside_every_branch():
    """Not merely one call in the text — one call *not itself repeated per
    branch*: `renderIndicator(` must not appear inside any of the four
    `if`/`else if`/`else` sections that pick the pane shape, only after
    them. A second occurrence hiding inside one branch would still pass a
    naive occurs-once-per-branch check while making some panes able to draw
    two under the wrong data."""
    body = _extract_function(server._PAGE, "renderPane")
    branches, _, tail = body.rpartition("renderIndicator(")
    assert "renderIndicator(" not in branches, (
        "an indicator call sits inside a branch, not after all of them"
    )


def test_the_guard_fires_when_a_second_indicator_call_is_planted():
    """A scan that has never fired has not been shown to check anything:
    take the real `renderPane` body and graft in a second call, the shape a
    careless future edit (an indicator per branch instead of one shared
    call) would actually take, and show the counter catches it."""
    body = _extract_function(server._PAGE, "renderPane")
    assert _count_indicator_calls(body) == 1

    planted = body.replace(
        "html+='<h3>Children</h3>';",
        "html+='<h3>Children</h3>';\n    html+=renderIndicator(data.indicator);",
        1,
    )
    assert _count_indicator_calls(planted) == 2


def test_a_clean_snippet_with_no_indicator_at_all_counts_zero():
    """The counter itself, exercised on the boundary case — the generic
    pane's own branch draws no indicator call of its own (the shared one
    sits after every branch), so a slice of just that branch counts zero,
    not a false positive."""
    body = _extract_function(server._PAGE, "renderPane")
    branches, _, _ = body.rpartition("renderIndicator(")
    assert _count_indicator_calls(branches) == 0
