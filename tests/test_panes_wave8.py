"""`app.panes.grant_pane` / `app.panes.venture_pane` (L8-surfaces, wave 8).

Headless throughout, the same posture `tests/test_panes.py` holds for the
three wave-4 composers: every composer is called directly against a real
store, never through the browser, and planted L4/L5 content proves the
absent-on-the-list, present-on-open contract. The Chapter 13 plan-period
flag is proven here against the *real* producers (grant's `award_amount`,
venture's `safe.amount`) rather than the fake pack `tests/test_plan_period.py`
and `tests/test_panes.py` use — those cover the consumer in isolation;
this file covers the two Wave 8 wires end to end, through the pane and the
queue both.
"""
from __future__ import annotations

import json

import pytest

from homestead.keep.rungs import Classified, Rung
from homestead_law import instances
from homestead_law import queue as queue_mod
from homestead_law.app import panes
from homestead_law.app.window import Window
from homestead_law.packs import bankruptcy, grant, venture
from homestead_law.store import Sidecar

TODAY = "2026-08-10"


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    yield


def _put(store: Sidecar, pack, field: str, sub: str | None, payload: str) -> None:
    """One record, classified at the pack's own declared rung and derived
    form (decision 3) — the same helper shape `app.demo.seed_pane_demo` and
    `tests/test_panes.py` already use, so a planted record here is
    classified exactly as a real write door would classify it."""
    store.put(
        pack.MATTER, field, instances.item_id("primary", sub),
        Classified(pack.FIELDS[field], payload, pack.SCHEMA[field].get("derived")),
        overwrite=True,
    )


# ── grant pane shape ─────────────────────────────────────────────────────────

def test_grant_pane_composes_milestones_reports_disbursements_and_timeline():
    store = Sidecar()
    _put(store, grant, "milestone.name", "m1", "Phase 1 report")
    _put(store, grant, "milestone.due", "m1", "2026-10-01")
    _put(store, grant, "report.period", "q3", "Q3 2026")
    _put(store, grant, "report.due", "q3", "2026-09-30")
    _put(store, grant, "disbursement.expected", "t1", "2026-11-01")
    _put(store, grant, "disbursement.amount", "t1", "50000")
    _put(store, grant, "disbursement.account_label", "t1", "grant-ops")
    _put(store, grant, "submission_deadline", None, "2026-06-01")
    _put(store, grant, "award_date", None, "2026-08-01")
    _put(store, grant, "status", None, "awarded")

    pane = panes.pane_for(store, grant.MATTER, "primary", today=TODAY)

    milestone = pane["milestones"][0]
    assert milestone["sub"] == "m1"
    assert milestone["fields"]["milestone.name"]["text"] == "Phase 1 report"  # L3 renders

    report = pane["reports"][0]
    assert report["fields"]["report.due"]["text"] == "2026-09-30"

    disbursement = pane["disbursements"][0]
    assert disbursement["fields"]["disbursement.amount"]["text"] == "50000"  # L3 renders
    assert disbursement["fields"]["disbursement.account_label"]["text"] == "grant-ops"

    timeline = {t["item_type"]: t["text"] for t in pane["timeline"]}
    assert timeline["submission_deadline"] == "2026-06-01"
    assert timeline["award_date"] == "2026-08-01"

    assert pane["state"]["text"] == "awarded"
    assert pane["notice"] == grant.NOTICE


def test_grant_pane_disbursement_account_label_is_a_label_never_a_number():
    """`disbursement.account_label` names a ledger account instance's own
    label (decision 9) — the pane shows it as an ordinary field, never
    formatted or read as an amount; `disbursement.amount` is the field that
    carries money."""
    store = Sidecar()
    _put(store, grant, "disbursement.account_label", "t1", "visa-chase")
    pane = panes.pane_for(store, grant.MATTER, "primary", today=TODAY)
    card = pane["disbursements"][0]
    assert card["fields"]["disbursement.account_label"]["text"] == "visa-chase"
    assert "disbursement.amount" not in card["fields"]


