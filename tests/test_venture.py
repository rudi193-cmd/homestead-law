"""L8-venture — the application and the company's calendar, one federal clock.

Field rungs, the `derived`/digit/no-second-derived-table checks, and the
registration guards are already held *registry-relative* by
`tests/test_registry.py` for every registered pack — they cover this one the
day it is registered, with no edit there. This file holds what is specific to
venture: the exact rung table against the plan paragraph, the two closed-set/
label `validate_value` checks, the `election-83b` template end to end, `ein`'s
absence from every surface, and name/investor-free derived forms.
"""
from __future__ import annotations

import re

import pytest

from homestead.keep.rungs import Classified, Disposition, Rung, Surface, serve
from homestead_law import jurisdiction as jurisdiction_mod
from homestead_law import rules
from homestead_law.packs import venture
from homestead_law.store import Sidecar


# ── the rung table, against the plan paragraph ───────────────────────────────

def test_venture_is_delaware_and_oregon():
    assert venture.MATTER == "venture"
    assert venture.JURISDICTION == "US-DE"
    assert venture.JURISDICTIONS == ("US-DE", "US-OR")


def test_us_de_is_absent_from_the_engines_rules_us_or_is_not():
    """The plan's own premise, checked against the engine actually installed:
    `US-DE` is genuinely absent (I-42 would refuse a court_days/business_days
    template against it); `US-OR` is not — E1-dates-b added it for custody's
    own relocation. This pack declares no template that reaches either
    through `RULES` (see the module docstring's correction)."""
    from homestead.keep import dates

    assert "US-DE" not in dates.RULES
    assert "US-OR" in dates.RULES


def test_the_application_fields():
    for field in ("application_submitted", "interview_date", "decision_date"):
        assert venture.FIELDS[field] is Rung.L1, field
    for field in ("accelerator", "batch", "application_status"):
        assert venture.FIELDS[field] is Rung.L2, field


def test_the_company_fields():
    l1 = {
        "benefit_report_due", "formation_date", "grant_date",
        "foreign_qualification_date", "annual_report_due", "franchise_tax_due",
        "business_license_due", "revenue_start",
    }
    for field in l1:
        assert venture.FIELDS[field] is Rung.L1, field
    l2 = {"entity_type", "formation_state", "principal_office_state", "bank_account_label"}
    for field in l2:
        assert venture.FIELDS[field] is Rung.L2, field
    for field in ("legal_name", "public_benefit", "registered_agent"):
        assert venture.FIELDS[field] is Rung.L3, field
    assert venture.FIELDS["notes"] is Rung.L4
    assert venture.FIELDS["ein"] is Rung.L5


def test_the_repeatable_groups():
    expected = {
        "founder.name": Rung.L4, "founder.role": Rung.L2,
        "founder.equity_pct": Rung.L4, "founder.vesting_start": Rung.L1,
        "founder.cliff_months": Rung.L2, "founder.election_83b_deadline": Rung.L1,
        "safe.investor": Rung.L4, "safe.amount": Rung.L4,
        "safe.valuation_cap": Rung.L4, "safe.discount": Rung.L4,
        "safe.signed": Rung.L1, "safe.post_money": Rung.L2,
        "equity_grant.grantee": Rung.L4, "equity_grant.amount": Rung.L4,
        "equity_grant.granted": Rung.L1,
        "registration.kind": Rung.L2, "registration.due": Rung.L1,
        "registration.done": Rung.L1,
        "advisor.name": Rung.L3, "advisor.role": Rung.L2,
    }
    for field, rung in expected.items():
        assert venture.FIELDS[field] is rung, field
    assert venture.REPEATABLE == frozenset(expected)


def test_notice_names_what_this_pack_never_does():
    assert venture.NOTICE == (
        "This pack keeps dates and references; it forms nothing, files "
        "nothing, and computes no tax."
    )


# ── closed sets and the label shape (validate_value) ─────────────────────────

