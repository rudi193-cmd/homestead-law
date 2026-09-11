"""Per-pack panes — the pane registry (L4-surfaces, wave 4).

A **pane composer** is a plain function: `(store, matter_name, instance) ->
dict`. It reads through the gate exactly as `Window` does (this module lives
under `app/`, so the chokepoint's reflection ban and payload ban both apply —
see `tests/test_chokepoint.py`) and returns **plain data** — strings, lists,
dicts, no `Row`/`Rung` objects — so a caller (the browser's `/api/pane`, the
tkinter view, a test) renders it without importing anything from this
package's gate machinery. Composers are headless: no display, no HTTP, no I/O
beyond the store, which is why the tests call them directly rather than
driving the whole page.

**I-23, one level down from the matter registry.** `PANES` is keyed by each
pack's own `MATTER` constant — an attribute read, never a literal string — so
this file carries none of the enumeration the registry already forbids
elsewhere. `pane_for` falls back to `generic_pane` for any matter `PANES`
does not name, whether or not that matter is registered at all: a matter with
a pack but no dedicated pane gets the same generic list a wholly unknown name
would, so a newly registered pack renders *something* the day it lands, with
no change to this file required to avoid a crash.

**I-33 — one indicator per pane.** Every composer below returns exactly one
`"indicator"` key: `None`, or one of `"overdue"`, `"needs_attention"`,
`"nothing_due"` — a single scalar, not a list, so the shape itself rules out
a pane showing two badges. It is computed from dates *this pane already
served* (registration-contest and mediation dates for custody; the two bar
dates for bankruptcy) — never a second read of anything, and never a value
above the rung the pane's own rows already rendered.
"""
from __future__ import annotations

from typing import Callable

from homestead.keep.dates import Deadline, UnparseableDate

from homestead_law import instances
from homestead_law.app.window import Row, Window
from homestead_law.packs import bankruptcy, custody, workers_comp
from homestead_law.store import Sidecar

__all__ = [
    "PANES", "pane_for", "pane_text", "custody_pane", "bankruptcy_pane",
    "workers_comp_pane", "generic_pane",
]

PaneComposer = Callable[..., dict]


def _rows(store: Sidecar, matter_name: str, instance: str) -> list[Row]:
    """This instance's records, gated exactly as the list pane is (`S1_LIST`):
    L1-L3 render, L4 derives, L5 leaves no row. `instances.records_of` is the
    key-only filter; `Window` is the one place this module calls the gate."""
    return Window().open_list(instances.records_of(store, matter_name, instance))


def _row_dict(row: Row) -> dict:
    """A `Row`, as plain data — `Rung` becomes its string value, `ref` becomes
    the three strings a caller needs to open the detail (a reference, I-15)."""
    return {
        "matter": row.ref[0], "item_type": row.ref[1], "item_id": row.ref[2],
        "rung": row.rung.value, "text": row.text,
    }


def _plain(rows: list[Row]) -> dict[str, Row]:
    """This instance's own (non-repeatable) fields — item type -> row, for the
    rows whose item id carries no sub."""
    return {
        r.ref[1]: r for r in rows
        if instances.split_item_id(r.ref[2])[1] is None
    }


def _grouped(rows: list[Row], prefix: str) -> dict[str, dict[str, Row]]:
    """Every `<prefix>.<field>` row, grouped by sub id — one dict per
    sub-record (one child, one creditor, one exam), each holding its own
    fields by item type. A row with no sub is not part of any group (it is a
    matter-level field, not a repeatable one, even if its name happened to
    start with the prefix)."""
    groups: dict[str, dict[str, Row]] = {}
    for row in rows:
        item_type = row.ref[1]
        if not item_type.startswith(prefix + "."):
            continue
        sub = instances.split_item_id(row.ref[2])[1]
        if sub is None:
            continue
        groups.setdefault(sub, {})[item_type] = row
    return groups


def _cards(groups: dict[str, dict[str, Row]]) -> list[dict]:
    """`_grouped`'s output, as plain data, one card per sub id, sorted so the
    order does not depend on dict iteration."""
    return [
        {"sub": sub, "fields": {ft: _row_dict(r) for ft, r in fields.items()}}
        for sub, fields in sorted(groups.items())
    ]


