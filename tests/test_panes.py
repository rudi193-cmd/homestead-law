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
from homestead_law.packs import grant as grant_pack
from homestead_law.packs import venture as venture_pack
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
    assert set(panes.PANES) == {
        custody.MATTER, bankruptcy.MATTER, workers_comp.MATTER,
        grant_pack.MATTER, venture_pack.MATTER,
    }


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


# ── the rung ruling (audit, 2026-09-11) ─────────────────────────────────────
#
# **A pane is a list surface, not a detail one.** The pane composes *many*
# records for one instance, so it serves on `S1_LIST` (ceiling L3): L1–L3
# render, L4 shows its derived form, L5 leaves no row. `S1_DETAIL` is where
# an L4 payload renders, and the engine offers exactly one way to reach it —
# `Window.open_detail(ref)`, **one record, named by its reference**, because
# the act of opening that record *is* the purpose declaration (by widget).
# Serving a whole instance at `S1_DETAIL` would turn a tab switch into a bulk
# reveal of every L4 in the matter, under a default instance nobody chose;
# the pane's rows carry refs instead, and the page opens one at a time.
#
# So: child names, dates of birth and the workers' comp timeline are *derived*
# here and rendered on the detail the operator opens from a pane row.

def test_the_pane_never_carries_an_l4_payload_only_its_derived_form():
    """The ruling, pinned. Every L4 field the three panes read shows the
    pack's own derived sentence; not one of the planted payloads appears
    anywhere in the composed pane."""
    import json

    store = Sidecar()
    planted = {
        (custody.MATTER, "child.name", instances.item_id("primary", "c1"),
         custody.SCHEMA["child.name"]["derived"]): "Alex Rivera",
        (custody.MATTER, "child.dob", instances.item_id("primary", "c1"),
         custody.SCHEMA["child.dob"]["derived"]): "2018-04-01",
        (workers_comp.MATTER, "diagnosis", "primary",
         workers_comp.SCHEMA["diagnosis"]["derived"]): "L5-S1 disc herniation",
        (workers_comp.MATTER, "hcp_selection_date", "primary",
         workers_comp.SCHEMA["hcp_selection_date"]["derived"]): "2026-02-01",
    }
    for (mt, field, item, derived), payload in planted.items():
        store.put(mt, field, item, Classified(Rung.L4, payload, derived))

    for mt in (custody.MATTER, workers_comp.MATTER):
        pane = panes.pane_for(store, mt, "primary", today=TODAY)
        blob = json.dumps(pane) + "\n" + panes.pane_text(pane)
        for payload in planted.values():
            assert payload not in blob, f"{mt}: an L4 payload reached the pane"


def test_the_same_record_renders_its_payload_on_the_detail_the_row_opens():
    """The other half of the ruling — the L4 is not *lost*, it is one
    explicit open away. A pane row carries the record's ref; handing that ref
    to `Window.open_detail` (what clicking the row does, through
    `/api/record`) renders the payload the pane withheld."""
    from homestead_law.app.window import Window

    store = Sidecar()
    ref = (custody.MATTER, "child.name", instances.item_id("primary", "c1"))
    store.put(*ref, Classified(Rung.L4, "Alex Rivera",
                               custody.SCHEMA["child.name"]["derived"]))

    pane = panes.pane_for(store, custody.MATTER, "primary", today=TODAY)
    row = pane["children"][0]["fields"]["child.name"]
    assert row["text"] == "A child's name is on file"
    assert (row["matter"], row["item_type"], row["item_id"]) == ref

    window = Window()
    window.open_list(instances.records_of(store, custody.MATTER, "primary"))
    assert window.open_detail(ref).value == "Alex Rivera"


# ── L5 leaves no trace on any pane surface ──────────────────────────────────

