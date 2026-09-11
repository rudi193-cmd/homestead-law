"""The urgent queue — what the season owes, across every matter.

BUG-6 was the urgent queue: it hardcoded its matter list and workers' comp fell
out of it, never iterated. The load-bearing test here is that the queue iterates
`all_matters()` and nothing else, so a matter that exists is a matter the queue
reaches. The rest holds the rung model at the queue: an L5 deadline is not in it,
an L4 shows its derived form, and an unparseable date is a surfaced gap (I-8),
never a silent drop.
"""
from __future__ import annotations

import types

from homestead.keep.rungs import Classified, Rung
from homestead_law import queue as queue_mod
from homestead_law import registry as registry_mod
from homestead_law.queue import counts, cover, queue
from homestead_law.store import Sidecar

TODAY = "2026-08-10"


def _deadline(store: Sidecar, matter: str, item_id: str, rung: Rung, date: str, instruction: str):
    store.put(matter, "deadline", item_id, Classified(rung, date, derived=instruction))


def _register_second_matter(monkeypatch, name: str = "_fake_second") -> None:
    """Add a second matter to the registry the way test_registry does — a real
    module, keyed by its own MATTER, injected for the test. `"_fake_second"`,
    never a real future pack name (bankruptcy/workers' comp land in Wave 3), so
    this stays a *fake* second matter — and keeps exercising "a matter the
    registry did not have before" — even after those packs are registered for
    real."""
    fake = types.ModuleType(f"homestead_law.packs._fake_{name}")
    fake.MATTER = name
    fake.JURISDICTION = "US-NM"
    fake.JURISDICTIONS = ("US-NM",)
    fake.FIELDS = {"deadline": Rung.L1}
    fake.SCHEMA = {"deadline": {"rung": Rung.L1, "matter": name}}
    monkeypatch.setitem(registry_mod.REGISTRY, name, registry_mod._entry(fake))


# ── the BUG-6 fix — the queue iterates the registry ──────────────────────────

def test_the_queue_iterates_the_registry_not_a_hardcoded_list(tmp_path, monkeypatch):
    """A newly registered matter's deadlines appear in the queue with no change
    to the queue — the exact thing the predecessor got wrong when workers' comp
    fell out of a hand-kept list."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _deadline(store, "custody", "hearing", Rung.L1, "2026-09-15", "a hearing is set")
    _register_second_matter(monkeypatch)
    _deadline(store, "_fake_second", "341", Rung.L1, "2026-08-20", "a meeting is set")

    matters_in_queue = {it.matter for it in queue(store, today=TODAY)}
    assert matters_in_queue == {"custody", "_fake_second"}


# ── ordering ─────────────────────────────────────────────────────────────────

def test_overdue_comes_before_upcoming(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _deadline(store, "custody", "hearing", Rung.L1, "2026-09-15", "a hearing is set")   # +36
    _deadline(store, "custody", "response", Rung.L1, "2026-08-05", "a response was due")  # -5

    order = [it.ref[2] for it in queue(store, today=TODAY)]
    assert order.index("response") < order.index("hearing")


def test_a_gap_is_surfaced_first_never_dropped(tmp_path, monkeypatch):
    """I-8: a deadline whose stored date will not parse is not dropped — it is a
    gap, surfaced at the top, flagged, for a human to fix."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _deadline(store, "custody", "hearing", Rung.L1, "2026-09-15", "a hearing is set")
    _deadline(store, "custody", "broken", Rung.L1, "sometime soon", "a deadline with a bad date")

    q = queue(store, today=TODAY)
    assert q[0].ref[2] == "broken"
    assert q[0].gap is True and q[0].days_until is None
    assert "broken" in {it.ref[2] for it in q}, "the gap is present, not dropped"


# ── the rung model, at the queue ─────────────────────────────────────────────

