"""`homestead_law.packs.grant` — a funder's application and award (L8-grant).

Field rungs and the generic `derived`/digit/why-names-a-step checks are
already held *registry-relative* by `tests/test_registry.py` for every
registered pack (they cover this one the day it is registered, with no edit
there). This file holds what is specific to grant: the closed `status` set,
`validate_value`'s two refusals, the empty `TEMPLATES` shape, the
`S1_DETAIL`-only rendering of `allowable_uses`, and the Chapter 13
plan-period flag wired against the real pack rather than a fake one.
"""
from __future__ import annotations

import re

import pytest

from homestead.keep.rungs import Classified, Disposition, Rung, Surface, serve
from homestead_law import instances, plan_period
from homestead_law import queue as queue_mod
from homestead_law.packs import grant
from homestead_law.registry import all_matters, matter
from homestead_law.store import Sidecar

MATTER = grant.MATTER  # "grant"
TODAY = "2026-09-11"


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    yield


# ── the pack classifies at import, and registers ─────────────────────────────

def test_the_pack_classifies_at_import():
    assert isinstance(grant.FIELDS, dict)
    assert grant.FIELDS
    assert all(isinstance(r, Rung) for r in grant.FIELDS.values())
    assert set(grant.FIELDS) == set(grant.SCHEMA)


def test_the_pack_is_registered():
    assert MATTER in all_matters()
    entry = matter(MATTER)
    assert entry.pack is grant
    assert entry.fields is grant.FIELDS
    assert entry.jurisdiction == "US-federal"
    assert entry.jurisdictions == ("US-federal",)


def test_grant_is_us_federal_placeholder_only():
    """A grant has no court; JURISDICTIONS is a placeholder for decision 1's
    contract, not a forum this pack ever counts a day under (TEMPLATES is
    empty — see the templates section below)."""
    assert grant.JURISDICTION == "US-federal"
    assert grant.JURISDICTIONS == ("US-federal",)


# ── the ladder, field by field ────────────────────────────────────────────────

EXPECTED = {
    "jurisdiction": Rung.L1,
    "backing_agreed_date": Rung.L1,
    "submission_deadline": Rung.L1,
    "submitted_date": Rung.L1,
    "decision_date": Rung.L1,
    "award_date": Rung.L1,
    "award_period_start": Rung.L1,
    "award_period_end": Rung.L1,
    "program": Rung.L2,
    "status": Rung.L2,
    "funder": Rung.L3,
    "backer": Rung.L3,
    "program_officer": Rung.L3,
    "amount_requested": Rung.L3,
    "award_amount": Rung.L3,
    "allowable_uses": Rung.L4,
    "restrictions": Rung.L4,
    "notes": Rung.L4,
    "milestone.name": Rung.L3,
    "milestone.due": Rung.L1,
    "milestone.done": Rung.L1,
    "report.period": Rung.L2,
    "report.due": Rung.L1,
    "report.submitted": Rung.L1,
    "report.kind": Rung.L2,
    "disbursement.expected": Rung.L1,
    "disbursement.amount": Rung.L3,
    "disbursement.received": Rung.L1,
    "disbursement.account_label": Rung.L2,
}


def test_the_pack_spans_exactly_this_ladder():
    assert set(grant.SCHEMA) == set(EXPECTED)
    for field, rung in EXPECTED.items():
        assert grant.FIELDS[field] is rung, field


def test_every_field_records_matter_and_jurisdiction_and_a_step():
    step = re.compile(r"\bstep \d\b")
    for name, spec in grant.SCHEMA.items():
        assert spec.get("matter") == "grant", name
        assert spec.get("jurisdiction") == "US-federal", name
        why = spec.get("why", "")
        assert why, f"{name} declares a rung with no recorded reason"
        assert step.search(why), f"{name}'s why never names a step: {why!r}"