def test_an_l5_record_never_reaches_the_pane_the_text_or_the_demo():
    """A planted `ssn` (the bankruptcy pack's one L5 field) must be absent
    from the composed pane, from `pane_text`, and from the demo's own pane
    section — L5 has no override anywhere (I-13) and leaves no row, not even
    a placeholder saying something was withheld (product decision 2)."""
    import json

    from homestead_law.app import demo

    store = Sidecar()
    # Named `planted_l5`, not `ssn` (X7-drift audit, 2026-09-11): CodeQL's
    # sensitive-data heuristic keys on variable names, and a local literally
    # called `ssn` taints every element of any list it rides in and flags the
    # first print downstream as clear-text logging. The field name stored
    # under (`"ssn"`, the string key) is unrelated and stays as-is — that is
    # the real field this pack declares, and the assertions below check it by
    # name deliberately.
    planted_l5 = "123-45-6789"
    store.put(bankruptcy.MATTER, "ssn", "primary", Classified(Rung.L5, planted_l5))
    store.put(bankruptcy.MATTER, "claims_bar_date", "primary",
              Classified(Rung.L1, "2026-09-01"))

    pane = panes.pane_for(store, bankruptcy.MATTER, "primary", today=TODAY)
    blob = json.dumps(pane)
    assert planted_l5 not in blob and "ssn" not in blob
    text = panes.pane_text(pane)
    assert planted_l5 not in text and "ssn" not in text
    # the row that *is* readable still renders, so this is not a pane that
    # simply failed to compose
    assert any(b["field"] == "claims_bar_date" for b in pane["bar_dates"])

    assert planted_l5 not in demo.compose_panes(store, today=TODAY)


def test_the_generic_pane_drops_an_l5_too():
    """The fallback composer has no field list of its own — it renders every
    row the gate hands it — so the L5 drop there is the gate's, not a filter
    this module keeps. Planted under a matter with no composer at all."""
    store = Sidecar()
    store.put("an_unregistered_matter", "secret", "primary",
              Classified(Rung.L5, "123-45-6789"))
    store.put("an_unregistered_matter", "note", "primary",
              Classified(Rung.L4, "x", "A note is on file"))

    pane = panes.pane_for(store, "an_unregistered_matter", "primary", today=TODAY)
    assert [r["item_type"] for r in pane["rows"]] == ["note"]
    assert "123-45-6789" not in panes.pane_text(pane)


def test_the_demo_composes_a_pane_for_every_registered_matter(monkeypatch):
    """I-23 one level down (audit, 2026-09-11): `demo.compose_panes` used to
    iterate the three packs it happens to seed — a hand-kept list of module
    objects rather than of strings, invisible to `test_registry.py`'s scan
    because that one reads constants. It now iterates `all_matters()`, so a
    fourth registered pack appears through the generic fallback with no edit
    to `demo.py`. Planted: a fake pack in the registry must show up.
    """
    from homestead_law.app import demo

    fake = _signal_pack("_fake_demo_pane")
    monkeypatch.setitem(registry_mod.REGISTRY, fake.MATTER, registry_mod._entry(fake))

    text = demo.compose_panes(Sidecar(), today=TODAY)
    for name in registry_mod.all_matters():
        assert f"{name}/primary" in text, f"{name} composes no pane in the demo"
    assert f"{fake.MATTER}/primary" in text


# ── the composer contract: a Row in, plain data out (L8-surfaces audit) ──────
#
# The L4 audit's ruling, now a guard: a composer consumes `Row.text`,
# `Row.ref` and `Row.rung` and nothing else a pack declares about a record.
# L8-surfaces shipped one bypass — `venture_pane` appended `public_benefit`
# to its company card with `venture.SCHEMA["public_benefit"]["derived"]` read
# straight off the pack, so one `L3` field rendered as its derived sentence
# on a surface whose ceiling is `L3` and whose every other `L3` field (
# `bankruptcy.creditor.name`, `grant.milestone.name`) renders in full. Two
# things were wrong with it and only one is about leakage: the composer was
# re-deciding a rung the pack had already decided, in one surface, with no
# `why` beside it and no other surface following. The ruling is that a rung
# is changed in the pack (where the rung, its `why` and its derived form live
# together) or not at all; the scan below makes the shortcut a build failure.


def _pack_attribute_reads(source: str) -> list[str]:
    """Every place `source` reaches into a pack's declaration tables rather
    than reading the `Row` the gate handed it: an attribute named `SCHEMA`
    or `FIELDS`, a `derived_of(...)` call, or a subscript by the literal
    `"derived"`. `MATTER` and `NOTICE` are deliberately *not* in the list —
    `MATTER` is the registry key `PANES` is built from (I-23) and `NOTICE`
    is a fixed sentence about the pack, not a classification of any
    record."""
    import ast

    banned_attrs = {"SCHEMA", "FIELDS", "REPEATABLE", "TEMPLATES"}
    hits = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Attribute) and node.attr in banned_attrs:
            hits.append(f"{node.lineno}: reads pack.{node.attr}")
        elif isinstance(node, ast.Name) and node.id == "derived_of":
            hits.append(f"{node.lineno}: calls derived_of")
        elif (
            isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and node.slice.value == "derived"
        ):
            hits.append(f'{node.lineno}: subscripts ["derived"]')
    return sorted(hits)


