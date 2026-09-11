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
    """Entered dates at `L2`, not `L1` (audit, 2026-09-12 — the ruling the
    parallel L8-grant audit settled). `Rung.L1` is "public in this matter's
    forum"; an accelerator application has no forum at all, and a submission
    or interview date reveals that an application exists, which is household
    metadata — custody's `move_date` rung, the ledger's posting-date rung."""
    for field in ("application_submitted", "interview_date", "decision_date"):
        assert venture.FIELDS[field] is Rung.L2, field
    for field in ("accelerator", "batch", "application_status"):
        assert venture.FIELDS[field] is Rung.L2, field


def test_the_company_fields():
    """Same ruling, applied to the company half: a Secretary of State's
    corporate register is not this matter's forum either — it is a register
    the company files into — so the compliance dates are `L2` with the rest."""
    l2 = {
        "benefit_report_due", "formation_date", "foreign_qualification_date",
        "annual_report_due", "franchise_tax_due", "business_license_due",
        "revenue_start",
        "entity_type", "formation_state", "principal_office_state",
        "bank_account_label",
    }
    for field in l2:
        assert venture.FIELDS[field] is Rung.L2, field
    assert venture.FIELDS["grant_date"] is Rung.L1  # the one exception, below
    for field in ("legal_name", "public_benefit", "registered_agent"):
        assert venture.FIELDS[field] is Rung.L3, field
    assert venture.FIELDS["notes"] is Rung.L4
    assert venture.FIELDS["ein"] is Rung.L5


def test_grant_date_is_the_only_l1_date_and_why():
    """The whole of the exception, in one place. `grant_date` is `L1` because
    `rules.validate_templates` refuses an anchor that is not — and
    `election-83b` is this pack's one computed template. Nothing else that
    holds a date is `L1`; `jurisdiction` is `L1` and is not a date but a
    constant of the pack (decision 1). Pinned so the exception cannot
    quietly become a habit: a second `L1` date added later fails here and
    has to argue for itself in this docstring first."""
    l1 = {f for f, rung in venture.FIELDS.items() if rung is Rung.L1}
    assert l1 == {"jurisdiction", "grant_date"}, sorted(l1)

    (row,) = venture.TEMPLATES
    assert row["anchor"] == "grant_date"
    # ...and the rule that forces it, exercised rather than quoted: the same
    # pack with grant_date at L2 refuses at import-time validation.
    import copy

    from homestead_law import rules as rules_mod

    class _Demoted:
        MATTER = venture.MATTER
        JURISDICTION = venture.JURISDICTION
        JURISDICTIONS = venture.JURISDICTIONS
        SCHEMA = venture.SCHEMA
        FIELDS = dict(venture.FIELDS, grant_date=Rung.L2)
        TEMPLATES = copy.deepcopy(venture.TEMPLATES)

    with pytest.raises(rules_mod.InvalidTemplate) as exc:
        rules_mod.validate_templates(_Demoted)
    assert "grant_date" in str(exc.value) and "L1" in str(exc.value)


