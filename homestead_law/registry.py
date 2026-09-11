"""The matter-type registry — the one enumeration of what a household handles.

I-23: **the registry is the only enumeration.** Anything that touches "all
matters" iterates this, and nothing keeps a matter list of its own. That is not
tidiness; it is the direct answer to BUG-6.

## BUG-6, which is why this file exists

The predecessor advertised three matter types and enumerated them by hand in
three separate places — navigation, the urgent queue, and the briefing. The
three lists drifted, and workers' comp — one of the three — was structurally
absent from the urgent queue: not filtered out, not deprioritised, *never
iterated*. A deadline in a workers'-comp matter could not become urgent because
the loop that raised urgency did not know the matter type existed. No test
caught it, because every test that asked "are all matters handled?" asked its
own hand-kept list the same wrong question.

A single enumeration cannot drift from itself. `all_matters()` is that
enumeration, `REGISTRY` is what it iterates, and the guard below makes a matter
that exists but is not registered — BUG-6's exact shape, a real type missing
from the list a loop trusts — a build failure rather than a silent gap.

## What a registry entry is, and what it is not

Keyed by matter name, valued by a `MatterType` that ties the name to its
**pack** — the closed schema module (`homestead_law.packs.custody`) that authored
and classified the fields. The registry holds a *reference* to the pack, not a
copy of it: `fields` and `schema` read `pack.FIELDS`/`pack.SCHEMA` live, so
there is exactly one field list in the process and the registry cannot drift
from the pack the way three hand-kept lists drifted from each other. The host
imports the pack; the pack never imports the host (Article IV's injected-seam
shape, and the reason this file depends on `packs` and not the reverse).

This is `surfaces.FACTS` in a second place: an authored table, keyed by a
member, cross-checked at import against the set of members that actually exist,
so one added and forgotten stops the build instead of failing open on the day
something iterates it. The value shape is a frozen dataclass rather than the
raw module for the same reason `SurfaceFacts` is one — a consumer reads a small
closed contract (`name`, `jurisdiction`, `jurisdictions`, `fields`, `schema`)
instead of rummaging a module's namespace for whatever it happens to expose.
`jurisdiction` is the default a new instance of the matter starts under and
`jurisdictions` is every jurisdiction it may be filed in (decision 1); the
guard below holds the first inside the second.

## Only custody is built

Custody is the one pack in v1 — *"one pack proves the seam; three prove nothing
that one does not."* Bankruptcy and workers' comp are the two other types the
model discusses (a case number is `L1` in a bankruptcy, `L3` in a family
matter), and they are **Phase 5, not built**. They are not in this registry,
and inventing a stub for either would be the hand-kept phantom this invariant
forbids — a matter name in a list with no pack behind it, which is the missing
half of BUG-6.

## What it does not hold

* **No rung logic.** A matter's rungs live in its pack, classified at import by
  `rungs.classify_schema`. The registry reads them; it does not set them.
* **No store, no gate.** This file deals in matter *names* and *schemas*, never
  in record content — it never reaches a `.payload`
  (`tests/test_invariants_chokepoint.py` enforces that it cannot).
"""
from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass
from types import ModuleType
from typing import Any, Mapping

from homestead_law import packs
from homestead.keep.rungs import Rung
from homestead_law.packs import custody

__all__ = ["MatterType", "REGISTRY", "all_matters", "matter"]