def test_a_sealed_deadline_is_not_in_the_queue(tmp_path, monkeypatch):
    """An L5 deadline is dropped without a trace — the queue may not reveal, or
    count, what L5 forbids."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _deadline(store, "custody", "hearing", Rung.L1, "2026-09-15", "a hearing is set")
    store.put("custody", "deadline", "sealed", Classified(Rung.L5, "2026-08-11"))

    refs = {it.ref[2] for it in queue(store, today=TODAY)}
    assert "sealed" not in refs
    assert "hearing" in refs


def test_an_l4_deadline_shows_the_derived_form_but_still_counts(tmp_path, monkeypatch):
    """An L4 deadline is derived on the ambient queue (the operator sees the
    instruction, not the date), but its urgency is operational and still orders
    and counts it."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _deadline(store, "custody", "eval", Rung.L4, "2026-08-12", "an evaluation is due")  # +2

    item = next(it for it in queue(store, today=TODAY) if it.ref[2] == "eval")
    assert item.shown == "an evaluation is due"      # the derived form
    assert item.shown != "2026-08-12"                # never the date, on the ambient list
    assert item.days_until == 2 and item.overdue is False


# ── counts and the cover (I-31) ──────────────────────────────────────────────

def test_counts_aggregate_overdue_and_due_soon(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _deadline(store, "custody", "response", Rung.L1, "2026-08-05", "overdue")   # -5 overdue
    _deadline(store, "custody", "eval", Rung.L4, "2026-08-12", "due soon")       # +2 soon
    _deadline(store, "custody", "hearing", Rung.L1, "2026-09-30", "far off")     # +51 not soon

    assert counts(store, today=TODAY) == {"overdue": 1, "due_soon": 1}


def test_the_cover_hides_counts_over_a_single_matter(tmp_path, monkeypatch):
    """I-31: '1 overdue' over one matter identifies that matter, so the cover
    shows nothing — it rests on 'Nothing is open'."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _deadline(store, "custody", "response", Rung.L1, "2026-08-05", "overdue")

    assert cover(store, today=TODAY) == {}


def test_the_cover_counts_matters_that_hold_a_deadline_not_registered_types(
    tmp_path, monkeypatch
):
    """I-31's second gate reads *open* matters, and a registered pack is not an
    open matter. More than one matter is registered here but every deadline
    sits in a single one of them, so the household still *is* that one matter
    and the count still resolves to it — the cover must show nothing.

    This is the second-pack failure that would have been silent: passing
    `all_matters()` as the roster satisfies the gate with the *software's*
    shape, so the day a second pack ships this household's "2 overdue" starts
    appearing on a resting screen with no code change and no test failure."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _register_second_matter(monkeypatch)
    _deadline(store, "custody", "response", Rung.L1, "2026-08-05", "overdue")
    _deadline(store, "custody", "answer", Rung.L1, "2026-08-04", "overdue")

    # registry-relative: "more than one", never a count — a third real pack
    # must not turn this test's own premise into the hand-kept number the bite
    # exists to remove.
    assert len(registry_mod.all_matters()) > 1, "more than one matter type is registered"
    assert len({it.matter for it in queue(store, today=TODAY)}) == 1, "one open matter"
    assert cover(store, today=TODAY) == {}


def test_the_cover_shows_a_count_spread_across_two_matters(tmp_path, monkeypatch):
    """Two matters each with an overdue deadline: the count is 2 over 2 matters,
    which clears both anonymity gates, so it may be shown."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _register_second_matter(monkeypatch)
    _deadline(store, "custody", "response", Rung.L1, "2026-08-05", "overdue")
    _deadline(store, "_fake_second", "objection", Rung.L1, "2026-08-04", "overdue")

    assert cover(store, today=TODAY) == {"overdue": 2}


# ── the queue reaches no payload (the chokepoint holds it too) ────────────────

def test_queue_module_reaches_no_payload():
    """The queue works over `Due`s the store already gated; it never reads a
    `.payload`. Held package-wide by test_chokepoint, pinned here for the module
    that is most tempted to reach for a deadline's date."""
    import ast
    from pathlib import Path

    src = Path(queue_mod.__file__).read_text("utf-8")
    reaches = [
        n.lineno for n in ast.walk(ast.parse(src))
        if isinstance(n, ast.Attribute) and n.attr == "payload"
    ]
    assert not reaches, f"queue.py reaches a payload at {reaches}"
