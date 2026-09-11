"""L3-bankruptcy-ch13 — the second real pack, and the registry seam a second
time.

Field rungs and the `derived`/digit/why-names-a-step checks are already held
*registry-relative* by `tests/test_registry.py` for every registered pack —
they cover this one the day it is registered, with no edit there. This file
holds what is specific to bankruptcy: the exact rung table against the plan
paragraph, the `account_number` guard, the TEMPLATES shape check, and the
engine-pack `why` reuse the module docstring promises.
"""
from __future__ import annotations

import copy
import re

import pytest

from homestead.keep.rungs import Rung, classify_schema
from homestead_law.packs import bankruptcy


# ── the rung table, exactly per the plan paragraph ───────────────────────────

def test_bankruptcy_is_us_federal_only():
    assert bankruptcy.MATTER == "bankruptcy"
    assert bankruptcy.JURISDICTION == "US-federal"
    assert bankruptcy.JURISDICTIONS == ("US-federal",)


def test_the_l1_fields():
    l1 = {
        "jurisdiction", "district", "district_state", "courthouse", "chapter",
        "case_number",
        "trustee", "petition_date", "creditor_meeting_date", "plan_filed_date",
        "first_plan_payment_due", "claims_bar_date",
        "governmental_claims_bar_date", "confirmation_hearing_date",
        "objection_deadline", "plan_confirmation_date", "plan_length_months",
        "plan_payment_due_day", "plan_completion_date", "debtor_education_date",
        "discharge_date", "plan_modification",
        "creditor.secured", "creditor.claim_filed_date", "creditor.claim_number",
    }
    for field in l1:
        assert bankruptcy.FIELDS[field] is Rung.L1, field


def test_the_l3_fields():
    l3 = {
        "plan_payment_amount", "income", "assets",
        "creditor.name", "creditor.amount_scheduled", "creditor.claim_amount",
    }
    for field in l3:
        assert bankruptcy.FIELDS[field] is Rung.L3, field


def test_the_l2_l4_l5_fields():
    assert bankruptcy.FIELDS["attorney"] is Rung.L2
    assert bankruptcy.FIELDS["notes"] is Rung.L4
    assert bankruptcy.FIELDS["creditor.note"] is Rung.L4
    assert bankruptcy.FIELDS["ssn"] is Rung.L5


def test_ssn_is_l5_the_canonical_datum():
    assert bankruptcy.FIELDS["ssn"] is Rung.L5, "an SSN is L5 — L5 has no override"


# ── district_state — the second calendar a forward count reads ───────────────

def test_district_state_is_declared_at_l1_under_exactly_that_name():
    """FRBP 9006(a)(6)(C) adds the holidays of the state a federal district
    court sits in to a period measured *after* an event. The sibling
    `rules.py` bite reads that state off the **instance**
    (`rules._district_state_for`), and it reads it by two hard conditions:
    the field is named exactly `district_state`, and it is classified exactly
    `L1`. Both are this pack's side of that contract, so both are pinned
    here — a rename or a rung moved down would not break any test in the
    sibling's own file, it would silently stop applying the district's
    calendar and compute a claims-bar date on the federal one."""
    assert "district_state" in bankruptcy.FIELDS
    assert bankruptcy.FIELDS["district_state"] is Rung.L1


def test_district_state_declares_no_derived_form_and_names_step_one():
    """`L1` renders unconditionally, so it needs no stand-in (decision 3
    requires `derived` at L3/L4 only) — and the `why` has to say *why* this
    is public, not merely that a counting rule wants it, which is the one
    argument a rung may never be set by."""
    spec = bankruptcy.SCHEMA["district_state"]
    assert "derived" not in spec
    assert re.search(r"\bstep 1\b", spec["why"])
    assert "district" in spec["why"]


