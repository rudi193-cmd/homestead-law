# DECISION: jurisdiction absent → refuse (provisional I-42)

**Status:** proposed by the builder (L2b-instances). `verified_by:` — blank
for the auditor.

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
the kind of confident wrong answer I-2 already refuses for the date. Ratifying
the number, and confirming the refusal's exact boundary (in particular,
whether a `DERIVE`-disposition jurisdiction record — a plant, since no path in
this bite ever writes one above `L1` — should refuse identically to a denied
one, as it does today) is left to audit.
