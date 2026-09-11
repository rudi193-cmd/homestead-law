"""The plan-period interaction flag (L3-bankruptcy-ch13, added 2026-09-11).

While a bankruptcy instance is **confirmed** (`plan_confirmation_date` is on
file) and **not yet discharged** (`discharge_date` is absent), new income, an
award, or an equity interest arising *anywhere else* in the household's
affairs is something 11 U.S.C. §§ 541(a)(7), 1306(a) and 1329 make relevant to
that plan — property of the estate continues to include post-petition
earnings and acquisitions during the plan (§ 1306(a)), and either a debtor or
a trustee may seek to modify the plan on account of them (§ 1329); the plan's
own terms and local rules commonly impose disclosure duties of their own.
None of that is a judgement this app may make. `flag()` reads two dates on
each confirmed-but-undischarged bankruptcy instance and scans every *other*
registered matter for a record of `SIGNAL_FIELDS` — none of which exist yet
(Wave 8's `grant`/`venture` packs are the producers) — and yields exactly one
reference line per such instance when at least one exists, cross-matter,
never through `.payload`, never carrying a value.

**A flag, not a refusal.** Nothing here blocks a `put`, a `deadline`, or
anything else; `flag()` is read-only over the store and has no write path at
all. It is offered to the queue as reference lines — see `queue.notices()`,
the one hook this bite adds there — never folded into a `QueueItem`'s date
arithmetic, because a flag with no date is not a deadline.

**Why `MATTER` is a module constant, and not the literal `"bankruptcy"` in a
comparison.** `tests/test_registry.py::test_no_module_outside_the_registry_
hardcodes_the_set_of_matters` (I-23) fails the build on a registered matter
name appearing as an element of a list/set/tuple literal, or as either side
of a comparison, outside the registry and the packs. This module is neither,
so every comparison against the bankruptcy matter goes through
`bankruptcy_pack.MATTER` — the pack's own name, read live, the same "the
registry cannot drift from the pack" reasoning `registry.py` already applies
one level up — never a second-hand string this module would be hand-keeping.
"""
from __future__ import annotations

from homestead.keep.rungs import Disposition, Surface, serve

from homestead_law import instances
from homestead_law.packs import bankruptcy as bankruptcy_pack
from homestead_law.registry import all_matters
from homestead_law.store import Sidecar

__all__ = ["SIGNAL_FIELDS", "flag"]

#: Item types, in any *other* matter, whose mere presence — never their value
#: — is the signal (Wave 8's producers, none built yet): `award_amount`/
#: `disbursement` from a grant, `safe`/`equity_grant`/`revenue_start` from a
#: venture. A frozenset of field names, not matter names, so it carries no
#: I-23 exposure of its own.
SIGNAL_FIELDS: frozenset[str] = frozenset(
    {"award_amount", "disbursement", "safe", "equity_grant", "revenue_start"}
)

#: This pack's own name, read once, live — never retyped as a literal in a
#: comparison (see the module docstring's I-23 note).
MATTER = bankruptcy_pack.MATTER


def _served_value(store: Sidecar, matter_name: str, item_type: str, instance: str):
    """`Served.value` for one field of one instance, or `None` if there is
    nothing to serve — absent outright, or present but denied (I-11's
    absence-fails-closed extended to "nothing rendered is nothing to read").
    Never `.payload`; this is the one door (`serve`) every reader in this
    package already trusts, the same one `jurisdiction.py` uses."""
    if not store.has(matter_name, item_type, instance):
        return None
    record = store.get(matter_name, item_type, instance)
    served = serve(record, Surface.S1_LIST)
    return served.value


def _any_signal_elsewhere(store: Sidecar) -> bool:
    """Whether *any* other registered matter holds a record whose item type is
    in `SIGNAL_FIELDS` and that renders or derives — never a payload read, and
    never which matter or field it was: a bool, nothing more. A record at
    `L5` (or otherwise denied) is dropped here exactly as `plan_period`'s own
    spec requires: the gate, not this module, decides what counts as
    present."""
    for matter_name in all_matters():
        if matter_name == MATTER:
            continue
        for ref, record in store.records(matter_name):
            if ref[1] not in SIGNAL_FIELDS:
                continue
            served = serve(record, Surface.S1_LIST)
            if served.disposition is not Disposition.DENY:
                return True
    return False


def flag(store: Sidecar) -> tuple[str, ...]:
    """One reference line per bankruptcy instance that is confirmed, not yet
    discharged, and sits alongside a `SIGNAL_FIELDS` record in some other
    matter — in `instances_of` order, empty when nothing qualifies.

    Reads `plan_confirmation_date` and `discharge_date` through the gate on
    `S1_LIST` via `Served.value` (never `.payload`), for every instance
    `instances.instances_of` names; both must actually render for an instance
    to qualify — an instance with no bankruptcy records at all, one that has
    not yet been confirmed, or one already discharged, contributes nothing.
    """
    lines: list[str] = []
    for instance in instances.instances_of(store, MATTER):
        confirmed = _served_value(store, MATTER, "plan_confirmation_date", instance)
        if confirmed is None:
            continue
        discharged = _served_value(store, MATTER, "discharge_date", instance)
        if discharged is not None:
            continue
        if _any_signal_elsewhere(store):
            lines.append(
                f"{MATTER}/{instance}: income or assets arising during the "
                "plan: confirm with your attorney (11 U.S.C. §§ 541(a)(7), "
                "1306(a), 1329; disclosure duties under the plan and local "
                "rules)"
            )
    return tuple(lines)