def test_l1_is_what_makes_the_district_state_readable_to_the_arithmetic():
    """Not an assertion about the number: the behaviour the rung buys.

    A counting rule reads this value through the gate on `S1_LIST`, like
    everything else in this package (`Served.value`, never `.payload`), and
    the sibling `rules._district_state_for` additionally requires the pack to
    have declared it **exactly** `L1` — a pack that files the code lower has
    said it is not public in this forum, and a counting rule may not reach
    past that. Both halves are shown here rather than asserted: `L1` renders
    the code itself on that door, while `L4` hands back a derived stand-in
    and `L5` is denied outright — so a district's state filed above `L3`
    would be *absent* to the arithmetic, not merely protected, and the count
    would quietly fall back to the federal calendar."""
    from homestead.keep.rungs import Classified, Disposition, Surface, serve

    rendered = serve(Classified(Rung.L1, "NM", None), Surface.S1_LIST)
    assert rendered.disposition is Disposition.RENDER
    assert rendered.value == "NM"

    withheld = serve(Classified(Rung.L4, "NM", "a state"), Surface.S1_LIST)
    assert withheld.disposition is not Disposition.RENDER
    assert withheld.value != "NM"

    denied = serve(Classified(Rung.L5, "NM", "a state"), Surface.S1_LIST)
    assert denied.disposition is not Disposition.RENDER


def test_district_state_is_entered_never_computed():
    """It is geography, not a deadline: no template anchors on it, and none
    could — an anchor is a date."""
    assert all(t["anchor"] != "district_state" for t in bankruptcy.TEMPLATES)


def test_every_forward_court_days_template_says_the_district_calendar_applies():
    """The three `court_days` rows are the ones whose answer moves when a
    district's state closes. Each `note` has to say so, because the row
    itself carries no `district_state` — the pack is general, the field is on
    the instance — and a reader of the table alone would otherwise take the
    computed date for the whole answer."""
    checked = 0
    for template in bankruptcy.TEMPLATES:
        if template["rule"] != "court_days":
            continue
        note = template["note"]
        assert "district_state" in note, template["name"]
        assert "9006(a)(6)(C)" in note, template["name"]
        assert "district holidays not applied" in note, template["name"]
        checked += 1
    assert checked == 3


def test_the_calendar_days_template_says_the_district_calendar_does_not_reach_it():
    """`first-plan-payment` counts calendar days, which read no calendar at
    all. Silence there would read as an oversight next to three rows that
    mention it; the note says it is the rule."""
    note = next(
        t["note"] for t in bankruptcy.TEMPLATES if t["name"] == "first-plan-payment"
    )
    assert "district_state" in note
    assert "does not reach this row" in note


def test_the_backward_template_claims_no_district_calendar():
    """9006(a)(6)(C) is forward-only — the engine's `court_days_before` takes
    no `district_state` parameter at all — so the backward row must not
    promise one."""
    note = next(t["note"] for t in bankruptcy.TEMPLATES if t["name"] == "objection")
    assert "district_state" not in note


def test_case_number_is_l1_here_and_l3_in_custody_the_worked_example():
    """Step 5's canonical contrast, held as a behavioural check rather than a
    promise in a docstring: the same field name, different rungs, in the two
    real packs now registered."""
    from homestead_law.packs import custody

    assert bankruptcy.FIELDS["case_number"] is Rung.L1
    assert custody.FIELDS["case_number"] is Rung.L3


# ── every field records matter, jurisdiction, and a step ────────────────────

def test_every_field_records_matter_and_jurisdiction():
    for name, spec in bankruptcy.SCHEMA.items():
        assert spec.get("matter") == "bankruptcy", name
        assert spec.get("jurisdiction") == "US-federal", name
        assert spec.get("why"), f"{name} declares a rung with no recorded reason"


def test_every_why_names_a_step():
    step = re.compile(r"\bstep \d\b")
    for field, spec in bankruptcy.SCHEMA.items():
        why = spec.get("why", "")
        assert step.search(why), f"{field}'s why never names a step: {why!r}"