def test_closed_sets_match_the_plan_and_refuse_an_outsider():
    cases = {
        "application_status": (
            venture.APPLICATION_STATUSES,
            {"preparing", "submitted", "interview", "accepted", "declined", "deferred"},
            "drafting",
        ),
        "entity_type": (venture.ENTITY_TYPES, {"pbc", "c-corp", "llc", "not-formed"}, "s-corp"),
        "registration.kind": (
            venture.REGISTRATION_KINDS,
            {"state-tax", "city-license", "dba", "foreign-qualification"},
            "trademark",
        ),
    }
    for field, (actual, expected, bad) in cases.items():
        assert actual == frozenset(expected), field
        for good in actual:
            venture.validate_value(field, good)
        with pytest.raises(venture.InvalidChoice):
            venture.validate_value(field, bad)
    # decision 8's own word choice: no application status reads as an act
    # this app does.
    assert not venture.APPLICATION_STATUSES & {"drafting", "filing", "filed"}


def test_bank_account_label_shape():
    venture.validate_value("bank_account_label", "venture-ops")
    for bad in ("Bad Label", "UPPER", "has_underscore", "-leading-hyphen", "", "a" * 41):
        with pytest.raises(venture.InvalidLabel):
            venture.validate_value("bank_account_label", bad)
    venture.validate_value("legal_name", "anything at all")  # not a checked field


def test_the_label_pattern_matches_instances_id_pattern_shape():
    """Mirrored, not imported (see the module docstring) — pinned equal to
    `homestead_law.instances.ID_PATTERN` so the two conventions cannot drift
    apart silently."""
    from homestead_law import instances

    assert venture._LABEL_PATTERN.pattern == instances.ID_PATTERN.pattern


def test_refusals_never_echo_the_offered_value():
    """I-15: name the field and the closed set/shape (the pack's own
    published data), never the value someone actually typed."""
    secret_value = "zzz-not-a-real-choice-zzz"
    with pytest.raises(venture.InvalidChoice) as exc:
        venture.validate_value("application_status", secret_value)
    assert secret_value not in str(exc.value)

    bad_label = "ZZZ_BAD_LABEL_ZZZ"
    with pytest.raises(venture.InvalidLabel) as exc:
        venture.validate_value("bank_account_label", bad_label)
    assert bad_label not in str(exc.value)


# ── the one computed template: election-83b ──────────────────────────────────

def test_exactly_one_template_and_its_shape():
    assert len(venture.TEMPLATES) == 1
    (row,) = venture.TEMPLATES
    assert row["name"] == "election-83b"
    assert row["anchor"] == "grant_date"
    assert row["days"] == 30
    assert row["direction"] == "forward"
    assert row["rule"] == "calendar_days"
    assert row["mail"] is False
    assert row["jurisdiction"] is None
    assert row["status"] == "VERIFIED"


def test_founder_vesting_start_is_not_the_anchor():
    """The Wave 8 plan paragraph names `founder.vesting_start` as the
    template's anchor; this pack uses the top-level `grant_date` instead
    (`rules.compute` addresses `(matter, anchor, instance)` with no sub-id,
    so a REPEATABLE field cannot be a computed anchor — see the module
    docstring). Pinned so the substitution cannot silently revert."""
    (row,) = venture.TEMPLATES
    assert row["anchor"] != "founder.vesting_start"
    assert venture.FIELDS["grant_date"] is Rung.L1
    assert venture.FIELDS["founder.vesting_start"] is Rung.L1  # still entered


def test_the_real_registry_validates_this_packs_templates():
    """`registry._validate` already ran `rules.validate_templates` on this
    pack at import; re-run here against the live pack."""
    rules.validate_templates(venture)


