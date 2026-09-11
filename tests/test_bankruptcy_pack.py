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
        "jurisdiction", "district", "courthouse", "chapter", "case_number",
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

EXPECTED_TEMPLATES = {
    "plan_filed": dict(anchor="petition_date", days=14, direction="forward",
                        rule="court_days", mail=False),
    "first_plan_payment": dict(anchor="petition_date", days=30,
                                direction="forward", rule="calendar_days",
                                mail=False),
    "claims_bar": dict(anchor="petition_date", days=70, direction="forward",
                        rule="court_days", mail=False),
    "governmental_claims_bar": dict(anchor="petition_date", days=180,
                                     direction="forward", rule="court_days",
                                     mail=False),
    "objection": dict(anchor="confirmation_hearing_date", days=7,
                       direction="backward", rule="court_days_before",
                       mail=True),
}


def test_templates_match_the_plan_paragraph_exactly():
    assert set(bankruptcy.TEMPLATES) == set(EXPECTED_TEMPLATES)
    for name, expected in EXPECTED_TEMPLATES.items():
        row = bankruptcy.TEMPLATES[name]
        assert row["name"] == name
        for key, value in expected.items():
            assert row[key] == value, f"{name}.{key}"
        assert row["jurisdiction"] == "US-federal"
        assert row["status"] in ("VERIFIED", "UNCERTAIN")


def test_every_template_anchor_is_an_l1_field_of_this_pack():
    for name, row in bankruptcy.TEMPLATES.items():
        assert row["anchor"] in bankruptcy.FIELDS, name
        assert bankruptcy.FIELDS[row["anchor"]] is Rung.L1, name


def test_every_template_carries_exactly_the_ten_keys():
    keys = {"name", "anchor", "days", "direction", "rule", "mail",
            "jurisdiction", "source", "status", "note"}
    for name, row in bankruptcy.TEMPLATES.items():
        assert set(row) == keys, name


def test_every_source_carries_a_dated_provenance_sentence():
    for name, row in bankruptcy.TEMPLATES.items():
        assert "PROVENANCE, 2026-09-11" in row["source"], name


def test_all_five_templates_are_verified():
    """Every template found converging, reachable secondary sources (WebSearch
    could not be blocked the way direct WebFetch to the primary hosts was —
    see the module's PROVENANCE note); none is UNCERTAIN. Pinned as its own
    check so a status silently downgraded later is caught."""
    for name, row in bankruptcy.TEMPLATES.items():
        assert row["status"] == "VERIFIED", name


# ── the local shape check fires on a planted bad template ───────────────────

def test_check_templates_fires_on_a_non_l1_anchor():
    bad = {
        "plan_filed": {
            **bankruptcy.TEMPLATES["plan_filed"],
            "anchor": "income",  # a real field, but L3, not L1
        }
    }
    with pytest.raises(ValueError) as exc:
        bankruptcy._check_templates(
            bankruptcy.SCHEMA, bankruptcy.FIELDS, bankruptcy.JURISDICTIONS, bad
        )
    assert "income" in str(exc.value) and "L1" in str(exc.value)


def test_check_templates_fires_on_an_unknown_anchor():
    bad = {
        "plan_filed": {**bankruptcy.TEMPLATES["plan_filed"], "anchor": "not_a_field"}
    }
    with pytest.raises(ValueError) as exc:
        bankruptcy._check_templates(
            bankruptcy.SCHEMA, bankruptcy.FIELDS, bankruptcy.JURISDICTIONS, bad
        )
    assert "not_a_field" in str(exc.value)


def test_check_templates_fires_on_a_missing_key():
    bad = {"plan_filed": {k: v for k, v in bankruptcy.TEMPLATES["plan_filed"].items() if k != "mail"}}
    with pytest.raises(ValueError) as exc:
        bankruptcy._check_templates(
            bankruptcy.SCHEMA, bankruptcy.FIELDS, bankruptcy.JURISDICTIONS, bad
        )
    assert "keys" in str(exc.value)


def test_check_templates_fires_on_a_bad_direction():
    bad = {"plan_filed": {**bankruptcy.TEMPLATES["plan_filed"], "direction": "sideways"}}
    with pytest.raises(ValueError) as exc:
        bankruptcy._check_templates(
            bankruptcy.SCHEMA, bankruptcy.FIELDS, bankruptcy.JURISDICTIONS, bad
        )
    assert "sideways" in str(exc.value)


def test_check_templates_fires_on_a_bad_rule():
    bad = {"plan_filed": {**bankruptcy.TEMPLATES["plan_filed"], "rule": "guess_days"}}
    with pytest.raises(ValueError) as exc:
        bankruptcy._check_templates(
            bankruptcy.SCHEMA, bankruptcy.FIELDS, bankruptcy.JURISDICTIONS, bad
        )
    assert "guess_days" in str(exc.value)


def test_check_templates_fires_on_a_jurisdiction_outside_the_tuple():
    bad = {"plan_filed": {**bankruptcy.TEMPLATES["plan_filed"], "jurisdiction": "US-NM"}}
    with pytest.raises(ValueError) as exc:
        bankruptcy._check_templates(
            bankruptcy.SCHEMA, bankruptcy.FIELDS, bankruptcy.JURISDICTIONS, bad
        )
    assert "US-NM" in str(exc.value)


def test_check_templates_fires_on_a_bad_status():
    bad = {"plan_filed": {**bankruptcy.TEMPLATES["plan_filed"], "status": "MAYBE"}}
    with pytest.raises(ValueError) as exc:
        bankruptcy._check_templates(
            bankruptcy.SCHEMA, bankruptcy.FIELDS, bankruptcy.JURISDICTIONS, bad
        )
    assert "MAYBE" in str(exc.value)


def test_check_templates_is_silent_on_the_real_table():
    bankruptcy._check_templates(
        bankruptcy.SCHEMA, bankruptcy.FIELDS, bankruptcy.JURISDICTIONS,
        bankruptcy.TEMPLATES,
    )  # must not raise
