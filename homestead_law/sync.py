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
does for a directly-passed URL.
"""
from __future__ import annotations

import os

from homestead.keep import paths
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
from homestead_law.registry import all_matters
from homestead_law.store import Sidecar

__all__ = [
    "UnknownMatter", "HouseholdAlreadyInitialized",
    "scope_from", "preview", "send", "preview_destination", "init_household",
    # re-exported so a caller needs one import for the whole vocabulary
    "SyncScope", "Envelope", "Receipt", "Confirm",
    "UnnamedScope", "AlreadyDelivered", "TamperedEnvelope",
]

#: Law binds `Sidecar`/`Canonical` to one SQLite file — no second table a
#: sync could ever read from.
_TABLES = ("sidecar",)


class UnknownMatter(ValueError):
    """A `--matters`/`--types` value naming a matter the registry does not
    have. The registry is the only enumeration (I-23); refused by name
    (I-11), never silently dropped from the scope it was named in."""


class HouseholdAlreadyInitialized(RuntimeError):
    """`--init-household` refuses once `household.id` already exists —
    minting a fresh id for a household whose fleet rows are keyed by the
    old one would fork its identity. Creating one is a one-time act; every
    sync after the first reads the id `household_id()` already minted."""


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
    own `UnnamedScope` unchanged — this only adds the one check the engine
    cannot make for itself (it has no registry). `ceiling` is a `Rung`
    value string; anything that does not parse is a plain `ValueError`
    naming the string — a call-site mistake, not a declined scope.
    """
    matters = tuple(matters)
    if "all" in matters:
        raise UnnamedScope(
            "'all' is not a matter — there is no --matters all (I-40); name "
            "each matter explicitly, e.g. --matters custody,bankruptcy"
        )
    registered = set(all_matters())
    unknown = sorted(set(matters) - registered)
    if unknown:
        raise UnknownMatter(
            f"unregistered matter(s) {unknown} — registered: "
            f"{sorted(registered)}"
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


def preview_destination(envelope_id: str, *, url: str | None = None) -> str:
    """The destination a `send()` with these same arguments would use — a
    plain description (`"POST <url>"`/`"FILE <path>"`), never a live
    `Wire`: nothing here calls `deliver()`, sends, or writes."""
    dest = _destination_url(url)
    if dest is not None:
        return f"POST {dest}"
    return f"FILE {default_drop_dir() / f'{envelope_id}.json'}"


def send(
    envelope: Envelope,
    *,
    url: str | None = None,
    drop_dir=None,
    confirm: Confirm,
) -> Receipt:
    """Deliver `envelope` through the engine's `deliver()` — one destination,
    resolved once, then handed straight to the same confirm contract
    `deliver()` already enforces: `url`, else `HOMESTEAD_FLEET_URL`, else
    `home()/fleet.url`, else `drop_dir` if given, else the engine's own
    `default_drop_dir()`. `confirm` must still return `True` before a byte
    moves — this function only decides *where*, never *whether*."""
    dest_url = _destination_url(url)
    if dest_url is not None:
        return deliver(envelope, confirm=confirm, url=dest_url)
    target = drop_dir if drop_dir is not None else default_drop_dir()
    return deliver(envelope, confirm=confirm, drop_dir=target)


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