@pytest.mark.parametrize(
    "due,expect",
    [("2026-07-01", "overdue"), ("2026-08-15", "needs_attention"), ("2027-01-01", "nothing_due")],
)
def test_grant_pane_indicator_from_the_nearest_undone_milestone_due(due, expect):
    store = Sidecar()
    _put(store, grant, "milestone.due", "m1", due)
    pane = panes.pane_for(store, grant.MATTER, "primary", today=TODAY)
    assert pane["indicator"] == expect


def test_grant_pane_indicator_from_the_nearest_undone_report_due():
    store = Sidecar()
    _put(store, grant, "report.due", "q3", "2026-07-01")
    pane = panes.pane_for(store, grant.MATTER, "primary", today=TODAY)
    assert pane["indicator"] == "overdue"


def test_grant_pane_a_done_milestone_drops_out_of_the_indicator():
    """An overdue-looking due date belongs to a milestone already marked
    `done` — it must not make the pane call anything overdue."""
    store = Sidecar()
    _put(store, grant, "milestone.due", "m1", "2026-07-01")
    _put(store, grant, "milestone.done", "m1", "2026-07-05")
    pane = panes.pane_for(store, grant.MATTER, "primary", today=TODAY)
    assert pane["indicator"] is None


def test_grant_pane_a_submitted_report_drops_out_of_the_indicator():
    store = Sidecar()
    _put(store, grant, "report.due", "q3", "2026-07-01")
    _put(store, grant, "report.submitted", "q3", "2026-07-02")
    pane = panes.pane_for(store, grant.MATTER, "primary", today=TODAY)
    assert pane["indicator"] is None


def test_grant_pane_indicator_is_none_with_nothing_on_file():
    pane = panes.pane_for(Sidecar(), grant.MATTER, "primary", today=TODAY)
    assert pane["indicator"] is None
    assert pane["milestones"] == [] and pane["reports"] == [] and pane["disbursements"] == []
    assert pane["state"] is None


def test_grant_pane_never_carries_allowable_uses_restrictions_or_notes():
    """The plan's own field list for this pane names milestones, reports,
    disbursements, the timeline and `status` — never these three L4 fields.
    Planted directly, opened on `S1_DETAIL` afterwards to prove the record
    is one explicit open away rather than lost."""
    store = Sidecar()
    _put(store, grant, "allowable_uses", None, "PLANTEDUSE")
    _put(store, grant, "restrictions", None, "PLANTEDRESTRICTION")
    _put(store, grant, "notes", None, "PLANTEDNOTE")

    pane = panes.pane_for(store, grant.MATTER, "primary", today=TODAY)
    blob = json.dumps(pane) + panes.pane_text(pane)
    for marker in ("PLANTEDUSE", "PLANTEDRESTRICTION", "PLANTEDNOTE",
                   "Allowable uses are on file", "Restrictions are on file",
                   "An operator note is on file"):
        assert marker not in blob, marker

    window = Window()
    window.open_list(instances.records_of(store, grant.MATTER, "primary"))
    ref = (grant.MATTER, "allowable_uses", "primary")
    assert window.open_detail(ref).value == "PLANTEDUSE"


# ── venture pane shape ───────────────────────────────────────────────────────

def test_venture_pane_composes_application_company_and_registrations():
    store = Sidecar()
    _put(store, venture, "application_submitted", None, "2026-06-01")
    _put(store, venture, "interview_date", None, "2026-07-01")
    _put(store, venture, "application_status", None, "interview")
    _put(store, venture, "entity_type", None, "pbc")
    _put(store, venture, "formation_state", None, "DE")
    _put(store, venture, "formation_date", None, "2026-05-01")
    _put(store, venture, "public_benefit", None, "PLANTEDPURPOSE")
    _put(store, venture, "registration.kind", "r1", "state-tax")
    _put(store, venture, "registration.due", "r1", "2026-12-01")

    pane = panes.pane_for(store, venture.MATTER, "primary", today=TODAY)

    timeline = {t["item_type"]: t["text"] for t in pane["application_timeline"]}
    assert timeline["application_submitted"] == "2026-06-01"
    assert timeline["interview_date"] == "2026-07-01"
    assert pane["application_state"]["text"] == "interview"

    company = {c["item_type"]: c["text"] for c in pane["company"]}
    assert company["entity_type"] == "pbc"
    assert company["formation_state"] == "DE"
    assert company["formation_date"] == "2026-05-01"
    # public_benefit is L3 and S1_LIST's ceiling is L3, so the gate renders
    # the payload — the same posture bankruptcy's L3 creditor.name takes on
    # the pane beside this one. The composer does not re-classify it
    # (`tests/test_panes.py::test_no_composer_reads_a_pack_schema_or_a_
    # derived_string`); if the purpose sentence is ever judged too specific
    # for a list surface, the rung moves in `venture.py`.
    assert company["public_benefit"] == "PLANTEDPURPOSE"

    registration = pane["registrations"][0]
    assert registration["fields"]["registration.kind"]["text"] == "state-tax"
    assert registration["fields"]["registration.due"]["text"] == "2026-12-01"

    assert pane["notice"] == venture.NOTICE


