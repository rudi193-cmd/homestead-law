# The affairs build-out — this repo's copy (Wave 7, X7-drift-law)

Status: **A partial copy, law bites only, struck through as they land.** The
full plan — households, all three modules, all eight waves — lives at
`/root/.claude/plans/so-lets-plan-it-sparkling-shell.md` ("Homestead ·
Affairs — full build-out of law and ledger for one real household"), a file
this repo does not have and is not the place to vendor whole: the engine,
`homestead-ledger` and `homestead-health` are separate checkouts this bite
cannot read, and copying their bites here would let two copies of "is
L2b-instances landed" drift apart — the exact failure this document's own
guard exists to prevent (the same shape the engine's `X7-drift-engine` bite
settled on; this file follows it). What follows is the subset this repo *can*
verify from its own git history — every law bite (`W0-LAW`, Wave 2's `L2a`/
`L2c`, Wave 3's `L2b`/`L3-*`, Wave 4's `L4-surfaces`, Wave 5's `L5-sync`,
Wave 8's `L8-grant`/`L8-venture`/`L8-surfaces`) — struck through with the PR
that landed it and the release that shipped it, both read off `git log` and
`CHANGELOG.md`, never asserted from memory. Bites in the other three repos
are named where the plan names them, for orientation, and are **not struck
here**: this repo cannot see whether they landed, and a strike this repo
could not verify would be worse than no mark at all.

`docs/DECISION-jurisdiction-absent-refuses.md` and
`docs/DECISION-deadline-ids-are-instance-addressed.md` already hold the
detailed, dated record of *how* the bites that proposed them landed — what
each changed, what an audit found, what got corrected. This document's job is
narrower and different: one line of "landed or not, and where," so a reader
(or the orchestrator's own dry run of the Wave 7 meta-scan) can answer "is
L3-workers-comp in yet?" without reading five files.

---

## Releases (from `CHANGELOG.md` and `git log`)

Every law bite that landed cut its own release, one `feat:`/`fix:` PR
followed by one release-please PR, the same one-release-per-feature cadence
the engine's own drift bite found in its history.

| release | PR | shipped |
|---|---|---|
| 0.2.0 | [#26](https://github.com/homestead-affairs/homestead-law/pull/26) | `W0-LAW` (#25), `L2a-pack-contract` (#28), `L2c-second-pack-readiness` (#29) |
| 0.3.0 | [#32](https://github.com/homestead-affairs/homestead-law/pull/32) | `L2b-instances` (#31) |
| 0.4.0 | [#37](https://github.com/homestead-affairs/homestead-law/pull/37) | `L3-custody-relocation` (#33), `L3-workers-comp` (#34), `L3-bankruptcy-ch13` (#35), `L3-deadline-templates` (#36) |
| 0.5.0 | [#39](https://github.com/homestead-affairs/homestead-law/pull/39) | `L4-surfaces` (#38) |
| 0.6.0 | [#41](https://github.com/homestead-affairs/homestead-law/pull/41) | `L5-sync` (#40) |
| 0.7.0 | [#43](https://github.com/homestead-affairs/homestead-law/pull/43) | `L8-grant` (#42) |
| 0.8.0 | [#45](https://github.com/homestead-affairs/homestead-law/pull/45) | `L8-venture` (#44) |

Two small fix branches merged between named bites (`claude/law-refused-body-drain`,
#27, and `claude/law-drain-spy-wait`, #30 — both a request-body drain fix
found while auditing `W0-LAW`) are not named plan bites and are not struck
below for that reason; they shipped inside 0.2.0/0.3.0 alongside the bites
that actually cut those releases.

---

## Wave 0 — land the base

- ~~**W0-LAW** `homestead-law`, existing branch. Audit+fix+PR. Fix:
  `/api/store`/`/api/deadline` refuse a missing `matter` (400) instead of
  defaulting to `"custody"`; JS fallback uses the first registry matter.~~
  **Landed: PR [#25](https://github.com/homestead-affairs/homestead-law/pull/25),
  release 0.2.0.**

## Wave 2 — modules adopt 0.3.0

- ~~**L2a-pack-contract** `feat:` — floor 0.3.0; custody `JURISDICTION="US-NM"`,
  `JURISDICTIONS=("US-NM","US-OR")`, `"derived"` per L3/L4 field, `jurisdiction`
  L1 field; `MatterType.jurisdictions`; delete `cli._default_derived` and
  `server._derived` → `derived_of`. AST guard: a derived-form dict outside
  `packs/` is a build failure (plant).~~ **Landed: PR
  [#28](https://github.com/homestead-affairs/homestead-law/pull/28), release
  0.2.0.**
- ~~**L2c-second-pack-readiness** `test:`+`fix:` — registry-relative tests
  (drop literal `{"custody"}`, fake packs named `_fake_second`, cover asserted
  via `queue.cover()`'s rule); `app/view.py` one "Open <matter>" button per
  `all_matters()`; `show_queue` loads every matter.~~ **Landed: PR
  [#29](https://github.com/homestead-affairs/homestead-law/pull/29), release
  0.2.0.**

## Wave 3 — instances, jurisdiction, the three law packs

- ~~**L2b-instances** `feat:` (first in law) — `instances.py` (`item_id`,
  `split`, `instances_of` key scan, `records_of`), `jurisdiction.py`
  (`set_jurisdiction`, `jurisdiction_of` served on S1_LIST — I-42); `--id`/
  `--sub` on `put`/`deadline`/`show`; packs declare `REPEATABLE`; `matter
  open`; `/api/instances`, `/api/matter/open`.~~ **Landed: PR
  [#31](https://github.com/homestead-affairs/homestead-law/pull/31), release
  0.3.0.**
- ~~**L3-custody-relocation** `feat:`, depends L2b — repeatable `child` (name
  L4, dob L4, school L4; `child_name` struck through), `custody_type` L3,
  `custody_order_date` L1, `move_date` L3, `new_residence_state` L2,
  `relocation_notice_date` L3, `uccjea_registration_date` L1,
  `registration_contest_deadline` L1, `mediation_date` L1; templates: NM
  contest +20d (verified-secondary); OR contest UNCERTAIN; OR relocation
  notice UNCERTAIN; NM relocation none.~~ **Landed: PR
  [#33](https://github.com/homestead-affairs/homestead-law/pull/33), release
  0.4.0.** **Not fully closed by this landing:** the pack's own docstring
  named `L4-surfaces` (wave 4) as the bite that would retire the superseded
  `child_name` field once every door naming it was rewritten. `L4-surfaces`
  landed (below) and left every door naming it unchanged — see *Open items*.
- ~~**L3-bankruptcy-ch13** `feat:`, depends L2b — 35 fields; the plan-period
  interaction flag (`homestead_law.plan_period`, `SIGNAL_FIELDS`); `NOTICE`;
  I-44 AST guard; `district_state` as the second calendar a forward count
  reads.~~ **Landed: PR
  [#35](https://github.com/homestead-affairs/homestead-law/pull/35), release
  0.4.0.**
- ~~**L3-workers-comp** `feat:`, depends L2b — `wca_case_number`/
  `claim_number` L3; the health boundary (decision 7): `MAX_L4_CHARS`,
  `validate_value`; `ime.*` `REPEATABLE`; every NM date entered, none
  computed (the 60-day HCP-selection window anchors above L1).~~ **Landed:
  PR [#34](https://github.com/homestead-affairs/homestead-law/pull/34),
  release 0.4.0.**
- ~~**L3-deadline-templates** `feat:`, depends L2b — `rules.py`:
  `Template(name, anchor_field, days, direction, rule, mail, source,
  status)`, `compute()`, `deadline compute … [--mail] [--accept]`;
  `/api/deadline/compute|accept` with a preview token.~~ **Landed: PR
  [#36](https://github.com/homestead-affairs/homestead-law/pull/36), release
  0.4.0.** **Not fully closed by this landing:** `accept()`'s instruction
  hard-coded "confirm against the court's notice", which was false the day a
  non-judicial template (`L8-venture`'s `election-83b`, an IRS filing with no
  court) started writing through the same door. Corrected by `X7-drift-law`
  (this document's own bite) — see *Open items*.

## Wave 4 — sync in the engine; ledger overlay; law surfaces

- ~~**L4-surfaces** `feat:`, depends L3-* — matter+instance switcher,
  per-pack panes (children + relocation timeline; creditors/claims with
  bar-date countdown and the `NOTICE`; WC treatment/IME timeline),
  computed-deadlines pane with Accept (token = what was shown), intake
  options from `mt.fields`, I-33 one indicator per pane, tk view minimal
  parity.~~ **Landed: PR
  [#38](https://github.com/homestead-affairs/homestead-law/pull/38), release
  0.5.0.** Its own audit (2026-09-11, recorded in `app/cover.py`'s
  strike-through) found and fixed the vendored `cover_counts` signature, but
  left `child_name` un-retired — see *Open items*.

## Wave 5 — sync in the modules

- ~~**L5-sync** `feat:` (floor 0.4.0) — `sync --matters a,b [--types …]
  --ceiling L3 [--url] [--init-household]`; Sync tab; replaced the vendored
  `app/cover.py` with an import of `homestead.app.cover` (engine #58's
  `by_matter` distribution).~~ **Landed: PR
  [#40](https://github.com/homestead-affairs/homestead-law/pull/40), release
  0.6.0.**

## Wave 7 — drift and closure sweep

- **X7-drift-law** (this bite) — `tests/test_docs_drift.py`,
  `tests/test_scans_fire.py`, the README capabilities table, and this
  document; the two corrections named under *Open items* below. Not struck
  here: a document does not mark its own landing before the PR that lands it
  exists.

## Wave 8 — the grant, the accelerator application, and the business

Depends on Wave 3 (`L2b-instances`, `L3-bankruptcy-ch13` for the flag
consumer) and `G2b` (`homestead-ledger`, not this repo).

- ~~**L8-grant** `feat:` — `packs/grant.py`, `JURISDICTIONS=("US-federal",)`
  placeholder for the funder's terms; no computed deadlines (every date
  entered); repeatable `milestone`/`report`/`disbursement`; produces the
  Chapter 13 flag.~~ **Landed: PR
  [#42](https://github.com/homestead-affairs/homestead-law/pull/42), release
  0.7.0.**
- ~~**L8-venture** `feat:` — `packs/venture.py`
  (`JURISDICTIONS=("US-DE","US-OR")`, both absent from the engine's `RULES`
  except the pack's own `calendar_days` template); the application and the
  PBC's compliance calendar; `founder.election_83b_deadline`, the one
  computed template (26 U.S.C. § 83(b)(2)); `ein` L5; produces the Chapter
  13 flag.~~ **Landed: PR
  [#44](https://github.com/homestead-affairs/homestead-law/pull/44), release
  0.8.0.**
- **L8-surfaces** `feat:`, depends L4-surfaces — grant pane, venture pane,
  the Chapter 13 flag line on the bankruptcy pane and the queue; its own
  audit found and fixed a composer reading a pack's `SCHEMA`/`FIELDS`
  straight off the pack instead of the `Row` the gate served it. **Merged,
  not yet released:** PR
  [#46](https://github.com/homestead-affairs/homestead-law/pull/46) merged
  to `main` as `32c9804` (head `d1969a9`) — this branch has merged `main` at
  that commit. Left unstruck on purpose: release-please had not cut the
  release containing it when this was written, so there is no release
  number to name, and `tests/test_plan_affairs_face.py` requires a struck
  bite to name both a PR and a release. It is struck, with `#46` and the
  release, by whoever next touches this document once that tag exists — the
  same pattern the engine's own `X7-drift-engine` bite used for
  `E7b-fleet-structured-values`.

---

## Open items this document tracks

1. **`child_name` retirement is still open.** `L3-custody-relocation`'s pack
   docstring and `L4-surfaces`'s own landing both said `L4-surfaces` would
   retire the superseded singular `child_name` field once every door naming
   it (`cli.py`'s `party_fields`, `server.py`'s intake form, `app/demo.py`)
   was rewritten to the repeatable `child.name`. `L4-surfaces` landed (PR
   #38, release 0.5.0) and left all three doors unchanged — the promise was
   false the moment the bite that was supposed to keep it shipped without
   doing so. `X7-drift-law` (this document's own bite) corrected the
   now-false claim in `homestead_law/packs/custody.py`'s `why` string and in
   `tests/test_packs.py`'s docstring so neither asserts a completed or
   promised retirement that did not happen, and records the retirement here,
   unstruck, as a real open bite: rewriting `cli.py`'s `party_fields`,
   `server.py`'s intake form and `app/demo.py` to stop offering `child_name`
   is more than the docstring/test-only change this drift sweep's own scope
   allows (BRIEF: ≤ 40 lines, docs/tests only), so it is named here for a
   future bite rather than done partially now.
2. **`rules.accept`'s instruction wording was fixed by this bite.** It
   hard-coded `"confirm against the court's notice"` for every accepted
   template, including `L8-venture`'s `election-83b` (an IRS filing window
   under 26 U.S.C. § 83(b), with no court). `X7-drift-law` changed the
   wording to `"confirm against the source above"` — naming what the
   instruction already states a sentence earlier, true regardless of whether
   the source is a court, a trustee's rule, or the tax code — and updated
   every test and README passage that quoted the old text. This item is not
   struck above (`X7-drift-law` has not landed as of this document's own
   writing) but the fix itself is in this same branch's diff, not deferred.

---

## Module and cross-repo bites — named, not struck

Everything below lives in `homestead` (the engine), `homestead-ledger`,
`homestead-health`, or is a cross-repo orchestration step. This repo's own
git history says nothing about whether any of them landed, so — per the rule
stated at the top of this document — **none of the following is struck
here**, and none of it is omitted either: a bite left out of this list is
indistinguishable from a bite that never existed, which is the one mark this
document may not make. Each group names the checkout that can answer for it.

**tracked in `homestead`** (the engine) — `E1-hygiene`, `E1-procedure`,
`E1-pack-contract`, `E1-purpose-sync`, `E1-dates-a`, `E1-dates-b`,
`E1-pending`; `E4-sync-core`, `E4-postgres-fleet`, `E4-cover-distribution`;
`E5-integrity-keyed`; `E6-integrity-encrypt`; `E7-public-log-reader`,
`E7b-fleet-structured-values`; `E8-jurisdictions-de-or-corp` (optional);
`X7-drift-engine`.

**tracked in `homestead-ledger`** — `W0-LEDGER`; `G2a-account-packs`,
`G2c-importer-dates`; `G2b-account-instances`, `G3-cadence-paidby`;
`G4-overlay`, `G4-transfers`, `G4-budget`, `G4-schedules-export`; `G5-sync`;
`G7b-floor-0.13`; `G8-business-books`; `X7-drift-ledger`.

**tracked in `homestead-health`** — `W0-HEALTH`; `H2-cap`;
`H6-sealed-reader`; `H7-floor-0.12`; `X7-drift-health`.

**cross-repo, tracked by the orchestrator** — `ORCH-0`, `ORCH-2`, `ORCH-8`,
`ORCH-R1`, `ORCH-R2`, `ORCH-R3`, `ORCH-R4`.

A reader who has the other checkouts open can strike these directly against
their own `git log`, the same way this document struck the law half.
