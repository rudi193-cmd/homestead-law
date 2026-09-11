"""Per-matter-instance jurisdiction (decision 1) — no date arithmetic here.

A matter's forum is not fixed at the pack level (`MatterType.jurisdiction` is
only the *default*) — it is a fact about one *instance* of the matter (this
household's NM custody order, being registered in OR after the relocation, is
the case decision 1 is named for), stored alongside its other records at
`(matter, "jurisdiction", <instance>)` at the pack's own declared rung for
that field (L1 today) — read live, never assumed here.

**No calendar is imported.** The whole job is: accept a jurisdiction only from
the pack's own `JURISDICTIONS`, and read one back *through the gate* so
nothing downstream can compute from a jurisdiction it was never actually
shown — the one fact a later bite's counting rules will need first. That is
**provisional I-42**: *"jurisdiction absent → refuse."*

**Why the read goes through `serve()` rather than a bare store read.** The
store's own fail-closed rule reads a corrupted or unclassified blob as `L5`
(I-11, `store.py::_hydrate`), and nothing stops a bug or a test from writing a
`jurisdiction` record by hand at some other rung. `serve(record,
Surface.S1_LIST)` is the one door every reader in this package already trusts
for exactly this: only `Disposition.RENDER` means "readable as itself right
now", and a denied plant refuses identically to a genuinely missing record —
from an arithmetic caller's point of view, both are nothing to compute from.
"""
from __future__ import annotations

from homestead.keep.rungs import (
    Classified,
    Disposition,
    Rung,
    Surface,
    derived_of,
    serve,
)
from homestead.keep.store import Replaced

from homestead_law import instances
from homestead_law.registry import matter
from homestead_law.store import Sidecar

__all__ = [
    "ITEM_TYPE",
    "JurisdictionAbsent",
    "UnsupportedJurisdiction",
    "set_jurisdiction",
    "jurisdiction_of",
]

#: The item type a jurisdiction is filed under — one per instance, the pack's
#: own `"jurisdiction"` field (custody declares it L1; decision 1).
ITEM_TYPE = "jurisdiction"


class UnsupportedJurisdiction(ValueError):
    """A code outside `matter(name).jurisdictions`.

    The attempted code is named in the message (unlike an id — see
    `instances.InvalidId`): a jurisdiction code is not yet stored anywhere,
    and once accepted it is filed at L1, the pack's own public-forum rung
    (decision 1's "the forum's identity is public in this matter's forum").
    Echoing a rejected attempt at it is the same courtesy `_cmd_put`'s
    "unknown field" refusal already extends to a mistyped field name — a
    reference to a closed, published set the pack declares, not L3+ content."""


class JurisdictionAbsent(LookupError):
    """Provisional I-42: an instance with no jurisdiction the gate will render.

    Raised identically whether the record is missing outright or present but
    denied (a hand-planted `L5` jurisdiction, or any disposition other than
    `RENDER`) — from the point of view of "is there a jurisdiction to compute
    a deadline under", those are the same absence, and I-11 says absence
    refuses by name rather than by picking a rung to guess with. The message
    names the matter and the instance and says what to run; it never carries
    record content, because there is none to carry — the whole point of this
    exception is that nothing was rendered."""

    def __init__(self, matter_name: str, instance_id: str) -> None:
        super().__init__(
            f"{matter_name}/{instance_id}: no jurisdiction is on file. Run "
            f"`homestead-law matter open {matter_name} --id {instance_id} "
            "--jurisdiction <code>` before computing anything from a date in "
            "this instance."
        )
        self.matter = matter_name
        self.instance = instance_id


def set_jurisdiction(
    store: Sidecar,
    matter_name: str,
    instance: str,
    code: str,
    *,
    replace: bool = False,
) -> Replaced | None:
    """Declare `instance`'s jurisdiction.

    Refuses, before writing anything:

    * a malformed `instance` id (`instances.InvalidId`, naming the component);
    * an unregistered `matter_name` (`KeyError`, `registry.matter`'s own);
    * a `code` outside `matter(matter_name).jurisdictions`
      (`UnsupportedJurisdiction`, naming the offered set).

    Refuses an already-open instance unless `replace=True` — not a rule this
    module invents, but the store's own I-9: `Sidecar.put(overwrite=False)`
    raises `RecordExists` on an occupied key, and "opening" the same instance
    twice without saying so is exactly the unconsented overwrite that rule
    already forbids everywhere else in this package.
    """
    instance = instances.item_id(instance)
    mt = matter(matter_name)
    if not isinstance(code, str) or code not in mt.jurisdictions:
        raise UnsupportedJurisdiction(
            f"{matter_name}: {code!r} is not one of this matter's "
            f"jurisdictions {mt.jurisdictions}"
        )
    rung = mt.fields["jurisdiction"]
    derived = (
        derived_of(mt.schema, "jurisdiction") if rung in (Rung.L3, Rung.L4) else None
    )
    item = Classified(rung, code, derived)
    return store.put(matter_name, ITEM_TYPE, instance, item, overwrite=replace)


def jurisdiction_of(store: Sidecar, matter_name: str, instance: str) -> str:
    """The jurisdiction code for `instance`, read through the gate.

    Served on `S1_LIST` — `serve()`, `Served.value`, never `.payload` (I-16) —
    and refused (`JurisdictionAbsent`, provisional I-42) unless the
    disposition is `RENDER`. **Anything that will do date arithmetic on a
    record in this instance must call this first**: an anchor date counted
    under an assumed jurisdiction is a guess about *which rules to count
    under*, and I-2's refusal-over-guessing already governs the date itself —
    this is that same rule one step earlier, applied to the forum.
    """
    instance = instances.item_id(instance)
    if not store.has(matter_name, ITEM_TYPE, instance):
        raise JurisdictionAbsent(matter_name, instance)
    record = store.get(matter_name, ITEM_TYPE, instance)
    served = serve(record, Surface.S1_LIST)
    if served.disposition is not Disposition.RENDER:
        raise JurisdictionAbsent(matter_name, instance)
    return str(served.value)