@pytest.mark.parametrize(
    "due,expect",
    [("2026-07-01", "overdue"), ("2026-08-15", "needs_attention"), ("2027-01-01", "nothing_due")],
)
def test_venture_pane_indicator_from_the_nearest_undone_registration_due(due, expect):
    store = Sidecar()
    _put(store, venture, "registration.due", "r1", due)
    pane = panes.pane_for(store, venture.MATTER, "primary", today=TODAY)
    assert pane["indicator"] == expect


def test_venture_pane_a_done_registration_drops_out_of_the_indicator():
    store = Sidecar()
    _put(store, venture, "registration.due", "r1", "2026-07-01")
    _put(store, venture, "registration.done", "r1", "2026-07-05")
    pane = panes.pane_for(store, venture.MATTER, "primary", today=TODAY)
    assert pane["indicator"] is None


@pytest.mark.parametrize(
    "field", ["annual_report_due", "franchise_tax_due", "business_license_due", "benefit_report_due"],
)
def test_venture_pane_indicator_reads_every_named_compliance_date(field):
    """These four have no `done` sibling of their own — each is always a
    candidate, unlike a registration."""
    store = Sidecar()
    _put(store, venture, field, None, "2026-07-01")
    pane = panes.pane_for(store, venture.MATTER, "primary", today=TODAY)
    assert pane["indicator"] == "overdue"


def test_venture_pane_indicator_is_none_with_nothing_on_file():
    pane = panes.pane_for(Sidecar(), venture.MATTER, "primary", today=TODAY)
    assert pane["indicator"] is None
    assert pane["registrations"] == [] and pane["founders"] == [] and pane["safes"] == []


def test_venture_pane_founders_safes_and_equity_grants_are_reference_rows_only():
    """Reference rows only — `"founder 1"`, `"SAFE 2 — signed 2027-01-05"` —
    never the group's own fields; the L4 content each row names renders
    only once that row's ref is opened on `S1_DETAIL`."""
    store = Sidecar()
    _put(store, venture, "founder.name", "1", "PLANTEDFOUNDER")
    _put(store, venture, "founder.role", "1", "CEO")
    _put(store, venture, "safe.investor", "2", "PLANTEDINVESTOR")
    _put(store, venture, "safe.signed", "2", "2027-01-05")
    _put(store, venture, "equity_grant.grantee", "3", "PLANTEDGRANTEE")

    pane = panes.pane_for(store, venture.MATTER, "primary", today=TODAY)
    blob = json.dumps(pane) + panes.pane_text(pane)

    for marker in ("PLANTEDFOUNDER", "PLANTEDINVESTOR", "PLANTEDGRANTEE",
                   "A founder is named", "A SAFE investor is on file",
                   "An equity grant recipient is on file", "CEO"):
        assert marker not in blob, marker

    (founder_row,) = pane["founders"]
    assert founder_row["text"] == "founder 1"
    assert founder_row["item_type"] == "founder.name"

    (safe_row,) = pane["safes"]
    assert safe_row["text"] == "SAFE 2 — signed 2027-01-05"

    (grant_row,) = pane["equity_grants"]
    assert grant_row["text"] == "equity grant 3"

    window = Window()
    window.open_list(instances.records_of(store, venture.MATTER, "primary"))
    ref = (venture.MATTER, founder_row["item_type"], founder_row["item_id"])
    assert window.open_detail(ref).value == "PLANTEDFOUNDER"


