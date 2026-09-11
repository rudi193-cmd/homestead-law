"""Bite 4, end to end — the store → gate → surface pipeline, headless.

`demo.compose_demo` seeds a synthetic custody matter into the store, lists it and
opens two details entirely through `Window` and `serve()`. This is the plan's
'done when' run as a *pipeline* rather than against hand-built records: a real
matter, loaded from disk, composed through the gate — the L4 payload absent from
the list and present in the detail, and no L5 anywhere.

No display is opened; `view.run` (the tkinter drawing) is a thin consumer of this
same `Window`, and is exercised by `python -m homestead.app --smoke`.
"""
from __future__ import annotations

import types

from homestead.keep.rungs import Classified, Rung
from homestead_law import queue as queue_mod
from homestead_law import registry as registry_mod
from homestead_law.app import demo
from homestead_law.app.cover import cover_counts
from homestead_law.registry import all_matters
from homestead_law.store import Sidecar


def _register_second_matter(monkeypatch, name: str = "_fake_second") -> None:
    """Add a second matter to the registry — a real module, keyed by its own
    `MATTER`, injected for the test. `"_fake_second"`, never a real future pack
    name (bankruptcy/workers' comp land in Wave 3), so this stays a fake second
    matter even after they are registered for real. `monkeypatch.setitem`
    removes it again at teardown, so the registry a later test reads is the real
    one no matter what order the suite runs in. It declares `JURISDICTIONS`
    alongside `JURISDICTION` — the pack contract decision 1 settles — so this
    fake stays a stand-in for a real pack once the registry validates that
    tuple."""
    fake = types.ModuleType(f"homestead_law.packs.{name}")
    fake.MATTER = name
    fake.JURISDICTION = "US-NM"
    fake.JURISDICTIONS = ("US-NM",)
    fake.FIELDS = {"deadline": Rung.L1}
    fake.SCHEMA = {"deadline": {"rung": Rung.L1, "matter": name}}
    monkeypatch.setitem(registry_mod.REGISTRY, name, registry_mod._entry(fake))