def _indicator_for_dates(dates: list[str], *, today: str) -> str | None:
    """`"overdue"` / `"needs_attention"` (<=14 days) / `"nothing_due"`, from
    the nearest of a handful of ISO-ish date strings **already through the
    gate** — never a second read. `None` when there is nothing to judge: an
    empty list, or every string unparseable (a free-text field the operator
    has not yet filled with a real date; this is a display nicety, not the
    queue's own gap tracking, so an unparseable date here is silently
    skipped rather than flagged). A single return value, by construction —
    the whole of how this module holds I-33: a scalar cannot become two
    badges no matter how many dates were judged."""
    worst: Deadline | None = None
    for text in dates:
        try:
            parsed = Deadline.from_text(text, today=today)
        except UnparseableDate:
            continue
        if worst is None or parsed.days_until < worst.days_until:
            worst = parsed
    if worst is None:
        return None
    if worst.overdue:
        return "overdue"
    if worst.days_until <= 14:
        return "needs_attention"
    return "nothing_due"


#: The relocation-timeline fields, as served, in the order the household's
#: own timeline runs.
_CUSTODY_TIMELINE = (
    "custody_order_date", "relocation_notice_date", "move_date",
    "uccjea_registration_date", "registration_contest_deadline",
    "mediation_date",
)
#: The two still-upcoming dates on that timeline — a filed order date and a
#: past notice date are not something a badge should call "overdue".
_CUSTODY_INDICATOR_FIELDS = ("registration_contest_deadline", "mediation_date")


def custody_pane(
    store: Sidecar, matter_name: str, instance: str, *, today: str,
) -> dict:
    """Children (one card per `child.*` sub-record, served) and the
    relocation timeline. `matter_name` is accepted rather than hardcoded to
    `custody.MATTER` so `pane_for`'s dispatch stays uniform across
    composers; every real caller passes `custody.MATTER`."""
    rows = _rows(store, matter_name, instance)
    plain = _plain(rows)
    timeline = [_row_dict(plain[f]) for f in _CUSTODY_TIMELINE if f in plain]
    indicator = _indicator_for_dates(
        [plain[f].text for f in _CUSTODY_INDICATOR_FIELDS if f in plain],
        today=today,
    )
    return {
        "matter": matter_name,
        "instance": instance,
        "children": _cards(_grouped(rows, "child")),
        "timeline": timeline,
        "indicator": indicator,
    }


#: The two Chapter 13 bar dates a household's own calendar turns on.
_BANKRUPTCY_BAR_FIELDS = ("claims_bar_date", "governmental_claims_bar_date")


def bankruptcy_pane(
    store: Sidecar, matter_name: str, instance: str, *, today: str,
) -> dict:
    """Creditors/claims (one row per `creditor.*` sub-record, served), the
    bar-date countdown (arithmetic on the L1 date the gate already
    rendered — a countdown, not a new read), the `NOTICE` sentence
    verbatim, and this instance's plan-period reference lines
    (`homestead_law.plan_period.flag`, surfaced through `queue.notices`)."""
    from homestead_law import queue as queue_mod

    rows = _rows(store, matter_name, instance)
    plain = _plain(rows)
    bar_dates = []
    for field in _BANKRUPTCY_BAR_FIELDS:
        if field not in plain:
            continue
        row = plain[field]
        entry = {"field": field, "date": row.text, "gap": True,
                 "days_until": None, "overdue": None}
        try:
            parsed = Deadline.from_text(row.text, today=today)
        except UnparseableDate:
            pass
        else:
            entry.update(gap=False, days_until=parsed.days_until,
                         overdue=parsed.overdue)
        bar_dates.append(entry)
    indicator = _indicator_for_dates(
        [plain[f].text for f in _BANKRUPTCY_BAR_FIELDS if f in plain],
        today=today,
    )
    prefix = f"{matter_name}/{instance}:"
    plan_period = [
        line for line in queue_mod.notices(store) if line.startswith(prefix)
    ]
    return {
        "matter": matter_name,
        "instance": instance,
        "creditors": _cards(_grouped(rows, "creditor")),
        "bar_dates": bar_dates,
        "notice": bankruptcy.NOTICE,
        "plan_period": plan_period,
        "indicator": indicator,
    }


#: The two flat fields on the treatment timeline, beside the repeatable exams.
_WORKERS_COMP_TIMELINE = ("hcp_selection_date", "mmi_date")


