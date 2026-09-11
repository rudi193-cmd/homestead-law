"""A synthetic custody matter, for seeing the surfaces work end to end (bite 4).

**Synthetic data only** — the plan holds real data until the ledger is wired, and
this writes to a throwaway store, never a real household root. It seeds one
custody matter into the sidecar and composes the list and a detail through the
gate, so the store → `serve` → surface pipeline can be run and read without a
display: `python -m homestead.app --demo`.

The values are invented; the rungs are the custody pack's, so what renders where
is the real crossing, not a mock. `courthouse`/`hearing_date` (L1) and `ssn` (L5)
carry no derived form; the L3/L4 fields carry one, because that is the human
re-identification judgement `Classified` requires and a pack does not author.

**`child.name`, not `child_name` (L9-child-name, 2026-09-11).** The demo used
to seed the retired singular field alongside every other `_DEMO` entry, at the
instance's single slot. `child_name` is gone from the pack's own `SCHEMA`/
`FIELDS` now, so `seed()` writes the child's name separately, the way a real
household would: under a sub-id (`"ar"`, Rivera's initials — a label, never a
name, I-15), giving the stored key `custody/child.name/primary.ar`. The list
and detail composition below is otherwise unchanged.
"""
from __future__ import annotations

from homestead.keep.rungs import Classified, Disposition, Rung
from homestead_law import instances
from homestead_law import queue as queue_mod
from homestead_law.app import panes as panes_mod
from homestead_law.app.window import Ref, Window
from homestead_law.packs import bankruptcy, custody, grant, venture, workers_comp
from homestead_law.registry import all_matters
from homestead_law.store import Sidecar

MATTER = custody.MATTER  # "custody"

#: A fixed reference date, so the seeded deadlines have stable urgency in the
#: demo. The running app uses the real today.
TODAY = "2026-08-10"

#: field → (payload, derived form or None). Invented content; real rungs.
_DEMO: dict[str, tuple[str, str | None]] = {
    "courthouse": ("Dept 4, Second Judicial District Court, Bernalillo County", None),
    "hearing_date": ("2026-09-15 08:30 · Dept 4", None),
    "case_number": ("FL-2026-00123", "A case number is on file"),
    "docket": ("Entry 14 — response filed 2026-08-01", "A docket entry is on file"),
    "opposing_party": ("Jordan Rivera", "The other parent is named"),
    "parenting_time": (
        "Tue/Thu 3-7pm, alternating weekends — minor A.R.",
        "A recurring parenting-time obligation on Tue/Thu",
    ),
    "diagnosis": ("ADHD (per IEP, 2026-03)", "A medical category is on file for a person"),
    "notes": (
        "Late to pickup twice this month; smelled of alcohol on the 3rd.",
        "An operator note is on file",
    ),
    "ssn": ("123-45-6789", None),
}

#: The one `_DEMO` field that moved off the single instance slot: `child.name`
#: is REPEATABLE (L9-child-name), so it is seeded at a sub-id rather than
#: folded into the loop above, which writes every other field at `"primary"`.
_CHILD_FIELD = "child.name"
_CHILD_SUB = "ar"
_CHILD_PAYLOAD = "A. Rivera, age 8"
_CHILD_DERIVED = "A child's name is on file"


#: deadline id → (rung, ISO date, instruction). A deadline's payload is the date;
#: its derived form is the instruction, shown on the ambient queue when the rung
#: withholds the date. Urgency is against TODAY (2026-08-10).
_DEADLINES: dict[str, tuple[Rung, str, str]] = {
    "answer": (Rung.L1, "2026-08-05", "Response to the petition"),         # overdue by 5
    "evaluation": (Rung.L4, "2026-08-12", "A submission is due"),          # due in 2 (L4 → derived)
    "mediation": (Rung.L3, "2026-08-18", "Mediation session"),            # due in 8
    "hearing": (Rung.L1, "2026-09-15", "Custody hearing"),                # due in 36
}


