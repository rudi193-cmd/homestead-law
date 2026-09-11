"""`app.panes` — the pane registry and its three composers (L4-surfaces).

Headless throughout: every composer is called directly against a real store,
never through the browser. Planted L4 content proves the absent-on-the-list,
present-on-open contract the same way `tests/test_view.py` proves it for
`Window`.
"""
from __future__ import annotations

import types

import pytest

from homestead.keep.rungs import Classified, Rung
from homestead_law import instances
from homestead_law import registry as registry_mod
from homestead_law.app import panes
from homestead_law.packs import bankruptcy, custody, workers_comp
from homestead_law.store import Sidecar

TODAY = "2026-08-10"


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    yield


# ── custody pane ─────────────────────────────────────────────────────────────

def test_custody_pane_lists_children_derived_and_withholds_the_payload():
    store = Sidecar()
    store.put(
        custody.MATTER, "child.name", instances.item_id("primary", "c1"),
        Classified(Rung.L4, "Alex Rivera", custody.SCHEMA["child.name"]["derived"]),
    )
    store.put(
        custody.MATTER, "child.dob", instances.item_id("primary", "c1"),
        Classified(Rung.L4, "2018-04-01", custody.SCHEMA["child.dob"]["derived"]),
    )

    pane = panes.pane_for(store, custody.MATTER, "primary", today=TODAY)

    assert pane["matter"] == custody.MATTER and pane["instance"] == "primary"
    card = pane["children"][0]
    assert card["sub"] == "c1"
    assert card["fields"]["child.name"]["text"] == "A child's name is on file"
    assert card["fields"]["child.dob"]["text"] == "A child's date of birth is on file"

    import json
    blob = json.dumps(pane)
    assert "Alex Rivera" not in blob and "2018-04-01" not in blob


def test_custody_pane_serves_the_relocation_timeline_as_l1_l3_payloads():
    store = Sidecar()
    store.put(custody.MATTER, "custody_order_date", "primary", Classified(Rung.L1, "2025-01-10"))
    store.put(custody.MATTER, "move_date", "primary", Classified(Rung.L3, "2026-06-01", "A move date is on file"))
    store.put(custody.MATTER, "registration_contest_deadline", "primary", Classified(Rung.L1, "2026-09-01"))

    pane = panes.pane_for(store, custody.MATTER, "primary", today=TODAY)
    timeline = {t["item_type"]: t["text"] for t in pane["timeline"]}
    assert timeline["custody_order_date"] == "2025-01-10"
    assert timeline["move_date"] == "2026-06-01"           # L3 payload, not derived
    assert timeline["registration_contest_deadline"] == "2026-09-01"


@pytest.mark.parametrize(
    "deadline,indicator",
    [("2026-07-01", "overdue"), ("2026-08-15", "needs_attention"), ("2027-01-01", "nothing_due")],
)
def test_custody_pane_indicator_from_the_contest_deadline(deadline, indicator):
    store = Sidecar()
    store.put(custody.MATTER, "registration_contest_deadline", "primary", Classified(Rung.L1, deadline))
    pane = panes.pane_for(store, custody.MATTER, "primary", today=TODAY)
    assert pane["indicator"] == indicator


def test_custody_pane_indicator_is_none_with_nothing_to_judge():
    pane = panes.pane_for(Sidecar(), custody.MATTER, "primary", today=TODAY)
    assert pane["indicator"] is None
    assert pane["children"] == [] and pane["timeline"] == []


def test_custody_pane_indicator_skips_an_unparseable_timeline_date():
    """A relocation-timeline field is plain free text, not the strict-parsed
    `deadline` door — the operator may not have typed a real date yet, and
    the indicator degrades to `None` rather than raising."""
    store = Sidecar()
    store.put(custody.MATTER, "registration_contest_deadline", "primary", Classified(Rung.L1, "TBD"))
    pane = panes.pane_for(store, custody.MATTER, "primary", today=TODAY)
    assert pane["indicator"] is None


# ── bankruptcy pane ──────────────────────────────────────────────────────────

def test_bankruptcy_pane_lists_creditors_and_the_bar_date_countdown():
    store = Sidecar()
    store.put(
        bankruptcy.MATTER, "creditor.name", instances.item_id("primary", "cred1"),
        Classified(Rung.L3, "First National Bank", bankruptcy.SCHEMA["creditor.name"]["derived"]),
    )
    store.put(bankruptcy.MATTER, "claims_bar_date", "primary", Classified(Rung.L1, "2026-08-01"))
    store.put(bankruptcy.MATTER, "governmental_claims_bar_date", "primary", Classified(Rung.L1, "2027-01-01"))

    pane = panes.pane_for(store, bankruptcy.MATTER, "primary", today=TODAY)

    card = pane["creditors"][0]
    assert card["sub"] == "cred1"
    # creditor.name is L3, not L4: at S1_LIST's ceiling (L3) the payload
    # itself renders, the same posture every other L1-L3 pane field takes —
    # only the pack's L4 fields (creditor.note) ever show a derived stand-in.
    assert card["fields"]["creditor.name"]["text"] == "First National Bank"

    by_field = {b["field"]: b for b in pane["bar_dates"]}
    assert by_field["claims_bar_date"]["overdue"] is True
    assert by_field["claims_bar_date"]["days_until"] < 0
    assert by_field["governmental_claims_bar_date"]["overdue"] is False
    assert pane["indicator"] == "overdue"


