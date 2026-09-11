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
none yet; `--sub` on any of its fields is refused by name. Workers' comp
declares one: `ime` (below).

`GET /api/instances?matter=` and `POST /api/matter/open` are the browser UI's
doors onto the same two functions; `/api/store` and `/api/deadline` accept
`id`/`sub` alongside the existing fields. The page's own forms do not yet
offer an instance picker — that UI wiring is left to a later (surfaces) bite;
today they always write the `primary` instance, exactly as before this one.

## Workers' comp

A second registered matter, `workers_comp` — an active New Mexico WCA claim
that stays an NM claim after the household's move to Oregon (unlike custody,
`JURISDICTIONS = ("US-NM",)`: the forum does not move, only where treatment
happens does). Registering it touched exactly one line in `registry.py`
(I-23) — no change to `cli.py`, `server.py`, `queue.py`, or the view.

```bash
homestead-law matter open workers_comp --id primary --jurisdiction US-NM
homestead-law put workers_comp employer "Acme Distribution"
homestead-law put workers_comp wca_case_number "WCA-2026-00456"
homestead-law put workers_comp diagnosis "Rotator cuff strain"   # L4 — never on the list
homestead-law put workers_comp ime "2026-10-05 -- Dr. R. Chen -- no permanent restrictions" --sub 2026-10
homestead-law show workers_comp --id primary
```

### What computes vs. what is entered

`homestead_law.packs.workers_comp.TEMPLATES` is **data**, not arithmetic — the
counting itself belongs to the parallel `L3-deadline-templates` bite
(`rules.py`, not imported by this pack). Two candidate templates exist, and
both ship `status: "UNCERTAIN"` — a template in that state refuses to compute
rather than guess (I-2's rule, applied to a counting rule instead of a date):

| template | anchor (must be `L1`) | days | citation | status |
|---|---|---|---|---|
| `hcp_selection` | `hcp_selection_date` | 60, calendar | NMSA 1978 § 52-1-49(B)-(C) | UNCERTAIN — no reachable PROVENANCE (below) |
| `hcp_change_objection` | `hcp_change_notice_date` | 3, calendar | NMSA 1978 § 52-1-49 area | UNCERTAIN — counting rule unverified |

A third rule the plan names — the 15-day notice-of-accident window (§ 52-1-29)
— is **not** a template at all: it would anchor on `date_of_injury`, which is
`L4`, and a computed template's anchor must render at `L1`. It is entered by
the household directly (`notice_of_accident_date`, `L3`), never derived.

Every other date on this pack — `mediation_date`, `hearing_date`,
`complaint_date`, `hcp_change_objection_deadline`, and the notice/selection
dates once they are actually known — is likewise entered, through the same
`put`/`deadline` doors every other field uses. Nothing here files or drafts
anything (decision 8's guard is a sibling bite's job over the whole package;
this pack's own `why` text and derived forms are checked against
"you should"/"file by" language in `tests/test_workers_comp.py`).

**PROVENANCE attempted, both unreachable.** `https://law.justia.com/codes/new-mexico/2021/chapter-52/article-1/section-52-1-49/`
returned `EGRESS_BLOCKED`; `https://www.wca.state.nm.us/` failed DNS
resolution. Three further tries — the 2025-edition Justia page, the official
compiler at `nmonesource.com`, and a `web.archive.org` snapshot of the first —
were each blocked the same way. A general web search corroborates the 60-day
figure in prose but is not a dated, quoted fetch of the statute, so both
templates ship `UNCERTAIN` rather than `VERIFIED`.

### The health boundary (decision 7)

*"Workers' comp is a law pack; medical content stays in health."* Every field
that touches the claimant's medical facts (`date_of_injury`, `body_part`,
`diagnosis`, `impairment_rating`, `mmi_date`, `treating_physician`, `ime`,
`oos_provider_affidavit_date`) holds only a **date or a short reference** —
the clinical narrative belongs in `homestead-health`'s own packs. A pack-level
cap, `MAX_L4_CHARS = 200`, and `validate_value(field, value)` are the
structural fence: a value over the cap on an `L4` field is refused by field
name, naming `homestead-health` as where the longer content belongs, and
never echoing what was typed (I-15).

**`validate_value` is not yet called by either door.** Neither `cli.py`'s
`_cmd_put` nor `server.py`'s `/api/store` has a per-pack validation hook today
— checked before writing this function, and none exists. `L4-surfaces` (wave
4) is the bite that wires it in; `tests/test_workers_comp.py` documents the
gap with a test that fails, by design, the day that wiring lands.

`ime` is the one `REPEATABLE` field: one composed record per independent
medical exam, addressed by `--sub` (e.g. `--sub 2026-10`), each carrying a
short reference — date, examiner, a one-line note — never the underlying
report.

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
