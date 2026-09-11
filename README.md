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

Workers' comp declares three of its own — `ime.date`, `ime.examiner`,
`ime.note`, one independent medical exam per sub-id (below).

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

## Bankruptcy (Chapter 13)

`homestead_law/packs/bankruptcy.py` is the second real pack, the first with
`JURISDICTION`/`JURISDICTIONS` fixed to `("US-federal",)` — a Chapter 13 case
does not move between forums the way a custody order can. 35 fields: case
administrivia (`district`, `district_state`, `courthouse`, `chapter`,
`case_number`, `trustee`)
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

**`TEMPLATES`** — five deadlines, as a **tuple** of rows of data (`name`,
`anchor`, `days`,
`direction`, `rule`, `mail`, `jurisdiction`, `source`, `status`, `note`); the
sibling `rules.py` bite (L3-deadline-templates) reads this table and does the
counting — nothing here imports it or `homestead.keep.dates`. All five
anchor on an `L1` field of this pack and are `VERIFIED` (converging secondary
sources — see each `source`'s dated PROVENANCE sentence; every primary host
this environment could try was refused by the egress proxy):

| template | anchor | days | direction / rule | mail | citation |
|---|---|---|---|---|---|
| `plan-filed` | `petition_date` | 14 | forward, court days | no | FRBP 3015(b) |
| `first-plan-payment` | `petition_date` | 30 | forward, calendar days | no | 11 U.S.C. § 1326(a)(1) |
| `claims-bar` | `petition_date` | 70 | forward, court days | no | FRBP 3002(c) |
| `governmental-claims-bar` | `petition_date` | 180 | forward, court days | no | FRBP 3002(c)(1) |
| `objection` | `confirmation_hearing_date` | 7 | backward, court days | **no** | FRBP 3015(f) |

A template name is stored as the sub half of `(matter, "deadline",
"<instance>.<template>")`, so it is an **id**: lowercase, digits and hyphens,
never an underscore.

`objection` takes **no** mail days, and that is the rule rather than an
omission. FRBP 9006(f) adds its three days to a period that runs *after
service*, and adds them **forward**; an objection deadline runs backward from
the confirmation hearing, so there is nothing for them to extend — and adding
them anyway would name a date *later* than the 7-days-before cutoff the rule
sets. Some districts lengthen the 7 days by local rule; the template encodes
the FRBP default and its `note` says to check the district's own rules.
`first-plan-payment` anchors on `petition_date` alone, so § 1326(a)(1)'s
"whichever is earlier" clause is the operator's to apply — its `note` says so.

`creditor_meeting_date` (the § 341 meeting) is deliberately **never
computed** — its 21–50-day window is set administratively by the U.S.
Trustee, not by a rule this pack can count.

**`district_state` — the second calendar a forward count reads.** FRBP
9006(a)(6)(C) makes "any other day declared a holiday by the state where the
district court is located" a legal holiday too, for periods measured **after**
an event. The pack is general — a Chapter 13 case is filed in whichever
district the debtor lives in — so the district's state is an `L1` field on the
*instance*, entered like any other, not a constant in the table and not a
lookup from `district` (a court-name-to-state table is an enumeration, which
I-23 keeps in a registry or a pack, and every miss in one would be a silently
wrong calendar rather than a refusal):

```bash
homestead-law put bankruptcy district      "District of New Mexico" --id primary
homestead-law put bankruptcy district_state NM --id primary
```

With it, the sibling `rules.py` bite counts the three `court_days` rows on
both calendars; without it they are counted federally and every door says
"district holidays not applied" rather than letting the operator assume state
closures were counted. It matters: a 2026-09-18 petition puts `claims-bar`
(70 days forward) on **2026-11-27** federally and **2026-11-30** with
`district_state` = `NM`, because New Mexico keeps Presidents' Day on the
Friday after Thanksgiving and its district courts are closed on a day the
federal calendar has open. `first-plan-payment` is unaffected and its `note`
says why — calendar days read no calendar at all.

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
`homestead-law queue` prints each one after the items (and prints them even
when nothing is due — a notice has no date, so it neither expires nor waits
its turn), and `GET /api/queue` carries them in a `notices` array beside
`items`. Rendering them on the browser pane is L4-surfaces' work.

Only a value that actually **renders** counts as on file: a
`plan_confirmation_date` hand-stored at the wrong rung derives rather than
renders, and a derived form is not a date anything read, so it is treated as
absent (no line) — the same reading the sibling `rules.py` gives an anchor it
cannot see. The line itself is computed on every read and never logged: it is
a reference derived from records that were logged when they were written, not
an event of its own.

## Workers' comp

A third registered matter, `workers_comp` — an active New Mexico WCA claim
that stays an NM claim after the household's move to Oregon (unlike custody,
`JURISDICTIONS = ("US-NM",)`: the forum does not move, only where treatment
happens does). Registering it touched exactly one line in `registry.py`
(I-23) — no change to `cli.py`, `server.py`, `queue.py`, or the view.