def test_venture_pane_a_founder_missing_its_name_field_gets_no_row():
    """A sub-record with no `founder.name` on file has nothing to open — it
    is skipped rather than shown as a row with a dead reference."""
    store = Sidecar()
    _put(store, venture, "founder.role", "1", "CTO")
    pane = panes.pane_for(store, venture.MATTER, "primary", today=TODAY)
    assert pane["founders"] == []


def test_venture_pane_never_carries_ein_anywhere():
    store = Sidecar()
    store.put(venture.MATTER, "ein", "primary", Classified(Rung.L5, "99-7654321"))
    pane = panes.pane_for(store, venture.MATTER, "primary", today=TODAY)
    blob = json.dumps(pane) + panes.pane_text(pane)
    assert "99-7654321" not in blob and "ein" not in blob

    from homestead_law.app import demo

    assert "99-7654321" not in demo.compose_panes(store, today=TODAY)


# ── the pack's own NOTICE reaches the pane verbatim ──────────────────────────

def test_grant_and_venture_panes_render_notice_verbatim():
    store = Sidecar()
    grant_pane = panes.pane_for(store, grant.MATTER, "primary", today=TODAY)
    venture_pane = panes.pane_for(store, venture.MATTER, "primary", today=TODAY)
    assert grant_pane["notice"] == grant.NOTICE
    assert venture_pane["notice"] == venture.NOTICE


# ── the PANES registry and pane_text ─────────────────────────────────────────

def test_grant_and_venture_are_in_the_pane_registry():
    assert panes.PANES[grant.MATTER] is panes.grant_pane
    assert panes.PANES[venture.MATTER] is panes.venture_pane


def test_pane_text_covers_both_new_shapes_without_raising():
    store = Sidecar()
    _put(store, grant, "milestone.name", "m1", "Phase 1")
    _put(store, venture, "founder.name", "1", "A. Founder")
    for mt in (grant.MATTER, venture.MATTER):
        text = panes.pane_text(panes.pane_for(store, mt, "primary", today=TODAY))
        assert mt in text


def test_demo_composes_both_new_panes():
    from homestead_law.app import demo

    text = demo.compose_panes(Sidecar(), today=TODAY)
    assert f"{grant.MATTER}/primary" in text
    assert f"{venture.MATTER}/primary" in text
    assert "Phase 1 report" in text  # grant's seeded milestone name (L3, renders)


# ── I-33 ────────────────────────────────────────────────────────────────────
# Both new panes are covered by `tests/test_i33_one_indicator.py`, which
# parametrizes over `panes.PANES` itself rather than a list of matters (this
# bite's audit, 2026-09-12) — the scalar-shape check and the
# no-second-indicator-shaped-key scan both reach grant and venture there, so
# the copies that stood here have been dropped rather than left to drift from
# the canonical ones. `tests/test_panes.py` holds the other half: the
# `state`/`application_state` key renames are cosmetic, and the row under
# either key is the pack's own `status`/`application_status` row.


# ── the plan-period flag, wired against the two real Wave 8 producers ───────

def _confirmed_bankruptcy(store: Sidecar, instance: str = "primary") -> None:
    store.put(bankruptcy.MATTER, "plan_confirmation_date", instance, Classified(Rung.L1, "2026-06-01"))


def test_grant_award_amount_shows_the_line_on_the_bankruptcy_pane_and_the_queue():
    store = Sidecar()
    _confirmed_bankruptcy(store)
    store.put(grant.MATTER, "award_amount", "primary",
              Classified(Rung.L3, "285000", "An award amount is on file"))

    pane = panes.pane_for(store, bankruptcy.MATTER, "primary", today=TODAY)
    assert len(pane["plan_period"]) == 1
    line = pane["plan_period"][0]
    assert line.startswith("bankruptcy/primary:")
    assert grant.MATTER not in line and "award_amount" not in line and "285000" not in line

    assert queue_mod.notices(store) == (line,)