def workers_comp_pane(
    store: Sidecar, matter_name: str, instance: str, *, today: str,
) -> dict:
    """The treatment/IME timeline: `ime.*` sub-records, plus
    `hcp_selection_date`/`mmi_date`, all served — every one of these fields
    is `L4`, so what this pane ever holds is the derived sentence, never a
    date to judge urgency from; the indicator is always `None`."""
    rows = _rows(store, matter_name, instance)
    plain = _plain(rows)
    return {
        "matter": matter_name,
        "instance": instance,
        "exams": _cards(_grouped(rows, "ime")),
        "timeline": [_row_dict(plain[f]) for f in _WORKERS_COMP_TIMELINE if f in plain],
        "indicator": None,
    }


def generic_pane(
    store: Sidecar, matter_name: str, instance: str, *, today: str,
) -> dict:
    """The fallback: every one of this instance's rows, served, with no
    pack-specific grouping — what a matter with no dedicated pane gets,
    whether or not it is even registered (`pane_for` never checks)."""
    rows = _rows(store, matter_name, instance)
    return {
        "matter": matter_name,
        "instance": instance,
        "rows": [_row_dict(r) for r in rows],
        "indicator": None,
    }


#: Keyed by each pack's own `MATTER` — an attribute read, never a literal
#: string, so this table carries none of the hand-kept-enumeration shape
#: `tests/test_registry.py`'s I-23 scan forbids elsewhere in this package.
PANES: dict[str, PaneComposer] = {
    custody.MATTER: custody_pane,
    bankruptcy.MATTER: bankruptcy_pane,
    workers_comp.MATTER: workers_comp_pane,
}


def pane_for(
    store: Sidecar, matter_name: str, instance: str, *, today: str | None = None,
) -> dict:
    """The composed pane for `matter_name`/`instance` — `PANES[matter_name]`
    if this pack has one, else `generic_pane`. Every registered matter has a
    pane one way or the other (`all_matters()` is read only for that
    guarantee to hold in a test, never here — this function itself does not
    need the registry to answer "which composer")."""
    if today is None:
        import datetime as dt

        today = dt.date.today().isoformat()
    composer = PANES.get(matter_name, generic_pane)
    return composer(store, matter_name, instance, today=today)


def _card_lines(label: str, cards: list[dict]) -> list[str]:
    """One `_cards()` entry per line-group — the same shape for a child, a
    creditor and an exam, so `pane_text` renders all three through one
    function rather than three copies that can drift."""
    lines = []
    for card in cards:
        lines.append(f"  {label} {card['sub']}:")
        for field_type, field in sorted(card["fields"].items()):
            lines.append(f"    {field_type}: {field['text']}")
    return lines


def _timeline_lines(rows: list[dict]) -> list[str]:
    return [f"  {row['item_type']}: {row['text']}" for row in rows]


def pane_text(pane: dict) -> str:
    """A pane composed by `pane_for`, as a few lines of plain text — the tk
    view's own rendering (`app/view.py`'s `show_list`), and a headless way
    to check a composer's output with no display attached. Shape-dispatched
    exactly as `pane_for` and the browser's JS are, so a fourth pack shape
    added later renders here as the generic fallback with no change to this
    function, the same guarantee `pane_for` already holds."""
    lines = [f"{pane['matter']}/{pane['instance']}"]
    if pane.get("indicator"):
        lines.append(f"  [{pane['indicator']}]")
    if "children" in pane:
        lines += _card_lines("child", pane["children"])
        lines += _timeline_lines(pane["timeline"])
    elif "creditors" in pane:
        lines.append(f"  {pane['notice']}")
        lines += _card_lines("creditor", pane["creditors"])
        for bar in pane["bar_dates"]:
            if bar["gap"]:
                mark = "unreadable"
            elif bar["overdue"]:
                mark = f"overdue by {abs(bar['days_until'])}d"
            else:
                mark = f"in {bar['days_until']}d"
            lines.append(f"  {bar['field']}: {bar['date']} ({mark})")
        for note in pane["plan_period"]:
            lines.append(f"  note: {note}")
    elif "exams" in pane:
        lines += _timeline_lines(pane["timeline"])
        lines += _card_lines("exam", pane["exams"])
    else:
        lines += _timeline_lines(pane["rows"])
    return "\n".join(lines)
