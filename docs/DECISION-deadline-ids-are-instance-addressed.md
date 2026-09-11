# DECISION: every deadline id is instance-addressed

**Status:** ratified by the L2b-instances audit, 2026-09-11. There is no
separate builder proposal: this decision *replaces* a compromise the builder
shipped, and the reasons are the audit's.

## What changed

Before this bite a deadline's item id was free-form — `deadline custody
hearing 2026-09-15` stored `(custody, "deadline", "hearing")`, and the id was
whatever short label the operator typed. The builder kept that meaning when
`--sub` was not passed, to avoid disturbing the existing regression test that
plants an XSS payload in a deadline id.

It is now always `homestead_law.instances.item_id(instance, name)` —
`"<instance>.<name>"`:

* `deadline custody hearing 2026-09-15` files `primary.hearing`. **The command
  line is unchanged**; the key it writes is now attributable.
* `deadline custody or-order 2026-09-15 --sub hearing` files
  `or-order.hearing`.
* `POST /api/deadline {"id": "hearing"}` → `primary.hearing`;
  `{"id": "or-order", "sub": "hearing"}` → `or-order.hearing`. The page's own
  form is unchanged.
* An id outside `ID_PATTERN` (`^[a-z0-9][a-z0-9-]{0,39}$`) is refused by name
  and nothing is stored.

## Why the compromise could not stand

1. **The same bite added a key scan that assumes the shape.**
   `instances.instances_of` splits every stored item id to find the instances a
   matter has. Handed a free-form id it has exactly two bad options: read the
   label as an instance — inventing one that no other door will accept, since
   `item_id` refuses it, so `show --id <that>`, `matter open --id <that>` and
   `jurisdiction_of` all refuse the very id the list just offered — or skip it,
   hiding a record from the list whose job is to say what is on file.

2. **It was not hypothetical.** On the branch as built, one deadline entered
   the documented way (`deadline custody "it's-due" …`, or the README's own
   pre-instance `hearing`) made `homestead-law show custody` exit with an
   `InvalidId` traceback and `GET /api/instances` return a 500 with a dropped
   connection. Two crashes, reachable from the blessed workflow.

3. **Nothing downstream could address a deadline.** L3-deadline-templates
   stores `(matter, "deadline", "<inst>.<template>")` and the queue and window
   rows name matter+instance. With free-form ids there is no consistent
   addressing for either to grow into.

## Why it does not weaken W0's XSS guarantee

W0 audited the property *"a stored key never reaches the page as JavaScript"*,
and fixed it structurally: the key rides in `data-` attributes through `esc()`
and the click handler is bound afterwards, instead of being spliced into
`onclick="openRecord('…')"` where an attribute value is entity-decoded before
the script is parsed. None of that changed.

What changed is the *plant*. The regression test used `/api/deadline` to put a
hostile key on disk; that door now refuses it, so the test plants through
`Sidecar` instead — which is the honest source anyway (a database written
before this convention, another tool, a restore). The guarantee under test is
strictly stronger: it no longer depends on one write door staying lax, and the
same test now also asserts the door's refusal does not echo what was posted.
A second test covers the surface where the XSS actually lives today — a
*value*, which is free text at any rung and reaches the page only through
`esc()`.

`instances_of` refuses (`UnreadableStoredId`) when the store does hold such a
key, naming the matter and the item types and never the id, so the crash above
is a one-line refusal rather than a traceback.

## Migration

None. The store is v1 synthetic-only (the same call the ledger's
`G2c-importer-dates` bite made for ISO fingerprints). A deadline written before
this bite keeps its free-form id on disk and still opens by that id through
`show <matter> deadline <id>`; only the instance *listing* refuses, by name,
until it is re-entered. Re-entering it is one command.
