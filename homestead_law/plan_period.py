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
registered matter for a record of `SIGNAL_FIELDS` — `homestead_law.packs.
grant` (L8-grant) is the first producer built; the venture side of Wave 8 is
not yet built — and yields exactly one reference line per such instance when
at least one exists, cross-matter, never through `.payload`, never carrying
a value.

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
#: — is the signal: `award_amount`/`disbursement.amount`/
#: `disbursement.received` from a grant (`packs/grant.py`, L8-grant),
#: `safe.amount`/`equity_grant.amount`/`revenue_start` from a venture
#: (`packs/venture.py`, L8-venture). A frozenset of field names, not matter
#: names, so it carries no I-23 exposure of its own.
#:
#: **Every name is dotted where its group is `REPEATABLE` (decision 2).** The
#: plan paragraph names the *groups* — `"safe"`, `"equity_grant"`,
#: `"disbursement"` — and no record is ever stored under a bare group name: a
#: repeatable group is one composed `Classified` per sub-id, addressed
#: `safe.amount`, `disbursement.received` and so on. A set naming the bare
#: group would match nothing a real pack writes, and this consumer would
#: silently never fire — `_any_signal_elsewhere` compares `ref[1]` exactly.
#: So each group contributes the member that actually carries money or its
#: arrival, and nothing else: a scheduling date or a ledger reference is
#: neither new income nor an asset.
#:
#: `grant.disbursement` contributes `disbursement.amount` (a tranche's
#: amount) and `disbursement.received` (the date a tranche actually landed,
#: which alone marks an asset having arrived even on a record silent about
#: the amount); `disbursement.expected` and `disbursement.account_label` are
#: scheduling and a ledger reference. `venture.safe`/`venture.equity_grant`
#: contribute their `.amount` each.
#:
#: **`safe.amount`/`equity_grant.amount`, not the bare `"safe"`/
#: `"equity_grant"` (L8-venture).** Both groups are `REPEATABLE` (decision
#: 2), so no field is ever written under the bare group name, and
#: `_any_signal_elsewhere`'s `ref[1] not in SIGNAL_FIELDS` check needs the
#: dotted name to be exact. `revenue_start` needs no correction: venture's
#: one top-level, non-repeatable signal field.
#:
#: **One entry per line, sorted.** Two Wave 8 bites add producers to this one
#: literal in parallel; a packed line is a merge conflict inside a line,
#: while a sorted one-per-line set merges as a plain union.
SIGNAL_FIELDS: frozenset[str] = frozenset(
    {
        "award_amount",
        "disbursement.amount",
        "disbursement.received",
        "equity_grant.amount",
        "revenue_start",
        "safe.amount",
    }
)

#: This pack's own name, read once, live — never retyped as a literal in a
#: comparison (see the module docstring's I-23 note).
MATTER = bankruptcy_pack.MATTER


def _on_file(store: Sidecar, matter_name: str, item_type: str, instance: str) -> bool:
    """Whether one field of one instance is on file **and actually renders**
    on `S1_LIST` — `Disposition.RENDER`, not merely a non-`None` `.value`.

    The distinction is the whole of I-11 here. A `plan_confirmation_date`
    hand-stored at `L4` (the wrong rung, by hand or by a corrupt row read
    back under I-11's fail-closed rule) does not render: the gate hands back
    `DERIVE` and the derived *form* — "A confirmation date is on file" — a
    perfectly non-`None` string that is not a date and was never read. Taking
    it as proof of confirmation would be this module inferring a case's
    posture from a sentence the gate wrote to avoid showing it one. So a
    field that does not render is treated as **absent**, exactly as if the
    row were missing, and the two conditions fail closed in the two
    directions that keep the flag honest: an unrendered confirmation date
    means "not shown to be confirmed" (no line), an unrendered discharge date
    means "not shown to be discharged" (the line stands). The sibling
    `rules.compute` reads an anchor the same way — a derived `L4` is
    `AnchorUnavailable` there, not a value.

    Never `.payload`; `serve` is the one door every reader in this package
    already trusts, the same one `jurisdiction.py` uses."""
    if not store.has(matter_name, item_type, instance):
        return False
    served = serve(store.get(matter_name, item_type, instance), Surface.S1_LIST)
    return served.disposition is Disposition.RENDER


def _any_signal_elsewhere(store: Sidecar) -> bool:
    """Whether *any* other registered matter holds a record whose item type is
    in `SIGNAL_FIELDS` and that renders or derives — never a payload read, and
    never which matter or field it was: a bool, nothing more. A record at
    `L5` (or otherwise denied) is dropped here exactly as `plan_period`'s own
    spec requires: the gate, not this module, decides what counts as
    present.

    **`DERIVE` counts here and does not in `_on_file`, and the asymmetry is
    the point.** The two helpers ask different questions. There: is this
    date on file and readable as a date? — a derived form is not one. Here:
    does a record of this kind exist at all? — and "an award amount is on
    file" answers that in as many words, without this module ever learning
    the amount. Presence, never value, is the whole signal (§§ 541(a)(7),
    1306(a)), so the rung a producer chose for it must not decide whether
    the household is reminded that it exists."""
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
    `S1_LIST` (never `.payload`), for every instance `instances.instances_of`
    names; the confirmation date must actually render for an instance to
    qualify — an instance with no bankruptcy records at all, one that has not
    yet been confirmed, or one already discharged, contributes nothing. Two
    bankruptcy instances (a dismissed case and a refiling is the ordinary
    way that happens) are two independent asks, so each confirmed and
    undischarged one gets its own line.

    The store is scanned for signals **once**, before the loop, not once per
    instance: whether a signal exists anywhere else is a fact about the
    household, not about an instance, and the number of signals never
    changes the number of lines — three signals and one signal both mean
    "there is something to confirm", said once per instance.
    """
    if not _any_signal_elsewhere(store):
        return ()
    lines: list[str] = []
    for instance in instances.instances_of(store, MATTER):
        if not _on_file(store, MATTER, "plan_confirmation_date", instance):
            continue
        if _on_file(store, MATTER, "discharge_date", instance):
            continue
        lines.append(
            f"{MATTER}/{instance}: income or assets arising during the "
            "plan: confirm with your attorney (11 U.S.C. §§ 541(a)(7), "
            "1306(a), 1329; disclosure duties under the plan and local "
            "rules)"
        )
    return tuple(lines)
