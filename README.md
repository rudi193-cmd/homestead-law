# homestead-law

**Homestead · Affairs — module one.** The household handling its own deeds and
disputes. Prose name: **Law Gazelle**.

A **self-contained** desktop module: it ships to a self-represented parent or a
legal-aid clinic who double-clicks it, so its store is embedded **SQLite** — a
linked library, not a server (the face's 2026-08-04 "no listening socket"
decision holds; SQLite binds no port). The record layer is the engine's now:
`store.py` is a thin binding — `homestead.keep.store`'s adapter contract on a
SQLite backing, in the law database. The invariants (I-6/I-7/I-9/I-11) are the
engine's, tested there against every backing; this module only chooses the
backing and the database. It **pins the engine from PyPI** —
`homestead-affairs>=0.1.0,<1.0` (the distribution name; `import homestead` is
unchanged) — and shares the `~/.homestead` root with the ledger, because a
household's affairs are one thing.

The shared **Postgres** engine on the fleet side (the Willow side of the die) is
a *sync target*, reached through the egress gate — never a runtime dependency of
the shipped app. Sync is an **S4 egress**: an `L5` record never crosses, and what
lands in the shared store is only what the household chose to expose.

> **Status: bite 3 — runnable end to end on SQLite.** The store (bite 1), the
> custody pack and registry (bite 2), and now the **app** — the two S1 surfaces
> (`app/window`, `app/view`), the cover's re-identification check (`app/cover`,
> I-31), the surfaced advisory matcher (`app/advisories`), and the citation
> extractor (`patterns`, I-18) — all reading the SQLite store. The chokepoint
> (I-16) guards the app: only the store reaches a payload, and no surface
> reflects. `python -m homestead_law --demo` prints the whole store→gate→surface
> pipeline headless. And the **queue** (`queue`) — *what the season owes* —
> deadlines across every matter, iterating `all_matters()` (the registry, not a
> hand-kept list — BUG-6's fix), computing urgency with `homestead.keep.dates`,
> surfacing an unparseable date as a gap (I-8), dropping a sealed deadline, and
> feeding the cover's re-identification check (I-31). The queue is **wired into
> the app**: the resting cover shows only counts that survive re-identification
> (nothing, over a single matter), a "What's due" view lists the queue, and
> `--demo` prints it headless. Suite: **85 passed**. The "prove one app on
> SQLite end to end" milestone is met; the adapter seam and the gated Postgres
> sync generalize from here.

## Entering your own information

The demo (`--demo`) is synthetic. A household's own records go into the
household root — `$HOMESTEAD_HOME`, else `~/.homestead` — and nothing below
needs the optional `entity` extra:

```bash
pip install -e .

homestead-law ui                                   # entry forms, intake and dashboard, on localhost
homestead-law put custody courthouse "Dept 4, Second Judicial District Court, Bernalillo County"
homestead-law put custody child_name "A. Rivera"   # stored at the pack's rung (L4) — no rung is chosen here
homestead-law deadline custody hearing 2026-10-01 "Custody hearing"
homestead-law deadline custody evaluation 2026-08-12 --rung L4 "A submission is due"
homestead-law show custody                         # the list pane: L1–L3 shown, L4 derived, L5 absent
homestead-law show custody child_name              # the detail pane: L4 renders, L5 still refused
homestead-law queue                                # what's due
python -m homestead_law                            # the window, on these records (the demo only if empty)
```

Dates go through the engine's one strict parser on both doors: `deadline` takes
`2026-10-01` or `August 10, 2026`, stores the ISO form, and refuses anything it
cannot read in one line — a date the queue could not have read is a refusal
where it can still be fixed, never a gap met weeks later.

The browser UI (`ui`) is the plain way in: a *Records* tab with a field form
(matter, field, value — the rung and its reason shown beside the field), a
deadline form, and the records on file composed through the gate; an *Intake*
tab that extracts dates, parties, case numbers and courts from pasted text so
each can be stored with one click. Entity resolution (`resolve`, `propose`),
court orders (`orders`) and the ledger check (`verify`) need
`pip install 'homestead-law[entity]'` and say so when it is missing.

## Instances and jurisdiction

A matter can be more than one order in more than one forum — an NM custody
order being registered in Oregon after a relocation is one matter, custody,
with two **instances**: the original NM order and the OR registration. Nothing
in the engine changed to say so (wave 3, decision 2): an item id is just a
string, and this bite is the convention it now follows —

```
item_id(instance)        -> "<instance>"
item_id(instance, sub)   -> "<instance>.<sub>"
```

— stored exactly where it always was, `(matter, item_type, item_id)`. An id
matches `^[a-z0-9][a-z0-9-]{0,39}$` (`homestead_law.instances.ID_PATTERN`) —
lowercase letters, digits and hyphens, never a dot — so `split_item_id` can
always recover the two halves without guessing. `--id` defaults to `primary`
everywhere, so a household with one instance of a matter sees no change at
all.

An instance's **jurisdiction** — which forum's rules govern it — is a fact
about the instance, not the matter: a pack declares a default (`JURISDICTION`)
and the full set an instance may be filed under (`JURISDICTIONS`); an operator
opens an instance by declaring which one it is actually in:

```bash
homestead-law matter open custody --id nm-order --jurisdiction US-NM
homestead-law matter open custody --id or-order --jurisdiction US-OR
homestead-law put custody courthouse "Second Judicial District Court" --id nm-order
homestead-law deadline custody nm-order 2026-11-01 --sub hearing
homestead-law deadline custody hearing 2026-11-01     # the default instance: primary.hearing
homestead-law show custody                    # lists instances: nm-order, or-order
homestead-law show custody --id nm-order      # that instance's records
```

**Every deadline is addressed to an instance.** What is stored is always
`"<instance>.<name>"`: with no `--sub` the positional id is the deadline's
*name* inside the default instance (so the command line an operator already
knows is unchanged and `deadline custody hearing …` files `primary.hearing`),
and with `--sub` the positional id is the instance and `--sub` the deadline
within it. A free-form id is refused by name, not stored — an id that cannot
be split is a deadline no instance can own, and the instance list, the queue's
matter+instance naming and the computed-deadline keys a later bite writes
(`(matter, "deadline", "<inst>.<template>")`) all rest on the shape. See
`docs/DECISION-deadline-ids-are-instance-addressed.md`; there is no migration
(the store is v1 synthetic-only), and a deadline written before this
convention still opens by its own id through `show <matter> deadline <id>`.

A code outside the pack's own `JURISDICTIONS` is refused by name, and nothing
is stored; opening an already-open instance again is refused unless
`--replace` is given (the store's own I-9, not a new rule). Reading a
jurisdiction back (`homestead_law.jurisdiction.jurisdiction_of`) goes through
the same gate every other record does — `serve()`, never `.payload` — and
refuses (**provisional I-42**: *"jurisdiction absent → refuse"*) whenever
nothing was actually rendered, whether because no jurisdiction was ever set or
because what is on file does not read back as itself (a jurisdiction planted
by hand at `L5`, say, or a code the pack's own tuple does not contain —
checked on the way out as well as on the way in, since `L1` renders whatever
is on disk). **Anything that will one day do date arithmetic on a
deadline in an instance must call `jurisdiction_of` first** — an anchor date
counted under an assumed forum is a guess about which rules to count under,
and this module refuses that guess before the counting rules themselves ever
run (see "Computing a deadline", below).

A pack may also declare `REPEATABLE` — field names that accept a `--sub`
(a repeatable sub-record, e.g. a child of a custody matter). Custody declares
none yet; `--sub` on any of its fields is refused by name.

`GET /api/instances?matter=` and `POST /api/matter/open` are the browser UI's
doors onto the same two functions; `/api/store` and `/api/deadline` accept
`id`/`sub` alongside the existing fields. The page's own forms do not yet
offer an instance picker — that UI wiring is left to a later (surfaces) bite;
today they always write the `primary` instance, exactly as before this one.

## Computing a deadline

A pack may declare **templates** — data, not code — on its own `TEMPLATES`
tuple: an anchor field (one of the pack's own `L1`, public fields), a period,
a counting rule (`court_days`, `court_days_before`, `business_days` or
`calendar_days`), whether mail days apply, the jurisdiction it is scoped to
(or `None` for whichever the instance is actually opened in), the citation
behind it, and a `VERIFIED`/`UNCERTAIN` status. `homestead_law.rules` is the
one place that reads that data, checks it against the pack's own fields at
**registry time** (a bad template — a missing key, an anchor that is not the
pack's own `L1` field, a backward or `calendar_days` row asking for mail — is
a build failure
naming the pack and the template, exactly like an unclassified schema field),
and turns it into a computed date at runtime, through `homestead.keep.dates`.

```bash
homestead-law deadline templates custody
homestead-law deadline compute custody notice --id nm-order
homestead-law deadline compute custody notice --id nm-order --mail --accept
```

**`deadline compute` stores nothing** — it reads the anchor (through the
gate — an anchor that is missing, or on file at a rung the gate would not
render, is refused by name) and the instance's jurisdiction (provisional
I-42), checks the template applies to that jurisdiction, and prints the
result, the source and a preview token. **`--accept` is the only thing that
writes**, and only once a token proves it matches a fresh computation of the
same anchor and jurisdiction: it stores `(matter, "deadline",
"<instance>.<template>")` at `L1` with the instruction *"computed from
`<anchor>` under `<source>`; confirm against the court's notice"* — the same
two-field shape (a date, an instruction) the plain `deadline` command already
writes, so the queue and `show` read a computed deadline exactly as they read
a hand-entered one, by reference. `--replace` is the same consent an occupied
key always needs (I-9); without it, a second `--accept` of the same
`<instance>.<template>` is refused, not silently overwritten.

**`UNCERTAIN` means the citation behind that branch of the rule has not been
checked against a primary source** — a pack author's honest "not yet",
not "probably fine." A template whose `status` is `UNCERTAIN` refuses,
`"UNCERTAIN: <source>"`, before any counting function is ever called; a
`VERIFIED` template can still hit the same wall one layer down; if the
specific branch `homestead.keep.dates` needs (a short period, a backward
count, the added mail days) is itself unverified for that jurisdiction, the
engine's own refusal propagates unchanged. Either way nothing is guessed —
confirm the actual date against the court's own notice regardless of what
this prints, which is exactly what the accepted instruction says.

**A template name is a label and also half of a stored key.** An accepted
deadline is filed under `"<instance>.<template>"`, so a name matches the same
alphabet every other id does — lowercase letters, digits and hyphens, no
underscore, no dot. `registration-contest`, not `registration_contest`: a
pack whose template names are snake_case like its *field* names refuses at
import rather than at the first `--accept`.

**One name may be declared more than once, for different jurisdictions**, and
that is the ordinary shape of a rule that differs by forum rather than a
duplicate: custody declares `registration-contest` twice, 20 court days under
`US-NM` and 21 under `US-OR`. `compute` picks the row written for the
*instance's* own jurisdiction, falling back to a row that names none; a name
that fits no declared forum is refused, listing the ones it does declare.
What is refused at import is only the repeat nothing could choose between —
the same name twice for one jurisdiction, or one name declared both for a
particular forum and for all of them.

**Mail days extend a period that runs from service.** The three days of FRBP
9006(f)/FRCP 6(d) are added to the rolled end of a *forward* count; a period
counted backward from a hearing does not run from service at all, and
`calendar_days` has no jurisdiction rule to add them under. `mail: True` on
either is a build failure, and `--mail` against either is refused by name at
the door.

**A federal district court also reads the holidays of the state it sits in**
(FRBP 9006(a)(6)(C)), forward periods only. A template may name that state
with an optional `"district_state": "NM"`; failing that, a pack that declares
an `L1` `district_state` field lets each instance say which district it is
in. Nothing maps a district's *name* to a state — "District of New Mexico" →
`NM` is a table of court names this package does not keep, and every miss in
it would be a silently wrong calendar rather than a refusal. When neither
source names one, the count runs on the federal calendar alone and every door
says so out loud (`district holidays not applied`, `"district_state": null`)
rather than letting the operator assume the state's closures were counted.
It matters: the Friday after Thanksgiving is a working day federally and a
legal holiday in New Mexico, so a 70-day claims bar from a 2026-09-18
petition is 2026-11-27 without it and 2026-11-30 with it.

`calendar_days` is the one rule this package computes itself rather than
asking the engine for: a plain count of days with **no roll off a weekend or
holiday, and no calendar read at all** — a 30-day `calendar_days` span that
lands on a Sunday stays on that Sunday. Use `court_days` or `business_days`
for a period a court's calendar should move.

`POST /api/deadline/compute` and `POST /api/deadline/accept` are the browser
UI's doors onto the same two functions; `accept` recomputes fresh from the
current store state before comparing the submitted token, so a preview left
open in a tab while the underlying anchor or jurisdiction changed is refused
as stale rather than accepted against content nobody actually saw.

## What is enforced here today

*The record invariants, carried from `homestead.keep.record` and held more
tightly by the database.*

| | |
|---|---|
| **I-6** | The canonical record is **read-only, enforced by type**. `Canonical` reads the canonical table and has no `put`/`update`/`delete`; `Sidecar` writes its own. The Postgres sync target is the shared canonical on the fleet side. |
| **I-7** | **One key.** `(matter, item_type, item_id)` is the composite **primary key**, computed once by `key()`, shared by read and write. Two call sites cannot derive it two ways (BUG-11). |
| **I-9** | **Writes never silently overwrite.** A first write is an `INSERT`; the primary key makes a racing second write an `IntegrityError`, refused — race-safe by the database, no lock. An explicit overwrite reports what it replaced. |
| **I-11** | **Absence fails closed to `L5`** at the storage boundary. A row whose rung is missing, unreadable, or whose payload will not decode reads `L5` on the way out — never `L1` — using the same `rungs._read_rung` the gate uses. |

## The method

Test-first, as in `homestead`: every claim is a check somebody can run. From a
cold checkout — the engine (`homestead.keep`) resolves from PyPI as
`homestead-affairs`, no sibling checkout needed:

```bash
pip install -e .    # pulls homestead-affairs (homestead.keep) from PyPI
pytest -q
```

Apache-2.0.