def test_the_repeatable_groups():
    expected = {
        "founder.name": Rung.L4, "founder.role": Rung.L2,
        "founder.equity_pct": Rung.L4, "founder.vesting_start": Rung.L2,
        "founder.cliff_months": Rung.L2, "founder.election_83b_deadline": Rung.L2,
        "safe.investor": Rung.L4, "safe.amount": Rung.L4,
        "safe.valuation_cap": Rung.L4, "safe.discount": Rung.L4,
        "safe.signed": Rung.L2, "safe.post_money": Rung.L2,
        "equity_grant.grantee": Rung.L4, "equity_grant.amount": Rung.L4,
        "equity_grant.granted": Rung.L2,
        "registration.kind": Rung.L2, "registration.due": Rung.L2,
        "registration.done": Rung.L2,
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
    planted = "zzz-not-a-real-choice-zzz"
    with pytest.raises(venture.InvalidChoice) as exc:
        venture.validate_value("application_status", planted)
    assert planted not in str(exc.value)

    planted_label = "ZZZ_BAD_LABEL_ZZZ"
    with pytest.raises(venture.InvalidLabel) as exc:
        venture.validate_value("bank_account_label", planted_label)
    assert planted_label not in str(exc.value)

    planted_ein = "00-0000000x"
    with pytest.raises(venture.InvalidEin) as exc:
        venture.validate_value("ein", planted_ein)
    assert planted_ein not in str(exc.value)


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
    assert venture.FIELDS["founder.vesting_start"] is Rung.L2  # still entered
    assert "founder.vesting_start" in venture.REPEATABLE


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


# ── audit additions (L8-venture, 2026-09-12) ────────────────────────────────

def test_a_bank_account_label_that_is_all_digits_is_refused():
    """`bank_account_label`'s own `why` promises the account NUMBER can never
    live here, and `_LABEL_PATTERN` alone does not keep that promise:
    `"12345678"` matches it. An all-digit string is never a label the
    operator chose, and it is exactly the shape of the one value (I-43) this
    field exists to keep out — refused separately, naming the rule and not
    the digits."""
    with pytest.raises(venture.InvalidLabel) as exc:
        venture.validate_value("bank_account_label", "12345678")
    assert "12345678" not in str(exc.value)
    assert "account number" in str(exc.value)

    # a label that merely *contains* digits is fine — the ledger's own shape
    venture.validate_value("bank_account_label", "venture-ops-2")
    venture.validate_value("bank_account_label", "1st-business")


def test_ein_shape_is_validated_by_name_and_never_echoed():
    """Deciding the open question the plan's audit line raises: an `L5`
    value's *shape* may be validated without ever echoing it. `ein` has no
    derived form and renders on no surface, so entry is the only moment a
    value typed into the wrong box can be caught at all (I-11 — absence of a
    check is not permission)."""
    venture.validate_value("ein", "12-3456789")
    for bad in ("123456789", "12-345678", "12-34567890", "ab-cdefghi",
                "12-3456789 ", "", 123456789, None):
        with pytest.raises(venture.InvalidEin):
            venture.validate_value("ein", bad)

    planted = "991111111"  # the right digits, the wrong shape
    with pytest.raises(venture.InvalidEin) as exc:
        venture.validate_value("ein", planted)
    message = str(exc.value)
    assert "ein" in message
    assert planted not in message and "1111111" not in message
    assert "L5" in message


def test_no_template_computes_an_entered_compliance_date():
    """Every compliance date in this pack is entered — a fixed statutory date
    is not a period to count, and 8 Del. C. § 366(b) fixes only a floor. The
    structural version of that claim: no template anchors on, or is named
    for, any of them."""
    entered = {
        "benefit_report_due", "annual_report_due", "franchise_tax_due",
        "business_license_due", "registration.due", "formation_date",
        "foreign_qualification_date", "founder.election_83b_deadline",
    }
    anchors = {row["anchor"] for row in venture.TEMPLATES}
    names = {row["name"] for row in venture.TEMPLATES}
    assert not (anchors & entered), sorted(anchors & entered)
    assert not (names & entered)
    assert names == {"election-83b"}


def test_the_public_benefit_derived_form_is_the_fixed_sentence():
    """8 Del. C. § 362's stated purpose is L3 and derives to one sentence
    that says a purpose is on file and never what it is — the certificate
    language would otherwise reach S2 (a model prompt) through the derived
    form the moment a surface derived instead of rendering."""
    from homestead.keep.rungs import derived_of

    assert derived_of(venture.SCHEMA, "public_benefit") == (
        "A stated public benefit is on file"
    )
    assert venture.FIELDS["public_benefit"] is Rung.L3
    assert "pbc" in venture.ENTITY_TYPES
    assert derived_of(venture.SCHEMA, "entity_type") is None  # L2 renders itself
    assert derived_of(venture.SCHEMA, "benefit_report_due") is None


@pytest.mark.parametrize(
    "anchor,expected,why",
    [
        ("2026-06-04", "2026-07-04", "a Saturday AND Independence Day"),
        ("2027-06-04", "2027-07-04", "a Sunday AND Independence Day"),
        ("2026-09-04", "2026-10-04", "a Sunday"),
        ("2026-12-06", "2027-01-05", "an ordinary weekday, across a year end"),
    ],
)
def test_the_83b_window_never_rolls_off_a_weekend_or_a_federal_holiday(
    anchor, expected, why, tmp_path, monkeypatch,
):
    """`rule="calendar_days"` is counted by `rules.compute` itself as a plain
    `timedelta` and never reaches `homestead.keep.dates.RULES`, so there is
    no calendar for it to roll against — proven rather than asserted, on a
    landing that is a weekend and a federal holiday at once. This is the
    conservative reading of the window: 26 U.S.C. § 7503's general extension
    is an UNCERTAIN reference the template's `note` points at an accountant,
    never something this count applies."""
    import datetime

    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    jurisdiction_mod.set_jurisdiction(store, "venture", "primary", "US-DE")
    store.put("venture", "grant_date", "primary", Classified(Rung.L1, anchor))

    computed = rules.compute(store, "venture", "primary", "election-83b")

    assert computed.result_iso == expected, why
    landing = datetime.date.fromisoformat(expected)
    assert (landing - datetime.date.fromisoformat(anchor)).days == 30


def test_the_landings_this_test_uses_really_are_a_weekend_and_a_holiday():
    """The plant behind the test above: if 2026-07-04 stopped being both a
    Saturday and a federal holiday, that test would prove nothing and this
    one says so."""
    import datetime

    holidays = pytest.importorskip("holidays")
    us = holidays.US(years=[2026, 2027])
    assert datetime.date(2026, 7, 4).weekday() == 5  # Saturday
    assert datetime.date(2027, 7, 4).weekday() == 6  # Sunday
    assert datetime.date(2026, 7, 4) in us and datetime.date(2027, 7, 4) in us


def test_mail_days_are_refused_not_silently_ignored(tmp_path, monkeypatch):
    """`mail=False` is pinned on the row, and asking for `--mail` anyway is a
    refusal by name — not a silent +0. FRBP 9006(f)'s three days extend a
    period that runs from service; a federal tax election's 30-day window
    runs from a transfer of property and is not served on anyone."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    jurisdiction_mod.set_jurisdiction(store, "venture", "primary", "US-DE")
    store.put("venture", "grant_date", "primary", Classified(Rung.L1, "2026-09-04"))

    (row,) = venture.TEMPLATES
    assert row["mail"] is False
    with pytest.raises(rules.MailUnsupported):
        rules.compute(store, "venture", "primary", "election-83b", mail=True)


def test_the_accepted_deadline_is_stored_l1_with_the_instruction_and_queues_by_reference(
    tmp_path, monkeypatch,
):
    """The accept path end to end: `--accept` files
    `(venture, "deadline", "<instance>.election-83b")` at `L1` carrying the
    "computed from <anchor> under <source>" instruction, and the queue shows
    it as a reference — matter, instance and the date, never the statute text
    it was computed under (I-15)."""
    from homestead_law import instances, queue as queue_mod

    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    jurisdiction_mod.set_jurisdiction(store, "venture", "x", "US-DE")
    store.put("venture", "grant_date", "x", Classified(Rung.L1, "2026-09-04"))

    computed = rules.compute(store, "venture", "x", "election-83b")
    rules.accept(store, computed, token=computed.preview_token)

    item_id = instances.item_id("x", "election-83b")
    assert item_id == "x.election-83b"
    stored = store.get("venture", "deadline", item_id)
    assert stored.rung is Rung.L1
    served = serve(stored, Surface.S1_DETAIL)
    assert served.disposition is Disposition.RENDER and served.value == "2026-10-04"

    items = queue_mod.queue(store, today="2026-09-11")
    (due,) = [i for i in items if i.ref[0] == "venture"]
    assert due.ref == ("venture", "deadline", item_id)
    assert "83(b)(2)" not in due.shown and "Secretary" not in due.shown


def test_one_venture_instance_per_grant_is_the_documented_answer():
    """Item 4 of this bite's audit, pinned rather than left to a reader:
    `grant_date` is one top-level field, so one instance carries one grant
    date and one computed `election-83b`. A second founder's stock
    transferred on a different day is a second *instance*, not a second
    anchor — `rules.compute` is not extended here. The pack docstring and
    the README both say so; this asserts the pack half, so the sentence
    cannot be deleted without a red test."""
    assert "One venture instance per grant" in venture.__doc__
    assert "grant_date" not in venture.REPEATABLE
    # the entered, per-founder half is unaffected: every founder's own
    # confirmed date still fits in one instance.
    assert "founder.election_83b_deadline" in venture.REPEATABLE


def test_two_instances_each_compute_their_own_83b_date(tmp_path, monkeypatch):
    """The behavioural half of the ruling above — two grants, two instances,
    two independent answers, no engine change."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    for inst, anchor, expected in (
        ("founders-2026-09", "2026-09-04", "2026-10-04"),
        ("hire-2026-11", "2026-11-02", "2026-12-02"),
    ):
        jurisdiction_mod.set_jurisdiction(store, "venture", inst, "US-DE")
        store.put("venture", "grant_date", inst, Classified(Rung.L1, anchor))
        computed = rules.compute(store, "venture", inst, "election-83b")
        assert computed.result_iso == expected, inst
        assert computed.instance == inst