def test_venture_safe_amount_shows_the_line_on_the_bankruptcy_pane_and_the_queue():
    store = Sidecar()
    _confirmed_bankruptcy(store)
    store.put(venture.MATTER, "safe.amount", "primary.s1",
              Classified(Rung.L4, "50000", "A SAFE amount is on file"))

    pane = panes.pane_for(store, bankruptcy.MATTER, "primary", today=TODAY)
    assert len(pane["plan_period"]) == 1
    line = pane["plan_period"][0]
    assert line.startswith("bankruptcy/primary:")
    assert venture.MATTER not in line and "safe.amount" not in line and "50000" not in line

    assert queue_mod.notices(store) == (line,)


def test_venture_revenue_start_also_shows_the_line():
    store = Sidecar()
    _confirmed_bankruptcy(store)
    store.put(venture.MATTER, "revenue_start", "primary", Classified(Rung.L1, "2026-07-01"))

    assert len(queue_mod.notices(store)) == 1


# ── XSS: a registration kind is refused at the closed set; a milestone ─────
# name renders unescaped through the API and is escaped only by the page

def test_a_hostile_registration_kind_is_refused_by_the_closed_set():
    hostile = "<script>alert(1)</script>"
    with pytest.raises(venture.InvalidChoice):
        venture.validate_value("registration.kind", hostile)


def test_a_hostile_milestone_name_reaches_the_pane_json_unescaped_but_the_page_escapes_it():
    """`app.panes` hands back plain text exactly as the gate served it
    (`tests/test_panes.py`'s own pinned contract) — escaping is the page's
    job. `milestone.name` is `L3` and renders in full at `S1_LIST`, so a
    hostile value reaches this composer's output unescaped; the served page
    must still only ever place it through `esc()` (`fieldRow`, shared by
    every card the page renders, `renderCards` included)."""
    from homestead_law import server

    hostile = "<script>alert(1)</script>"
    store = Sidecar()
    _put(store, grant, "milestone.name", "m1", hostile)

    pane = panes.pane_for(store, grant.MATTER, "primary", today=TODAY)
    assert pane["milestones"][0]["fields"]["milestone.name"]["text"] == hostile

    assert "esc(f.text)" in server._PAGE
    assert "esc(card.sub)" in server._PAGE


# ── renderRefRows escapes, and escapes through the one shared helper ────────

def test_render_ref_rows_places_every_value_through_esc():
    """`renderRefRows` is the one new page function L8-surfaces adds, and it
    builds markup by string concatenation like every other renderer on this
    page. Structural, over the served page: its body assigns nothing to
    `innerHTML`, and every fragment it appends either goes through `esc()`
    or through `fieldRow()` — the shared row renderer that escapes each of
    the five values it places. A raw `+r.text+` would fail both halves."""
    from homestead_law import server

    page = server._PAGE
    start = page.index("function renderRefRows(")
    end = page.index("\n}\n", start)
    body = page[start:end]

    assert "innerHTML" not in body
    assert "fieldRow(r)" in body
    fragments = [line for line in body.splitlines() if "html+=" in line or "return html+" in line]
    assert fragments, "the scan found no markup in renderRefRows"
    for fragment in fragments:
        assert "esc(" in fragment or "fieldRow(" in fragment, fragment


def test_a_hostile_safe_signed_date_rides_the_label_and_the_page_escapes_it():
    """`safe.signed` is the one *served value* `_ref_rows` folds into a row's
    synthesized label, and no closed set or shape check guards it — so it is
    the one place a hostile string can reach a reference row's text. It
    reaches the composer's output unescaped (escaping is the page's job,
    `tests/test_panes.py`'s pinned contract) and the page places it through
    `fieldRow`, which escapes it."""
    from homestead_law import server

    hostile = "<script>alert(1)</script>"
    store = Sidecar()
    _put(store, venture, "safe.investor", "s1", "An Investor")
    _put(store, venture, "safe.signed", "s1", hostile)

    pane = panes.pane_for(store, venture.MATTER, "primary", today=TODAY)
    (row,) = pane["safes"]
    assert row["text"] == f"SAFE s1 — signed {hostile}"
    assert row["rung"] == "L4"          # still the investor row's own ref
    assert "esc(f.text)" in server._PAGE