def test_deleting_a_fields_rung_fails_the_build_naming_it():
    for victim in bankruptcy.SCHEMA:
        wounded = copy.deepcopy(bankruptcy.SCHEMA)
        del wounded[victim]["rung"]
        with pytest.raises(Exception) as caught:
            classify_schema(wounded)
        assert victim in str(caught.value)


# ── why reuse from the engine's own bankruptcy pack ──────────────────────────

def test_reused_why_strings_cite_the_engine_pack():
    """The module docstring promises several `why` strings are reused from
    the engine's own 13-field pack, cited inline. Held here as a check that
    the citation actually appears, not merely a claim in prose."""
    reused = {
        "courthouse", "case_number", "chapter", "trustee",
        "creditor_meeting_date", "attorney", "income", "assets", "notes",
        "ssn", "discharge_date",
    }
    for field in reused:
        why = bankruptcy.SCHEMA[field]["why"]
        assert "engine bankruptcy.py" in why, f"{field} does not cite the engine pack"


# ── account_number is refused as a field name ────────────────────────────────

def test_account_number_is_not_a_real_field():
    assert "account_number" not in bankruptcy.SCHEMA
    assert "account_number" not in bankruptcy.FIELDS


def test_the_account_number_guard_fires_on_a_planted_field():
    """A scan that has never fired has not been shown to check anything —
    planted in a copy of the real schema, never the real one."""
    planted = dict(bankruptcy.SCHEMA)
    planted["account_number"] = {
        "rung": Rung.L5, "matter": "bankruptcy", "jurisdiction": "US-federal",
        "why": "key material (step 4)",
    }
    with pytest.raises(ValueError) as exc:
        bankruptcy._refuse_account_number(planted)
    assert "account_number" in str(exc.value)


def test_the_account_number_guard_is_silent_on_the_real_schema():
    bankruptcy._refuse_account_number(bankruptcy.SCHEMA)  # must not raise


# ── REPEATABLE ────────────────────────────────────────────────────────────────

def test_repeatable_names_the_creditor_and_modification_fields():
    expected = {
        "creditor.name", "creditor.amount_scheduled", "creditor.claim_amount",
        "creditor.secured", "creditor.claim_filed_date", "creditor.claim_number",
        "creditor.note", "plan_modification",
    }
    assert bankruptcy.REPEATABLE == expected
    assert bankruptcy.REPEATABLE <= set(bankruptcy.FIELDS)


# ── NOTICE ────────────────────────────────────────────────────────────────────

def test_notice_drafts_nothing_files_nothing_names_no_chapter():
    assert bankruptcy.NOTICE == (
        "This pack keeps dates and references for a Chapter 13 case. It "
        "drafts nothing, files nothing, and does not say which chapter fits."
    )


# ── TEMPLATES — shape, per the plan paragraph exactly ────────────────────────

#: Keyed by template name for readability; the pack itself declares a
#: **tuple** of rows (the shape `rules.validate_templates` requires), so
#: `_by_name` below is what the tests index through.
EXPECTED_TEMPLATES = {
    "plan-filed": dict(anchor="petition_date", days=14, direction="forward",
                       rule="court_days", mail=False),
    "first-plan-payment": dict(anchor="petition_date", days=30,
                               direction="forward", rule="calendar_days",
                               mail=False),
    "claims-bar": dict(anchor="petition_date", days=70, direction="forward",
                       rule="court_days", mail=False),
    "governmental-claims-bar": dict(anchor="petition_date", days=180,
                                    direction="forward", rule="court_days",
                                    mail=False),
    "objection": dict(anchor="confirmation_hearing_date", days=7,
                      direction="backward", rule="court_days_before",
                      mail=False),
}


def _by_name() -> dict:
    return {row["name"]: row for row in bankruptcy.TEMPLATES}


def _row(_target: str = "plan-filed", **overrides) -> tuple:
    """The real table with the row named `_target` replaced by itself plus
    `overrides` — the shape every planted-failure test below feeds
    `_check_templates`. `_target` is positional-by-convention and leading-
    underscored so `name=` stays free as an override (a planted bad *name*
    is one of the cases)."""
    return tuple(
        {**row, **overrides} if row["name"] == _target else row
        for row in bankruptcy.TEMPLATES
    )


