"""The urgent queue — what the season owes, across every matter.

*A homesteader knows what the season owes.* This is that: the deadlines across a
household's matters, sorted by what needs a hand first. It is also the module
BUG-6 was about — the predecessor's urgent queue hardcoded its matter list and
workers' comp fell out of it, never iterated. This one calls `all_matters()`
(the registry, I-23) and nothing else, so a matter type that exists is a matter
type the queue reaches, by construction.

**It reaches no payload.** The store is the payload boundary: `Sidecar.deadlines`
parses each date and serves the display there, handing back `Due`s. The queue
computes urgency over the parsed date, sorts, and counts — it never sees a raw
payload, and the chokepoint holds.

**Urgency is operational; the specifics are gated.** `days_until` and `overdue`
are computed from the date so the queue can order and count. What the operator
*sees* for each item is the `Due`'s `shown` — the date for `L1`–`L3`, the derived
instruction for `L4` — already through the gate. A sealed (`L5`) deadline is not
in the queue at all. And a deadline whose stored date will not parse is a **gap**
(I-8): surfaced at the top, flagged, never silently dropped.

The **cover** counts (I-31) are the queue's aggregate passed through the
re-identification check, so the resting screen shows a number only where it
reveals nothing about which matter it came from.
"""
from __future__ import annotations

from dataclasses import dataclass

from homestead.keep.dates import Deadline
from homestead.keep.rungs import Rung

from homestead_law import instances
from homestead_law.app.cover import cover_counts
from homestead_law.registry import all_matters
from homestead_law.store import Due, Ref, Sidecar

__all__ = ["QueueItem", "queue", "counts", "cover", "notices"]


@dataclass(frozen=True)
class QueueItem:
    """One line of the queue: which matter and instance, the reference to open
    it, the gated display, and the urgency. `days_until` is `None` for a gap
    (an unparseable date), and `gap` is why.

    `instance` names the matter *instance* this deadline belongs to (decision
    2) — `instances.split_item_id(ref[2])[0]`, a reference exactly as `matter`
    and `ref` already are (I-15), never content. A deadline stored before this
    bite (a bare label with no dot) reads as its own instance here — the
    honest answer for a string this module cannot know was ever meant to
    carry one."""

    matter: str
    instance: str
    ref: Ref
    rung: Rung
    shown: str
    overdue: bool
    days_until: int | None
    gap: bool


def _urgency(due: Due, today: str) -> tuple[int | None, bool]:
    """`(days_until, overdue)` for a `Due`, or `(None, False)` for a gap. The date
    was validated on the way out of the store, so re-parsing it against `today`
    cannot fail here."""
    if due.gap or due.iso is None:
        return None, False
    deadline = Deadline.from_text(due.iso, today=today)
    return deadline.days_until, deadline.overdue


def _sort_key(item: QueueItem) -> tuple[int, int]:
    """Gaps first — a deadline that cannot be assessed needs a hand before any
    that can (I-8). Then by `days_until` ascending: the most overdue (most
    negative) first, then the soonest upcoming."""
    if item.gap:
        return (0, 0)
    return (1, item.days_until if item.days_until is not None else 0)


def queue(store: Sidecar, *, today: str) -> list[QueueItem]:
    """Every matter's deadlines, in one list, ordered by what needs acting on
    first. Iterates `all_matters()` — so a newly registered matter's deadlines
    appear here with no change to this function (the BUG-6 fix)."""
    items: list[QueueItem] = []
    for matter in all_matters():
        for due in store.deadlines(matter):
            days_until, overdue = _urgency(due, today)
            items.append(
                QueueItem(
                    matter=matter,
                    instance=instances.split_item_id(due.ref[2])[0],
                    ref=due.ref,
                    rung=due.rung,
                    shown=due.shown,
                    overdue=overdue,
                    days_until=days_until,
                    gap=due.gap,
                )
            )
    items.sort(key=_sort_key)
    return items


def counts(store: Sidecar, *, today: str, soon_days: int = 14) -> dict[str, int]:
    """The raw aggregate — `overdue` and `due_soon` across all matters — before
    re-identification. `due_soon` is a not-yet-overdue deadline falling within
    `soon_days`. Gaps count as neither; an unassessable deadline is surfaced in
    `queue()`, not folded into a number."""
    overdue = 0
    due_soon = 0
    for item in queue(store, today=today):
        if item.gap:
            continue
        if item.overdue:
            overdue += 1
        elif item.days_until is not None and item.days_until <= soon_days:
            due_soon += 1
    return {"overdue": overdue, "due_soon": due_soon}


def cover(store: Sidecar, *, today: str, soon_days: int = 14) -> dict[str, int]:
    """The counts the resting cover may show — the aggregate passed through the
    re-identification check (I-31), so a number appears only where it reveals
    nothing about which matter it came from. Over a single-matter household this
    is empty, and the cover rests on 'Nothing is open'.

    The roster handed to the check is **the matters this household actually has
    a deadline in**, not every matter type the registry knows about. `cover.py`
    says what it is being handed: *"`matters` is the roster of open matters"*,
    and its second gate is *"with a single open matter, the household is that
    matter"*. Registered types are not open matters — the registry is the same
    list on every install, so passing it would let the second gate be satisfied
    by the *software's* shape rather than the household's, and a household with
    one live matter would start showing counts the moment a second pack shipped.
    That is the second-pack readiness failure in the one place it would have
    been silent: nothing breaks, a number simply appears. Derived from the
    queue, so a matter with records but no deadline does not inflate the roster
    for a deadline count either.

    It is still the weaker of the two available checks: a roster of two says the
    count *could* be spread across both, not that it is. `(2, 0)` passes here.
    The engine's `cover_counts` is explicit that it cannot tell `(2,0)` from
    `(1,1)` without the per-matter distribution, and closing that is the
    distribution argument a later engine bite adds; until then this narrows the
    roster to the truth it can establish today.
    """
    items = queue(store, today=today)
    open_matters = sorted({item.matter for item in items})
    return cover_counts(
        open_matters, **counts(store, today=today, soon_days=soon_days)
    )


def notices(store: Sidecar) -> tuple[str, ...]:
    """Reference lines from every consumer that flags a cross-matter
    interaction rather than a deadline — today, only
    `homestead_law.plan_period.flag` (L3-bankruptcy-ch13's plan-period
    interaction flag; Wave 8 wires the producers). A line here is never a
    `QueueItem`: it carries no date, so it cannot be sorted by urgency or
    dropped by the gap/sealed rules above without inventing a date it does
    not have — a tuple of strings the CLI and the app print after the queue
    instead, the smallest change that shows them on the queue without
    stretching `QueueItem`'s own contract to a shape it was not built for.
    Imported lazily so a module with no cross-matter consumer of its own pays
    nothing to import this one."""
    from homestead_law import plan_period

    return plan_period.flag(store)
