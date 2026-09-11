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
and this module refuses that guess before the counting rules themselves exist
to make it (they are a later bite).

A pack may also declare `REPEATABLE` — field names that accept a `--sub`
(a repeatable sub-record, e.g. a child of a custody matter). Custody declares
three — `child.name`, `child.dob`, `child.school` — one record per child per
field, so a second child does not overwrite the first the way the older,
singular `child_name` field always could:

```bash
homestead-law put custody child.name "Alex Rivera" --id primary --sub c1
homestead-law put custody child.dob 2016-03-02 --id primary --sub c1
homestead-law put custody child.name "Robin Rivera" --id primary --sub c2
homestead-law show custody child.name primary.c1     # the detail pane, that child only
```

`--sub` on any other custody field is refused by name (not declared
`REPEATABLE`) — and a `REPEATABLE` field written *without* one is refused too,
because it would otherwise land in the instance's single slot, where the
second child overwrites the first. `REPEATABLE` holds **field names**, not a
concept: `child.name`, `child.dob`, `child.school`, each a field the pack
declares, because both guards that read it (`cli._cmd_put` and
`registry._validate`) compare a member against the field string a `put`
actually names.

`GET /api/instances?matter=` and `POST /api/matter/open` are the browser UI's
doors onto the same two functions; `/api/store` and `/api/deadline` accept
`id`/`sub` alongside the existing fields. The page's own forms do not yet
offer an instance picker — that UI wiring is left to a later (surfaces) bite;
today they always write the `primary` instance, exactly as before this one.

## The custody matter — fields, and what a deadline needs

Beyond the original set (`courthouse`, `hearing_date`, `jurisdiction`,
`case_number`, `docket`, `opposing_party`, `parenting_time`, `child_name`
— kept, struck through, see `homestead_law/packs/custody.py`'s module
docstring — `diagnosis`, `notes`, `ssn`), the relocation bite (wave 3) adds:

| field | rung | what it is |
|---|---|---|
| `custody_order_date` | L1 | the date the underlying order was entered |
| `uccjea_registration_date` | L1 | the date the order was registered with the receiving forum |
| `registration_contest_deadline` | L1 | the deadline to contest that registration |
| `mediation_date` | L1 | a court-ordered mediation session's date |
| `new_residence_state` | L2 | the destination state (household-level, no identity) |
| `custody_type` | L3 | sole / joint / legal / physical — the arrangement's shape |
| `move_date` | L3 | the date of the household's relocation |
| `relocation_notice_date` | L3 | the date notice of the move was given to the other parent |
| `child.name` / `child.dob` / `child.school` | L4 each | repeatable, one record per child per field (`--sub`) |

**What the app can compute, and what the operator enters.** Deadline
*templates* are declared as data (`custody.TEMPLATES`) for a parallel bite's
engine-backed `rules.py` to read and compute from — this module does not
compute a date itself (I-2: one door). Every row anchors on an **L1** field
(the anchor is named in refusals, and only a public-in-this-forum rung
survives that), carries a **name that is a legal sub-id** (`--accept` files
the result at `"<instance>.<template>"`), and carries a name that is
**unique in the pack** (a template is found by name; the jurisdiction belongs
to the instance). Today:

* **`nm-registration-contest`** — 20 days forward from
  `uccjea_registration_date`, `VERIFIED` (NMSA 1978 § 40-10A-305). The
  primary text is blocked from this build, so the row's `source` carries a
  dated `PROVENANCE` sentence naming the hosts that were refused and the
  converging restatements read instead. A pinpoint subsection is deliberately
  not cited: it could not be confirmed from here.
* **`or-registration-contest`** — `UNCERTAIN`. Secondary sources say 21 days
  (ORS 109.787) and 21 is what the row carries, but the uniform section and
  every other state enactment read here say 20, and the primary is unread. The
  operator enters the date from the court's own notice.
* **No relocation-notice template, in either forum.** New Mexico has none, and
  Oregon's (ORS 107.159) requires "reasonable notice" without fixing a day
  count — there is no period to count. The date notice was actually given is
  **entered, not computed**, as the `relocation_notice_date` field.

An `UNCERTAIN` template is a documented refusal, never a guess, and a missing
template is the same refusal in its strongest form: the app will not compute a
date it cannot stand behind, so the operator's own read of the court's notice
is what goes on file, at the rung `deadline` was always given at (L1 by
default).

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
