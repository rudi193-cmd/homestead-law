"""Matter instances — item ids that name *which instance* of a matter a record
belongs to (decision 2, plan wave 3; no engine change).

Until this bite every record filed under a matter used a single hardcoded item
id, `"primary"` (`put`'s `_cmd_put`) or a freeform label of the operator's own
choosing (`deadline`'s item id). That was fine for a household with one order
in one forum. This household has an NM custody order being registered in OR
(decision 1) — one matter, more than one *instance* of it — and nothing in the
engine's four-method store contract needed to change to say so: the store
already keys a record by `(matter, item_type, item_id)`, and an item id was
always just a string. This module is the convention that string now follows:

    item_id(instance)        -> "<instance>"
    item_id(instance, sub)   -> "<instance>.<sub>"

**Both halves share one closed alphabet, and it excludes the separator.**
`_ID_RE` accepts lowercase letters, digits and hyphens, one to forty
characters, starting with a letter or digit — and, because a dot can never
appear *inside* either half, `split_item_id` can always recover them by
splitting on the first one. No lookup, no schema, no ambiguity: a caller
handed a bare item id from the store never has to guess whether it is looking
at an instance or an instance-with-a-dot-in-it, because the alphabet makes the
second shape impossible to construct in the first place.

**This is a naming convention layered over the existing key, not a new
concept the engine has to know about.** `homestead.keep.store.key()` still
validates the whole tuple exactly as it always has (I-7); `item_id()` just
narrows what a caller may pass as the *third* component before it gets there,
for the callers that opt into the instance shape.

**Ids are labels, never names (I-15).** An id is operator-typed — a household
picks `"primary"`, or `"nm-order"`, or whatever short string is meaningful to
them — and it is never itself the content a rung protects. But it is still
*input*, and a malformed one is refused **by naming which component failed
and what shape was required, never by echoing what was typed** (I-11's
build/write-time refusal, held to I-15's rule that a refusal names a
reference, not a value). A matter or field name gets echoed elsewhere in this
package because it is drawn from a closed, published registry; an id has no
such registry to check it against, so this module treats it more
conservatively than that.
"""
from __future__ import annotations

import re

from homestead.keep.rungs import Classified
from homestead_law.store import Ref, Sidecar

__all__ = [
    "DEFAULT_INSTANCE", "ID_PATTERN", "InvalidId", "UnreadableStoredId",
    "item_id", "split_item_id", "instances_of", "records_of",
]

#: The instance every matter starts under absent an operator choice, and the
#: item id `put`/`deadline` always used before this bite — kept as the default
#: so a household with one instance sees no change at all.
DEFAULT_INSTANCE = "primary"

#: One alphabet for both halves of an item id: lowercase letters, digits and
#: hyphens, 1-40 characters, starting with a letter or digit. No dot (so the
#: split below is never ambiguous), no uppercase, no underscore, no leading
#: hyphen — narrower than `homestead.keep.store.key()`'s own rules (which
#: forbid only separators, NUL and surrounding whitespace) on purpose: this is
#: the stricter shape *this module's own callers* opt into, not a replacement
#: for the engine's key validation, which still runs underneath it either way.
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")


class InvalidId(ValueError):
    """An instance or sub id that does not match `ID_PATTERN`.

    Names the component (`"instance"` or `"sub"`) and the required shape —
    never the value that was typed (I-15). An id is a label; a caller that
    mistyped one is helped by being told the alphabet, not by seeing their own
    keystrokes echoed back, which would make this exception itself a second
    unscored surface for whatever they typed."""

    def __init__(self, component: str) -> None:
        super().__init__(
            f"{component} id is malformed — an id matches {ID_PATTERN.pattern} "
            "(lowercase letters, digits and hyphens, 1-40 characters, "
            f"starting with a letter or digit). An id is a label, never a "
            "name (I-15) — this refusal does not repeat what was typed."
        )
        self.component = component


class UnreadableStoredId(ValueError):
    """A record already on disk whose item id does not name an instance.

    Not an operator mistake — this is what a key written before this
    convention existed, by another tool, or by a test reaching past the CLI,
    looks like to `instances_of`. Names the matter and which *item types* hold
    one (references, both), never the id, on the same reasoning as
    `InvalidId`: a stored id this module cannot read is still a string
    somebody typed."""

    def __init__(self, matter: str, item_types: list[str]) -> None:
        super().__init__(
            f"{matter}: {len(item_types)} item type(s) hold a record whose "
            f"item id does not name an instance — {item_types}. An instance "
            f"id matches {ID_PATTERN.pattern}; a record filed under anything "
            "else cannot be attributed to an instance, so this list refuses "
            "rather than invent one or hide the record. This refusal does not "
            "repeat the id."
        )
        self.matter = matter
        self.item_types = tuple(item_types)