def seed(store: Sidecar) -> None:
    """Write the synthetic matter into the store, replacing any prior demo. Each
    `_DEMO` field becomes one record keyed `(custody, <field>, primary)`,
    classified at the pack's rung — plus `child.name`, REPEATABLE, keyed at a
    sub-id instead (see the module docstring)."""
    for field, (payload, derived) in _DEMO.items():
        rung = custody.FIELDS[field]
        store.put(MATTER, field, "primary", Classified(rung, payload, derived), overwrite=True)
    store.put(
        MATTER, _CHILD_FIELD, instances.item_id(instances.DEFAULT_INSTANCE, _CHILD_SUB),
        Classified(custody.FIELDS[_CHILD_FIELD], _CHILD_PAYLOAD, _CHILD_DERIVED),
        overwrite=True,
    )


def seed_deadlines(store: Sidecar) -> None:
    """Write the synthetic deadlines — the queue's input. Separate from `seed` so
    the field list in `compose_demo` stays fields-only.

    Each is keyed `(custody, "deadline", "primary.<name>")` — the same
    instance-addressed id the `deadline` door writes (decision 2). A demo that
    seeded the free-form ids this dict is named with would put four phantom
    instances into `instances.instances_of`, which is exactly the shape the
    real doors refuse: a demo store must look like a real one."""
    for name, (rung, date, instruction) in _DEADLINES.items():
        store.put(
            MATTER, "deadline", instances.item_id(instances.DEFAULT_INSTANCE, name),
            Classified(rung, date, instruction), overwrite=True,
        )


def open_matter(store: Sidecar) -> Window:
    """Load the matter from the store into a Window's list pane."""
    window = Window()
    window.open_list(store.records(MATTER))
    return window


def _ref(field: str) -> Ref:
    return (MATTER, field, "primary")


def compose_demo(store: Sidecar) -> str:
    """Seed, list, and open two items — a headless proof of the whole pipeline,
    returning the text a view would draw so it can be read without a display.

    It shows the list (L1-L3 payloads, L4 as its derived form, no L5), then opens
    the `child.name` detail (at its sub-id — see the module docstring) — where
    the L4 payload the list withheld now renders — and finally opens the sealed
    `ssn`, which the detail still denies."""
    seed(store)
    window = open_matter(store)

    lines = [f"{MATTER} — list (S1_LIST):"]
    for row in window.rows:
        lines.append(f"  [{row.rung.value}] {row.text}")

    child_ref = (MATTER, _CHILD_FIELD, instances.item_id(instances.DEFAULT_INSTANCE, _CHILD_SUB))
    served = window.open_detail(child_ref)
    shown = served.value if served.disposition is Disposition.RENDER else "(withheld)"
    lines.append(f"detail {_CHILD_FIELD} (S1_DETAIL): [{served.rung.value}] {shown}")

    sealed = window.open_detail(_ref("ssn"))
    lines.append(
        f"detail ssn (S1_DETAIL): {sealed.disposition.value} (value={sealed.value!r})"
    )
    return "\n".join(lines)


def compose_queue(store: Sidecar, today: str = TODAY) -> str:
    """Seed the deadlines and render the queue — the store→dates→gate pipeline for
    *what is due*, headless. Overdue first, then soonest; an L4 deadline shows its
    derived instruction, not its date; and the resting cover shows only what
    survives the re-identification check (I-31) — nothing at all while the
    demo's deadlines all sit in one matter, even though the queue itself has
    items."""
    seed_deadlines(store)
    lines = [f"{MATTER} — what's due, as of {today}:"]
    for item in queue_mod.queue(store, today=today):
        if item.gap:
            mark = "date unreadable"
        elif item.overdue:
            mark = f"overdue by {abs(item.days_until)} days"
        else:
            mark = f"due in {item.days_until} days"
        lines.append(f"  [{item.rung.value}] {item.shown} — {mark}")

    resting = queue_mod.cover(store, today=today)
    # "single matter" was the *reason* nothing survived while one pack was
    # built; with a second registered it can also be "no count reached the
    # anonymity floor". The line says what the cover does — shows nothing —
    # and names the invariant, rather than asserting a reason that stops being
    # the true one the day a second pack lands.
    lines.append(f"cover (resting): {resting or 'Nothing is open (I-31)'}")
    return "\n".join(lines)


