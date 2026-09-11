# DECISION: jurisdiction absent → refuse (provisional I-42)

**Status:** ratified. Proposed by the builder (L2b-instances);
`verified_by:` L2b-instances audit, 2026-09-11.

`homestead_law.jurisdiction.jurisdiction_of(store, matter, instance)` refuses,
rather than guessing or defaulting, whenever an instance has no jurisdiction
the gate will render as itself — whether because none was ever set
(`homestead-law matter open` was never run for it) or because what is on file
does not read back as a rendered value (a jurisdiction record planted by hand
at a rung the gate withholds, `L5` included). This is proposed here as
**invariant I-42**, provisionally numbered following the engine's I-37…I-41
reservations from the same build-out plan: *jurisdiction absent → refuse.* The
rationale is the same one behind I-2's refusal-over-guessing for a date
itself, one step earlier in the pipeline: any future counting rule
(`homestead.keep.dates`, a later bite) that computes a deadline from an anchor
in a given instance must know *which forum's rules to count under* before it
can honestly compute anything, and an assumed or defaulted forum is exactly
the kind of confident wrong answer I-2 already refuses for the date.

## Ratified boundary (audit, 2026-09-11)

The number **I-42** is ratified as proposed, and the refusal's boundary is
settled as follows.

1. **Anything short of `Disposition.RENDER` is absence.** A `DENY` (a planted
   `L5`) and a `DERIVE` (a planted `L4`, whose derived sentence is *not* a
   jurisdiction code) refuse identically to a record that was never written.
   The builder's behaviour is kept: from the point of view of "which forum's
   rules do I count under", all three are the same nothing, and picking one to
   guess with is the failure I-2 already refuses one step later, at the date.

2. **Rendering is necessary but not sufficient — the code is re-checked
   against the pack's own `JURISDICTIONS` on read, not only on write.** This is
   the audit's amendment. `L1` is the rung `set_jurisdiction` writes at, so a
   hand-planted `US-CA` renders perfectly and the gate has nothing to object
   to; only the pack says it is not a forum this matter has. The same shape
   arises with no plant at all when a pack's `JURISDICTIONS` tuple *shrinks*
   after an instance was opened: the record was legal when written and is not
   now. Without the read-side check, `jurisdiction_of` is `store.get` with
   extra steps, and the one thing it exists to guarantee — that arithmetic
   never counts under a forum this matter does not claim — does not hold.

3. **The refusal names the matter, the instance and the pack's published
   tuple; never the code that was on file.** On the write path
   `UnsupportedJurisdiction` echoes the rejected code, because that is
   something the operator has just typed against a closed published set. On the
   read path the offending code is a *record value*, so it is not echoed
   (I-15) — the message says which set was expected, not what was found.

4. **Absence is refused, never defaulted, at every door.** `matter open`
   without `--jurisdiction` is a usage error and `POST /api/matter/open`
   without one is a 400; neither falls back to the pack's `JURISDICTION`,
   which is the pack's *default for a new instance* and not a fact about this
   one. A silent default would defeat I-42 completely, one layer above it.