def _panes_source() -> str:
    from pathlib import Path

    return Path(panes.__file__).read_text("utf-8")


def test_no_composer_reads_a_pack_schema_or_a_derived_string():
    """Every composer in `app/panes.py` renders what the gate served it. No
    `SCHEMA`/`FIELDS` read, no `derived_of` call, no `["derived"]`
    subscript — a pack's own classification reaches a pane only by having
    been applied when the record was served."""
    assert _pack_attribute_reads(_panes_source()) == [], (
        "a pane composer reaches past the gate into a pack's declaration "
        "tables. A composer consumes Row.text/.ref/.rung; if a field's rung "
        "is wrong for a list surface, change the rung in the pack, not the "
        "rendering in one composer."
    )


@pytest.mark.parametrize(
    "bypass",
    [
        # the exact line L8-surfaces shipped, put back
        '            "text": venture.SCHEMA["public_benefit"]["derived"],',
        # the same shortcut spelled through the engine's own helper
        '            "text": derived_of(venture.SCHEMA, "public_benefit"),',
        # and through the rung table rather than the derived one
        '            "rung": venture.FIELDS["public_benefit"].value,',
    ],
)
def test_the_composer_contract_scan_fires_on_each_planted_bypass(bypass):
    """A scan that has never fired has not been shown to check anything.
    Each plant is grafted into the real module's source at the exact place
    the shipped bypass sat — inside `venture_pane`'s company card — and the
    real scan must report it."""
    source = _panes_source()
    assert _pack_attribute_reads(source) == []

    anchor = "    company = [_row_dict(plain[f]) for f in _VENTURE_COMPANY_FIELDS if f in plain]"
    assert anchor in source, "the plant's anchor moved; update this test"
    planted = source.replace(
        anchor,
        anchor + "\n    company.append({\n" + bypass + "\n    })",
        1,
    )
    assert planted != source, "the plant did not graft"
    assert _pack_attribute_reads(planted), f"the scan missed {bypass!r}"


def test_public_benefit_renders_like_every_other_l3_field_on_the_pane():
    """The ruling that replaced the bypass. `public_benefit` is `L3`
    (`tests/test_venture.py::test_the_public_benefit_derived_form_is_the_
    fixed_sentence` pins the rung and the sentence), `S1_LIST`'s ceiling is
    `L3`, and so the pane renders the payload — exactly as it renders
    `bankruptcy.creditor.name`, also `L3`, in the test above. The derived
    sentence is what `S2`/`S3` get, and the gate is what decides that."""
    store = Sidecar()
    store.put(
        venture_pack.MATTER, "public_benefit", "primary",
        Classified(Rung.L3, "PLANTEDPURPOSE",
                   venture_pack.SCHEMA["public_benefit"]["derived"]),
    )
    pane = panes.pane_for(store, venture_pack.MATTER, "primary", today=TODAY)
    company = {c["item_type"]: c for c in pane["company"]}
    assert company["public_benefit"]["text"] == "PLANTEDPURPOSE"
    assert company["public_benefit"]["rung"] == "L3"
    assert venture_pack.SCHEMA["public_benefit"]["derived"] not in panes.pane_text(pane)


# ── the renamed keys are cosmetic, not a way around the I-33 key scan ────────

@pytest.mark.parametrize(
    "pack,field,key",
    [
        (grant_pack, "status", "state"),
        (venture_pack, "application_status", "application_state"),
    ],
)
def test_a_renamed_pane_key_still_carries_the_packs_own_field(pack, field, key):
    """`tests/test_i33_one_indicator.py`'s key scan calls any key containing
    `status` indicator-shaped, and its rule is that exactly one key per pane
    may look like one. These two composers rename theirs rather than spend
    that one on a field that is not a badge — so the rename must be proven
    cosmetic: the value under the new key is the served row for the real
    field, item type and all, and `pane_text` labels it by that real
    name."""
    store = Sidecar()
    store.put(pack.MATTER, field, "primary", Classified(pack.FIELDS[field], "submitted"))
    pane = panes.pane_for(store, pack.MATTER, "primary", today=TODAY)

    assert field not in pane, f"{field} is both renamed and kept"
    assert pane[key]["item_type"] == field
    assert pane[key]["item_id"] == "primary"
    assert pane[key]["text"] == "submitted"
    assert f"{field}: submitted" in panes.pane_text(pane)
