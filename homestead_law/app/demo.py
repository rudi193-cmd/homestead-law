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
"""
from __future__ import annotations

from homestead.keep.rungs import Classified, Disposition, Rung
from homestead_law import instances
from homestead_law import queue as queue_mod
from homestead_law.app.window import Ref, Window
from homestead_law.packs import custody
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
    "child_name": ("A. Rivera, age 8", "A minor child is named in this matter"),
    "diagnosis": ("ADHD (per IEP, 2026-03)", "A medical category is on file for a person"),
    "notes": (
        "Late to pickup twice this month; smelled of alcohol on the 3rd.",
        "An operator note is on file",
    ),
    "ssn": ("123-45-6789", None),
}


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
    field becomes one record keyed `(custody, <field>, primary)`, classified at
    the pack's rung."""
    for field, (payload, derived) in _DEMO.items():
        rung = custody.FIELDS[field]
        store.put(MATTER, field, "primary", Classified(rung, payload, derived), overwrite=True)


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
    the `child_name` detail — where the L4 payload the list withheld now renders —
    and finally opens the sealed `ssn`, which the detail still denies."""
    seed(store)
    window = open_matter(store)

    lines = [f"{MATTER} — list (S1_LIST):"]
    for row in window.rows:
        lines.append(f"  [{row.rung.value}] {row.text}")

    served = window.open_detail(_ref("child_name"))
    shown = served.value if served.disposition is Disposition.RENDER else "(withheld)"
    lines.append(f"detail child_name (S1_DETAIL): [{served.rung.value}] {shown}")

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
