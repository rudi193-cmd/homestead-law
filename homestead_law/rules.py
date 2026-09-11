"""Deadline templates (decision 4, L3-deadline-templates) — data on a pack,
counted here, never stored until an operator says so.

A **template** is not code a pack author writes; it is a row of data a pack
declares on its own `TEMPLATES` tuple — `homestead_law.packs.custody` (and the
sibling custody/bankruptcy/workers'-comp bites landing in parallel) name an
anchor field, a period, a counting rule and the citation behind it, and this
module is the one place that reads that data, validates it, and turns it into
a computed date. Nothing here invents a rule: every count is
`homestead.keep.dates` — `court_days`, `court_days_before`, `add_mail_days`,
`business_days` — reached with the template's own numbers, or (for
`calendar_days`, which the engine does not implement) a plain `timedelta`
this module owns and documents as such.

**Two acts, kept apart on purpose.** `compute()` reads an anchor and a
jurisdiction and returns a `Computed` — nothing is stored, and calling it a
second time with the same inputs answers the same way. `accept()` is the only
function in this module that writes, and it writes only what a token proves
was actually shown: `preview_token` is a hash of exactly the fields the
operator (or the browser) saw, so `accept` cannot be pointed at a stale
preview by name-confusion or a slow client — `server.py`'s accept endpoint
recomputes and compares before it ever calls this module's `accept`.

**A template name is a label, not a sentence, and it is also half of a
stored key.** `accept()` files a computed deadline under
`instances.item_id(instance, template)`, so a template's `name` must match
`instances.ID_PATTERN` — lowercase letters, digits and hyphens, no
underscore, no dot. `registration-contest`, not `registration_contest`: a
pack whose template names are snake_case like its *field* names refuses at
import rather than at the first `--accept`, which is the difference between
a build failure and a deadline that computes and then cannot be filed.

**One name may be declared more than once — for different jurisdictions.**
That is not a duplicate; it is the ordinary shape of a rule that differs by
forum, and custody's `registration-contest` (20 court days under `US-NM`,
21 under `US-OR`) is exactly it. `compute()` picks by the *instance's* own
jurisdiction, and `validate_templates` refuses only the repeats it could not
pick between: the same name twice for the same jurisdiction, or one name
declared both for a particular jurisdiction and for all of them.

**Validation lives at registry time, not at first use.** `validate_templates`
is `registry._validate`'s one addition for this bite: a pack whose `TEMPLATES`
violates its own contract — a key missing, an anchor that is not one of the
pack's own `L1` fields, a `calendar_days` template that asks for `--mail` —
fails the *build*, naming the pack and the template, the same "absence fails
closed, at construction" posture `classify_schema` already holds custody's
`SCHEMA` to (I-11). A pack that declares no `TEMPLATES` at all — custody, as
shipped by this bite — validates clean; templates are optional pack data.

**This module is a surface.** `compute()` reads the anchor **through the
gate** (`serve()` on `Surface.S1_LIST` — the same door `jurisdiction.py` reads
a forum through), so `tests/test_chokepoint.py`'s `_calls_a_door` finds it and
holds the whole file to the wider reflection ban: no `getattr`, no `vars`, no
`dataclasses.fields`/`asdict`/`astuple`, no `operator.attrgetter`, anywhere in
this file — not only near the `serve()` call. `preview_token` is therefore a
hand-built dict, not `dataclasses.asdict(computed)`; `validate_templates`
checks `hasattr(pack, "TEMPLATES")` rather than `getattr(pack, "TEMPLATES",
())`, for the same reason.

**Refusals name a field, never a value above L1.** Every anchor this module
will ever read is validated, at registry time, to be an `L1` field — the
pack's own public-forum rung — so echoing the anchor's text in an
`UnparseableDate` (the engine's own message shape) or in a computed-date
refusal is not an I-15 violation the way it would be for an `L3`+ value; it is
the same posture `deadline`'s own CLI door already takes with a date it cannot
parse. What this module never echoes is a jurisdiction *hand-planted* outside
the gate (`jurisdiction.py`'s job, unchanged here) or an anchor record planted
at a rung the gate withholds — those refuse by field name only, exactly as
`JurisdictionAbsent` already does.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Mapping

from homestead.keep.rungs import Classified, Disposition, Rung, Surface, serve

from homestead_law import instances
from homestead_law.store import Replaced, Sidecar

if TYPE_CHECKING:
    from homestead_law.registry import MatterType

__all__ = [
    "Template",
    "Computed",
    "InvalidTemplate",
    "TemplateNotFound",
    "AmbiguousTemplate",
    "AnchorUnavailable",
    "TemplateJurisdictionMismatch",
    "UncertainTemplate",
    "MailUnsupported",
    "StaleToken",
    "validate_templates",
    "templates_of",
    "compute",
    "accept",
]

#: The exact keys every `TEMPLATES` entry must carry — no more, no fewer. A
#: dict rather than a dataclass on the pack side (decision: templates are
#: *data*, so a pack author edits a literal, never imports this module to
#: build one) — `Template` below is this module's own typed mirror of it.
_KEYS = frozenset(
    {"name", "anchor", "days", "direction", "rule", "mail",
     "jurisdiction", "source", "status", "note"}
)
#: Keys an entry *may* carry and usually does not. `district_state` is the
#: USPS code of the state a **federal** district court sits in — FRBP
#: 9006(a)(6)(C)'s second calendar, forward periods only. It is optional
#: because only a federal template in a district whose state the pack knows
#: can honestly name one; a template that omits it computes on the federal
#: calendar alone and `Computed.district_state` is `None`, which every door
#: says out loud rather than leaving the operator to assume state closures
#: were counted. See `_district_state_for`.
_OPTIONAL_KEYS = frozenset({"district_state"})
#: Two upper-case ASCII letters — the *shape* of a USPS code, not the list.
#: Which codes actually exist is `homestead.keep.dates`' own question (it
#: refuses one `holidays` does not recognize, by name); this check only stops
#: a pack typo at build time instead of at the operator's first compute.
_DISTRICT_STATE = re.compile(r"^[A-Z]{2}$")
#: The one counting rule the engine accepts a `district_state` for:
#: `court_days` (and `add_mail_days` over its result). `court_days_before`
#: takes none at all — a state holiday must never reach a backward count —
#: `business_days` has no such parameter, and `calendar_days` reads no
#: calendar whatsoever.
_DISTRICT_STATE_RULE = "court_days"
_DIRECTIONS = frozenset({"forward", "backward"})
_RULES = frozenset({"court_days", "court_days_before", "business_days", "calendar_days"})
_STATUSES = frozenset({"VERIFIED", "UNCERTAIN"})
#: The one rule whose direction is backward, and the only one — validated as
#: an if-and-only-if below so the two can never say different things.
_BACKWARD_RULE = "court_days_before"


@dataclass(frozen=True)
class Template:
    """One deadline template — a pack's own `TEMPLATES` entry, typed.

    Field-for-field the dict shape a pack declares (see the module docstring
    and `validate_templates`): `anchor` is one of the pack's own `L1` fields,
    `jurisdiction` is `None` (the instance's own, whatever it is) or one
    member of the pack's `JURISDICTIONS`, and `status` gates whether `compute`
    will ever reach the counting rule at all.
    """

    name: str
    anchor: str
    days: int
    direction: str
    rule: str
    mail: bool
    jurisdiction: str | None
    source: str
    status: str
    note: str
    #: Optional, and defaulted so the ten required keys keep building a
    #: `Template` unchanged: the USPS code of the state a federal district
    #: court sits in (FRBP 9006(a)(6)(C)). `None` — the ordinary case — means
    #: no second calendar was named, and `compute` then falls back to the
    #: instance's own `district_state` record if (and only if) the pack
    #: declares such an `L1` field. Never guessed from a district's *name*:
    #: "District of New Mexico" → `"NM"` is a table of court names this
    #: package does not own and I-23 would not let it keep.
    district_state: str | None = None


@dataclass(frozen=True)
class Computed:
    """What `compute()` found — the anchor read, the date it counts to, and
    everything `preview_token` is a hash of. Never stored by this class;
    `accept()` is the only writer, and only after the token matches.
    """

    matter: str
    instance: str
    template: str
    anchor_field: str
    anchor_iso: str
    result_iso: str
    source: str
    jurisdiction: str
    mail: bool
    #: The second holiday calendar this count actually used, or `None` for
    #: "district holidays were not applied" — part of the answer, so part of
    #: the token: the same anchor under the same rule gives a different date
    #: with and without it (2026-11-27 is a federal working day and an
    #: `US-NM` closure), and a preview that did not say which was shown is a
    #: preview an `accept` could quietly disagree with.
    district_state: str | None

    @property
    def preview_token(self) -> str:
        """`sha256` of the canonical JSON of exactly the ten fields above.

        Built by hand — `matter`, `instance`, … named one at a time — rather
        than `dataclasses.asdict(self)`: this module is a surface (it calls
        `serve()`), and `tests/test_chokepoint.py` bans `asdict` anywhere in a
        surface file, the same way it bans `getattr`. Sorted keys and compact
        separators so the same ten values always hash to the same string,
        regardless of how this dict happens to be built.
        """
        payload = {
            "matter": self.matter,
            "instance": self.instance,
            "template": self.template,
            "anchor_field": self.anchor_field,
            "anchor_iso": self.anchor_iso,
            "result_iso": self.result_iso,
            "source": self.source,
            "jurisdiction": self.jurisdiction,
            "mail": self.mail,
            "district_state": self.district_state,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ── refusals ──────────────────────────────────────────────────────────────

class InvalidTemplate(ValueError):
    """One `TEMPLATES` entry that does not meet the pack contract.

    Raised at import, through `registry._validate` (a build failure, I-11's
    first half — the same moment an unclassified `SCHEMA` field already stops
    the build), and again from `templates_of`/`compute` for a pack reached
    some other way (a test's fake `MatterType` that never passed through the
    registry). Names the matter, the template (when one entry is at fault),
    and the clause — the template's own `name`/`anchor`/`rule`/… are pack
    *declarations*, not stored content, so echoing them is the same courtesy
    `UnsupportedJurisdiction` already extends to a pack's published set.
    """


class TemplateNotFound(LookupError):
    """No template named this on the matter's pack. Names what was asked for
    and what the pack actually declares — both are labels a pack author
    published, never stored content."""

    def __init__(self, matter_name: str, template_name: str, declared: tuple[str, ...]) -> None:
        super().__init__(
            f"{matter_name}: no template named {template_name!r} — declared: "
            f"{list(declared)}"
        )
        self.matter = matter_name
        self.template = template_name


class AmbiguousTemplate(LookupError):
    """More than one template of this name fits this instance's jurisdiction.

    `validate_templates` makes this unreachable for a pack that came through
    the registry — a name may repeat only across *different* jurisdictions,
    and a name declared once with `jurisdiction=None` may not also be
    declared for a specific one — so this is the runtime half of that rule,
    for a `MatterType` built by hand that never passed through it. Refusing
    is the only honest answer: picking the first match would file a deadline
    counted under a rule the operator never chose."""

    def __init__(
        self, matter_name: str, instance: str, template_name: str, code: str,
    ) -> None:
        super().__init__(
            f"{matter_name}/{instance}/{template_name}: more than one template "
            f"of this name fits {code} — the pack declares an ambiguous set "
            "and no date can be counted from it"
        )
        self.matter = matter_name
        self.instance = instance
        self.template = template_name


class AnchorUnavailable(LookupError):
    """The template's anchor field is not on file at a rung the gate renders.

    Named exactly the way `JurisdictionAbsent` is: the matter, the instance
    and the field, never the record's value or its derived form (I-15) — the
    anchor may be missing outright, or on file at a rung the gate withholds
    (a hand-planted `L3`/`L4`/`L5`, which a template's own `L1` contract
    should never produce through the ordinary write doors but which this
    check does not trust to have been kept that way)."""

    def __init__(self, matter_name: str, instance: str, field: str, *, because: str) -> None:
        super().__init__(
            f"{matter_name}/{instance}: the anchor field {field!r} {because}. "
            f"Run `homestead-law put {matter_name} {field} <value> --id "
            f"{instance}` first."
        )
        self.matter = matter_name
        self.instance = instance
        self.field = field


class TemplateJurisdictionMismatch(ValueError):
    """The template names one jurisdiction; the instance is opened in another.

    Both are the pack's own published codes (never stored free text), so both
    are named — the same courtesy `UnsupportedJurisdiction` already extends."""

    def __init__(
        self, matter_name: str, instance: str, template_name: str,
        expected: tuple[str, ...] | str, actual: str,
    ) -> None:
        declared = (expected,) if isinstance(expected, str) else tuple(expected)
        for_what = declared[0] if len(declared) == 1 else f"{list(declared)}"
        super().__init__(
            f"{matter_name}/{instance}/{template_name}: this template is for "
            f"{for_what}; the instance is {actual}"
        )
        self.matter = matter_name
        self.instance = instance
        self.template = template_name


class UncertainTemplate(ValueError):
    """`Template.status == "UNCERTAIN"` — refused before any arithmetic runs.

    The message is exactly `"UNCERTAIN: <source>"`: `source` is the pack
    author's own citation, so the refusal is also the pointer to what still
    needs a primary read, the same posture `homestead.keep.dates`'s own
    `_require_verified` takes."""

    def __init__(self, matter_name: str, template_name: str, source: str) -> None:
        super().__init__(f"UNCERTAIN: {source}")
        self.matter = matter_name
        self.template = template_name
        self.source = source


class MailUnsupported(ValueError):
    """`mail=True` on a template whose rule has no forward-rolled end to add
    mail days to: `court_days_before` is already rolled backward, and
    `calendar_days` has no jurisdiction rule to add mail days under at all."""

    def __init__(self, matter_name: str, template_name: str, rule: str) -> None:
        super().__init__(
            f"{matter_name}/{template_name}: --mail is refused for a {rule!r} "
            "template — mail days apply only to a forward court-rolled "
            "deadline (court_days/business_days); court_days_before is "
            "already rolled backward and calendar_days has no jurisdiction "
            "rule to add mail days under"
        )
        self.matter = matter_name
        self.template = template_name
        self.rule = rule


class StaleToken(ValueError):
    """The token handed to `accept` does not match a fresh `compute` of the
    same instance, template and anchor. Neither token is echoed: a token is
    a hash of the same fields a stored deadline's date already is, and naming
    a mismatch is enough to act on."""

    def __init__(self, matter_name: str, instance: str, template_name: str) -> None:
        super().__init__(
            f"{matter_name}/{instance}/{template_name}: the preview token does "
            "not match a fresh computation — recompute and confirm before "
            "accepting"
        )
        self.matter = matter_name
        self.instance = instance
        self.template = template_name


# ── validation, run at registry time (registry._validate's one addition) ────

def validate_templates(pack: object) -> None:
    """Every entry of `pack.TEMPLATES` against the pack contract, or a build
    failure naming the pack and the offending template.

    A pack with no `TEMPLATES` attribute at all validates clean — templates
    are optional pack data (custody, as shipped by this bite, has none yet).
    `hasattr`, not `getattr(pack, "TEMPLATES", ())`: this module is a surface
    (see the module docstring), and the chokepoint scan bans `getattr`
    anywhere in a surface file, not only near the door it guards.
    """
    matter_name = pack.MATTER if hasattr(pack, "MATTER") else repr(pack)
    templates = pack.TEMPLATES if hasattr(pack, "TEMPLATES") else ()
    if not isinstance(templates, tuple):
        raise InvalidTemplate(
            f"{matter_name}: TEMPLATES must be a tuple, not "
            f"{type(templates).__name__}"
        )
    fields = pack.FIELDS if hasattr(pack, "FIELDS") else {}
    jurisdictions = pack.JURISDICTIONS if hasattr(pack, "JURISDICTIONS") else ()

    #: name → every jurisdiction it is declared for, in declaration order.
    #: Checked after the loop, once each entry's own `jurisdiction` has been
    #: validated against the pack's tuple: *one name may repeat across
    #: different jurisdictions* (custody's `registration-contest` is a
    #: 20-day NM rule and a 21-day OR one, and `compute` picks by the
    #: instance's own forum), and only a repeat that `compute` could not
    #: resolve is a build failure.
    by_name: dict[str, list[str | None]] = {}
    for entry in templates:
        if not isinstance(entry, Mapping):
            raise InvalidTemplate(
                f"{matter_name}: a TEMPLATES entry must be a mapping, not "
                f"{type(entry).__name__}"
            )
        keys = set(entry)
        if not _KEYS <= keys or not keys <= (_KEYS | _OPTIONAL_KEYS):
            raise InvalidTemplate(
                f"{matter_name}: a TEMPLATES entry has the wrong keys — "
                f"missing {sorted(_KEYS - keys)}, unexpected "
                f"{sorted(keys - _KEYS - _OPTIONAL_KEYS)}. Every entry needs "
                f"exactly {sorted(_KEYS)}, and may add "
                f"{sorted(_OPTIONAL_KEYS)}."
            )

        name = entry["name"]
        if not isinstance(name, str) or not name:
            raise InvalidTemplate(
                f"{matter_name}: a template name must be a non-empty string, "
                f"not {name!r}"
            )
        if not instances.ID_PATTERN.match(name):
            raise InvalidTemplate(
                f"{matter_name}/{name}: a template name is stored as a "
                f"repeatable sub-id and must match {instances.ID_PATTERN.pattern}"
            )

        anchor = entry["anchor"]
        if not isinstance(anchor, str) or anchor not in fields:
            raise InvalidTemplate(
                f"{matter_name}/{name}: anchor {anchor!r} is not a field this "
                "pack declares"
            )
        if fields[anchor] is not Rung.L1:
            raise InvalidTemplate(
                f"{matter_name}/{name}: anchor {anchor!r} is "
                f"{fields[anchor].value}, not L1 — a deadline template may "
                "only anchor on a field public in this matter's forum"
            )

        days = entry["days"]
        if isinstance(days, bool) or not isinstance(days, int) or days <= 0:
            raise InvalidTemplate(
                f"{matter_name}/{name}: days must be a positive integer, not "
                f"{days!r}"
            )

        direction = entry["direction"]
        if direction not in _DIRECTIONS:
            raise InvalidTemplate(
                f"{matter_name}/{name}: direction must be one of "
                f"{sorted(_DIRECTIONS)}, not {direction!r}"
            )

        rule = entry["rule"]
        if rule not in _RULES:
            raise InvalidTemplate(
                f"{matter_name}/{name}: rule must be one of {sorted(_RULES)}, "
                f"not {rule!r}"
            )

        if (direction == "backward") != (rule == _BACKWARD_RULE):
            raise InvalidTemplate(
                f"{matter_name}/{name}: direction {direction!r} and rule "
                f"{rule!r} disagree — backward counting is {_BACKWARD_RULE} "
                "and nothing else"
            )

        mail = entry["mail"]
        if not isinstance(mail, bool):
            raise InvalidTemplate(
                f"{matter_name}/{name}: mail must be a bool, not {mail!r}"
            )
        if mail and rule == "calendar_days":
            raise InvalidTemplate(
                f"{matter_name}/{name}: calendar_days has no jurisdiction "
                "rule to add mail days under — mail must be false"
            )
        if mail and direction == "backward":
            # The rule dates-a states and this module only re-states: the
            # three added days of FRBP 9006(f)/FRCP 6(d) extend a period
            # that *runs from service* — the served party gets the time the
            # post took. A period counted **backward** from a hearing runs
            # from the hearing, not from anything served, so there is no
            # such period to extend and nothing to add the days to; adding
            # them anyway would move an objection deadline three days
            # *later*, i.e. past the point the rule was protecting. A pack
            # that wants a mailed-service allowance on a backward period is
            # describing a different rule, and must cite it.
            raise InvalidTemplate(
                f"{matter_name}/{name}: mail must be false on a backward "
                f"({rule!r}) template — the three mail days of FRBP "
                "9006(f)/FRCP 6(d) extend a period that runs from service, "
                "and a period counted backward from an event does not run "
                "from service at all"
            )

        jurisdiction = entry["jurisdiction"]
        if jurisdiction is not None and jurisdiction not in jurisdictions:
            raise InvalidTemplate(
                f"{matter_name}/{name}: jurisdiction {jurisdiction!r} is not "
                f"one of this matter's {jurisdictions}"
            )

        source = entry["source"]
        if not isinstance(source, str) or not source.strip():
            raise InvalidTemplate(
                f"{matter_name}/{name}: source must be a non-empty string"
            )

        status = entry["status"]
        if status not in _STATUSES:
            raise InvalidTemplate(
                f"{matter_name}/{name}: status must be one of "
                f"{sorted(_STATUSES)}, not {status!r}"
            )

        note = entry["note"]
        if not isinstance(note, str):
            raise InvalidTemplate(
                f"{matter_name}/{name}: note must be a string, not "
                f"{type(note).__name__}"
            )

        if "district_state" in entry and entry["district_state"] is not None:
            district_state = entry["district_state"]
            if not isinstance(district_state, str) or not _DISTRICT_STATE.match(
                district_state
            ):
                raise InvalidTemplate(
                    f"{matter_name}/{name}: district_state must be a two-letter "
                    f"upper-case USPS code, not {district_state!r}"
                )
            if rule != _DISTRICT_STATE_RULE:
                raise InvalidTemplate(
                    f"{matter_name}/{name}: district_state is only counted by "
                    f"{_DISTRICT_STATE_RULE!r} — 9006(a)(6)(C) adds the "
                    "district's state holidays to a period measured *after* "
                    "an event, and court_days_before, business_days and "
                    "calendar_days each take none"
                )
            if jurisdiction not in (None, "US-federal"):
                raise InvalidTemplate(
                    f"{matter_name}/{name}: district_state names the state a "
                    "*federal* district court sits in; a template already "
                    f"scoped to {jurisdiction!r} is a state court's own "
                    "counting rule and reads its own state's holidays alone"
                )

        by_name.setdefault(name, []).append(jurisdiction)

    for name, declared in by_name.items():
        if len(declared) == 1:
            continue
        if len(set(declared)) != len(declared):
            raise InvalidTemplate(
                f"{matter_name}: template name {name!r} is declared more than "
                f"once for the same jurisdiction ({sorted(set(declared), key=str)}) "
                "— one name may repeat only across different jurisdictions"
            )
        if None in declared:
            raise InvalidTemplate(
                f"{matter_name}: template name {name!r} is declared both for "
                "every jurisdiction (jurisdiction=None) and for a particular "
                f"one ({sorted(c for c in declared if c is not None)}) — "
                "`compute` would have two rules to count under and no way to "
                "choose between them"
            )


# ── reading templates ────────────────────────────────────────────────────

def templates_of(mt: "MatterType") -> tuple[Template, ...]:
    """Every template `mt`'s pack declares, as `Template`s — `()` for a pack
    that names none.

    `mt` is a `registry.MatterType` (`registry.matter(name)`). Re-validates
    the pack's `TEMPLATES` first: `registry._validate` already ran this at
    import for every pack reached through the registry, so the check is
    idempotent there; it is load-bearing for a `MatterType` built by hand (a
    test's fake pack) that never passed through it.
    """
    validate_templates(mt.pack)
    templates = mt.pack.TEMPLATES if hasattr(mt.pack, "TEMPLATES") else ()
    return tuple(Template(**entry) for entry in templates)


def _named(mt: "MatterType", name: str) -> tuple[Template, ...]:
    """Every template of this name — *plural*, because a name is unique only
    within one jurisdiction (see `validate_templates`). Refuses by name when
    the pack declares none, listing what it does declare (labels a pack
    author published, never stored content)."""
    found = templates_of(mt)
    matching = tuple(t for t in found if t.name == name)
    if not matching:
        raise TemplateNotFound(mt.name, name, tuple(dict.fromkeys(t.name for t in found)))
    return matching


def _for_jurisdiction(
    mt: "MatterType", instance: str, name: str, code: str,
) -> Template:
    """The one template of this name that fits `code`.

    A template naming a jurisdiction fits only that one; a template naming
    `None` fits any. An exact match wins over the catch-all, so a pack may
    (in principle) publish a general rule and one state's variant — though
    `validate_templates` refuses that combination outright, because the two
    would not be a rule and an exception so much as two rules the operator
    never chose between. None fitting refuses by name with the jurisdictions
    the pack *does* declare this template for; more than one fitting refuses
    rather than picking the first (`AmbiguousTemplate`)."""
    matching = _named(mt, name)
    exact = tuple(t for t in matching if t.jurisdiction == code)
    chosen = exact or tuple(t for t in matching if t.jurisdiction is None)
    if not chosen:
        raise TemplateJurisdictionMismatch(
            mt.name, instance, name,
            tuple(str(t.jurisdiction) for t in matching), code,
        )
    if len(chosen) > 1:
        raise AmbiguousTemplate(mt.name, instance, name, code)
    return chosen[0]


def _district_state_for(
    store: Sidecar, mt: "MatterType", instance: str, template: Template,
) -> str | None:
    """The state whose holidays 9006(a)(6)(C) adds, or `None`.

    Two sources, in order, and **no third**:

    1. the template's own optional `district_state` — a pack that knows its
       matter is filed in one district says so in the row;
    2. an `L1` `district_state` field on the *instance*, if the pack declares
       one — read through the gate on `S1_LIST` like every other value this
       module reads, and only when the pack declares it at `L1` (a pack that
       files the code lower has said it is not public in this forum, and a
       counting rule may not reach past that).

    What this deliberately does not do is read the pack's `district` field
    and map "District of New Mexico" to `"NM"`. That table is a list of court
    names — the enumeration I-23 says lives in a registry or a pack, not in a
    counting module — and every miss in it would be a silently *wrong*
    calendar rather than a refusal. Absent both sources the answer is `None`
    and `Computed.district_state` says so, which the CLI prints as "district
    holidays not applied" and the browser shows in the preview.
    """
    if template.district_state is not None:
        return template.district_state
    fields = mt.pack.FIELDS if hasattr(mt.pack, "FIELDS") else {}
    if fields.get("district_state") is not Rung.L1:
        return None
    if not store.has(mt.name, "district_state", instance):
        return None
    served = serve(store.get(mt.name, "district_state", instance), Surface.S1_LIST)
    if served.disposition is not Disposition.RENDER:
        return None
    return str(served.value)


def _read_anchor(store: Sidecar, matter_name: str, instance: str, field: str) -> str:
    """The anchor's text, through the gate on `S1_LIST` — `Served.value`,
    never `.payload` (I-16). Absent, or on file at a rung the gate does not
    render, both refuse identically (`AnchorUnavailable`), the same "anything
    short of RENDER is absence" posture `jurisdiction_of` already takes."""
    if not store.has(matter_name, field, instance):
        raise AnchorUnavailable(matter_name, instance, field, because="is not on file")
    record = store.get(matter_name, field, instance)
    served = serve(record, Surface.S1_LIST)
    if served.disposition is not Disposition.RENDER:
        raise AnchorUnavailable(
            matter_name, instance, field,
            because="is on file but not at a rung this door renders",
        )
    return str(served.value)


# ── compute — reads, never writes ────────────────────────────────────────

def compute(
    store: Sidecar,
    matter_name: str,
    instance: str,
    template_name: str,
    *,
    mail: bool = False,
    today: str | None = None,
) -> Computed:
    """Count one template's deadline for one instance. **Stores nothing.**

    In order, each refusing by name before the next step runs:

    1. the template name against the pack (`TemplateNotFound`) — a pack
       question, answered before the store is opened at all;
    2. the instance's jurisdiction (`jurisdiction_of` — provisional I-42,
       propagated unchanged);
    3. **which** template of that name counts here: the one whose
       `jurisdiction` is the instance's, or the one that names none. A name
       is unique only within a jurisdiction — custody declares
       `registration-contest` twice, 20 court days under `US-NM` and 21
       under `US-OR` — so this is a choice, not a lookup. None fitting is
       `TemplateJurisdictionMismatch`; more than one is `AmbiguousTemplate`
       (unreachable through the registry, which refuses such a pack);
    4. `status == "UNCERTAIN"` (`UncertainTemplate`, `"UNCERTAIN: <source>"`,
       *before any arithmetic and before the anchor is even read* — the
       counting functions below are never reached for such a template);
    5. `mail=True` against a rule with nothing forward-rolled to add days to
       (`MailUnsupported` — `court_days_before`, `calendar_days`);
    6. the anchor, read through the gate on `S1_LIST` (`AnchorUnavailable`
       for absent or ungated — a derived `L4`, a sealed `L5`).

    Then the district's state, if there is one to have (`_district_state_for`
    — the template's own optional `district_state`, else an `L1`
    `district_state` record on the instance, else `None`), for `court_days`
    and nothing else: FRBP 9006(a)(6)(C) adds the legal holidays of the state
    a federal district court sits in to a period measured *after* an event.
    `None` is carried into `Computed` and said out loud by every door —
    "district holidays not applied" — rather than passed off as a complete
    answer.

    Then `homestead.keep.dates`, by `template.rule`:

    * `court_days` / `court_days_before` / `business_days` — the engine's own
      three counters, given the template's `days` and the instance's
      jurisdiction. Any `UnparseableDate` they raise (an unverified branch,
      an unreadable anchor) propagates unchanged — it already names what
      failed and the anchor is `L1`, so nothing here needs to re-word it
      (I-15's echo rule binds `L3`+, not the pack's own public-forum field).
    * `calendar_days` — **not** an engine function. `template.days` added to
      the anchor by plain `datetime.timedelta`: no roll off a weekend or
      holiday, no calendar read at all. A 30-day `calendar_days` span that
      lands on a Sunday stays on that Sunday. Use `court_days`/`business_days`
      for a period a court's calendar should move.

    `mail=True` then runs `add_mail_days` over the result (refused above for
    the two rules it cannot apply to). `today` fixes `parse_deadline`'s
    reckoning day, for a deterministic anchor `Deadline` the way every other
    date-consuming call in this package accepts one; it does not change which
    date is computed, only what `Deadline.reference` (unused by the fields
    `Computed` carries) is set to.
    """
    from homestead_law.jurisdiction import jurisdiction_of
    from homestead_law.registry import matter

    mt = matter(matter_name)
    instance_id = instances.item_id(instance)
    # The name is checked against the pack before anything is read from the
    # store: a typo'd template is the caller's, not the household's, and
    # answering it with "no such template" beats answering it with whatever
    # happens to be missing from this instance.
    _named(mt, template_name)

    code = jurisdiction_of(store, matter_name, instance_id)
    template = _for_jurisdiction(mt, instance_id, template_name, code)

    if template.status == "UNCERTAIN":
        raise UncertainTemplate(matter_name, template_name, template.source)

    if mail and template.rule in (_BACKWARD_RULE, "calendar_days"):
        raise MailUnsupported(matter_name, template_name, template.rule)

    anchor_text = _read_anchor(store, matter_name, instance_id, template.anchor)
    # Resolved only for the one rule that can count under it, so
    # `Computed.district_state` means "the second calendar this count used"
    # and never "a code was on file somewhere" — a token that claimed the
    # latter would say a backward count had applied NM's holidays when
    # 9006(a)(6)(C) forbids exactly that.
    district_state = (
        _district_state_for(store, mt, instance_id, template)
        if template.rule == _DISTRICT_STATE_RULE
        else None
    )

    from homestead.keep.dates import (
        Deadline,
        add_mail_days,
        business_days,
        court_days,
        court_days_before,
        parse_deadline,
    )

    anchor_deadline = parse_deadline(anchor_text, today)

    if template.rule == "court_days":
        result = court_days(
            anchor_deadline, template.days, jurisdiction=code,
            district_state=district_state,
        )
    elif template.rule == _BACKWARD_RULE:
        # No `district_state` here, and not because this module forgot: a
        # state's holidays may not reach a backward count (9006(a)(6)(C) is
        # "after an event" only), and `court_days_before` takes no such
        # argument at all — which is why it is resolved to `None` above for
        # every rule but `court_days`.
        result = court_days_before(anchor_deadline, template.days, jurisdiction=code)
    elif template.rule == "business_days":
        result = business_days(anchor_deadline, template.days, jurisdiction=code)
    else:  # "calendar_days" — validated to be the only remaining member
        result = Deadline(
            anchor_deadline.date + timedelta(days=template.days),
            anchor_deadline.reference,
        )

    if mail:
        result = add_mail_days(result, jurisdiction=code, district_state=district_state)

    return Computed(
        matter=matter_name,
        instance=instance_id,
        template=template_name,
        anchor_field=template.anchor,
        anchor_iso=anchor_deadline.iso,
        result_iso=result.iso,
        source=template.source,
        jurisdiction=code,
        mail=mail,
        district_state=district_state,
    )


# ── accept — the only writer ─────────────────────────────────────────────

def accept(
    store: Sidecar, computed: Computed, *, token: str, replace: bool = False,
) -> Replaced | None:
    """Store `computed`'s result, once the token proves it is what was shown.

    Writes `(matter, "deadline", instances.item_id(instance, template))` at
    `L1` with the instruction `"computed from <anchor_field> under <source>;
    confirm against that source"` — the same two-field shape (a date,
    an instruction) the existing `deadline` command already writes, so the
    queue and the detail pane read an accepted template exactly as they read
    a hand-entered deadline; nothing downstream needs to know which door
    filed it. Refuses an occupied id unless `replace=True` (I-9 — `Sidecar.put`'s
    own rule, not a new one; the first write of a given `(instance,
    template)` is therefore atomic the same way `set_jurisdiction`'s is).

    This *is* the event log for a computed deadline: this package has no
    separate audit trail for a `deadline` record beyond the store write
    itself (the same write `_cmd_deadline`/`_post_deadline` perform), and the
    queue and `show` already read that write by reference — there is nothing
    this function adds on top of it to log.

    `token` must equal `computed.preview_token`, checked with no re-derivation
    of `computed` from anything else: a caller worried a preview has gone
    stale (the anchor or jurisdiction changed since it was shown) calls
    `compute()` again first and passes *that* fresh `Computed` here — see
    `server.py`'s accept endpoint, which does exactly that before calling this
    function, so a stale preview token compares against a token the current
    store state would not itself produce.
    """
    if not isinstance(token, str) or token != computed.preview_token:
        raise StaleToken(computed.matter, computed.instance, computed.template)

    item_id = instances.item_id(computed.instance, computed.template)
    # Named after the source, not "the court": this function is shared by
    # every pack's templates, and not every anchor runs under a court (the
    # venture pack's `election-83b` counts an IRS filing window under 26
    # U.S.C. § 83(b), with no court and no docket). "Confirm against the
    # court's notice" was accurate for custody/bankruptcy alone and false the
    # day a non-judicial template used this same writer (X7-drift audit,
    # 2026-09-11) — corrected to name what was already right there, the
    # source just stated, rather than assuming a forum that may not exist.
    #
    # *"That source"*, not *"the source above"* (same audit, second pass):
    # "above" is true at two of the three doors and false at the third. The
    # CLI prints `source:` on the line above `accepted:`, and the page shows
    # the source div above the Accept button — but this string is also read
    # back on its own, by `show`, the queue and the pane, where there is no
    # "above" to point at, and several `source` texts end in a PROVENANCE
    # sentence of their own that says "see the module-level note above",
    # so the stored line read "... note above.; confirm against the source
    # above" with the two "above"s meaning different things. The source is
    # named in this same sentence; "that source" points at it from every
    # door and assumes no layout.
    instruction = (
        f"computed from {computed.anchor_field} under {computed.source}; "
        "confirm against that source"
    )
    item = Classified(Rung.L1, computed.result_iso, instruction)
    return store.put(computed.matter, "deadline", item_id, item, overwrite=replace)