def test_repeatable_names_exactly_the_dotted_sub_fields():
    assert grant.REPEATABLE == frozenset(
        {
            "milestone.name", "milestone.due", "milestone.done",
            "report.period", "report.due", "report.submitted", "report.kind",
            "disbursement.expected", "disbursement.amount",
            "disbursement.received", "disbursement.account_label",
        }
    )
    assert grant.REPEATABLE <= set(grant.FIELDS)


# ── derived forms: every L3/L4 field has one, digit-free, and names neither
#    a funder nor an amount ──────────────────────────────────────────────────

def test_every_l3_l4_field_declares_a_non_empty_derived_form():
    checked = 0
    for field, rung in grant.FIELDS.items():
        if rung in (Rung.L3, Rung.L4):
            sentence = grant.SCHEMA[field].get("derived")
            assert isinstance(sentence, str) and sentence.strip(), field
            checked += 1
    l3 = sum(1 for r in EXPECTED.values() if r is Rung.L3)
    l4 = sum(1 for r in EXPECTED.values() if r is Rung.L4)
    assert checked == l3 + l4


#: Words a derived form must never carry: any funder/backer/entity name (this
#: pack names none of its own, so the check is that the *sentence itself*
#: never grew one) and the shape of a dollar amount.
_MONEY_WORDS = ("$", "dollar", "usd")


def test_no_derived_form_carries_a_digit_a_funder_or_an_amount():
    for field, rung in grant.FIELDS.items():
        if rung not in (Rung.L3, Rung.L4):
            continue
        sentence = grant.SCHEMA[field]["derived"]
        assert not any(ch.isdigit() for ch in sentence), f"{field}: {sentence!r}"
        lowered = sentence.lower()
        for word in _MONEY_WORDS:
            assert word not in lowered, f"{field}: {sentence!r} carries {word!r}"
        # "A funder is named" (the field's own derived sentence) is the
        # sanctioned shape; what must never appear is an actual name, which
        # this test cannot see in a schema-level string that carries none —
        # held instead as "the sentence is the same for every instance of
        # the field" per field below.
    assert grant.SCHEMA["funder"]["derived"] == "A funder is named"
    assert grant.SCHEMA["backer"]["derived"] == "A backer is named"
    assert grant.SCHEMA["award_amount"]["derived"] == "An award amount is on file"
    assert grant.SCHEMA["amount_requested"]["derived"] == "An amount requested is on file"


# ── status: a closed set, and no I-44 word in it ─────────────────────────────

#: The exact words provisional I-44 (`tests/test_i44_no_drafting.py`) bans
#: from the tree — checked directly against the enum here rather than only
#: relying on the tree-wide scan, so this test fails on its own if the enum
#: ever grows the operator's own word for "not yet submitted".
_I44_WORDS = ("drafting", "draft", "filing", "file")


def test_status_values_is_the_closed_set_from_the_plan():
    assert grant.STATUS_VALUES == frozenset(
        {"preparing", "submitted", "under-review", "awarded", "declined",
         "active", "closed"}
    )


def test_status_enum_contains_no_i44_word():
    for value in grant.STATUS_VALUES:
        lowered = value.lower()
        for word in _I44_WORDS:
            assert word not in lowered, f"{value!r} carries the banned word {word!r}"


def test_validate_value_accepts_every_declared_status():
    for value in grant.STATUS_VALUES:
        grant.validate_value("status", value)  # does not raise


def test_validate_value_refuses_a_status_outside_the_set_and_never_echoes_it():
    bogus = "drafting"  # the plan's own word for the state — not in the set
    with pytest.raises(grant.InvalidStatus) as exc:
        grant.validate_value("status", bogus)
    message = str(exc.value)
    assert bogus not in message
    assert "status" in message


def test_validate_value_ignores_every_other_field():
    for field in grant.FIELDS:
        if field in ("status", "disbursement.account_label"):
            continue
        grant.validate_value(field, "anything at all")  # never raises


# ── disbursement.account_label — a label, never a number ────────────────────

def test_validate_value_accepts_a_well_shaped_label():
    grant.validate_value("disbursement.account_label", "visa-chase")