def _check(templates):
    bankruptcy._check_templates(
        bankruptcy.SCHEMA, bankruptcy.FIELDS, bankruptcy.JURISDICTIONS, templates
    )


def test_templates_are_a_tuple_not_a_dict():
    """`rules.templates_of` (L3-deadline-templates) iterates the table and
    builds one `Template(**row)` per element; handed a dict it iterates the
    *keys* and calls `Template(**"plan-filed")`. `validate_templates` catches
    that as a build failure at registry time — in a file this bite does not
    own — so the shape is pinned here, where it is authored. `custody.py` and
    `workers_comp.py` declare the same tuple."""
    assert isinstance(bankruptcy.TEMPLATES, tuple)
    for row in bankruptcy.TEMPLATES:
        assert isinstance(row, dict)


def test_a_dict_shaped_table_fails_the_build():
    with pytest.raises(ValueError) as exc:
        _check({row["name"]: row for row in bankruptcy.TEMPLATES})
    assert "tuple" in str(exc.value)


def test_every_template_name_is_a_usable_sub_id():
    """A template's name is stored as the sub half of
    `(matter, "deadline", "<instance>.<template>")`, so it must match the
    package's own id pattern — no underscore. Held against
    `instances.ID_PATTERN` itself, not a copy, so the pack's local
    `_NAME_PATTERN` cannot drift from the one that will actually validate the
    stored key."""
    from homestead_law import instances

    assert bankruptcy._NAME_PATTERN == instances.ID_PATTERN.pattern
    for row in bankruptcy.TEMPLATES:
        assert instances.ID_PATTERN.match(row["name"]), row["name"]


def test_an_underscored_template_name_fails_the_build():
    with pytest.raises(ValueError) as exc:
        _check(_row("plan-filed", name="plan_filed"))
    assert "plan_filed" in str(exc.value)


def test_templates_match_the_plan_paragraph_exactly():
    rows = _by_name()
    assert set(rows) == set(EXPECTED_TEMPLATES)
    for name, expected in EXPECTED_TEMPLATES.items():
        row = rows[name]
        for key, value in expected.items():
            assert row[key] == value, f"{name}.{key}"
        assert row["jurisdiction"] == "US-federal"
        assert row["status"] in ("VERIFIED", "UNCERTAIN")


def test_no_template_asks_for_mail_days_on_a_backward_period():
    """FRBP 9006(f)'s 3 days extend a period that runs *after service*, and
    they are added **forward**. On a period counted backward from the
    confirmation hearing there is nothing to add them to, and adding them
    anyway would name a date LATER than the 7-days-before cutoff the rule
    sets — a deadline wrong in the one direction a deadline may not be wrong
    in. The sibling `rules.compute` raises `MailUnsupported` for exactly this
    combination, so a `mail: True` here could never have been honoured; the
    refusal belongs in the data, where the operator's surface reads it."""
    for row in bankruptcy.TEMPLATES:
        if row["direction"] == "backward" or row["rule"] == "calendar_days":
            assert row["mail"] is False, row["name"]


def test_the_objection_template_says_why_it_refuses_mail_days():
    row = _by_name()["objection"]
    assert "9006(f)" in row["source"]
    assert "after service" in row["note"]
    assert "PROVENANCE" in row["source"]


def test_check_templates_fires_on_mail_days_asked_for_backward():
    with pytest.raises(ValueError) as exc:
        _check(_row("objection", mail=True))
    assert "9006(f)" in str(exc.value)


def test_check_templates_fires_on_a_direction_that_disagrees_with_its_rule():
    with pytest.raises(ValueError) as exc:
        _check(_row(direction="backward"))
    assert "disagree" in str(exc.value)