def test_bankruptcy_pane_renders_the_notice_verbatim():
    pane = panes.pane_for(Sidecar(), bankruptcy.MATTER, "primary", today=TODAY)
    assert pane["notice"] == bankruptcy.NOTICE


def test_bankruptcy_pane_bar_date_gap_when_unparseable():
    store = Sidecar()
    store.put(bankruptcy.MATTER, "claims_bar_date", "primary", Classified(Rung.L1, "not a date"))
    pane = panes.pane_for(store, bankruptcy.MATTER, "primary", today=TODAY)
    entry = pane["bar_dates"][0]
    assert entry["gap"] is True and entry["days_until"] is None and entry["overdue"] is None
    assert pane["indicator"] is None


def _signal_pack(name: str = "_fake_signal_pane") -> types.ModuleType:
    fake = types.ModuleType(f"homestead_law.packs.{name}")
    fake.MATTER = name
    fake.JURISDICTION = "US-NM"
    fake.JURISDICTIONS = ("US-NM",)
    fake.FIELDS = {"award_amount": Rung.L3}
    fake.SCHEMA = {"award_amount": {"rung": Rung.L3, "matter": name,
                                    "derived": "An award amount is on file"}}
    return fake


def test_bankruptcy_pane_carries_the_plan_period_line_when_present(monkeypatch):
    fake = _signal_pack()
    monkeypatch.setitem(registry_mod.REGISTRY, fake.MATTER, registry_mod._entry(fake))

    store = Sidecar()
    store.put(bankruptcy.MATTER, "plan_confirmation_date", "primary", Classified(Rung.L1, "2026-01-01"))
    store.put(fake.MATTER, "award_amount", "grant-1", Classified(Rung.L3, "1000", "An award amount is on file"))

    pane = panes.pane_for(store, bankruptcy.MATTER, "primary", today=TODAY)
    assert len(pane["plan_period"]) == 1
    assert pane["plan_period"][0].startswith("bankruptcy/primary:")
    import json
    assert "1000" not in json.dumps(pane)


def test_bankruptcy_pane_carries_no_plan_period_line_when_absent():
    store = Sidecar()
    store.put(bankruptcy.MATTER, "plan_confirmation_date", "primary", Classified(Rung.L1, "2026-01-01"))
    pane = panes.pane_for(store, bankruptcy.MATTER, "primary", today=TODAY)
    assert pane["plan_period"] == []


def test_bankruptcy_pane_scopes_the_plan_period_line_to_its_own_instance(monkeypatch):
    """Two bankruptcy instances (a dismissed case and a refiling) each get
    their own line, and one instance's pane never shows the other's."""
    fake = _signal_pack()
    monkeypatch.setitem(registry_mod.REGISTRY, fake.MATTER, registry_mod._entry(fake))

    store = Sidecar()
    store.put(bankruptcy.MATTER, "plan_confirmation_date", "case-a", Classified(Rung.L1, "2026-01-01"))
    store.put(bankruptcy.MATTER, "plan_confirmation_date", "case-b", Classified(Rung.L1, "2026-02-01"))
    store.put(fake.MATTER, "award_amount", "grant-1", Classified(Rung.L3, "1000", "An award amount is on file"))

    pane_a = panes.pane_for(store, bankruptcy.MATTER, "case-a", today=TODAY)
    pane_b = panes.pane_for(store, bankruptcy.MATTER, "case-b", today=TODAY)
    assert pane_a["plan_period"] == ["bankruptcy/case-a: income or assets arising during the "
                                     "plan: confirm with your attorney (11 U.S.C. §§ 541(a)(7), "
                                     "1306(a), 1329; disclosure duties under the plan and local rules)"]
    assert pane_b["plan_period"][0].startswith("bankruptcy/case-b:")


# ── workers' comp pane ───────────────────────────────────────────────────────

def test_workers_comp_pane_lists_exams_and_the_treatment_timeline_derived():
    store = Sidecar()
    store.put(
        workers_comp.MATTER, "ime.date", instances.item_id("primary", "2026-05"),
        Classified(Rung.L4, "2026-05-12", workers_comp.SCHEMA["ime.date"]["derived"]),
    )
    store.put(
        workers_comp.MATTER, "ime.examiner", instances.item_id("primary", "2026-05"),
        Classified(Rung.L4, "Dr. R. Chen", workers_comp.SCHEMA["ime.examiner"]["derived"]),
    )
    store.put(
        workers_comp.MATTER, "hcp_selection_date", "primary",
        Classified(Rung.L4, "2026-02-01", workers_comp.SCHEMA["hcp_selection_date"]["derived"]),
    )

    pane = panes.pane_for(store, workers_comp.MATTER, "primary", today=TODAY)

    card = pane["exams"][0]
    assert card["sub"] == "2026-05"
    assert card["fields"]["ime.date"]["text"] == "An independent medical exam date is on file"
    import json
    assert "2026-05-12" not in json.dumps(pane) and "Chen" not in json.dumps(pane)

    timeline = {t["item_type"]: t["text"] for t in pane["timeline"]}
    assert timeline["hcp_selection_date"] == "A health care provider selection date is on file"