@dataclass(frozen=True)
class MatterType:
    """One matter type, tied to the pack that defines its schema.

    `pack` is the imported pack module — the host holding a reference to the
    thing it consumes, never the reverse (Article IV's injected seam). `fields`
    and `schema` read through to it live rather than copying, so the registry is
    a *pointer* to the one field list and can never carry a stale second copy of
    it. That is the whole of the drift defence: BUG-6 was copies of a list
    disagreeing, and a copy that is a property over the original cannot disagree
    with it.
    """

    name: str
    jurisdiction: str
    pack: ModuleType

    @property
    def fields(self) -> dict[str, Rung]:
        """The pack's classified fields — `field name → Rung`, read live.

        Not stored on the entry. The registry never hardcodes the field list; it
        holds the pack and asks it, so there is one list and it is the pack's.
        """
        return self.pack.FIELDS

    @property
    def schema(self) -> dict[str, Any]:
        """The pack's closed schema — the declarations `fields` was classified
        from, carrying each field's rung, matter and jurisdiction."""
        return self.pack.SCHEMA

    @property
    def jurisdictions(self) -> tuple[str, ...]:
        """Every jurisdiction an instance of this matter may be filed under —
        `pack.JURISDICTIONS`, read live like `fields`/`schema` so there is one
        tuple and the registry cannot carry a stale copy of it. `jurisdiction`
        above is the *default* a new instance starts with (decision 1); this is
        the full set `set_jurisdiction` (Wave 3) may move an instance within,
        and `_validate` requires the default itself be one of its members."""
        return self.pack.JURISDICTIONS

    @property
    def repeatable(self) -> frozenset[str]:
        """Field names this matter allows a sub-id on (decision 2,
        `homestead_law.instances`) — read live from `pack.REPEATABLE`, like
        `jurisdictions`. A pack that names none (custody, today) is read as an
        empty set rather than required to declare one explicitly: only a
        *declared* `REPEATABLE` is checked against `FIELDS` below, so a pack
        with nothing repeatable pays nothing for that."""
        return getattr(self.pack, "REPEATABLE", frozenset())


def _entry(pack: ModuleType) -> MatterType:
    """A `MatterType` from a pack, reading the name and jurisdiction it declares.

    The name is *the pack's own* `MATTER`, never a string typed here — so the
    key this entry goes under and the pack's identity are the same value read
    once, and the validation below is checking that reading rather than a
    transcription that could be wrong.
    """
    return MatterType(name=pack.MATTER, jurisdiction=pack.JURISDICTION, pack=pack)


#: The one enumeration (I-23). Keyed by matter name → its `MatterType`. Authored
#: here, the way `surfaces.FACTS` is authored — add a pack by importing it and
#: adding a line, and everything that iterates `all_matters()` picks it up with
#: no other change. Only `custody` is built (bankruptcy, workers' comp: Phase 5).
REGISTRY: dict[str, MatterType] = {
    custody.MATTER: _entry(custody),
}


def _discover_packs() -> dict[str, ModuleType]:
    """Every module under `homestead_law.packs` that declares a `MATTER`.

    This is the mirror `surfaces` has for its enum: there, `Surface` is the
    closed set and `FACTS` must cover it; here, the packs on disk are the set and
    `REGISTRY` must cover them. A pack authored and left out of the registry is
    BUG-6 exactly — a real matter type that no loop over "all matters" will ever
    reach — so it is found here and made a build failure, not discovered the day
    a deadline in it fails to become urgent.
    """
    found: dict[str, ModuleType] = {}
    for info in pkgutil.iter_modules(packs.__path__, prefix=f"{packs.__name__}."):
        module = importlib.import_module(info.name)
        name = getattr(module, "MATTER", None)
        if isinstance(name, str) and name:
            found[name] = module
    return found