def test_the_first_plan_payment_note_carries_the_whichever_is_earlier_clause():
    """§ 1326(a)(1) runs from the order for relief *or* the plan filing,
    whichever is earlier. This template anchors on `petition_date` alone, so
    the other trigger is the operator's to enter — and the note has to say
    so, or a converted case computes a date the statute does not set."""
    note = _by_name()["first-plan-payment"]["note"]
    assert "EARLIER" in note or "earlier" in note
    assert "notice" in note


def test_every_template_anchor_is_an_l1_field_of_this_pack():
    for row in bankruptcy.TEMPLATES:
        assert row["anchor"] in bankruptcy.FIELDS, row["name"]
        assert bankruptcy.FIELDS[row["anchor"]] is Rung.L1, row["name"]


def test_every_template_carries_exactly_the_ten_keys():
    keys = {"name", "anchor", "days", "direction", "rule", "mail",
            "jurisdiction", "source", "status", "note"}
    for row in bankruptcy.TEMPLATES:
        assert set(row) == keys, row["name"]


def test_every_source_carries_a_dated_provenance_sentence():
    for row in bankruptcy.TEMPLATES:
        assert "PROVENANCE, 2026-09-1" in row["source"], row["name"]


def test_every_source_names_at_least_two_independent_restatements():
    """VERIFIED here is claimed on *converging* secondary sources, and one
    source does not converge with itself — the standard the dates-a audit
    set. Counted as distinct hostnames in the `source` sentence."""
    import re

    for row in bankruptcy.TEMPLATES:
        hosts = set(re.findall(r"\b(?:[a-z0-9-]+\.)+(?:gov|com|org)\b", row["source"]))
        assert len(hosts) >= 2, (row["name"], hosts)


def test_all_five_templates_are_verified():
    """Every template found converging, reachable secondary sources (WebSearch
    could not be blocked the way direct WebFetch to the primary hosts was —
    see the module's PROVENANCE note); none is UNCERTAIN. Pinned as its own
    check so a status silently downgraded later is caught."""
    for row in bankruptcy.TEMPLATES:
        assert row["status"] == "VERIFIED", row["name"]


# ── the local shape check fires on a planted bad template ───────────────────

def test_check_templates_fires_on_a_non_l1_anchor():
    with pytest.raises(ValueError) as exc:
        _check(_row(anchor="income"))  # a real field, but L3, not L1
    assert "income" in str(exc.value) and "L1" in str(exc.value)


def test_check_templates_fires_on_an_unknown_anchor():
    with pytest.raises(ValueError) as exc:
        _check(_row(anchor="not_a_field"))
    assert "not_a_field" in str(exc.value)


def test_check_templates_fires_on_a_missing_key():
    bad = tuple(
        {k: v for k, v in row.items() if k != "mail"} if row["name"] == "plan-filed"
        else row
        for row in bankruptcy.TEMPLATES
    )
    with pytest.raises(ValueError) as exc:
        _check(bad)
    assert "keys" in str(exc.value)


def test_check_templates_fires_on_a_bad_direction():
    with pytest.raises(ValueError) as exc:
        _check(_row(direction="sideways"))
    assert "sideways" in str(exc.value)


def test_check_templates_fires_on_a_bad_rule():
    with pytest.raises(ValueError) as exc:
        _check(_row(rule="guess_days"))
    assert "guess_days" in str(exc.value)


def test_check_templates_fires_on_a_jurisdiction_outside_the_tuple():
    with pytest.raises(ValueError) as exc:
        _check(_row(jurisdiction="US-NM"))
    assert "US-NM" in str(exc.value)


def test_check_templates_fires_on_a_bad_status():
    with pytest.raises(ValueError) as exc:
        _check(_row(status="MAYBE"))
    assert "MAYBE" in str(exc.value)


def test_check_templates_fires_on_a_duplicate_name():
    with pytest.raises(ValueError) as exc:
        _check(bankruptcy.TEMPLATES + (dict(bankruptcy.TEMPLATES[0]),))
    assert "more than once" in str(exc.value)


def test_check_templates_is_silent_on_the_real_table():
    _check(bankruptcy.TEMPLATES)  # must not raise