def test_compute_refuses_when_the_anchor_is_absent(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    jurisdiction_mod.set_jurisdiction(store, "venture", "primary", "US-DE")

    with pytest.raises(rules.AnchorUnavailable):
        rules.compute(store, "venture", "primary", "election-83b")


@pytest.mark.parametrize("code", ["US-DE", "US-OR"])
def test_compute_succeeds_at_either_jurisdiction_and_never_rolls(code, tmp_path, monkeypatch):
    """jurisdiction=None on the template fits any instance jurisdiction
    (`rules._for_jurisdiction`'s fallback) — proven at both members of
    JURISDICTIONS, `US-DE` included, the one the engine's RULES table does
    not know (calendar_days never consults it; see the module docstring).
    2026-10-04 is a Sunday; 30 calendar days before it is 2026-09-04 — the
    computed date must land ON that Sunday, never rolled to Monday."""
    import datetime

    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    jurisdiction_mod.set_jurisdiction(store, "venture", "primary", code)
    store.put("venture", "grant_date", "primary", Classified(Rung.L1, "2026-09-04"))

    computed = rules.compute(store, "venture", "primary", "election-83b")

    assert computed.jurisdiction == code
    assert computed.result_iso == "2026-10-04"
    assert datetime.date.fromisoformat(computed.result_iso).weekday() == 6  # Sunday


def test_compute_refuses_when_jurisdiction_is_entirely_absent(tmp_path, monkeypatch):
    """Provisional I-42, held here too: an unopened instance refuses
    arithmetic even for the one template whose own jurisdiction is None —
    `rules.compute` reads the instance's jurisdiction before the template's."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    store.put("venture", "grant_date", "primary", Classified(Rung.L1, "2026-01-01"))

    from homestead_law.jurisdiction import JurisdictionAbsent

    with pytest.raises(JurisdictionAbsent):
        rules.compute(store, "venture", "primary", "election-83b")


def test_a_deadline_compute_for_any_other_template_name_refuses(tmp_path, monkeypatch):
    """Every other date in this pack is entered, never computed — there are
    no other templates to ask for."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    jurisdiction_mod.set_jurisdiction(store, "venture", "primary", "US-DE")

    with pytest.raises(rules.TemplateNotFound):
        rules.compute(store, "venture", "primary", "annual-report")


def test_accept_stores_the_computed_deadline(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    jurisdiction_mod.set_jurisdiction(store, "venture", "primary", "US-DE")
    store.put("venture", "grant_date", "primary", Classified(Rung.L1, "2026-01-01"))

    computed = rules.compute(store, "venture", "primary", "election-83b")
    rules.accept(store, computed, token=computed.preview_token)

    from homestead_law import instances

    assert store.has("venture", "deadline", instances.item_id("primary", "election-83b"))


def test_the_source_cites_83b2_and_the_note_names_the_postmark_reference():
    (row,) = venture.TEMPLATES
    assert "83(b)(2)" in row["source"]
    assert "postmark" in row["note"]
    assert "accountant" in row["note"]


# ── ein crosses no surface ────────────────────────────────────────────────

def test_ein_never_renders_on_s1_list_s1_detail_or_s4():
    """`ein` is L5 — planted at every gated surface the app actually uses,
    and every one must deny it; there is no derived form to leak through."""
    from homestead.keep.rungs import derived_of

    record = Classified(Rung.L5, "12-3456789")
    for surface in (Surface.S1_LIST, Surface.S1_DETAIL, Surface.S4_EGRESS):
        served = serve(record, surface)
        assert served.disposition is Disposition.DENY, surface
        assert served.value is None
    assert derived_of(venture.SCHEMA, "ein") is None


# ── no investor or founder name in any derived form ──────────────────────────

def test_no_derived_form_names_a_specific_investor_founder_or_advisor():
    """A schema-level derived form is one sentence for every instance of the
    field — it may say a SAFE investor or a founder IS on file, never who,
    and never a digit (a count, an amount, a percentage). 'Never who' is
    held structurally: no word may be capitalized mid-sentence other than
    the field's own generic noun phrase ('SAFE') — a proper name inserted
    into the stand-in sentence would look exactly like that."""
    from homestead.keep.rungs import derived_of

    checked = 0
    for field in venture.SCHEMA:
        sentence = derived_of(venture.SCHEMA, field)
        if sentence is None:
            continue
        checked += 1
        assert not any(ch.isdigit() for ch in sentence), f"{field}: {sentence!r}"
        words = re.findall(r"[A-Za-z']+", sentence)
        capitalized_mid_sentence = [
            w for w in words[1:] if w[0].isupper() and w.upper() != w and w != "SAFE"
        ]
        assert not capitalized_mid_sentence, f"{field}: {sentence!r}"
    assert checked >= 10


def test_venture_is_registered():
    from homestead_law.registry import all_matters

    assert "venture" in all_matters()