def _checked(component: str, value: object) -> str:
    if not isinstance(value, str) or not ID_PATTERN.match(value):
        raise InvalidId(component)
    return value


def item_id(instance: str, sub: str | None = None) -> str:
    """The stored item id for one instance, or one repeatable sub-record
    within it — `"<instance>"` or `"<instance>.<sub>"`.

    Both components are validated against `ID_PATTERN` before either is used,
    so a malformed instance is refused even when `sub` would also have been
    fine, and vice versa (I-11: absence — here, an unusable shape — fails
    closed before anything is built from it, never partially).
    """
    instance = _checked("instance", instance)
    if sub is None:
        return instance
    sub = _checked("sub", sub)
    return f"{instance}.{sub}"


def split_item_id(value: str) -> tuple[str, str | None]:
    """The inverse of `item_id` — `(instance, sub-or-None)`.

    Splits on the *first* `.`, which is unambiguous only because neither
    `item_id()` half may itself contain one — the entire reason `ID_PATTERN`
    excludes the dot rather than, say, requiring callers to escape it. Any
    string reaches this function (not only ones `item_id()` built), because
    the store can hold an item id written by an earlier, pre-instances bite —
    `split_item_id("hearing")` reads that as instance `"hearing"`, sub `None`,
    which is the correct, honest answer for a string with no dot in it, not a
    crash or a guess.
    """
    instance, sep, sub = value.partition(".")
    return instance, (sub if sep else None)


def instances_of(store: Sidecar, matter: str) -> tuple[str, ...]:
    """Every instance id this matter's stored records mention, sorted.

    A key-only scan: `store.records(matter)` is the store's own contract (the
    payload boundary is the store, not this function), and everything this
    reads from each pair is the ref's item id, split — no `.payload`, no gate,
    nothing that needs one. A matter with no records at all yields `()`, not
    `(DEFAULT_INSTANCE,)` — an instance exists once something is filed under
    it, never by assumption.

    **A stored id `item_id` could not have built refuses the whole scan**
    (`UnreadableStoredId`), rather than being skipped or listed. Both halves
    are held to `ID_PATTERN`, so `a.B` is as unreadable as `Upper`: the
    engine's `key()` is far wider than this module's alphabet — `Upper`,
    `has_underscore` and `it's-due` are all keys it will happily hold — and
    neither of the other two answers is honest about one. *Listing* it invents
    an instance no door can address (`item_id` refuses it, so `--id <that>`,
    `matter open` and `jurisdiction_of` all refuse the very id this function
    just offered); *skipping* it hides records from a list whose whole purpose
    is to say what is on file. I-11: refuse by name — and the name here is the
    matter and the item types involved, never the id itself, which this module
    does not echo (see `InvalidId`).
    """
    seen: set[str] = set()
    unreadable: set[str] = set()
    for ref, _record in store.records(matter):
        instance, sub = split_item_id(ref[2])
        # Both halves, not only the instance: `a.B` names instance `a`
        # perfectly well and still is not an id `item_id` could have built, so
        # its sub-record is unaddressable even though the instance is not.
        if ID_PATTERN.match(instance) and (sub is None or ID_PATTERN.match(sub)):
            seen.add(instance)
        else:
            unreadable.add(ref[1])
    if unreadable:
        raise UnreadableStoredId(matter, sorted(unreadable))
    return tuple(sorted(seen))


def records_of(
    store: Sidecar, matter: str, instance: str
) -> list[tuple[Ref, Classified]]:
    """This instance's records only — `store.records(matter)` filtered to the
    ones whose item id names `instance`.

    `instance` is validated first (via `item_id`, discarding the normalized
    result since only the shape check matters here), so a malformed instance
    refuses rather than silently matching nothing and looking like an empty
    instance."""
    instance = item_id(instance)
    return [
        (ref, record)
        for ref, record in store.records(matter)
        if split_item_id(ref[2])[0] == instance
    ]
