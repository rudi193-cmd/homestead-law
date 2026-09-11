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

from homestead_law import nestor_seam
from homestead_law.nestor_store import get_store
from homestead_law.registry import all_matters, matter
from homestead_law.store import Sidecar

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
    """``put <matter> <field> <value>`` — store a real record.

    Writes to the household's law database (not a throwaway). The value is
    classified at the pack's declared rung — no rung is chosen here.

    If the field involves a party name (opposing_party, child_name), the name
    is also proposed to Nestor's party resolver as a draft alias.
    """
    if len(args) < 3:
        print("usage: homestead-law put <matter> <field> <value>", file=sys.stderr)
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

    from homestead.keep.rungs import Classified, Rung

    rung = mt.fields[field]

    derived = None
    if rung.value in ("L3", "L4"):
        derived = _default_derived(field, value)

    _boot()
    sidecar = Sidecar()
    item = Classified(rung, value, derived)
    replaced = sidecar.put(matter_name, field, "primary", item, overwrite=True)

    print(f"  stored: {matter_name}/{field}/primary")
    print(f"  rung:   {rung.value}")
    if replaced:
        print(f"  (replaced previous value)")

    # propose party names to Nestor's entity resolver
    _maybe_propose_party(field, value)

    return 0


def _default_derived(field: str, value: str) -> str:
    """A safe derived form for L3/L4 fields — what the ambient queue shows."""
    derivations = {
        "case_number": "A case number is on file",
        "docket": "A docket entry is on file",
        "opposing_party": "The other parent is named",
        "parenting_time": "A parenting-time obligation is on file",
        "child_name": "A minor child is named in this matter",
        "diagnosis": "A medical category is on file for a person",
        "notes": "An operator note is on file",
    }
    return derivations.get(field, f"A {field.replace('_', ' ')} is on file")


def _maybe_propose_party(field: str, value: str) -> None:
    """If the field is a party name, propose it to the entity resolver."""
    party_fields = {"opposing_party", "child_name"}
    if field not in party_fields or not nestor_seam.available():
        return

    try:
        store = get_store()
        resolver = nestor_seam.resolver_for("party", store)
        resolver.propose(value, value, reason=f"entered as {field}")
        print(f"  proposed to party resolver: {value}")
    except Exception:
        pass


# ── deadline ───────────────────────────────────────────────────────────────

def _cmd_deadline(args: Sequence[str]) -> int:
    """``deadline <matter> <id> <date> [instruction]`` — add a real deadline.

    The date is an ISO date (YYYY-MM-DD). The optional instruction is the
    derived form shown on the ambient queue when the rung withholds the date.
    Rung defaults to L1 (public date); pass ``--rung L3`` or ``--rung L4`` to
    classify higher.
    """
    rung_str = "L1"
    filtered: list[str] = []
    i = 0
    while i < len(args):
        if args[i] == "--rung" and i + 1 < len(args):
            rung_str = args[i + 1]
            i += 2
        else:
            filtered.append(args[i])
            i += 1
    args = filtered

    if len(args) < 3:
        print("usage: homestead-law deadline <matter> <id> <date> [instruction]", file=sys.stderr)
        print('  e.g.: homestead-law deadline custody hearing 2026-09-15 "Custody hearing"', file=sys.stderr)
        print('  e.g.: homestead-law deadline custody evaluation 2026-08-12 --rung L4 "A submission is due"', file=sys.stderr)
        return 1

    matter_name = args[0]
    item_id = args[1]
    date = args[2]
    instruction = " ".join(args[3:]) if len(args) > 3 else None

    try:
        matter(matter_name)
    except KeyError:
        print(f"unknown matter {matter_name!r} — registered: {', '.join(all_matters())}", file=sys.stderr)
        return 1

    from homestead.keep.rungs import Classified, Rung

    try:
        rung = Rung(rung_str)
    except ValueError:
        print(f"unknown rung {rung_str!r} — one of: L1, L2, L3, L4, L5", file=sys.stderr)
        return 1

    derived = instruction
    if rung.value in ("L3", "L4") and not derived:
        derived = "A deadline is on file"

    _boot()
    sidecar = Sidecar()
    item = Classified(rung, date, derived)
    replaced = sidecar.put(matter_name, "deadline", item_id, item, overwrite=True)

    print(f"  stored: {matter_name}/deadline/{item_id}")
    print(f"  date:   {date}  (rung {rung.value})")
    if instruction:
        print(f"  instruction: {instruction}")
    if replaced:
        print(f"  (replaced previous value)")
    return 0


# ── show (read back, through the gate) ─────────────────────────────────────

def _cmd_show(args: Sequence[str]) -> int:
    """``show [matter] [item_type [item_id]]`` — read a matter's records back.

    With no argument, lists every registered matter and how many records each
    holds.  With a matter, lists that matter's records as the list pane would
    draw them (``S1_LIST``: L1–L3 payloads, the derived form for L4, nothing for
    L5 — I-16 holds here exactly as on the window).  With an item, opens it in
    the detail pane (``S1_DETAIL``: L4 renders, L5 is still refused) and prints
    any advisory beneath it.  ``item_id`` defaults to ``primary``, the id
    ``put`` files a field under.
    """
    from homestead_law.app import advisories
    from homestead_law.app.window import Window

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
    rows = window.open_list(sidecar.records(matter_name))

    if len(args) == 1:
        if not rows:
            print(f"  {matter_name}: nothing on file — `homestead-law put {matter_name} <field> <value>`")
            return 0
        print(f"  {matter_name}:")
        for row in rows:
            _, item_type, item_id = row.ref
            where = item_type if item_id == "primary" else f"{item_type}/{item_id}"
            print(f"  [{row.rung.value}]  {where}: {row.text}")
        return 0

    item_type = args[1]
    item_id = args[2] if len(args) > 2 else "primary"
    ref = (matter_name, item_type, item_id)
    if not sidecar.has(*ref):
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


# ── queue (real) ───────────────────────────────────────────────────────────

def _cmd_queue(args: Sequence[str]) -> int:
    """``queue [--today YYYY-MM-DD]`` — what's due, from real data."""
    import datetime as dt

    today = dt.date.today().isoformat()
    i = 0
    while i < len(args):
        if args[i] == "--today" and i + 1 < len(args):
            today = args[i + 1]
            i += 2
        else:
            i += 1

    _boot()
    sidecar = Sidecar()

    from homestead_law import queue as queue_mod

    items = queue_mod.queue(sidecar, today=today)
    if not items:
        print("  nothing due")
        return 0

    print(f"  as of {today}:")
    for item in items:
        if item.gap:
            mark = "date unreadable"
        elif item.overdue:
            mark = f"overdue by {abs(item.days_until)}d"
        else:
            mark = f"in {item.days_until}d"
        print(f"  [{item.rung.value}]  {item.shown}  ·  {mark}")
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
            port = int(args[i + 1])
            i += 2
        else:
            i += 1

    serve(port=port)
    return 0


COMMANDS = {
    "resolve": (_cmd_resolve, "resolve <domain> <surface> — entity resolution"),
    "propose": (_cmd_propose, "propose <domain> <surface> <canonical> — propose an alias"),
    "orders": (_cmd_orders, "orders <propose|check|list> — court decisions"),
    "put": (_cmd_put, "put <matter> <field> <value> — store a record"),
    "deadline": (_cmd_deadline, "deadline <matter> <id> <date> — add a deadline"),
    "show": (_cmd_show, "show [matter] [item [id]] — read records back, gated"),
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