def test_validate_value_refuses_an_all_digit_label_and_never_echoes_it():
    bogus = "4242424242"
    with pytest.raises(grant.InvalidAccountLabel) as exc:
        grant.validate_value("disbursement.account_label", bogus)
    message = str(exc.value)
    assert bogus not in message
    assert "account_label" in message


def test_validate_value_refuses_a_label_off_the_alphabet():
    for bogus in ("Visa-Chase", "has_underscore", "", "-leading-hyphen"):
        with pytest.raises(grant.InvalidAccountLabel):
            grant.validate_value("disbursement.account_label", bogus)


# ── allowable_uses renders on S1_DETAIL only ─────────────────────────────────

def test_allowable_uses_derives_on_s1_list_and_renders_on_s1_detail():
    record = Classified(
        Rung.L4, "materials and contractor stipends only",
        grant.SCHEMA["allowable_uses"]["derived"],
    )
    on_list = serve(record, Surface.S1_LIST)
    assert on_list.disposition is Disposition.DERIVE
    assert on_list.value == "Allowable uses are on file"

    on_detail = serve(record, Surface.S1_DETAIL)
    assert on_detail.disposition is Disposition.RENDER
    assert on_detail.value == "materials and contractor stipends only"


# ── TEMPLATES is empty, and a compute refuses by name ────────────────────────

def test_templates_is_the_empty_tuple():
    assert grant.TEMPLATES == ()


def test_rules_templates_of_returns_the_empty_tuple():
    from homestead_law import rules

    assert rules.templates_of(matter(MATTER)) == ()


def test_deadline_compute_refuses_by_name_no_templates_declared():
    """A grant has no court and no procedural code to count a period under
    (the module docstring); `compute()` checks the template name against the
    pack before it ever opens the store, so this refuses on the pack alone —
    no instance needs to exist first."""
    from homestead_law import rules

    with pytest.raises(rules.TemplateNotFound) as exc:
        rules.compute(Sidecar(), MATTER, "primary", "anything")
    assert "grant" in str(exc.value)
    assert "no template named" in str(exc.value)
    assert "[]" in str(exc.value)  # nothing declared


# ── the queue: award_amount never appears; a filed deadline does, by ref ────

def test_award_amount_never_appears_as_a_queue_row():
    """`store.deadlines()` — what `queue()` reads — is keyed on the literal
    item type `"deadline"`; `award_amount` is filed under its own item type
    and can never be mistaken for one, but this pins the outcome behaviourally
    rather than only by construction."""
    store = Sidecar()
    store.put(MATTER, "award_amount", "primary", Classified(Rung.L3, "285000", "An award amount is on file"))

    items = queue_mod.queue(store, today=TODAY)
    assert not any(item.matter == MATTER for item in items)


def test_a_filed_deadline_surfaces_in_the_queue_by_reference():
    """`report.due`/`milestone.due`/`submission_deadline` are schema facts on
    file; tracking one on the operational queue is the same generic
    `(matter, "deadline", "<instance>.<label>")` lane every other pack uses
    (`cli._cmd_deadline`), addressed by an instance-shaped id
    (`primary.q3-2027`) — no grant-specific queue code is needed because
    `queue.queue()` already iterates `all_matters()` (I-23, BUG-6's fix)."""
    store = Sidecar()
    item_id = instances.item_id("primary", "q3-2027")
    store.put(MATTER, "deadline", item_id, Classified(Rung.L1, "2027-09-30", None))

    items = queue_mod.queue(store, today=TODAY)
    matching = [it for it in items if it.matter == MATTER]
    assert len(matching) == 1
    assert matching[0].instance == "primary"
    assert matching[0].ref == (MATTER, "deadline", item_id)


# ── the Chapter 13 plan-period flag, against the real producer ──────────────

EXPECTED_LINE = (
    "bankruptcy/primary: income or assets arising during the plan: confirm "
    "with your attorney (11 U.S.C. §§ 541(a)(7), 1306(a), 1329; disclosure "
    "duties under the plan and local rules)"
)