def _validate(registry: Mapping[str, Any], on_disk: Mapping[str, ModuleType]) -> None:
    """Hold the registry against the packs that actually exist, at import.

    Pure in its two arguments — like `rungs._check_crossing`'s spirit — so the
    guard can be fired against a deliberately broken registry in a test rather
    than only asserted about. Several ways it can be wrong, each BUG-6's shape
    from a different side:

    * a key that disagrees with its own entry's name, or its pack's `MATTER` —
      a transcription drifting from the thing transcribed;
    * a pack on disk with no registry entry — a matter type nothing enumerates,
      which is the workers'-comp-out-of-the-queue failure precisely;
    * a registry entry for a pack that is not on disk — a phantom matter, a name
      in the list with nothing behind it;
    * a pack whose `JURISDICTIONS` is missing, empty, holds a blank member, or
      does not contain its own `JURISDICTION` — decision 1's default-outside-the-
      supported-tuple failure: a pack whose default jurisdiction is not itself
      one it lists could never satisfy `set_jurisdiction`'s own refusal on the
      instance it starts every matter in;
    * an entry whose `jurisdiction` disagrees with its pack's `JURISDICTION` —
      the key check one field over. `jurisdiction` is the only part of an entry
      that is copied out of the pack instead of read live, so it is the only
      part that can drift, and the drift is invisible without this check now
      that `jurisdictions` next to it *is* live;
    * a pack whose `REPEATABLE` (decision 2, optional) names a field `FIELDS`
      does not have — a sub-id offered on a field that does not exist;
    * a pack with an `L3`/`L4` field that declares no `"derived"` sentence —
      decision 3's contract, held here rather than left to the write path.
      `classify_schema` deliberately ignores the key, so such a pack imports
      clean and fails at the first `put` instead: `derived_of` returns `None`,
      `Classified(rung, value, None)` raises `UnclassifiedField`, and neither
      door builds that `Classified` inside its `try`, so the CLI tracebacks and
      the browser's POST dies on the socket. A build failure naming the field
      is the refusal this module gives every other kind of absence (I-11).
    """
    # The rungs a stored record may be *served as a stand-in for*, which is
    # therefore the set that must carry one. Stated here rather than imported:
    # the engine's own copy (`rungs._NEEDS_DERIVED`) is private, and
    # `tests/test_registry.py::test_the_derived_requirement_matches_the_engines`
    # pins the two together behaviourally — by constructing a `Classified` and
    # watching which rungs refuse — so this cannot drift from it in silence.
    needs_derived = (Rung.L3, Rung.L4)
    for key, entry in registry.items():
        if not isinstance(entry, MatterType):
            raise RuntimeError(
                f"REGISTRY[{key!r}] is a {type(entry).__name__}, not a MatterType"
            )
        if key != entry.name or key != entry.pack.MATTER:
            raise RuntimeError(
                f"REGISTRY key {key!r} disagrees with its pack's MATTER "
                f"({entry.pack.MATTER!r}) — a matter is keyed by the name its "
                "pack declares, read once, so the two cannot drift. A key kept "
                "by hand next to a name set elsewhere is BUG-6's shape."
            )
        default = getattr(entry.pack, "JURISDICTION", None)
        if not isinstance(default, str) or not default.strip():
            raise RuntimeError(
                f"{key!r}: JURISDICTION must be a non-empty string, not "
                f"{default!r}. A pack that declares no default jurisdiction "
                "has nothing for a new instance to start under (decision 1), "
                "and absence refuses by name here rather than surfacing as an "
                "AttributeError from whatever reads it first (I-11)."
            )
        jurisdictions = getattr(entry.pack, "JURISDICTIONS", None)
        if (
            not isinstance(jurisdictions, tuple)
            or not jurisdictions
            or not all(isinstance(j, str) and j.strip() for j in jurisdictions)
        ):
            raise RuntimeError(
                f"{key!r}: JURISDICTIONS must be a non-empty tuple of non-empty "
                f"strings, not {jurisdictions!r}. A pack with none, or with a "
                "blank member, has an unreadable jurisdiction set — the exact "
                "shape absence takes elsewhere in this module (I-11's building "
                "failing closed) applied to decision 1's per-matter jurisdiction."
            )
        if entry.jurisdiction != entry.pack.JURISDICTION:
            raise RuntimeError(
                f"{key!r}: the entry's jurisdiction {entry.jurisdiction!r} "
                f"disagrees with its pack's JURISDICTION "
                f"{entry.pack.JURISDICTION!r}. `jurisdiction` is the one field "
                "on an entry that is a *copy* rather than a property over the "
                "pack (`fields`, `schema` and `jurisdictions` all read through "
                "live), so it is the one that can drift — and a copy that has "
                "drifted from the thing it copies is BUG-6, the same shape as "
                "the key check above."
            )
        if entry.jurisdiction not in jurisdictions:
            raise RuntimeError(
                f"{key!r}: JURISDICTION {entry.jurisdiction!r} is not in "
                f"its own JURISDICTIONS {jurisdictions!r}. A pack's default "
                "jurisdiction must be one of the jurisdictions it supports — "
                "every new instance starts at the default, and a default "
                "outside the supported tuple is a matter that cannot open."
            )
        repeatable = getattr(entry.pack, "REPEATABLE", frozenset())
        if not isinstance(repeatable, frozenset) or not all(
            isinstance(f, str) for f in repeatable
        ):
            raise RuntimeError(
                f"{key!r}: REPEATABLE must be a frozenset of field names, not "
                f"{repeatable!r}. A pack with nothing repeatable may simply "
                "omit it (decision 2) — but a declared one must be readable "
                "the same way JURISDICTIONS must be, or it fails closed."
            )
        unknown_repeatable = sorted(f for f in repeatable if f not in entry.fields)
        if unknown_repeatable:
            raise RuntimeError(
                f"{key!r}: REPEATABLE names {unknown_repeatable}, which FIELDS "
                "does not declare. A sub-id may only be offered on a field the "
                "pack actually has — a name in REPEATABLE with nothing behind "
                "it is the same 'enumerated but not real' shape I-23 forbids "
                "for matters, one level down, at fields."
            )
        for field, rung in entry.fields.items():
            if rung not in needs_derived:
                continue
            declaration = entry.schema.get(field)
            sentence = (
                declaration.get("derived") if isinstance(declaration, Mapping) else None
            )
            if not isinstance(sentence, str) or not sentence.strip():
                raise RuntimeError(
                    f"{key!r}: field {field!r} is {rung.value} and declares no "
                    "'derived' sentence. Decision 3 puts the stand-in a surface "
                    "shows in place of the payload on the pack itself, and an "
                    f"{rung.value} record is served as that stand-in on at "
                    "least one surface — so a pack that omits it has a field "
                    "that cannot be written at all, and would say so only at "
                    "the first `put`. Add SCHEMA[field]['derived']."
                )

    unregistered = sorted(set(on_disk) - set(registry))
    if unregistered:
        raise RuntimeError(
            f"packs with no registry entry: {unregistered}. Every pack that "
            "exists must be enumerated here (I-23) — a matter type the registry "
            "does not know is a matter type nothing that iterates all_matters() "
            "will reach, which is exactly how workers' comp fell out of the "
            "urgent queue (BUG-6). Add it to REGISTRY."
        )
    phantom = sorted(set(registry) - set(on_disk))
    if phantom:
        raise RuntimeError(
            f"registry entries with no pack: {phantom}. A matter name in the "
            "enumeration with no pack behind it is the hand-kept phantom I-23 "
            "forbids — enumerate only what is built (custody; bankruptcy and "
            "workers' comp are Phase 5)."
        )


_validate(REGISTRY, _discover_packs())


def all_matters() -> tuple[str, ...]:
    """Every matter type the household handles — the one place to ask.

    Iterates `REGISTRY` and nothing else. This is the function navigation, the
    queue and the briefing call instead of keeping a list; because they share
    this one, they cannot drift from each other the way BUG-6's three lists did.
    A tuple rather than a live view, so a caller cannot mutate the enumeration by
    holding what it returns.
    """
    return tuple(REGISTRY)


def matter(name: str) -> MatterType:
    """The `MatterType` for a name, or `KeyError`.

    Strict, like `surfaces.facts`: a caller holding a matter name that is not
    registered has skipped a step upstream, and this is a cheaper place to find
    that out than wherever the missing schema would otherwise have been read.
    """
    return REGISTRY[name]
