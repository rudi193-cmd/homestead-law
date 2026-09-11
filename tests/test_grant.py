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

#: The audit's rung ruling (2026-09-11) is in this table: `L1` is "public in
#: this matter's forum", and a grant has no forum, so every *entered* date
#: here is `L2` — household content that reveals an application or an award
#: exists. `jurisdiction` alone stays `L1`: it is a constant of the pack, not
#: a fact about the household. See `packs/grant.py`'s ladder section.
EXPECTED = {
    "jurisdiction": Rung.L1,
    "backing_agreed_date": Rung.L2,
    "submission_deadline": Rung.L2,
    "submitted_date": Rung.L2,
    "decision_date": Rung.L2,
    "award_date": Rung.L2,
    "award_period_start": Rung.L2,
    "award_period_end": Rung.L2,
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
    "milestone.due": Rung.L2,
    "milestone.done": Rung.L2,
    "report.period": Rung.L2,
    "report.due": Rung.L2,
    "report.submitted": Rung.L2,
    "report.kind": Rung.L2,
    "disbursement.expected": Rung.L2,
    "disbursement.amount": Rung.L3,
    "disbursement.received": Rung.L2,
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
    store.put(MATTER, "disbursement.received", sub, Classified(Rung.L2, "2026-07-01"))

    assert plan_period.flag(store) == (EXPECTED_LINE,)


def test_disbursement_expected_and_account_label_alone_flag_nothing():
    """The two scheduling/reference sub-fields are deliberately not in
    `SIGNAL_FIELDS` — neither is itself new income or an asset."""
    store = Sidecar()
    _confirmed_bankruptcy(store)
    sub = instances.item_id("primary", "tranche-1")
    store.put(MATTER, "disbursement.expected", sub, Classified(Rung.L2, "2026-07-01"))
    store.put(MATTER, "disbursement.account_label", sub, Classified(Rung.L2, "visa-chase"))

    assert plan_period.flag(store) == ()


def test_a_discharged_bankruptcy_gets_no_line_even_with_a_real_award():
    """The consumer's second condition, against the real producer rather than
    the fake pack `tests/test_plan_period.py` built it with: once a discharge
    date is on file the plan period is over and §§ 541(a)(7)/1306(a) have
    nothing left to say about a later award."""
    store = Sidecar()
    _confirmed_bankruptcy(store)
    store.put("bankruptcy", "discharge_date", "primary", Classified(Rung.L1, "2026-08-01"))
    store.put(MATTER, "award_amount", "primary",
              Classified(Rung.L3, "285000", "An award amount is on file"))

    assert plan_period.flag(store) == ()
    assert queue_mod.notices(store) == ()


def test_the_flag_line_names_neither_the_producing_matter_nor_its_field():
    """The line says "income or assets arising during the plan" and names the
    bankruptcy instance it belongs to — never which other matter produced the
    signal, nor which field of it. Naming the producer would turn a reference
    line into a statement about the household's other affairs, on a surface
    (the queue) that is ambient."""
    store = Sidecar()
    _confirmed_bankruptcy(store)
    store.put(MATTER, "award_amount", "primary",
              Classified(Rung.L3, "285000", "An award amount is on file"))

    (line,) = plan_period.flag(store)
    assert MATTER not in line
    for field in grant.FIELDS:
        assert field not in line, field


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
    """`app.demo.compose_panes` iterates `all_matters()`; `app/panes.py` now
    gives grant its own composer (L8-surfaces) — this pins that grant, with
    no records at all, composes cleanly rather than raising, through its own
    shape rather than the generic fallback."""
    from homestead_law.app import panes

    store = Sidecar()
    pane = panes.pane_for(store, MATTER, "primary", today=TODAY)
    assert pane["matter"] == MATTER
    assert pane["milestones"] == [] and pane["reports"] == [] and pane["disbursements"] == []
    assert pane["notice"] == grant.NOTICE
    panes.pane_text(pane)  # does not raise


def test_main_smoke_and_demo_still_run_with_grant_registered():
    from homestead_law import __main__ as entry

    assert entry.main(["--smoke"]) == 0
    assert entry.main(["--demo"]) == 0


# ── the rung ruling, held as checks rather than only as prose ───────────────

#: Every field on this pack that holds a date the operator enters off the
#: funder's notice. Named here rather than derived from the field names, so a
#: date field added later with a name this list does not anticipate makes
#: this list wrong visibly instead of silently skipping the check.
_ENTERED_DATES = (
    "backing_agreed_date", "submission_deadline", "submitted_date",
    "decision_date", "award_date", "award_period_start", "award_period_end",
    "milestone.due", "milestone.done", "report.due", "report.submitted",
    "disbursement.expected", "disbursement.received",
)


def test_every_field_that_holds_a_date_is_accounted_for():
    """The list above is the check's own coverage: any field whose name reads
    like a date must be in it, or the ruling below is quietly not testing a
    field somebody added."""
    looks_like_a_date = {
        f for f in grant.FIELDS
        if f.endswith(("_date", "_deadline", ".due", ".done", ".received",
                       ".expected", ".submitted", "_start", "_end"))
    }
    assert looks_like_a_date == set(_ENTERED_DATES)


def test_no_entered_date_is_l1_because_no_forum_publishes_one():
    """The audit's ruling (2026-09-11). `L1` is "public in this matter's
    forum" — a grant has no forum, so an entered date cannot reach it. The
    failure this guards against is the one the first draft of this pack made:
    reading `L1` as "the smallest kind of fact" and putting a household's
    private calendar there, where every surface renders it unconditionally
    and a template could anchor arithmetic on it.

    `custody.py`'s `move_date` ("nothing makes a family's moving date public
    in this forum on its own") and the ledger's posting `date` (`L2`,
    explicitly not `L1`) are the two in-repo precedents."""
    for field in _ENTERED_DATES:
        assert grant.FIELDS[field] is Rung.L2, (
            f"{field} is {grant.FIELDS[field].value}: an entered date that "
            "reveals an application or an award exists is household content "
            "(L2), never a public-forum fact (L1)"
        )


def test_jurisdiction_is_the_only_l1_field_and_it_is_not_a_household_fact():
    l1 = {f for f, r in grant.FIELDS.items() if r is Rung.L1}
    assert l1 == {"jurisdiction"}
    assert grant.SCHEMA["jurisdiction"]["rung"] is Rung.L1


def test_no_l1_date_means_no_template_could_ever_anchor_here():
    """The ruling's deliberate cost, stated as a check: `_check_templates`
    (and `rules.validate_templates`) require a template's `anchor` to name an
    `L1` field. After the ruling this pack has exactly one, and it is not a
    date, so a computed deadline is not merely unwritten here — it is
    unreachable until somebody re-argues a rung. That is the plan's "no
    computed deadlines" made structural rather than left to discipline."""
    l1_dates = [
        f for f, r in grant.FIELDS.items()
        if r is Rung.L1 and f != "jurisdiction"
    ]
    assert l1_dates == []


def test_the_ruling_moves_nothing_on_any_surface():
    """`L1` and `L2` render in the same places — every ceiling in the
    crossing table is `L2` or higher — so the ruling is a correction to what
    the pack *claims*, not a change to what an operator sees. Pinned, so a
    future reader does not have to take the docstring's word for it."""
    for surface in Surface:
        one = serve(Classified(Rung.L1, "2027-03-01"), surface)
        two = serve(Classified(Rung.L2, "2027-03-01"), surface)
        assert one.disposition is two.disposition, surface
        assert one.value == two.value, surface


# ── the import-time template shape check, planted ───────────────────────────

def _import_pack_with_templates(row_source: str):
    """This module's own source with `TEMPLATES` replaced by one planted row,
    executed as a fresh module. `_check_templates` runs on the last line of
    the file, so executing the source *is* the import, and a refusal is a
    build failure exactly as it would be on disk."""
    import pathlib

    source = pathlib.Path(grant.__file__).read_text("utf-8")
    marker = "TEMPLATES: tuple[dict[str, Any], ...] = ()"
    assert marker in source, "the TEMPLATES line moved; this plant is stale"
    planted = source.replace(
        marker, f"TEMPLATES: tuple[dict[str, Any], ...] = ({row_source},)"
    )
    namespace: dict = {"__name__": "homestead_law.packs._planted_grant"}
    exec(compile(planted, "<planted grant.py>", "exec"), namespace)
    return namespace


def _row(**over) -> str:
    row = {
        "name": "planted", "anchor": "jurisdiction", "days": 14,
        "direction": "forward", "rule": "calendar_days", "mail": False,
        "jurisdiction": "US-federal", "source": "a source", "status": "UNCERTAIN",
        "note": "a note",
    }
    row.update(over)
    return repr(row)


def test_the_template_check_refuses_a_planted_row_with_an_l3_anchor():
    """A scan that has never fired has not been shown to check anything. The
    row below is well-formed in every other respect and anchors on `funder`
    (`L3`) — arithmetic reading an anchor that does not render unconditionally
    is exactly what the `L1` rule exists to stop."""
    with pytest.raises(ValueError) as exc:
        _import_pack_with_templates(_row(anchor="funder"))
    message = str(exc.value)
    assert "funder" in message and "L3" in message


def test_the_template_check_refuses_a_planted_row_with_an_l2_date_anchor():
    """The ruling's own consequence, planted: `submission_deadline` reads
    like the natural anchor for this matter and is now `L2`, so a row
    anchoring on it is refused by name at import."""
    with pytest.raises(ValueError) as exc:
        _import_pack_with_templates(_row(anchor="submission_deadline"))
    assert "submission_deadline" in str(exc.value)
    assert "L2" in str(exc.value)


def test_the_template_check_refuses_an_unknown_anchor_and_a_bad_shape():
    for over, expected in (
        ({"anchor": "not_a_field"}, "not_a_field"),
        ({"days": 0}, "days"),
        ({"direction": "sideways"}, "direction"),
        ({"rule": "moon_days"}, "rule"),
        ({"status": "PROBABLY"}, "status"),
        ({"jurisdiction": "US-OR"}, "jurisdiction"),
        ({"name": "Not A Label"}, "name"),
        ({"note": "  "}, "note"),
    ):
        with pytest.raises(ValueError) as exc:
            _import_pack_with_templates(_row(**over))
        assert expected in str(exc.value), over


def test_the_template_check_is_not_simply_refusing_everything():
    """The other half of a planted guard: a row the contract actually allows
    must import clean, or "it refuses" says nothing. `jurisdiction` is this
    pack's one `L1` field — a nonsensical anchor for a real deadline, which
    is the point of the test above, but a valid one for the shape check."""
    namespace = _import_pack_with_templates(_row())
    assert len(namespace["TEMPLATES"]) == 1


# ── a planted funder name and a planted amount, across every surface ────────

#: Planted markers, not real: the audit puts both through every surface this
#: package renders and greps for them. Deliberately *not* named `secret` —
#: CodeQL treats such a name as sensitive data and taints every string it
#: touches (law PR #38).
_PLANTED_NAME = "BERI"
_PLANTED_AMOUNT = "285000"


def _seed_planted_grant(store: Sidecar) -> None:
    def put(field: str, payload: str, sub: str | None = None) -> None:
        store.put(
            MATTER, field, instances.item_id("primary", sub),
            Classified(grant.FIELDS[field], payload,
                       grant.SCHEMA[field].get("derived")),
            overwrite=True,
        )

    put("funder", f"{_PLANTED_NAME} Foundation")
    put("backer", _PLANTED_NAME)
    put("program_officer", f"{_PLANTED_NAME} officer")
    put("amount_requested", _PLANTED_AMOUNT)
    put("award_amount", _PLANTED_AMOUNT)
    put("allowable_uses", f"stipends from {_PLANTED_NAME}, {_PLANTED_AMOUNT} cap")
    put("restrictions", f"no lobbying; {_PLANTED_NAME} prior approval")
    put("notes", f"{_PLANTED_NAME} {_PLANTED_AMOUNT}")
    put("status", "awarded")
    put("submission_deadline", "2027-03-01")
    put("award_date", "2027-05-01")
    put("milestone.name", f"{_PLANTED_NAME} phase one", sub="m1")
    put("milestone.due", "2027-04-01", sub="m1")
    put("report.due", "2027-09-30", sub="q3-2027")
    put("disbursement.amount", _PLANTED_AMOUNT, sub="tranche-1")
    put("disbursement.received", "2027-06-01", sub="tranche-1")
    put("disbursement.account_label", "grant-ops", sub="tranche-1")


def test_no_planted_name_or_amount_reaches_a_prompt_an_agent_or_egress():
    """The three surfaces whose ceiling is `L2`: a local model's context
    window, agent retrieval, and egress with no purpose declared. Every `L3`
    and `L4` field must stand in with its derived sentence there, and the
    derived sentences carry neither a funder's name nor a figure."""
    store = Sidecar()
    _seed_planted_grant(store)

    for surface in (Surface.S2_PROMPT, Surface.S3_AGENT, Surface.S4_EGRESS):
        leaked = []
        for ref, record in store.records(MATTER):
            served = serve(record, surface)
            if served.disposition is Disposition.DENY:
                continue
            shown = str(served.value)
            if _PLANTED_NAME in shown or _PLANTED_AMOUNT in shown:
                leaked.append((ref[1], shown))
        assert not leaked, f"{surface.name} rendered {leaked}"


def test_the_dedicated_pane_never_renders_allowable_uses_restrictions_or_notes():
    """`app.panes.grant_pane` (L8-surfaces) composes milestones, reports,
    disbursements, the award timeline and `state` — never `allowable_uses`,
    `restrictions` or `notes`, which the plan's own field list for this pane
    leaves out. Not merely their payloads: neither of these fields' own
    derived stand-in sentences appears either, because the composer never
    reads them at all — the record is one explicit `S1_DETAIL` open away
    (`tests/test_panes_wave8.py` proves that half)."""
    import json

    from homestead_law.app import panes

    store = Sidecar()
    _seed_planted_grant(store)
    pane = panes.pane_for(store, MATTER, "primary", today=TODAY)
    rendered = panes.pane_text(pane) + json.dumps(pane)

    for payload in ("stipends from", "no lobbying", "prior approval"):
        assert payload not in rendered, payload
    for sentence in ("Allowable uses are on file", "Restrictions are on file",
                     "An operator note is on file"):
        assert sentence not in rendered, sentence


def test_neither_the_queue_nor_the_plan_period_line_carries_the_plant():
    """The two ambient places a grant reaches beyond its own pane: the queue
    (whose rows are `deadline` records, never a pack field) and the
    plan-period reference line."""
    import json

    store = Sidecar()
    _seed_planted_grant(store)
    _confirmed_bankruptcy(store)
    store.put(
        MATTER, "deadline", instances.item_id("primary", "q3-2027"),
        Classified(Rung.L1, "2027-09-30", None),
    )

    rows = json.dumps(
        [[i.matter, list(i.ref), i.shown] for i in queue_mod.queue(store, today=TODAY)]
    )
    lines = " ".join(queue_mod.notices(store))
    for blob in (rows, lines):
        assert _PLANTED_NAME not in blob
        assert _PLANTED_AMOUNT not in blob
    assert queue_mod.notices(store)  # the flag did fire, so this is not vacuous


# ── the writing doors call this pack's validate_value ───────────────────────

def test_the_cli_door_refuses_a_card_shaped_account_label_and_stores_nothing(capsys):
    """`cli._cmd_put` calls any pack's `validate_value` before it builds the
    `Classified` (L4-surfaces' wiring). A ledger account *label* is never a
    number (decision 9, provisional I-43), and the shape a mistyped card
    number takes is the case worth planting: refused by field name, echoing
    none of what was typed (I-15), nothing on disk."""
    from homestead_law.cli import run_cli

    planted = "4111111111111111"
    assert run_cli(
        ["put", MATTER, "disbursement.account_label", planted,
         "--id", "primary", "--sub", "tranche-1"]
    ) == 1
    err = capsys.readouterr().err
    assert err.startswith("refused:")
    assert "account_label" in err
    assert planted not in err and planted[:6] not in err
    assert not Sidecar().has(MATTER, "disbursement.account_label", "primary.tranche-1")


def test_the_cli_door_refuses_a_status_outside_the_closed_set(capsys):
    from homestead_law.cli import run_cli

    assert run_cli(["put", MATTER, "status", "drafting", "--id", "primary"]) == 1
    err = capsys.readouterr().err
    assert "status" in err and "drafting" not in err
    assert not Sidecar().has(MATTER, "status", "primary")


def test_the_cli_door_stores_a_declared_status_at_l2(capsys):
    from homestead_law.cli import run_cli

    assert run_cli(["put", MATTER, "status", "submitted", "--id", "primary"]) == 0
    assert "L2" in capsys.readouterr().out