# ── an accepted template deadline is the queue's, not the pane's ────────────

def test_an_accepted_83b_deadline_reaches_the_queue_not_the_venture_pane():
    """The audit's own question, answered as a pin rather than a change.
    `rules.accept` writes `(venture, "deadline", "<inst>.election-83b")`, and
    **no** pane composes `deadline` records — not custody's, not
    bankruptcy's, and not these two: the Matter tab draws computed deadlines
    in its own section under the pane (`/api/deadline/templates`), and
    `queue.queue()` lists them across every matter with their own urgency.
    Giving venture alone a deadlines block on the pane would make it the one
    pack whose accepted deadline is badged twice on one screen. So the
    contract is that the record is surfaced, and where."""
    from homestead.keep.rungs import Classified as _Classified
    from homestead_law import rules

    store = Sidecar()
    store.put(venture.MATTER, "jurisdiction", "primary", _Classified(Rung.L1, "US-DE"))
    _put(store, venture, "grant_date", None, "2026-08-01")

    computed = rules.compute(store, venture.MATTER, "primary", "election-83b")
    rules.accept(store, computed, token=computed.preview_token)
    assert computed.result_iso == "2026-08-31"      # 30 calendar days, no roll

    pane = panes.pane_for(store, venture.MATTER, "primary", today=TODAY)
    blob = json.dumps(pane) + panes.pane_text(pane)
    assert "election-83b" not in blob and computed.result_iso not in blob
    assert pane["indicator"] is None

    (item,) = [q for q in queue_mod.queue(store, today=TODAY) if q.matter == venture.MATTER]
    assert item.ref == (venture.MATTER, "deadline", "primary.election-83b")
    assert item.shown == computed.result_iso
    assert item.days_until == 21 and item.overdue is False


# ── a pane judges only what it shows ────────────────────────────────────────

def test_every_date_the_indicator_judges_is_a_date_the_pane_renders():
    """The audit's finding, pinned. `venture_pane` used to read
    `annual_report_due`, `franchise_tax_due` and `business_license_due` for
    its badge while rendering none of them, so an instance carrying only a
    franchise-tax date drew a bare `[overdue]` over an empty pane — an
    urgency the operator could neither see nor act on. Every field either
    composer feeds to `_indicator_for_dates` is now a field its own rows
    render, proved by planting a distinct date in each and finding all of
    them in the pane's text."""
    dates = {}
    store = Sidecar()
    for i, field in enumerate(panes._VENTURE_INDICATOR_DATES):
        dates[field] = f"2027-0{i + 1}-15"
        _put(store, venture, field, None, dates[field])
    dates["registration.due"] = "2027-05-15"
    _put(store, venture, "registration.due", "r1", dates["registration.due"])

    text = panes.pane_text(panes.pane_for(store, venture.MATTER, "primary", today=TODAY))
    for field, value in dates.items():
        assert value in text, f"{field} feeds the indicator but is not on the pane"

    grant_dates = {"milestone.due": "2027-06-15", "report.due": "2027-07-15"}
    gstore = Sidecar()
    _put(gstore, grant, "milestone.due", "m1", grant_dates["milestone.due"])
    _put(gstore, grant, "report.due", "q3", grant_dates["report.due"])
    gtext = panes.pane_text(panes.pane_for(gstore, grant.MATTER, "primary", today=TODAY))
    for field, value in grant_dates.items():
        assert value in gtext, f"{field} feeds the indicator but is not on the pane"


def test_a_lone_franchise_tax_date_now_shows_the_row_behind_its_badge():
    """The exact instance the bug produced: one statutory date and nothing
    else. The badge and the row it is about must both be on the pane."""
    store = Sidecar()
    _put(store, venture, "franchise_tax_due", None, "2020-01-01")
    pane = panes.pane_for(store, venture.MATTER, "primary", today=TODAY)
    assert pane["indicator"] == "overdue"
    assert [c["item_type"] for c in pane["company"]] == ["franchise_tax_due"]
    assert "2020-01-01" in panes.pane_text(pane)
