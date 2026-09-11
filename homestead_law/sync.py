"""Sync — an operator act, never background (Decision 5, Wave 5 L5-sync).

`homestead.keep.sync` (floor 0.11.0) carries the mechanism: `SyncScope`,
`compose()` (score every candidate on `S4_EGRESS` under `Purpose.SYNC`,
drop what fails, freeze the rest into an `Envelope`), and `deliver()`
(exactly one of a URL or an `O_EXCL` file drop, behind a per-call confirm,
ledgered once — I-37/I-38, ratified by the E4-sync-core audit, 2026-09-11).
This module is the household's own binding: it turns `--matters
custody,bankruptcy` into a `SyncScope` the registry has checked, and it
decides *where* a sync goes without ever deciding *whether* one may — the
confirm the engine already requires is the only door that opens.

**Law has one table.** `homestead_law.store.Sidecar`/`Canonical` bind the
same SQLite file, so every scope here carries `tables=("sidecar",)` and
`compose()` is always handed `{"sidecar": <the caller's Sidecar>}` — never
a `Canonical` reader, which would only read back what `Sidecar` wrote.

**`--matters all` does not exist (I-40).** The engine already refuses an
empty or `L5` scope by construction; the one refusal it cannot make for
itself is a matter this repo has never registered — `all_matters()` is the
only enumeration (I-23), so a name outside it, or the literal `"all"`, is
refused here before `SyncScope` ever sees it.

**A destination is a place to send to, never a permission to send.**
Reading `HOMESTEAD_FLEET_URL` or `home()/fleet.url` only decides *where*
`deliver()` sends; `deliver()` still requires an explicit per-call confirm
before a byte moves, and a declined confirm ledgers nothing, exactly as it
does for a directly-passed URL. It is resolved **once**, by
`resolve_destination()`, and a surface that previews now and sends later
carries that answer forward rather than asking again — otherwise a
`fleet.url` appearing in between turns a previewed file drop into a POST
nobody approved (found by this bite's audit; see `confirm_exactly`).

**The envelope's `head` is the head at compose time.** `compose()` freezes
this household's pre-sync integrity head into the envelope, so an envelope
composed, held, and sent after further records were written ships the head
as it was when the operator looked — the envelope is what was shown, not a
live view. The receiving fleet is what notices a stale head (and
`homestead-fleet ingest`'s `--allow-stale` is *its* flag, not one this side
has); nothing here silently recomposes to freshen it, because a recomposed
envelope is a different envelope than the one that was previewed.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from homestead.keep import paths
from homestead.keep.egress import Wire
from homestead.keep.household import household_id
from homestead.keep.rungs import Rung
from homestead.keep.sync import (
    AlreadyDelivered,
    Confirm,
    Envelope,
    Receipt,
    SyncScope,
    TamperedEnvelope,
    UnnamedScope,
    compose,
    default_drop_dir,
    deliver,
)
from homestead_law.registry import all_matters, matter as _matter
from homestead_law.store import Sidecar

__all__ = [
    "UnknownMatter", "UnknownItemType", "NothingToSync",
    "HouseholdAlreadyInitialized",
    "scope_from", "item_types_for", "preview", "send", "send_to",
    "resolve_destination", "describe_destination", "preview_destination",
    "confirm_exactly", "init_household",
    # re-exported so a caller needs one import for the whole vocabulary
    "SyncScope", "Envelope", "Receipt", "Confirm",
    "UnnamedScope", "AlreadyDelivered", "TamperedEnvelope",
]

#: Law binds `Sidecar`/`Canonical` to one SQLite file — no second table a
#: sync could ever read from.
_TABLES = ("sidecar",)

#: The one item type every matter may hold that is not one of its pack's own
#: fields: `rules.accept()`/`cli`/`server` all write computed deadlines as
#: `(matter, "deadline", "<instance>.<template>")`. Named here rather than
#: in each surface so `item_types_for()` is the single answer to "what could
#: `--types` name?" — the Sync tab's checkboxes read it too.
_DEADLINE_ITEM_TYPE = "deadline"


class UnknownMatter(ValueError):
    """A `--matters` value naming a matter the registry does not
    have. The registry is the only enumeration (I-23); refused by name
    (I-11), never silently dropped from the scope it was named in."""


class UnknownItemType(ValueError):
    """A `--types` value no named matter could ever hold.

    Refused rather than carried (I-11): `compose()` narrows by item type,
    so a typo'd type is not an error there — it simply matches nothing, and
    the operator is shown an envelope of zero rows for a scope they believe
    they named. A name the registry does not know is a refusal, not a
    silent empty sync."""


class NothingToSync(ValueError):
    """A composed `Envelope` holding no rows.

    Refused **before** the confirm: a zero-row delivery still writes a file
    (or POSTs a body), still appends one `record_synced` row to the
    integrity chain and still shows one `RECORD_SYNCED` line — a ledgered
    sync of nothing. The operator would be asked to approve, and the
    household's own record would then say a sync happened, for a scope that
    turned out to name nothing at all."""


class HouseholdAlreadyInitialized(RuntimeError):
    """`--init-household` refuses once `household.id` already exists —
    minting a fresh id for a household whose fleet rows are keyed by the
    old one would fork its identity. Creating one is a one-time act; every
    sync after the first reads the id `household_id()` already minted."""


def item_types_for(matters: tuple[str, ...] | list[str]) -> set[str]:
    """Every item type a scope over `matters` could name — each pack's own
    classified field names, live off the registry (I-23), plus the one
    computed type every matter may hold (`deadline`).

    One answer, read by `scope_from`'s `--types` check and by the Sync tab's
    `GET /api/sync/options` alike, so the list the page offers and the list
    the refusal is measured against cannot drift apart. An unregistered
    matter here is `UnknownMatter`, the same refusal `scope_from` makes.
    """
    registered = set(all_matters())
    unknown = sorted(set(matters) - registered)
    if unknown:
        raise UnknownMatter(
            f"unregistered matter(s) {unknown} — registered: "
            f"{sorted(registered)}"
        )
    types = {_DEADLINE_ITEM_TYPE}
    for name in matters:
        types.update(_matter(name).fields)
    return types


def scope_from(
    matters: tuple[str, ...] | list[str],
    item_types: tuple[str, ...] | list[str] | None,
    ceiling: str,
) -> SyncScope:
    """The operator's `--matters`/`--types`/`--ceiling` (or the Sync tab's
    checkboxes and select), turned into a `SyncScope` — or refused by name.

    `matters` must name only matters `all_matters()` actually has; `"all"`
    is refused first, with its own message (I-40). An empty `matters`, an
    empty result after that check, or `ceiling="L5"` all reach the engine's
    own `UnnamedScope` unchanged — this only adds the checks the engine
    cannot make for itself (it has no registry). `ceiling` is a `Rung`
    value string; anything that does not parse is a plain `ValueError`
    naming the string — a call-site mistake, not a declined scope.

    `item_types`, when given, must name types the named matters could
    actually hold (`item_types_for()`): `compose()` treats an unknown type
    as a narrowing that matches nothing, so an unchecked typo composes a
    silently empty envelope rather than a refusal (I-11).
    """
    matters = tuple(matters)
    if "all" in matters:
        raise UnnamedScope(
            "'all' is not a matter — there is no --matters all (I-40); name "
            "each matter explicitly, e.g. --matters custody,bankruptcy"
        )
    known_types = item_types_for(matters)   # also makes the UnknownMatter refusal
    if item_types:
        stray = sorted(set(item_types) - known_types)
        if stray:
            raise UnknownItemType(
                f"unknown item type(s) {stray} for matter(s) "
                f"{sorted(set(matters))} — a type no named matter holds "
                "would narrow the scope to nothing rather than refuse"
            )
    try:
        ceiling_rung = Rung(ceiling)
    except ValueError:
        raise ValueError(
            f"unknown ceiling {ceiling!r} — one of L1, L2, L3, L4"
        ) from None

    return SyncScope(
        matters=matters,
        item_types=tuple(item_types) if item_types else None,
        ceiling=ceiling_rung,
        tables=_TABLES,
    )


def preview(store: Sidecar, scope: SyncScope) -> Envelope:
    """Compose one `Envelope` from this household's own sidecar — the
    engine's `compose()`, handed the one reader law ever has. Read-only:
    nothing here writes, ledgers, or sends."""
    return compose({"sidecar": store}, scope)


def _destination_url(url: str | None) -> str | None:
    """`url`, else `HOMESTEAD_FLEET_URL`, else `home()/fleet.url` — or
    `None` when none of the three names anything. Every one of these is a
    **destination**, read only to decide *where* `deliver()` sends, never
    a decision about *whether* it may. Blank or empty reads as absent."""
    if url:
        return url
    env = os.environ.get("HOMESTEAD_FLEET_URL")
    if env and env.strip():
        return env.strip()
    fleet_file = paths.home() / "fleet.url"
    if fleet_file.exists():
        content = fleet_file.read_text(encoding="utf-8").strip()
        if content:
            return content
    return None


def resolve_destination(
    *, url: str | None = None, drop_dir=None
) -> tuple[str | None, Path | None]:
    """Where a sync would go, decided **once** — exactly one of
    `(url, None)` or `(None, drop_dir)`.

    Order: `url`, else `HOMESTEAD_FLEET_URL`, else `home()/fleet.url`, else
    `drop_dir` if the caller named one, else `default_drop_dir()`. The drop
    directory comes back `.resolve()`d, which is what the engine's
    `deliver()` will build its `Wire` from, so the path a preview shows and
    the path a `Wire` carries are one string.

    Resolution is a separate step from delivery because a surface that
    previews and then sends does both at *different times*: `fleet.url` can
    appear, or `HOMESTEAD_FLEET_URL` change, in between. Resolving inside
    `send()` meant the operator could be shown `FILE …` and the envelope
    then leave over the network — found by this bite's audit. A surface
    that previews holds the pair this returns and hands it to `send_to()`.
    """
    dest = _destination_url(url)
    if dest is not None:
        return dest, None
    target = Path(drop_dir) if drop_dir is not None else default_drop_dir()
    return None, target.resolve()


def describe_destination(
    envelope_id: str, *, dest_url: str | None, dest_dir: Path | None
) -> str:
    """`"POST <url>"` or `"FILE <path>"` — the same `"<method> <url>"` shape
    the engine's `Wire` carries, so `confirm_exactly()` can compare the two
    as strings. A description, never a live `Wire`: nothing here sends."""
    if dest_url is not None:
        return f"POST {dest_url}"
    return f"FILE {dest_dir / f'{envelope_id}.json'}"   # type: ignore[operator]


def preview_destination(envelope_id: str, *, url: str | None = None, drop_dir=None) -> str:
    """The destination a `send()` with these same arguments would use —
    `resolve_destination()` described. Nothing here delivers or writes."""
    dest_url, dest_dir = resolve_destination(url=url, drop_dir=drop_dir)
    return describe_destination(envelope_id, dest_url=dest_url, dest_dir=dest_dir)


def confirm_exactly(envelope: Envelope, shown: str) -> Confirm:
    """A confirm that approves **only** the `Wire` this envelope and this
    already-shown destination produce, for a surface whose consent was
    given before the `Wire` existed.

    The browser's Send click is that surface: the operator approved the
    preview they were shown, not "whatever the next `deliver()` builds". A
    callback that returns `True` whatever it is handed is an ambient
    permission wearing a confirm's signature — it cannot tell the approved
    envelope from any other, and `keep/egress.py`'s whole contract ("the
    preview is the payload") rests on the confirm being able to. So this
    one re-checks both halves against what was shown:

    * the destination — `"<method> <url>"` must equal `shown`, the string
      the preview displayed; and
    * the bytes — the POST body must carry this `envelope_id`, and the FILE
      leg's byte count must be this envelope's own.

    Anything else is declined, and `deliver()`/`egress.send` turn that into
    `EgressRefused` with nothing written and nothing ledgered.
    """

    def confirm(wire: Wire) -> bool:
        if f"{wire.method} {wire.url}" != shown:
            return False
        if wire.method == "FILE":
            return wire.body == f"{len(envelope.to_bytes())} bytes"
        try:
            body = json.loads(wire.body)
        except (json.JSONDecodeError, TypeError):
            return False
        return isinstance(body, dict) and body.get("envelope_id") == envelope.envelope_id

    return confirm


def send_to(
    envelope: Envelope,
    *,
    dest_url: str | None,
    dest_dir: Path | None,
    confirm: Confirm,
) -> Receipt:
    """Deliver `envelope` to exactly the destination named here — no
    ambient lookup, so a caller that resolved a destination at preview time
    sends to that one and no other.

    A zero-row envelope is refused (`NothingToSync`) before the confirm is
    ever shown: nothing to sync is not an act to approve, and delivering it
    would ledger a sync of nothing. Everything else is the engine's
    `deliver()` unchanged — the same per-call confirm, the same
    `EgressRefused` on a declined one, the same one-row-each ledgering.
    """
    if (dest_url is None) == (dest_dir is None):
        raise ValueError(
            "send_to needs exactly one of dest_url= or dest_dir= — use "
            "resolve_destination() to get the pair"
        )
    if envelope.count == 0:
        raise NothingToSync(
            "nothing to sync: this scope composed 0 rows, so there is no "
            "act to confirm — widen --matters/--types or raise --ceiling"
        )
    if dest_url is not None:
        return deliver(envelope, confirm=confirm, url=dest_url)
    return deliver(envelope, confirm=confirm, drop_dir=dest_dir)


def send(
    envelope: Envelope,
    *,
    url: str | None = None,
    drop_dir=None,
    confirm: Confirm,
) -> Receipt:
    """Resolve the destination and deliver to it, in one act — the CLI's
    path, where the preview, the confirm and the send all happen inside one
    command and nothing can change underneath them.

    A surface that shows a preview and sends on a *later* request must
    instead hold `resolve_destination()`'s pair from preview time and call
    `send_to()` with it; see `resolve_destination`. `confirm` must still
    return `True` before a byte moves — this decides only *where*, never
    *whether*.
    """
    dest_url, dest_dir = resolve_destination(url=url, drop_dir=drop_dir)
    return send_to(envelope, dest_url=dest_url, dest_dir=dest_dir, confirm=confirm)


def init_household() -> str:
    """Mint `household.id`, refusing outright if one already exists.

    `household_id()` is idempotent by design — the id a household already
    has, read back rather than replaced — which is exactly wrong for an
    explicit `--init-household`, so this checks first and refuses by name
    before ever calling it; only an absent file reaches the engine's own
    O_EXCL create.
    """
    target = paths.home() / "household.id"
    if target.exists():
        raise HouseholdAlreadyInitialized(
            f"{target} already exists — a household id is minted once. "
            "Sync without --init-household to use it."
        )
    paths.ensure(target.parent)
    return household_id()