# ── panes (L4-surfaces) — every registered pack, seeded minimally ───────────
#
# Separate from `seed()`'s `_DEMO` dict on purpose: that dict and the tests
# pinned to its exact field texts predate this bite, and adding a pane demo
# on top of it risks nothing already asserted. Custody already carries the
# fields its own pane reads (`registration_contest_deadline`, one child);
# bankruptcy and workers' comp get just enough of their own to show every
# pane shape — creditors/bar-dates/NOTICE, and an IME sub-record — composing
# through the real gate, invented content at the real rungs, same posture
# `seed()`'s own docstring states. Grant and venture (L8-surfaces) get the
# same minimal treatment: one milestone and a status for the grant pane, one
# registration and one founder for the venture pane — enough to show a card,
# a reference row and a state field without duplicating either pack's own
# closed-set values.

_PANE_INSTANCE = "primary"


#: What `seed_pane_demo` files, as data: `(pack, field, sub-or-None,
#: payload)`. A table rather than seven hand-written `store.put` calls — and
#: with neither the rung nor the derived form in it: both come off the pack's
#: own `FIELDS`/`SCHEMA` (decision 3), exactly as `seed()` already reads
#: them, so this demo has no way to classify a field differently from the
#: pack it is demonstrating.
_PANE_SEED = (
    (custody, "registration_contest_deadline", None, "2026-08-30"),
    (custody, "child.name", "c1", "A. Rivera"),
    (bankruptcy, "petition_date", None, "2026-01-15"),
    (bankruptcy, "claims_bar_date", None, "2026-03-26"),
    (bankruptcy, "creditor.name", "cred1", "First National Bank"),
    (workers_comp, "hcp_selection_date", None, "2026-02-01"),
    (workers_comp, "ime.date", "2026-05", "2026-05-12"),
    (grant, "status", None, "submitted"),
    (grant, "submission_deadline", None, "2026-09-30"),
    (grant, "milestone.name", "m1", "Phase 1 report"),
    (grant, "milestone.due", "m1", "2026-10-01"),
    (venture, "application_status", None, "submitted"),
    (venture, "application_submitted", None, "2026-06-01"),
    (venture, "registration.kind", "r1", "state-tax"),
    (venture, "registration.due", "r1", "2026-12-01"),
    (venture, "founder.name", "f1", "A. Founder"),
)


def seed_pane_demo(store: Sidecar) -> None:
    """Add just enough to `seed()`'s custody matter, plus a minimal
    bankruptcy and workers' comp instance, so `compose_panes` has something
    of every shape to compose. Idempotent, like `seed()`."""
    for pack, field, sub, payload in _PANE_SEED:
        store.put(
            pack.MATTER, field, instances.item_id(_PANE_INSTANCE, sub),
            Classified(pack.FIELDS[field], payload,
                       pack.SCHEMA[field].get("derived")),
            overwrite=True,
        )


def compose_panes(store: Sidecar, today: str = TODAY) -> str:
    """`app.panes.pane_for`, for every registered pack this demo seeds —
    headless proof that every pack composes a pane, and that the shape
    (children/creditors/exams) picks the rendering the same way
    `server.py`'s JS does, without a matter name literal anywhere in that
    dispatch (I-23)."""
    seed_pane_demo(store)
    # Every *registered* matter, not the three this function happens to seed
    # (I-23): a fourth pack composes here the day its registry entry lands,
    # through `pane_for`'s generic fallback, with no edit to this file. The
    # seed above is necessarily pack-shaped; the composition is not, and the
    # one that would have gone stale is the composition.
    sections = [
        panes_mod.pane_text(
            panes_mod.pane_for(store, name, _PANE_INSTANCE, today=today))
        for name in all_matters()
    ]
    return "panes:\n" + "\n".join(sections)