def test_the_generic_pane_shows_no_l4_payload_and_no_l5_row(tmp_path, monkeypatch):
    """Until `L8-surfaces` gives this pack its own pane, `pane_for` falls
    back to `generic_pane` — and the fallback is a surface like any other.
    Planted: a founder's name, a SAFE investor and amount, an operator note
    and an `ein`. The L4 fields must appear as their derived sentence and
    nothing else, and the `ein` must leave no row at all — not a placeholder,
    not a count (`serve_all` drops denials without a trace)."""
    import json

    from homestead_law.app import panes

    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    jurisdiction_mod.set_jurisdiction(store, "venture", "primary", "US-DE")
    planted = {
        ("ein", "primary", Rung.L5, "99-7654321", None),
        ("notes", "primary", Rung.L4, "PLANTEDNOTE", "An operator note is on file"),
        ("founder.name", "primary.f1", Rung.L4, "PLANTEDFOUNDER", "A founder is named"),
        ("founder.equity_pct", "primary.f1", Rung.L4, "55",
         "An equity percentage is on file"),
        ("safe.investor", "primary.s1", Rung.L4, "PLANTEDINVESTOR",
         "A SAFE investor is on file"),
        ("safe.amount", "primary.s1", Rung.L4, "250000", "A SAFE amount is on file"),
    }
    for field, item_id, rung, value, derived in sorted(planted):
        store.put("venture", field, item_id, Classified(rung, value, derived))

    pane = panes.pane_for(store, "venture", "primary", today="2026-09-11")
    blob = json.dumps(pane) + panes.pane_text(pane)

    for marker in ("99-7654321", "PLANTEDNOTE", "PLANTEDFOUNDER",
                   "PLANTEDINVESTOR", "250000", "7654321"):
        assert marker not in blob, marker
    assert "ein" not in {row["item_type"] for row in pane["rows"]}
    assert "L5" not in {row["rung"] for row in pane["rows"]}
    assert "A SAFE investor is on file" in blob