```bash
homestead-law matter open workers_comp --id primary --jurisdiction US-NM
homestead-law put workers_comp employer "Acme Distribution"
homestead-law put workers_comp wca_case_number "WCA-2026-00456"
homestead-law put workers_comp diagnosis "Rotator cuff strain"   # L4 — never on the list
homestead-law put workers_comp ime.date 2026-10-05 --sub 2026-10
homestead-law put workers_comp ime.examiner "Dr. R. Chen" --sub 2026-10
homestead-law put workers_comp ime.note "report received; no permanent restrictions" --sub 2026-10
homestead-law show workers_comp --id primary
```

### Nothing here computes a deadline; every date is entered

`homestead_law.packs.workers_comp.TEMPLATES` is empty, and that is a decision
rather than an omission. A computed deadline template may only anchor on a
field the pack declares `L1` — `rules.compute()` reads the anchor through the
gate on `S1_LIST`, where anything above `L1` renders as its derived form, so
no date reaches the arithmetic at all. All three New Mexico rules this matter
carries anchor above `L1`:

| rule | would anchor on | rung | so |
|---|---|---|---|
| 60-day health-care-provider change window (NMSA 1978 § 52-1-49(B)-(C)) | `hcp_selection_date` | `L4` | entered, not computed |
| 3-day objection to a provider change | the change-notice date | `L4` | entered, not computed (`hcp_change_objection_deadline`) |
| 15-day notice of accident (§ 52-1-29) | `date_of_injury` | `L4` | entered, not computed (`notice_of_accident_date`) |

~~`hcp_selection_date` is `L1` so the 60-day window can be computed.~~ Struck
(audit, 2026-09-11): a rung answers the harm of disclosing the value, never
what a template needs. This pack already rules that its forum does not post —
`wca_case_number`, `hearing_date` and `mediation_date` are all `L3` for that
reason — and a date saying a health care provider was chosen for an
identified claimant is a health-care fact about that person, which is `L4`.
The template went; the rung stayed. The statutes stay cited on the fields'
own `why` strings, so the reference survives the arithmetic that could not.

Every other date on this pack — `mediation_date`, `hearing_date`,
`complaint_date`, `hcp_change_objection_deadline`, the notice and selection
dates once they are actually known — is likewise entered, through the same
`put`/`deadline` doors every other field uses. Nothing here files or drafts
anything (decision 8's package-wide guard is a sibling bite's job; this pack's
own `why` text and derived forms are held against the advice-shaped phrases
the I-44 scan bans — an imperative aimed at the operator, a date given as an
instruction, a claim about which relief suits them — by
`tests/test_workers_comp.py`, which keeps the phrase list itself, where a test
file is out of the scan's reach and this file is not).

**PROVENANCE attempted, nothing reachable.** `https://law.justia.com/codes/new-mexico/2021/chapter-52/article-1/section-52-1-49/`
returned `EGRESS_BLOCKED`; `https://www.wca.state.nm.us/` failed DNS
resolution; the 2025-edition Justia page, the official compiler at
`nmonesource.com`, and a `web.archive.org` snapshot of the first were each
blocked the same way. A general web search corroborates the 60-day figure in
prose but is not a dated, quoted fetch of the statute. Even with an `L1`
anchor these would have shipped `UNCERTAIN` and refused to compute (I-2's
rule, applied to a counting rule instead of a date), so nothing computable is
lost by the ruling above. `_validate_templates` still runs at import: the day
a template *is* added here it is held to the shape and to the `L1` anchor
rule, by the build.

### The health boundary (decision 7)

*"Workers' comp is a law pack; medical content stays in health."* Every field
that touches the claimant's medical facts (`date_of_injury`, `body_part`,
`diagnosis`, `impairment_rating`, `mmi_date`, `treating_physician`,
`hcp_selection_date`, `ime.*`, `oos_provider_affidavit_date`) holds only a
**date or a short reference** —
the clinical narrative belongs in `homestead-health`'s own packs. A pack-level
cap, `MAX_L4_CHARS = 200`, and `validate_value(field, value)` are the
structural fence: a value over the cap on an `L4` field is refused by field
name, naming `homestead-health` as where the longer content belongs, and
never echoing what was typed (I-15).

**`validate_value` is not yet called by either door.** Neither `cli.py`'s
`_cmd_put` nor `server.py`'s `/api/store` has a per-pack validation hook today.
`L4-surfaces` (wave 4) is the bite that wires it in;
`tests/test_workers_comp.py` carries that claim as a pending `xfail(strict=True)`
— `test_the_doors_call_validate_value` — so the wiring is announced by a named
failure asking for the mark to be removed, not by a test that has to be
deleted. The function's own contract (200 accepted, 201 refused, the message
naming the field and `homestead-health` and echoing nothing) is tested
unconditionally today.

`ime.date`, `ime.examiner` and `ime.note` are the `REPEATABLE` fields: three
records per independent medical exam, all addressed by one `--sub` (e.g.
`--sub 2026-10`), each a short reference and never the underlying report. The
dotted-sub-field shape is the convention `homestead_law.packs.custody` uses
for `child.name`/`child.dob`/`child.school`, and for the same mechanical
reason — `_cmd_put` holds the *typed* field string against `REPEATABLE`, so a
bare `ime` would need a bare `ime` field, i.e. one free-text blob per exam
beside `notes`, which is the drift toward narrative decision 7 exists to
stop.

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