def _confirmed_bankruptcy(store: Sidecar, instance: str = "primary") -> None:
    store.put("bankruptcy", "plan_confirmation_date", instance, Classified(Rung.L1, "2026-06-01"))


def test_award_amount_flags_a_confirmed_undischarged_bankruptcy():
    store = Sidecar()
    _confirmed_bankruptcy(store)
    store.put(MATTER, "award_amount", "primary", Classified(Rung.L3, "285000", "An award amount is on file"))

    assert plan_period.flag(store) == (EXPECTED_LINE,)
    assert queue_mod.notices(store) == (EXPECTED_LINE,)


def test_award_amount_flags_nothing_without_a_bankruptcy_instance():
    store = Sidecar()
    store.put(MATTER, "award_amount", "primary", Classified(Rung.L3, "285000", "An award amount is on file"))

    assert plan_period.flag(store) == ()
    assert queue_mod.notices(store) == ()


def test_disbursement_amount_flags_a_confirmed_undischarged_bankruptcy():
    store = Sidecar()
    _confirmed_bankruptcy(store)
    sub = instances.item_id("primary", "tranche-1")
    store.put(MATTER, "disbursement.amount", sub, Classified(Rung.L3, "50000", "A disbursement amount is on file"))

    assert plan_period.flag(store) == (EXPECTED_LINE,)


def test_disbursement_received_alone_flags_a_confirmed_undischarged_bankruptcy():
    """`disbursement.received` carries the signal on its own — a tranche can
    mark an asset having arrived on a grant record silent about the amount."""
    store = Sidecar()
    _confirmed_bankruptcy(store)
    sub = instances.item_id("primary", "tranche-1")
    store.put(MATTER, "disbursement.received", sub, Classified(Rung.L1, "2026-07-01"))

    assert plan_period.flag(store) == (EXPECTED_LINE,)


def test_disbursement_expected_and_account_label_alone_flag_nothing():
    """The two scheduling/reference sub-fields are deliberately not in
    `SIGNAL_FIELDS` — neither is itself new income or an asset."""
    store = Sidecar()
    _confirmed_bankruptcy(store)
    sub = instances.item_id("primary", "tranche-1")
    store.put(MATTER, "disbursement.expected", sub, Classified(Rung.L1, "2026-07-01"))
    store.put(MATTER, "disbursement.account_label", sub, Classified(Rung.L2, "visa-chase"))

    assert plan_period.flag(store) == ()


def test_the_flag_line_carries_no_funder_name_and_no_amount():
    store = Sidecar()
    _confirmed_bankruptcy(store)
    store.put(MATTER, "funder", "primary", Classified(Rung.L3, "Example Foundation", "A funder is named"))
    store.put(MATTER, "award_amount", "primary", Classified(Rung.L3, "285000", "An award amount is on file"))

    (line,) = plan_period.flag(store)
    assert "Example Foundation" not in line
    assert "285000" not in line
    citation = "11 U.S.C. §§ 541(a)(7), 1306(a), 1329"
    assert citation in line
    assert not any(ch.isdigit() for ch in line.replace(citation, ""))


# ── --smoke / --demo still pass with the pack present ────────────────────────

def test_demo_panes_compose_for_every_registered_matter_including_grant():
    """`app.demo.compose_panes` iterates `all_matters()` and falls back to
    `panes.generic_pane` for any matter with no dedicated composer
    (`app/panes.py`'s own contract — L8-surfaces is the bite that gives grant
    one) — this pins that grant, with no records at all, composes cleanly
    rather than raising."""
    from homestead_law.app import panes

    store = Sidecar()
    pane = panes.pane_for(store, MATTER, "primary", today=TODAY)
    assert pane["matter"] == MATTER
    assert pane["rows"] == []
    panes.pane_text(pane)  # does not raise


def test_main_smoke_and_demo_still_run_with_grant_registered():
    from homestead_law import __main__ as entry

    assert entry.main(["--smoke"]) == 0
    assert entry.main(["--demo"]) == 0