# ── I-44's three new phrases, fired and not fired (L8-venture audit) ─────────

def _i44():
    """`tests/test_i44_no_drafting.py` as a module — the phrase list and its
    scanner, read rather than retyped, so these tests cannot drift from the
    guard they are about."""
    import importlib

    return importlib.import_module("test_i44_no_drafting")


def test_the_new_phrases_do_not_fire_on_this_packs_own_legitimate_words():
    """The failure mode a phrase list dies of: firing on the vocabulary the
    subject matter needs. This pack must be free to say `registration`,
    `formation_date`, `foreign_qualification_date`, that a certificate is
    *filed with* the Delaware Secretary of State, and that a form is due —
    none of which instructs the operator to do anything. Planted as the
    sentences the pack actually contains."""
    import ast

    i44 = _i44()
    for sentence in (
        "the certificate's filing date is on file with the Delaware "
        "Secretary of State",
        "an Oregon or local business-license renewal date, filed with the "
        "issuing authority",
        "the date the company qualified to do business in Oregon",
        "one of REGISTRATION_KINDS — a closed tag",
        "foreign_qualification_date is entered from the notice",
        "Delaware's fixed statutory annual-report date",
    ):
        assert not i44._banned_phrase_hits(ast.parse(f"X = {sentence!r}")), sentence


def test_the_new_phrases_fire_on_a_planted_notice_that_instructs_a_filing():
    """A scan that has never fired has not been shown to check anything. A
    third pack's `NOTICE` — the one string every surface renders, and so the
    likeliest place a "helpful" instruction would be added — carrying each of
    the three new phrases in turn, and each one caught."""
    import ast

    i44 = _i44()
    for phrase in ("form the company", "incorporate the company",
                   "file with the state"):
        assert phrase in i44.BANNED_PHRASES
        planted = (
            "This pack keeps dates and references. When you are ready, "
            f"{phrase} and enter the date here."
        )
        hits = i44._banned_phrase_hits(ast.parse(f"NOTICE = {planted!r}"))
        assert hits and hits[0][1] == phrase, phrase

    # ...and the real NOTICE, which says the opposite, is clean.
    assert not i44._banned_phrase_hits(
        ast.parse(f"NOTICE = {venture.NOTICE!r}")
    )
