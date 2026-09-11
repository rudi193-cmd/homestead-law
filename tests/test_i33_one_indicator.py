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


# ── level 2: the page's own markup ──────────────────────────────────────────

from homestead_law import server  # noqa: E402  (after the fixtures above)

#: **What an indicator badge is, in the DOM.** `renderIndicator` emits
#: `class="… ind ind-<name>"`; the `ind-` token is the badge's identity to a
#: stylesheet, a screen reader and anything else reading the page. The scan
#: below is over *that emitted markup*, not over a helper's name — which is
#: the whole point. A grep for `renderIndicator(` proves only that one
#: spelling is used once; it says nothing about a branch that writes
#: `'<span class="ind ind-overdue">overdue</span>'` inline and never calls the
#: helper at all. That is the plant `test_the_markup_scan_fires_*` below
#: grafts in, and the name-grep the builder shipped did not catch it.
INDICATOR_CLASS_TOKEN = "ind-"

#: The closed indicator vocabulary, from the composers themselves — not a
#: copy kept here.
INDICATOR_WORDS = frozenset({"overdue", "needs_attention", "nothing_due"})


def _line_of(source: str, offset: int) -> int:
    return source[:offset].count("\n") + 1


def _functions(source: str) -> list[tuple[str, int, int]]:
    """Every top-level `function <name>(…) { … }` in the page's JS as
    `(name, start, end)` character offsets — the structure the scans below
    attribute a piece of markup to. Bodies close on a bare `\n}\n`, which
    is safe here because every nested closure in this page closes on an
    indented line (`  });`)."""
    out = []
    for match in re.finditer(r"\nfunction ([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{", source):
        end = source.find("\n}\n", match.end())
        assert end != -1, f"{match.group(1)} does not close"
        out.append((match.group(1), match.start(), end))
    return out


def _enclosing_function(source: str, offset: int) -> str | None:
    for name, start, end in _functions(source):
        if start <= offset <= end:
            return name
    return None


def _badge_producers(page: str) -> list[tuple[int, str | None]]:
    """Every place the page emits indicator markup, as `(line, enclosing
    function)`. One entry means one producer; more than one means the badge
    can be drawn from more than one place, which is the I-33 failure however
    it is spelled."""
    return [
        (_line_of(page, m.start()), _enclosing_function(page, m.start()))
        for m in re.finditer(re.escape(INDICATOR_CLASS_TOKEN), page)
    ]


def _i33_offences(page: str) -> list[str]:
    """The guard itself, as a function of a page — so the plant below can be
    run through *this* scan rather than through a re-implementation of it.

    Three structural claims, none of which names a helper:

    1. the page emits indicator markup from exactly one place;
    2. that place is a function of its own, not one of the pane-shape
       branches (its enclosing function is not the one that dispatches on
       pane shape);
    3. the pane renderer reaches that one producer exactly once.
    """
    producers = _badge_producers(page)
    offences = []
    if len(producers) != 1:
        offences.append(
            f"indicator markup is emitted from {len(producers)} place(s): "
            f"{producers} — a pane can then carry more than one badge"
        )
        return offences
    line, producer = producers[0]
    if producer is None:
        offences.append(f"indicator markup at line {line} is in no function")
        return offences
    # The renderer is found by the shape it dispatches on — `data.indicator`,
    # the one key every composer returns — not by its name.
    renderers = [
        name for name, start, end in _functions(page)
        if "data.indicator" in page[start:end]
    ]
    if len(renderers) != 1:
        offences.append(f"{len(renderers)} function(s) read data.indicator: {renderers}")
        return offences
    (renderer,) = renderers
    if renderer == producer:
        offences.append(
            f"{renderer} both dispatches on pane shape and emits the badge "
            "itself — the badge must come from one call site outside every "
            "branch"
        )
        return offences
    start, end = next((s, e) for n, s, e in _functions(page) if n == renderer)
    reaches = len(re.findall(re.escape(producer) + r"\s*\(", page[start:end]))
    if reaches != 1:
        offences.append(
            f"{renderer} reaches the badge producer {producer} {reaches} "
            "time(s); exactly once, after every branch, is the whole of I-33 "
            "at this layer"
        )
    return offences


def test_the_page_emits_indicator_markup_from_exactly_one_place():
    """I-33 over the served page, structurally: one producer of badge markup,
    reached once by the one function that dispatches on pane shape. Nothing
    here depends on what the producer is *called* — rename it and the scan
    follows it, because it is found by the markup it emits."""
    assert _i33_offences(server._PAGE) == []


