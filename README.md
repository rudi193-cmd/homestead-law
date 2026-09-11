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
