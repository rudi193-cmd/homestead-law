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
none yet; `--sub` on any of its fields is refused by name.

`GET /api/instances?matter=` and `POST /api/matter/open` are the browser UI's
doors onto the same two functions; `/api/store` and `/api/deadline` accept
`id`/`sub` alongside the existing fields. The page's own forms do not yet
offer an instance picker — that UI wiring is left to a later (surfaces) bite;
today they always write the `primary` instance, exactly as before this one.

## Bankruptcy (Chapter 13)

`homestead_law/packs/bankruptcy.py` is the second real pack, the first with
`JURISDICTION`/`JURISDICTIONS` fixed to `("US-federal",)` — a Chapter 13 case
does not move between forums the way a custody order can. 34 fields: case
administrivia (`district`, `courthouse`, `chapter`, `case_number`, `trustee`)
and every procedural date this case has (`petition_date` the anchor,
`creditor_meeting_date`, `plan_filed_date`, `first_plan_payment_due`,
`claims_bar_date`, `governmental_claims_bar_date`, `confirmation_hearing_date`,
`objection_deadline`, `plan_confirmation_date`, `plan_completion_date`,
`debtor_education_date`, `discharge_date`, repeatable `plan_modification`) at
`L1`; `plan_payment_amount`/`income`/`assets` at `L3` (the same posture the
engine's own bankruptcy pack gives `income`/`assets` — resolves to the
debtor's finances, no further protected category); repeatable `creditor.*`
(name/amount_scheduled/claim_amount `L3`, secured/claim_filed_date/
claim_number `L1`, note `L4` — the per-creditor decomposition of the engine
pack's aggregate `creditors` field, decision 2's repeatable shape); `attorney`
`L2`; `notes` `L4`; `ssn` `L5`. `account_number` is refused as a field name at
import (`_refuse_account_number`) — an account number is ledger content, one
`L5` record per account instance (provisional I-43), never a law field.

**`NOTICE`** — rendered by every surface that opens this matter: *"This pack
keeps dates and references for a Chapter 13 case. It drafts nothing, files
nothing, and does not say which chapter fits."* Provisional **I-44**
(`tests/test_i44_no_drafting.py`) fails the build if `Purpose.DRAFTING` or
`Purpose.FILING` is ever referenced under `homestead_law/`, and separately if
any string literal in the tree carries an advice-shaped phrase (a filing
command, a chapter recommendation).

**`TEMPLATES`** — five deadlines, as data (`name`, `anchor`, `days`,
`direction`, `rule`, `mail`, `jurisdiction`, `source`, `status`, `note`); the
sibling `rules.py` bite (L3-deadline-templates) reads this table and does the
counting — nothing here imports it or `homestead.keep.dates`. All five
anchor on an `L1` field of this pack and are `VERIFIED` (converging secondary
sources — see each `source`'s dated PROVENANCE sentence; every primary host
this environment could try was refused by the egress proxy):

| template | anchor | days | direction / rule | mail | citation |
|---|---|---|---|---|---|
| `plan_filed` | `petition_date` | 14 | forward, court days | no | FRBP 3015(b) |
| `first_plan_payment` | `petition_date` | 30 | forward, calendar days | no | 11 U.S.C. § 1326(a)(1) |
| `claims_bar` | `petition_date` | 70 | forward, court days | no | FRBP 3002(c) |
| `governmental_claims_bar` | `petition_date` | 180 | forward, court days | no | FRBP 3002(c)(1) |
| `objection` | `confirmation_hearing_date` | 7 | backward, court days | yes | FRBP 3015(f) |

`creditor_meeting_date` (the § 341 meeting) is deliberately **never
computed** — its 21–50-day window is set administratively by the U.S.
Trustee, not by a rule this pack can count.

**The plan-period interaction flag** (`homestead_law.plan_period`). While a
bankruptcy instance is confirmed (`plan_confirmation_date` on file) and not
yet discharged (`discharge_date` absent), the presence of a
`SIGNAL_FIELDS` record — `award_amount`, `disbursement`, `safe`,
`equity_grant`, `revenue_start` — in *any other* registered matter (Wave 8's
still-unbuilt `grant`/`venture` packs) yields one reference line:

> `bankruptcy/<instance>: income or assets arising during the plan: confirm
> with your attorney (11 U.S.C. §§ 541(a)(7), 1306(a), 1329; disclosure
> duties under the plan and local rules)`

Never a value, never a number, and it never blocks a `put`, a `deadline`, or
anything else — a flag, not a refusal. `queue.notices(store)` is the one
queue hook: a tuple of such lines, alongside — not inside — the dated
`QueueItem` list, since a reference line has no date to sort or gap-check.

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