def test_the_pipeline_composes_the_surfaces(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    out = demo.compose_demo(Sidecar())

    # L1 and L3 payloads render on the list.
    assert "Dept 4" in out
    assert "FL-2026-00123" in out
    # the L4 child.name shows its derived form on the list (L9-child-name:
    # the demo's child record moved off the retired singular child_name).
    assert "A child's name is on file" in out

    # the L4 child.name payload appears only in the detail line, never on the list.
    list_section, detail_section = out.split("detail child.name", 1)
    assert "A. Rivera, age 8" not in list_section
    assert "A. Rivera, age 8" in detail_section

    # the sealed ssn renders nowhere — its payload is absent and the detail denies.
    assert "123-45-6789" not in out
    assert "deny" in out


def test_open_matter_lists_everything_but_the_sealed_field(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    demo.seed(store)

    window = demo.open_matter(store)
    assert window.state == "list"

    refs = {row.ref for row in window.rows}
    assert ("custody", "ssn", "primary") not in refs          # L5 dropped, no trace
    assert ("custody", "child.name", "primary.ar") in refs    # L4 shown as derived
    assert ("custody", "courthouse", "primary") in refs       # L1 shown
    assert all("123-45-6789" not in row.text for row in window.rows)


def test_the_queue_demo_orders_gates_and_hides_the_cover(tmp_path, monkeypatch):
    """The queue rendered headless: overdue before far-off, the L4 deadline shown
    as its derived instruction (never its date), and the resting cover held to
    `queue.cover()`'s own rule (I-31) rather than a literal "Nothing is open" —
    true under any registry, not only today's one-matter one. `cover()` returns
    `{}` whenever fewer than two matters hold a deadline or every count is below
    the anonymity floor, and the real counts otherwise (`cover.K`,
    `cover_counts`). Both halves are checked: the rule, *and* that the composed
    surface drew what the rule said — a test that only recomputed the rule would
    pass with the cover line deleted from the surface entirely."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    out = demo.compose_queue(store)

    overdue_line = next(i for i, l in enumerate(out.splitlines()) if "overdue by 5" in l)
    hearing_line = next(i for i, l in enumerate(out.splitlines()) if "due in 36" in l)
    assert overdue_line < hearing_line

    assert "A submission is due" in out    # the L4 deadline's derived form
    assert "2026-08-12" not in out         # never the L4 date on the ambient queue

    # the rule `cover()` is held to, recomputed here rather than restated: the
    # raw aggregate through `cover_counts`, over the matters that actually hold
    # a deadline. Planting a `cover()` that skips the check (returning the raw
    # counts) must fail this line.
    resting = queue_mod.cover(store, today=demo.TODAY)
    raw = queue_mod.counts(store, today=demo.TODAY)
    open_matters = sorted({it.matter for it in queue_mod.queue(store, today=demo.TODAY)})
    assert resting == cover_counts(open_matters, **raw)

    # …and that the composed surface *drew* that answer, which is the job the
    # literal `"Nothing is open" in out` used to do. Without this, deleting the
    # cover line from `compose_queue` outright leaves the test green — the rule
    # above is about `cover()`, not about what the operator is shown.
    cover_line = next(l for l in out.splitlines() if l.startswith("cover (resting):"))
    if resting:
        for category, n in resting.items():
            assert category in cover_line and str(n) in cover_line
    else:
        assert "Nothing is open" in cover_line
    for category in raw:
        if category not in resting:
            # absence, not zero (I-31): a dropped count leaves no key and no
            # "0 overdue" standing in for it.
            assert category not in cover_line


# ── the window opens on the household's own records (`compose_store`) ────────
#
# `compose_store()` is the real-vs-demo decision factored out of `run()`, so it
# can be driven headlessly: the store `homestead-law put` writes is the one the
# window draws, and only an empty store falls back to the seeded demo.


def test_compose_store_falls_back_to_demo_when_the_real_store_is_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    from homestead_law.app import view

    context = view.compose_store()

    assert context.demo is True
    assert context.today == demo.TODAY
    assert context.store.records(demo.MATTER) != []


def test_compose_store_never_seeds_the_real_root_on_fallback(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    from homestead.keep.store import SIDECAR, SQLiteAdapter
    from homestead_law.app import view

    assert view.compose_store().demo is True
    # `compose_store()` redirected `HOMESTEAD_HOME` to the fallback's own
    # tmpdir; point back at the real root to inspect it directly.
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    assert SQLiteAdapter(tmp_path / "homestead-law.db").read_matter(SIDECAR, demo.MATTER) == []


def test_compose_store_opens_the_real_store_when_a_record_was_entered(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    import os

    from homestead.keep.rungs import Classified, Rung
    from homestead_law.app import view
    from homestead_law.app.window import Window

    Sidecar().put("custody", "courthouse", "primary", Classified(Rung.L1, "Dept 9"))

    context = view.compose_store()

    assert context.demo is False
    assert os.environ["HOMESTEAD_HOME"] == str(tmp_path)
    window = Window()
    window.open_list(context.store.records("custody"))
    assert [row.text for row in window.rows] == ["Dept 9"]
    assert "Jordan Rivera" not in [row.text for row in window.rows]   # no demo bleed


def test_compose_store_does_not_seed_the_demo_for_a_second_matters_records(
    tmp_path, monkeypatch
):
    """`_has_real_data` iterates `all_matters()` (I-23), so a household whose
    only records live in a *second* matter has real data and must not be handed
    the custody demo on top of it. Held with a second matter registered, because
    with one pack the registry loop and a hardcoded `demo.MATTER` are
    indistinguishable — this is the one test that tells them apart."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    import os

    from homestead_law.app import view

    _register_second_matter(monkeypatch)
    Sidecar().put(
        "_fake_second", "deadline", "primary",
        Classified(Rung.L1, "2026-09-01", derived="a deadline is set"),
    )

    context = view.compose_store()

    assert context.demo is False, "a second matter's records are real data too"
    assert os.environ["HOMESTEAD_HOME"] == str(tmp_path), "the real root stays bound"
    assert context.store.records(demo.MATTER) == [], "no custody demo seeded over it"


def test_the_banner_and_hint_name_the_ways_in():
    from homestead_law.app import view

    assert "demonstration" in view.DEMO_BANNER
    assert "homestead-law ui" in view.DEMO_BANNER and "homestead-law put" in view.DEMO_BANNER
    assert "homestead-law ui" in view.ENTRY_HINT


# ── the cover and the queue are indifferent to how many matters exist ───────
#
# BUG-6's shape in the tkinter view: a single "Open custody matter" button and
# a queue pane that loaded only `demo.MATTER` would leave a second registered
# matter's deadlines reachable in the queue *list* but unopenable in the
# window, because the pane never loaded that matter's records. These two tests
# inject a second matter (`_fake_second` — never a real future pack name, so
# Wave 3's bankruptcy/workers'-comp packs cannot collide with it) and hold
# `view.py` to the registry rather than to custody by name.


def test_the_cover_offers_one_open_button_per_registered_matter(tmp_path, monkeypatch):
    """`matter_buttons(store)` — headless, no tkinter — is one `(label, name)`
    pair per entry in `all_matters()`. A newly registered matter gets a button
    with no change to `view.py` (I-23), the same guarantee the queue holds."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    from homestead_law.app import view

    _register_second_matter(monkeypatch)
    store = Sidecar()

    buttons = view.matter_buttons(store)
    names = {name for _, name in buttons}

    assert len(buttons) == len(all_matters())
    assert names == set(all_matters())
    assert {"custody", "_fake_second"} <= names
    for label, name in buttons:
        assert name in label, f"button label {label!r} does not name its matter"


def test_the_queue_pane_opens_a_detail_from_any_matter(tmp_path, monkeypatch):
    """A deadline in a second, non-custody matter appears in `queue.queue()`
    and — once the pane's records are loaded the way `show_queue` loads them,
    one `open_list` over every registered matter's records — its ref opens
    through the same gated detail path as any custody item."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    from homestead_law.app.window import Window

    _register_second_matter(monkeypatch)
    store = Sidecar()
    store.put(
        "_fake_second", "deadline", "primary",
        Classified(Rung.L1, "2026-09-01", derived="a deadline is set"),
    )

    items = queue_mod.queue(store, today="2026-08-10")
    match = next(it for it in items if it.matter == "_fake_second")
    assert match.ref == ("_fake_second", "deadline", "primary")

    window = Window()
    window.open_list(
        [record for name in all_matters() for record in store.records(name)]
    )
    served = window.open_detail(match.ref)
    assert served.value == "2026-09-01"


def test_the_demo_store_holds_one_instance_like_a_real_one(tmp_path, monkeypatch):
    """The demo is the store a reader meets first, so it must look like a store
    the real doors wrote. Seeding the four deadlines under their bare names put
    four phantom instances into the key scan — ids `instances.item_id` refuses,
    so `show custody` would have listed instances no other command could open.
    They are `primary.<name>` now, exactly as `deadline custody <name> …`
    writes."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    from homestead_law import instances as instances_mod
    from homestead_law.app import demo

    store = Sidecar()
    demo.seed(store)
    demo.seed_deadlines(store)

    assert instances_mod.instances_of(store, demo.MATTER) == ("primary",)
    subs = {
        instances_mod.split_item_id(ref[2])[1]
        for ref, _ in store.records(demo.MATTER)
        if ref[1] == "deadline"
    }
    assert subs == set(demo._DEADLINES)