def test_the_one_producer_is_reached_after_every_branch_not_inside_one():
    """The producer's call site sits after the shape dispatch, so every pane
    shape — including the generic fallback — goes through the same single
    badge. A call inside a branch would let two branches each draw one."""
    (producer,) = {p for _, p in _badge_producers(server._PAGE)}
    renderer = next(
        name for name, start, end in _functions(server._PAGE)
        if "data.indicator" in server._PAGE[start:end]
    )
    start, end = next(
        (s, e) for n, s, e in _functions(server._PAGE) if n == renderer)
    body = server._PAGE[start:end]
    branches, _, _ = body.rpartition(producer + "(")
    assert producer + "(" not in branches, (
        "a badge call sits inside a pane-shape branch, not after all of them"
    )


def test_the_markup_scan_fires_on_a_badge_grafted_into_one_branch():
    """A scan that has never fired has not been shown to check anything — and
    the plant is deliberately the one a *name* grep cannot see: a branch that
    writes the badge markup inline instead of calling the helper. The real
    scan runs over the mutated page and must report an offence."""
    page = server._PAGE
    assert _i33_offences(page) == []

    planted = page.replace(
        "html+=renderCards('Children','Child',",
        "html+='<span class=\"ind ind-overdue\">overdue</span>';\n"
        "    html+=renderCards('Children','Child',",
        1,
    )
    assert planted != page, "the plant did not graft"
    assert _i33_offences(planted), (
        "an inline badge in one pane-shape branch passed the scan — the guard "
        "is a name grep again"
    )


def test_the_markup_scan_fires_on_a_second_call_to_the_producer():
    """The other shape a second badge takes: the helper called once per
    branch instead of once after them all. Same real scan, same requirement
    that it fire."""
    page = server._PAGE
    planted = page.replace(
        "html+=renderCards('Children','Child',",
        "html+=renderIndicator(data.indicator);\n"
        "    html+=renderCards('Children','Child',",
        1,
    )
    assert planted != page, "the plant did not graft"
    assert _i33_offences(planted), "a second call to the producer passed the scan"


# ── the composers' own shape: no second indicator-shaped key ────────────────

def _indicator_shaped_keys(pane: dict) -> list[str]:
    """Every key of a composed pane that could be read as a status badge —
    named like one, or carrying one of the closed vocabulary's words as its
    value. `"indicator"` itself is the one that is allowed to be."""
    suspects = []
    for key, value in pane.items():
        named_like_one = any(
            word in key for word in ("indicator", "badge", "status", "urgency",
                                     "alert", "flag", "severity")
        )
        valued_like_one = isinstance(value, str) and value in INDICATOR_WORDS
        if named_like_one or valued_like_one:
            suspects.append(key)
    return suspects


@pytest.mark.parametrize(
    "mt", [custody.MATTER, bankruptcy.MATTER, workers_comp.MATTER, "unregistered"])
def test_no_composer_returns_a_second_indicator_shaped_key(mt, tmp_path, monkeypatch):
    """The data half of the same claim: a pane dict carries exactly one key a
    renderer could turn into a badge. Run against a store seeded so every
    composer has something overdue to judge, so the check is not vacuous on
    an empty pane."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    store.put(custody.MATTER, "registration_contest_deadline", "primary",
              Classified(Rung.L1, "2020-01-01"))
    store.put(custody.MATTER, "mediation_date", "primary", Classified(Rung.L1, "2019-01-01"))
    store.put(bankruptcy.MATTER, "claims_bar_date", "primary", Classified(Rung.L1, "2020-01-01"))
    store.put(bankruptcy.MATTER, "governmental_claims_bar_date", "primary",
              Classified(Rung.L1, "2019-01-01"))
    store.put(workers_comp.MATTER, "hcp_selection_date", "primary",
              Classified(Rung.L4, "2020-01-01",
                         workers_comp.SCHEMA["hcp_selection_date"]["derived"]))
    store.put("unregistered", "note", "primary", Classified(Rung.L4, "x", "A note is on file"))

    pane = panes.pane_for(store, mt, "primary", today=TODAY)
    assert _indicator_shaped_keys(pane) == ["indicator"], (
        f"{mt}'s pane carries more than one key a renderer could draw as a "
        f"badge: {_indicator_shaped_keys(pane)}"
    )


def test_the_key_scan_fires_on_a_planted_second_indicator():
    """The plant for the check above, in both shapes it would take — a second
    key *named* like an indicator, and a second key merely *valued* like
    one."""
    assert _indicator_shaped_keys({"indicator": "overdue", "rows": []}) == ["indicator"]
    assert _indicator_shaped_keys(
        {"indicator": "overdue", "creditor_status": "needs_attention"}
    ) == ["indicator", "creditor_status"]
    assert _indicator_shaped_keys(
        {"indicator": None, "urgency": None}
    ) == ["indicator", "urgency"]