def test_workers_comp_pane_indicator_is_always_none():
    """Every field this pane shows is L4-derived text — there is no
    parseable date to judge urgency from, so the indicator never fires."""
    store = Sidecar()
    store.put(workers_comp.MATTER, "hcp_selection_date", "primary",
              Classified(Rung.L4, "2026-01-01", workers_comp.SCHEMA["hcp_selection_date"]["derived"]))
    pane = panes.pane_for(store, workers_comp.MATTER, "primary", today=TODAY)
    assert pane["indicator"] is None


# ── I-23: registry-relative fallback, tested both ways ──────────────────────

def test_pane_for_falls_back_to_generic_for_a_wholly_unregistered_matter():
    """A matter `PANES` has never heard of and the registry has never heard
    of either — the wholly-unknown case."""
    store = Sidecar()
    store.put("nobody_registered_this", "note", "primary", Classified(Rung.L4, "x", "A note is on file"))
    pane = panes.pane_for(store, "nobody_registered_this", "primary", today=TODAY)
    assert pane["matter"] == "nobody_registered_this"
    assert pane["rows"][0]["text"] == "A note is on file"
    assert pane["indicator"] is None


def test_pane_for_falls_back_to_generic_for_a_registered_matter_with_no_pane(monkeypatch):
    """A matter *is* registered (a real pack, a real entry in `all_matters()`)
    but `PANES` names no composer for it — the other half of the fallback,
    and the one that matters once a fourth pack ships before its own pane
    does."""
    fake = types.ModuleType("homestead_law.packs._fake_no_pane")
    fake.MATTER = "_fake_no_pane"
    fake.JURISDICTION = "US-NM"
    fake.JURISDICTIONS = ("US-NM",)
    fake.FIELDS = {"case_number": Rung.L1}
    fake.SCHEMA = {"case_number": {"rung": Rung.L1, "matter": fake.MATTER}}
    monkeypatch.setitem(registry_mod.REGISTRY, fake.MATTER, registry_mod._entry(fake))
    assert fake.MATTER not in panes.PANES        # this is the case under test

    store = Sidecar()
    store.put(fake.MATTER, "case_number", "primary", Classified(Rung.L1, "BK-1"))
    pane = panes.pane_for(store, fake.MATTER, "primary", today=TODAY)
    assert pane["rows"][0]["text"] == "BK-1"
    assert pane["indicator"] is None


def test_the_pane_registry_is_a_subset_of_the_real_matters():
    from homestead_law.registry import all_matters

    assert set(panes.PANES) <= set(all_matters())
    assert set(panes.PANES) == {custody.MATTER, bankruptcy.MATTER, workers_comp.MATTER}


# ── XSS: an id shaped like a script tag is refused, never stored or rendered ─

def test_pane_for_refuses_a_script_shaped_instance_id():
    """`instances.item_id` is the id gate every door already trusts; `pane_for`
    calls it before touching the store, so a hostile id never reaches
    `records_of` at all."""
    with pytest.raises(instances.InvalidId):
        panes.pane_for(Sidecar(), custody.MATTER, "<script>alert(1)</script>", today=TODAY)


def test_a_hostile_value_in_a_pane_row_is_not_escaped_by_this_module():
    """Escaping is the browser's job (`esc()` in `server.py`'s page), not the
    composer's — this module hands back plain text exactly as the gate
    served it, which is what the browser then escapes on the way into HTML.
    Pinned here so a future change does not quietly start half-escaping."""
    store = Sidecar()
    hostile = "<script>alert(1)</script>"
    store.put(custody.MATTER, "custody_order_date", "primary", Classified(Rung.L1, hostile))
    pane = panes.pane_for(store, custody.MATTER, "primary", today=TODAY)
    timeline = {t["item_type"]: t["text"] for t in pane["timeline"]}
    assert timeline["custody_order_date"] == hostile


# ── pane_text — the tk view's own rendering ─────────────────────────────────

def test_pane_text_names_the_matter_instance_and_indicator():
    store = Sidecar()
    store.put(custody.MATTER, "registration_contest_deadline", "primary", Classified(Rung.L1, "2026-07-01"))
    pane = panes.pane_for(store, custody.MATTER, "primary", today=TODAY)
    text = panes.pane_text(pane)
    assert text.startswith("custody/primary")
    assert "[overdue]" in text
    assert "registration_contest_deadline: 2026-07-01" in text


def test_pane_text_covers_every_shape_without_raising():
    store = Sidecar()
    for mt in (custody.MATTER, bankruptcy.MATTER, workers_comp.MATTER, "an_unregistered_one"):
        text = panes.pane_text(panes.pane_for(store, mt, "primary", today=TODAY))
        assert mt in text
