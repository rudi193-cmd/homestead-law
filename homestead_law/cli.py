"""CLI commands that do real work — entity resolution, decision memory, matter input.

Every command here operates on a real household root (``$HOMESTEAD_HOME`` or
``~/.homestead``), not a throwaway.  Nestor's seam is bound and a SqliteStore
is opened at ``<root>/nestor-law.db`` before any command runs.

**Covenant**: no command here seals anything.  ``resolve`` proposes; ``orders
propose`` proposes.  Sealing is a human act, done through ``nestor ui`` or a
caller that passes a ``verifier=`` — never through this CLI.

**Nestor is optional.** ``put``, ``deadline``, ``show`` and ``queue`` — the
commands a household uses to enter and read its own records — need only the
engine.  ``resolve``, ``propose``, ``orders`` and ``verify`` need the ``entity``
extra and say so, in one line, when it is missing.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Sequence

from homestead.keep import paths

from homestead_law import instances, nestor_seam
from homestead_law.jurisdiction import (
    JurisdictionAbsent,
    UnsupportedJurisdiction,
    jurisdiction_of,
    set_jurisdiction,
)
from homestead_law.nestor_store import get_store
from homestead_law.registry import all_matters, matter
from homestead_law.store import RecordExists, Sidecar

__all__ = ["run_cli"]

# ── bootstrap ───────────────────────────────────────────────────────────────

def _boot(household_root: Path | None = None) -> None:
    """Bind the seam and ensure the household root exists."""
    root = Path(household_root) if household_root is not None else paths.home()
    root.mkdir(parents=True, exist_ok=True)
    (root / "keep").mkdir(parents=True, exist_ok=True)
    nestor_seam.bind(root)


def _needs_nestor() -> bool:
    """True when the Nestor-backed command can run; otherwise says why not."""
    if nestor_seam.available():
        return True
    print(f"  {nestor_seam.NOT_INSTALLED}", file=sys.stderr)
    return False


# ── resolve ─────────────────────────────────────────────────────────────────

def _cmd_resolve(args: Sequence[str]) -> int:
    """``resolve <domain> <surface>`` — resolve an entity against sealed aliases.

    Domains: party, court, citation, jurisdiction.
    If no sealed match exists, shows the top draft suggestion (if any).
    """
    if len(args) < 2:
        print("usage: homestead-law resolve <domain> <surface>", file=sys.stderr)
        print("  domains: party, court, citation, jurisdiction", file=sys.stderr)
        return 1

    domain = args[0]
    surface = " ".join(args[1:])
    valid = ("party", "court", "citation", "jurisdiction")
    if domain not in valid:
        print(f"unknown domain {domain!r} — one of {valid}", file=sys.stderr)
        return 1
    if not _needs_nestor():
        return 1

    _boot()
    store = get_store()
    resolver = nestor_seam.resolver_for(domain, store)
    result = resolver.resolve(surface)

    if result["sealed"]:
        print(f"  {surface}")
        print(f"  → {result['canonical']}  (sealed, confidence {result['confidence']:.2f})")
        prov = result.get("provenance", {})
        if prov.get("verifier"):
            print(f"    verified by: {prov['verifier']}")
    elif result["provenance"].get("suggestion"):
        print(f"  {surface}")
        print(f"  ~ {result['provenance']['suggestion']}  (draft suggestion, confidence {result['confidence']:.2f})")
        print(f"    not sealed — use `nestor ui` to seal")
    else:
        print(f"  {surface}")
        print(f"  ? no match")
    return 0


def _cmd_propose(args: Sequence[str]) -> int:
    """``propose <domain> <surface> <canonical>`` — propose an entity alias (draft).

    The machine proposes; a human seals.  Use ``nestor ui`` to review and seal.
    """
    if len(args) < 3:
        print("usage: homestead-law propose <domain> <surface> <canonical>", file=sys.stderr)
        return 1

    domain = args[0]
    surface = args[1]
    canonical = " ".join(args[2:])
    valid = ("party", "court", "citation", "jurisdiction")
    if domain not in valid:
        print(f"unknown domain {domain!r} — one of {valid}", file=sys.stderr)
        return 1
    if not _needs_nestor():
        return 1

    _boot()
    store = get_store()
    resolver = nestor_seam.resolver_for(domain, store)
    result = resolver.propose(surface, canonical)

    if result.get("sealed"):
        print(f"  already sealed: {surface} → {canonical}")
    elif result.get("draft"):
        print(f"  proposed: {surface} → {canonical}  (draft)")
        print(f"  seal with `nestor ui` when verified")
    return 0


# ── orders (decision memory) ───────────────────────────────────────────────

def _cmd_orders(args: Sequence[str]) -> int:
    """``orders <subcommand> ...`` — court orders and decisions.

    Subcommands:
        propose <question> <commitment>   — propose a decision (draft)
        check <question>                  — what constrains this?
        list                              — all decisions in the matter
    """
    if not args:
        print("usage: homestead-law orders <propose|check|list> ...", file=sys.stderr)
        return 1

    sub = args[0]
    rest = args[1:]

    if not _needs_nestor():
        return 1
    _boot()
    store = get_store()
    dm = nestor_seam.decisions_for("court", store)

    if sub == "propose":
        if len(rest) < 2:
            print("usage: homestead-law orders propose <question> <commitment>", file=sys.stderr)
            print('  e.g.: homestead-law orders propose "parenting time schedule" "Tue/Thu 3-7pm, alt weekends"', file=sys.stderr)
            return 1
        question = rest[0]
        commitment = " ".join(rest[1:])
        result = dm.propose(question, commitment, origin="homestead-law")
        print(f"  proposed: {question}")
        print(f"         → {commitment}")
        print(f"  pair_id: {result['id']}")
        print(f"  status:  {result['status']}  (seal with `nestor ui`)")
        return 0

    elif sub == "check":
        if not rest:
            print("usage: homestead-law orders check <question>", file=sys.stderr)
            print('  e.g.: homestead-law orders check "parenting time schedule"', file=sys.stderr)
            return 1
        question = " ".join(rest)
        result = dm.constraints_on(question, fuzzy_bar=0.45)
        print(f"  question: {question}")
        print(f"  match:    {result['match']} (similarity {result['similarity']:.2f})")
        if result["live"]:
            live = result["live"]
            seal_mark = "sealed" if live["sealed"] else "draft"
            print(f"  live:     {live['commitment']}  ({seal_mark})")
            if live.get("reason"):
                print(f"  reason:   {live['reason']}")
            if live.get("verifier"):
                print(f"  verifier: {live['verifier']}")
        else:
            print(f"  live:     (none)")
        if result["constraints"]:
            print(f"  constraints ({len(result['constraints'])}):")
            for c in result["constraints"]:
                direction = "←" if c["direction"] == "in" else "→"
                print(f"    {direction} {c['kind']}: {c.get('other_commitment', '?')}")
        if result["proposed"]:
            print(f"  proposed edges ({len(result['proposed'])}):")
            for p in result["proposed"]:
                direction = "←" if p["direction"] == "in" else "→"
                print(f"    {direction} {p['kind']}: {p.get('other_commitment', '?')} (unsigned)")
        if result["rejected"]:
            print(f"  rejected ({len(result['rejected'])}):")
            for r in result["rejected"]:
                reopen = f"  (reopen when: {r['reopen_when']})" if r.get("reopen_when") else ""
                print(f"    ✗ {r['option']}: {r['reason']}{reopen}")
        if result["lineage"]:
            print(f"  lineage ({len(result['lineage'])}):")
            for l in result["lineage"]:
                print(f"    superseded: {l['commitment']}")
        return 0

    elif sub == "list":
        decisions = dm.all_decisions()
        if not decisions:
            print("  (no decisions recorded)")
            return 0
        print(f"  {len(decisions)} decision(s):")
        for i, d in enumerate(decisions, 1):
            seal_mark = "sealed" if d.get("status") == "sealed" else "draft"
            q = d.get("source_text", "?")
            c = d.get("target_text", "?")
            print(f"  {i}. [{seal_mark}] {q}")
            print(f"     → {c}")
        return 0

    else:
        print(f"unknown subcommand {sub!r} — one of: propose, check, list", file=sys.stderr)
        return 1


# ── put (real record input) ────────────────────────────────────────────────

def _cmd_put(args: Sequence[str]) -> int:
    """``put <matter> <field> <value> [--id instance] [--sub sub]`` — store a
    real record.

    Writes to the household's law database (not a throwaway). The value is
    classified at the pack's declared rung — no rung is chosen here.

    ``--id`` names which instance of the matter the value belongs to
    (default ``primary`` — unchanged from before this bite, for a household
    with only one instance of a matter). ``--sub`` is only for a field the
    pack declares ``REPEATABLE`` — a sub-id, never a name (I-15); a value not
    on file yet is stored under a fresh one, not looked up.

    The rule runs both ways: a field the pack does **not** declare
    ``REPEATABLE`` refuses a ``--sub``, and a field it **does** declare
    refuses a write *without* one. Without that second half a repeatable
    field silently lands in the instance's single slot — the exact
    overwrite-the-first-child failure the sub-id exists to abolish — under a
    key ``instances.split_item_id`` then reads as a bare instance, so nothing
    downstream can tell it from an instance-level record. There is no default
    sub: a sub-id is the operator's own label, and inventing one here would be
    naming a record on their behalf (I-15).

    If the field involves a party name (opposing_party, child_name), the name
    is also proposed to Nestor's party resolver as a draft alias.
    """
    id_opt = instances.DEFAULT_INSTANCE
    sub_opt: str | None = None
    filtered: list[str] = []
    i = 0
    while i < len(args):
        if args[i] == "--id" and i + 1 < len(args):
            id_opt = args[i + 1]
            i += 2
        elif args[i] == "--sub" and i + 1 < len(args):
            sub_opt = args[i + 1]
            i += 2
        else:
            filtered.append(args[i])
            i += 1
    args = filtered

    if len(args) < 3:
        print("usage: homestead-law put <matter> <field> <value> [--id instance] [--sub sub]", file=sys.stderr)
        print(f"  matters: {', '.join(all_matters())}", file=sys.stderr)
        for name in all_matters():
            print(f"  fields ({name}): {', '.join(matter(name).fields)}", file=sys.stderr)
        return 1

    matter_name = args[0]
    field = args[1]
    value = " ".join(args[2:])

    try:
        mt = matter(matter_name)
    except KeyError:
        print(f"unknown matter {matter_name!r} — registered: {', '.join(all_matters())}", file=sys.stderr)
        return 1

    if field not in mt.fields:
        print(f"unknown field {field!r} for {matter_name} — fields: {', '.join(mt.fields)}", file=sys.stderr)
        return 1

    if sub_opt is not None and field not in mt.repeatable:
        print(
            f"refused: field {field!r} does not accept --sub for {matter_name!r} "
            "— it is not declared REPEATABLE",
            file=sys.stderr,
        )
        return 1

    if sub_opt is None and field in mt.repeatable:
        print(
            f"refused: field {field!r} is declared REPEATABLE for "
            f"{matter_name!r} and needs a --sub — one record per sub-id, so a "
            "second one does not overwrite the first. A sub-id is a label you "
            "choose (--sub c1), never a name.",
            file=sys.stderr,
        )
        return 1

    try:
        item_id = instances.item_id(id_opt, sub_opt)
    except instances.InvalidId as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1

    from homestead.keep.rungs import Classified, derived_of

    rung = mt.fields[field]

    derived = None
    if rung.value in ("L3", "L4"):
        # The pack's own declaration, never a second table (decision 3). Two
        # copies of this text — cli.py's and server.py's — used to drift from
        # each other and from the pack; both doors now read the one sentence
        # a pack author wrote.
        derived = derived_of(mt.schema, field)

    _boot()
    sidecar = Sidecar()
    item = Classified(rung, value, derived)
    replaced = sidecar.put(matter_name, field, item_id, item, overwrite=True)

    print(f"  stored: {matter_name}/{field}/{item_id}")
    print(f"  rung:   {rung.value}")
    if replaced:
        print(f"  (replaced previous value)")

    # propose party names to Nestor's entity resolver
    _maybe_propose_party(field, value)

    return 0


def _maybe_propose_party(field: str, value: str) -> None:
    """If the field is a party name, propose it to the entity resolver.

    The line it prints names the **field**, never the value. `child_name` is L4
    and `opposing_party` L3, and the gate is what decides where either may be
    rendered; a confirmation line printed straight from `argv` is a second door
    onto the same datum that scored nothing (I-16), and a terminal transcript is
    a log (I-15). `show custody child_name` is the gated way to read it back.
    """
    party_fields = {"opposing_party", "child_name"}
    if field not in party_fields or not nestor_seam.available():
        return

    try:
        store = get_store()
        resolver = nestor_seam.resolver_for("party", store)
        resolver.propose(value, value, reason=f"entered as {field}")
        print(f"  proposed to party resolver: {field}")
    except Exception:
        pass


# ── deadline ───────────────────────────────────────────────────────────────

def _cmd_deadline(args: Sequence[str]) -> int:
    """``deadline <matter> <id> <date> [instruction] [--sub sub]`` — add a real
    deadline.

    The date is parsed by the engine's one strict parser and stored in its ISO
    form; a date it cannot read is refused here, in one line, rather than stored
    and met later as a gap on the queue. The optional instruction is the derived
    form shown on the ambient queue when the rung withholds the date. Rung
    defaults to L1 (public date); pass ``--rung L3`` or ``--rung L4`` to
    classify higher.

    **Every deadline is addressed to an instance** (decision 2, and the audit's
    ruling on this bite): what is stored is always
    ``homestead_law.instances.item_id(instance, name)`` — ``"<instance>.<name>"``
    — never a free-form label. Without ``--sub``, ``<id>`` is the deadline's
    *name* within the default instance, so ``deadline custody hearing …`` files
    ``primary.hearing``: the command line an operator already knows is
    unchanged, and the key it writes is now addressable. With ``--sub``,
    ``<id>`` names the instance and ``--sub`` the deadline within it, so a
    second registered order in this matter carries its own ``hearing`` without
    colliding with the first one's.

    A free-form id is refused by name, not stored. That is not decoration: a
    deadline whose id is not instance-shaped cannot be attributed to an
    instance at all, so `instances.instances_of` (a key scan) would read the
    label itself as a phantom instance — and `show <matter>` and
    `/api/instances` would then ask `jurisdiction_of` about an id no door can
    address. L3-deadline-templates' ``(matter, "deadline", "<inst>.<template>")``
    and the queue's matter+instance naming both rest on this shape.
    """
    rung_str = "L1"
    sub_opt: str | None = None
    filtered: list[str] = []
    i = 0
    while i < len(args):
        if args[i] == "--rung" and i + 1 < len(args):
            rung_str = args[i + 1]
            i += 2
        elif args[i] == "--sub" and i + 1 < len(args):
            sub_opt = args[i + 1]
            i += 2
        else:
            filtered.append(args[i])
            i += 1
    args = filtered

    if len(args) < 3:
        print("usage: homestead-law deadline <matter> <id> <date> [instruction] [--sub sub]", file=sys.stderr)
        print('  e.g.: homestead-law deadline custody hearing 2026-09-15 "Custody hearing"   (files primary.hearing)', file=sys.stderr)
        print('  e.g.: homestead-law deadline custody evaluation 2026-08-12 --rung L4 "A submission is due"', file=sys.stderr)
        print('  e.g.: homestead-law deadline custody or-order 2026-09-15 --sub hearing   (another instance)', file=sys.stderr)
        print("  an id is a label, never a name (I-15), and matches "
              f"{instances.ID_PATTERN.pattern}", file=sys.stderr)
        return 1

    matter_name = args[0]
    id_arg = args[1]
    date = args[2]
    instruction = " ".join(args[3:]) if len(args) > 3 else None

    # An option this command does not take would otherwise be swept into the
    # positionals and end up *inside the stored instruction* — and `--id` is
    # exactly the one an operator will reach for, since `put` and `show` both
    # have it and this command's instance is named by the positional instead.
    # Silently storing "Custody hearing --id or-order" is the store agreeing to
    # something nobody typed, so it is refused by name.
    unknown = [a for a in args if a.startswith("--")]
    if unknown:
        print(
            f"refused: unknown option(s) {unknown} for deadline — it takes "
            "--rung and --sub; the instance is the positional id (with --sub) "
            "or `primary` (without it)",
            file=sys.stderr,
        )
        return 1

    try:
        matter(matter_name)
    except KeyError:
        print(f"unknown matter {matter_name!r} — registered: {', '.join(all_matters())}", file=sys.stderr)
        return 1

    from homestead.keep.dates import UnparseableDate, parse_deadline
    from homestead.keep.rungs import Classified, Rung
    from homestead.keep.store import InvalidKey

    try:
        rung = Rung(rung_str)
    except ValueError:
        print(f"unknown rung {rung_str!r} — one of: L1, L2, L3, L4, L5", file=sys.stderr)
        return 1

    # The one strict parser, on this door too (I-1/I-2). The browser UI already
    # parses here; the CLI stored whatever was typed, so `deadline custody
    # hearing "next Tuesday"` went in unread and came back as a gap on the queue
    # weeks later — the refusal belongs where the operator can still fix it.
    # The ISO form is what is stored, so the two doors write the same string.
    try:
        date = parse_deadline(date).iso
    except UnparseableDate as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1

    derived = instruction
    if rung.value in ("L3", "L4") and not derived:
        derived = "A deadline is on file"

    # Without --sub the positional is the deadline's *name* under the default
    # instance (`primary.<id>`); with it, the positional is the instance and
    # --sub the name. Either way `item_id` validates both halves, so no
    # free-form deadline id is ever written.
    instance, name = (
        (id_arg, sub_opt) if sub_opt is not None
        else (instances.DEFAULT_INSTANCE, id_arg)
    )
    try:
        item_id = instances.item_id(instance, name)
    except instances.InvalidId as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1

    _boot()
    sidecar = Sidecar()
    item = Classified(rung, date, derived)
    try:
        replaced = sidecar.put(matter_name, "deadline", item_id, item, overwrite=True)
    except InvalidKey as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1

    print(f"  stored: {matter_name}/deadline/{item_id}")
    print(f"  date:   {date}  (rung {rung.value})")
    if instruction:
        print(f"  instruction: {instruction}")
    if replaced:
        print(f"  (replaced previous value)")
    return 0


# ── show (read back, through the gate) ─────────────────────────────────────

def _cmd_show(args: Sequence[str]) -> int:
    """``show [matter] [item_type [item_id]] [--id instance] [--sub sub]`` —
    read a matter's records back.

    With no argument, lists every registered matter and how many records each
    holds.  With a matter and nothing else, lists that matter's *instances*
    (each with its jurisdiction, or a note that none is set) — an id is a
    label, never a name (I-15), so what is listed here is a reference to open
    with ``--id``, not a name to read anything from.  Pass ``--id`` to list one
    instance's records instead, exactly as the list pane draws them
    (``S1_LIST``: L1–L3 payloads, the derived form for L4, nothing for L5 —
    I-16 holds here exactly as on the window).  With an item type, opens a
    record in the detail pane (``S1_DETAIL``: L4 renders, L5 is still refused)
    and prints any advisory beneath it; the raw ``item_id`` positional, when
    given, is used exactly as typed (unchanged from before this bite) —
    ``--id``/``--sub`` compose one only when it is omitted, defaulting to the
    ``primary`` instance.
    """
    from homestead_law.app import advisories
    from homestead_law.app.window import Window

    id_opt: str | None = None
    sub_opt: str | None = None
    filtered: list[str] = []
    i = 0
    while i < len(args):
        if args[i] == "--id" and i + 1 < len(args):
            id_opt = args[i + 1]
            i += 2
        elif args[i] == "--sub" and i + 1 < len(args):
            sub_opt = args[i + 1]
            i += 2
        else:
            filtered.append(args[i])
            i += 1
    args = filtered

    _boot()
    sidecar = Sidecar()

    if not args:
        for name in all_matters():
            n = len(sidecar.records(name))
            print(f"  {name}: {n} record(s)")
        return 0

    matter_name = args[0]
    try:
        matter(matter_name)
    except KeyError:
        print(f"unknown matter {matter_name!r} — registered: {', '.join(all_matters())}", file=sys.stderr)
        return 1

    window = Window()

    if len(args) == 1 and id_opt is None:
        # No item type and no --id: list instances, not records — the id
        # printed here is a label to pass to --id, never content (I-15).
        try:
            ids = instances.instances_of(sidecar, matter_name)
        except instances.UnreadableStoredId as exc:
            print(f"refused: {exc}", file=sys.stderr)
            return 1
        if not ids:
            print(f"  {matter_name}: nothing on file — `homestead-law put {matter_name} <field> <value>`")
            return 0
        print(f"  {matter_name} instances:")
        for inst in ids:
            try:
                code = jurisdiction_of(sidecar, matter_name, inst)
            except JurisdictionAbsent:
                code = "no jurisdiction set"
            print(f"  {inst}  ({code})")
        return 0

    if len(args) == 1:
        # --id given: this instance's records, in the pre-instances flat form.
        try:
            rows = window.open_list(instances.records_of(sidecar, matter_name, id_opt))
        except instances.InvalidId as exc:
            print(f"refused: {exc}", file=sys.stderr)
            return 1
        if not rows:
            print(f"  {matter_name}/{id_opt}: nothing on file")
            return 0
        print(f"  {matter_name}/{id_opt}:")
        for row in rows:
            _, item_type, item_id = row.ref
            sub = instances.split_item_id(item_id)[1]
            where = item_type if sub is None else f"{item_type}/{sub}"
            print(f"  [{row.rung.value}]  {where}: {row.text}")
        return 0

    # Load-bearing despite the discarded result: `Window.open_list` is what
    # populates the window's record map, and `open_detail` below reads the
    # record out of it rather than out of a row (so nothing a `Row` carries is
    # ever a payload). Dropping this line makes every detail open a `KeyError`.
    window.open_list(sidecar.records(matter_name))

    from homestead.keep.store import InvalidKey

    item_type = args[1]
    if len(args) > 2:
        item_id = args[2]
    elif id_opt is not None or sub_opt is not None:
        try:
            item_id = instances.item_id(id_opt or instances.DEFAULT_INSTANCE, sub_opt)
        except instances.InvalidId as exc:
            print(f"refused: {exc}", file=sys.stderr)
            return 1
    else:
        item_id = instances.DEFAULT_INSTANCE
    ref = (matter_name, item_type, item_id)
    try:
        present = sidecar.has(*ref)
    except InvalidKey as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    if not present:
        print(f"  {matter_name}/{item_type}/{item_id}: no such record", file=sys.stderr)
        return 1
    served = window.open_detail(ref)
    from homestead.keep.rungs import Disposition

    print(f"  {matter_name}/{item_type}/{item_id}  [{served.rung.value}]")
    if served.disposition is Disposition.RENDER:
        print(f"  {served.value}")
    else:
        print("  This record is sealed and is not shown here.")
    for line in advisories.advisory_lines(sidecar, ref):
        print(f"  ~ {line}")
    return 0


# ── matter (open an instance) ───────────────────────────────────────────────

def _cmd_matter(args: Sequence[str]) -> int:
    """``matter open <matter> --id <instance> --jurisdiction <code> [--replace]``
    — declare an instance's jurisdiction, opening it.

    This is how an instance of a matter comes to exist under this bite: there
    is no separate "create" step, because the one fact every instance needs
    before anything else can be filed under it (or computed from a date in
    it) is which forum it is in (decision 1; provisional I-42). Refuses a
    ``--jurisdiction`` outside the matter's own pack (never a guess), and
    refuses re-opening an already-open instance unless ``--replace`` is given
    (I-9 — the store's own unconsented-overwrite rule, not a new one).

    ``--id`` is a label, never a name (I-15): pick anything that matches
    ``homestead_law.instances.ID_PATTERN`` and is meaningful to your
    household — it is never itself the content a rung protects.
    """
    if not args or args[0] != "open":
        print("usage: homestead-law matter open <matter> --id <instance> --jurisdiction <code> [--replace]", file=sys.stderr)
        return 1

    id_opt: str | None = None
    jurisdiction_opt: str | None = None
    replace = False
    positional: list[str] = []
    i = 1
    while i < len(args):
        if args[i] == "--id" and i + 1 < len(args):
            id_opt = args[i + 1]
            i += 2
        elif args[i] == "--jurisdiction" and i + 1 < len(args):
            jurisdiction_opt = args[i + 1]
            i += 2
        elif args[i] == "--replace":
            replace = True
            i += 1
        else:
            positional.append(args[i])
            i += 1

    if len(positional) != 1 or id_opt is None or jurisdiction_opt is None:
        print("usage: homestead-law matter open <matter> --id <instance> --jurisdiction <code> [--replace]", file=sys.stderr)
        return 1

    matter_name = positional[0]
    try:
        matter(matter_name)
    except KeyError:
        print(f"unknown matter {matter_name!r} — registered: {', '.join(all_matters())}", file=sys.stderr)
        return 1

    _boot()
    sidecar = Sidecar()
    try:
        replaced = set_jurisdiction(
            sidecar, matter_name, id_opt, jurisdiction_opt, replace=replace
        )
    except instances.InvalidId as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    except UnsupportedJurisdiction as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    except RecordExists:
        print(
            f"refused: {matter_name}/{id_opt} is already open — pass --replace "
            "to change its jurisdiction",
            file=sys.stderr,
        )
        return 1

    print(f"  opened: {matter_name}/{id_opt}")
    print(f"  jurisdiction: {jurisdiction_opt}")
    if replaced:
        print("  (replaced the previous jurisdiction)")
    return 0


# ── queue (real) ───────────────────────────────────────────────────────────

def _cmd_queue(args: Sequence[str]) -> int:
    """``queue [--today YYYY-MM-DD]`` — what's due, from real data."""
    import datetime as dt

    from homestead.keep.dates import UnparseableDate, parse_deadline

    today = dt.date.today().isoformat()
    i = 0
    while i < len(args):
        if args[i] == "--today" and i + 1 < len(args):
            today = args[i + 1]
            i += 2
        else:
            i += 1

    # `--today` reaches the same parser every date does, here rather than deep
    # in `_urgency` — an unreadable one used to surface as a traceback, and only
    # when a deadline happened to exist to compare it against.
    try:
        today = parse_deadline(today).iso
    except UnparseableDate as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1

    _boot()
    sidecar = Sidecar()

    from homestead_law import queue as queue_mod

    items = queue_mod.queue(sidecar, today=today)
    # Reference lines (`queue.notices`) print after the items and are printed
    # even when nothing is due: a cross-matter interaction has no date, so it
    # neither expires nor waits its turn, and "nothing due" would otherwise
    # swallow it. One line each, no rung marker and no urgency — it is not a
    # deadline and must not read like one.
    notices = queue_mod.notices(sidecar)
    if not items:
        print("  nothing due")
    else:
        print(f"  as of {today}:")
    for item in items:
        if item.gap:
            mark = "date unreadable"
        elif item.overdue:
            mark = f"overdue by {abs(item.days_until)}d"
        else:
            mark = f"in {item.days_until}d"
        # Named by matter and instance (a reference — I-15), not by the raw
        # item id, which may carry a sub the operator never asked to see here.
        print(f"  [{item.rung.value}]  {item.matter}/{item.instance}  {item.shown}  ·  {mark}")
    for line in notices:
        print(f"  note: {line}")
    return 0


# ── verify ─────────────────────────────────────────────────────────────────

def _cmd_verify(args: Sequence[str]) -> int:
    """``verify`` — verify the Nestor ledger chain."""
    if not _needs_nestor():
        return 1
    _boot()
    ok = nestor_seam.verify_ledger()
    if ok:
        print("  ledger: intact")
    else:
        print("  ledger: BROKEN — the hash chain does not verify", file=sys.stderr)
    return 0 if ok else 1


# ── dispatch ───────────────────────────────────────────────────────────────

def _cmd_ui(args: Sequence[str]) -> int:
    """``ui [--port N]`` — open the intake and dashboard UI in a browser."""
    from homestead_law.server import serve

    port = 8383
    i = 0
    while i < len(args):
        if args[i] == "--port" and i + 1 < len(args):
            try:
                port = int(args[i + 1])
            except ValueError:
                print(f"refused: --port {args[i + 1]!r} is not a number", file=sys.stderr)
                return 1
            if not 0 <= port <= 65535:
                print(f"refused: --port {port} is not a port number", file=sys.stderr)
                return 1
            i += 2
        else:
            i += 1

    serve(port=port)
    return 0


COMMANDS = {
    "resolve": (_cmd_resolve, "resolve <domain> <surface> — entity resolution"),
    "propose": (_cmd_propose, "propose <domain> <surface> <canonical> — propose an alias"),
    "orders": (_cmd_orders, "orders <propose|check|list> — court decisions"),
    "put": (_cmd_put, "put <matter> <field> <value> [--id inst] [--sub sub] — store a record"),
    "deadline": (_cmd_deadline, "deadline <matter> <id> <date> [--sub sub] — add a deadline"),
    "show": (_cmd_show, "show [matter] [item [id]] [--id inst] [--sub sub] — read records back, gated"),
    "matter": (_cmd_matter, "matter open <matter> --id inst --jurisdiction code — open an instance"),
    "queue": (_cmd_queue, "queue — what's due"),
    "verify": (_cmd_verify, "verify — check the Nestor ledger chain"),
    "ui": (_cmd_ui, "ui — intake and dashboard in the browser"),
}


def run_cli(argv: Sequence[str]) -> int:
    """Dispatch to a CLI command.  Returns the exit code."""
    if not argv:
        print("homestead-law commands:", file=sys.stderr)
        for name, (_, desc) in COMMANDS.items():
            print(f"  {name:12s} {desc}", file=sys.stderr)
        return 1

    cmd = argv[0]
    if cmd not in COMMANDS:
        print(f"unknown command {cmd!r}", file=sys.stderr)
        print(f"  commands: {', '.join(COMMANDS)}", file=sys.stderr)
        return 1

    handler, _ = COMMANDS[cmd]
    return handler(list(argv[1:]))
