"""L3-custody-relocation — the repeatable `child` sub-record and `TEMPLATES`.

Two things this bite adds that `tests/test_packs.py` does not already cover
field by field: the end-to-end CLI round trip for a repeatable sub-record
(`--id`/`--sub`, through `instances.item_id`, read back through the gate), and
the shape of `custody.TEMPLATES` — data for the parallel `L3-deadline-
templates` bite's `rules.py`, which this repo does not have on this branch, so
the only thing to hold it to here is a local, standalone check.
"""
from __future__ import annotations

import pytest

from homestead.keep.rungs import Disposition, Rung, Surface, derived_of, serve
from homestead_law import registry as registry_mod
from homestead_law.app.window import Window
from homestead_law.cli import run_cli
from homestead_law.packs import custody
from homestead_law.store import Sidecar


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))


# ── the repeatable child sub-record, end to end ───────────────────────────────

def test_a_child_subfield_is_put_by_cli_and_reads_back_through_the_gate(capsys):
    """`put custody child.name <v> --id primary --sub c1` — the exact command
    the brief specifies. `--sub` is accepted because `"child.name"` (the
    literal field string, not `"child"`) is in `custody.REPEATABLE`;
    `instances.item_id("primary", "c1")` is what composes the stored key.
    Read back: the S1_LIST pane shows the pack's derived sentence (L4 never
    renders on an ambient list — I-13), and the S1_DETAIL pane — the pane
    opening is itself the purpose declaration — renders the payload."""
    assert run_cli([
        "put", "custody", "child.name", "Alex Rivera", "--id", "primary", "--sub", "c1",
    ]) == 0
    out = capsys.readouterr().out
    assert "stored: custody/child.name/primary.c1" in out
    assert "L4" in out

    store = Sidecar()
    ref = ("custody", "child.name", "primary.c1")
    record = store.get(*ref)

    listed = serve(record, Surface.S1_LIST)
    assert listed.disposition is Disposition.DERIVE
    assert listed.value == derived_of(custody.SCHEMA, "child.name") == "A child's name is on file"
    assert "Alex Rivera" not in str(listed.value)

    detailed = serve(record, Surface.S1_DETAIL)
    assert detailed.disposition is Disposition.RENDER
    assert detailed.value == "Alex Rivera"

    # And through the window/CLI surfaces themselves, not only `serve()` bare.
    window = Window()
    window.open_list(store.records("custody"))
    rows = {row.ref: row for row in window.rows}
    assert rows[ref].text == "A child's name is on file"

    served = window.open_detail(ref)
    assert served.value == "Alex Rivera"

    assert run_cli(["show", "custody", "child.name", "primary.c1"]) == 0
    out = capsys.readouterr().out
    assert "Alex Rivera" in out


def test_two_children_do_not_collide_on_the_same_field(capsys):
    """The whole point of the sub-id: `child.dob` for two different children,
    same instance, same matter — one record per (field, sub), not one shared
    slot the second `put` would silently overwrite (the exact failure
    `child_name` — kept, singular — has always had for a two-child
    household; see the module docstring)."""
    assert run_cli([
        "put", "custody", "child.dob", "2016-03-02", "--id", "primary", "--sub", "c1",
    ]) == 0
    assert run_cli([
        "put", "custody", "child.dob", "2019-11-20", "--id", "primary", "--sub", "c2",
    ]) == 0
    capsys.readouterr()

    store = Sidecar()
    first = serve(store.get("custody", "child.dob", "primary.c1"), Surface.S1_DETAIL)
    second = serve(store.get("custody", "child.dob", "primary.c2"), Surface.S1_DETAIL)
    assert first.value == "2016-03-02"
    assert second.value == "2019-11-20"


def test_sub_on_a_field_outside_repeatable_is_still_refused(capsys):
    """The existing `courthouse`/`--sub` regression, re-run against a field
    this bite added at L1 (`custody_order_date`) — not just the pre-existing
    `courthouse` — so the refusal is shown to be about `REPEATABLE`
    membership generically, not a property only the original field had."""
    assert run_cli([
        "put", "custody", "custody_order_date", "2024-01-01", "--sub", "c1",
    ]) == 1
    err = capsys.readouterr().err
    assert "refused:" in err and "custody_order_date" in err and "REPEATABLE" in err


def test_put_refuses_sub_on_the_bare_word_child(capsys):
    """`"child"` alone is not a field this pack has — proving the module
    docstring's claim that `REPEATABLE` had to name the three dotted fields,
    not the bare word, for `put`'s own field check to ever let `--sub`
    through at all."""
    assert run_cli(["put", "custody", "child", "x", "--sub", "c1"]) == 1
    err = capsys.readouterr().err
    assert "unknown field" in err


# ── TEMPLATES: shape, a local check, and a planted refusal ───────────────────

_REQUIRED_KEYS = {
    "name", "anchor", "days", "direction", "rule", "mail", "jurisdiction",
    "source", "status", "note",
}
_DIRECTIONS = {"forward", "backward"}
_RULES = {"court_days", "court_days_before", "business_days", "calendar_days"}
_STATUSES = {"VERIFIED", "UNCERTAIN"}


def _template_errors(templates, schema, jurisdictions, *, require_l1_anchor=True):
    """Every shape violation in `templates`, empty when there are none.

    A standalone check — this repo does not have the sibling `L3-deadline-
    templates` bite's `rules.py` to import, so this is the only thing that
    exercises the shape `custody.TEMPLATES` promises to that bite. Mirrors
    the brief's own list of keys and enums exactly; `require_l1_anchor` is a
    parameter (not hardcoded True) so the one documented exception
    (`relocation_notice`'s anchor, `move_date`, is `L3` — flagged in the
    module docstring, not fixed here) can be checked on its own rather than
    hidden inside a check that would otherwise always run at full strictness.
    """
    errors: list[str] = []
    for i, tpl in enumerate(templates):
        if not isinstance(tpl, dict) or set(tpl.keys()) != _REQUIRED_KEYS:
            errors.append(f"[{i}] keys {set(tpl) if isinstance(tpl, dict) else tpl!r} "
                           f"!= {_REQUIRED_KEYS}")
            continue
        if not isinstance(tpl["name"], str) or not tpl["name"].strip():
            errors.append(f"[{i}] name must be a non-empty str")
        anchor = tpl["anchor"]
        if anchor not in schema:
            errors.append(f"[{i}] anchor {anchor!r} is not a field of this pack")
        elif require_l1_anchor and schema[anchor].get("rung") is not Rung.L1:
            errors.append(f"[{i}] anchor {anchor!r} is not L1")
        if not isinstance(tpl["days"], int) or isinstance(tpl["days"], bool) or tpl["days"] <= 0:
            errors.append(f"[{i}] days must be a positive int")
        if tpl["direction"] not in _DIRECTIONS:
            errors.append(f"[{i}] direction {tpl['direction']!r} not in {_DIRECTIONS}")
        if tpl["rule"] not in _RULES:
            errors.append(f"[{i}] rule {tpl['rule']!r} not in {_RULES}")
        if not isinstance(tpl["mail"], bool):
            errors.append(f"[{i}] mail must be a bool")
        j = tpl["jurisdiction"]
        if j is not None and j not in jurisdictions:
            errors.append(f"[{i}] jurisdiction {j!r} not in {jurisdictions} and not None")
        if not isinstance(tpl["source"], str) or not tpl["source"].strip():
            errors.append(f"[{i}] source must be a non-empty str")
        if tpl["status"] not in _STATUSES:
            errors.append(f"[{i}] status {tpl['status']!r} not in {_STATUSES}")
        if not isinstance(tpl["note"], str) or not tpl["note"].strip():
            errors.append(f"[{i}] note must be a non-empty str")
    return errors


def test_templates_is_the_exact_shape_the_plan_specifies():
    """Three rows, the exact keys, no more and no fewer."""
    assert len(custody.TEMPLATES) == 3
    for tpl in custody.TEMPLATES:
        assert set(tpl.keys()) == _REQUIRED_KEYS


def test_templates_pass_every_check_except_the_one_documented_exception():
    """The shape/enum/jurisdiction checks, run at full strictness including
    "anchor is L1" — and they hold for every row **except**
    `relocation_notice`, whose anchor (`move_date`) is declared `L3` two
    sections up. That single, named exception is asserted next, not hidden
    by loosening this check."""
    strict = [t for t in custody.TEMPLATES if t["name"] != "relocation_notice"]
    assert strict, "expected at least one non-relocation_notice row to check at full strictness"
    errors = _template_errors(strict, custody.SCHEMA, custody.JURISDICTIONS)
    assert errors == []


def test_relocation_notices_anchor_is_l3_a_documented_cross_bite_tension():
    """The module docstring's "Deadline templates as data" section names this
    exactly: `relocation_notice` anchors on `move_date` (`L3`), not `L1`, and
    its own `status` is `UNCERTAIN` with a `note` saying the operator enters
    the date — so `compute()` never actually reads the anchor's payload for
    this row today. Asserted here, by name, rather than left for a future
    `rules.py` import guard to discover as a surprise: the field exists, the
    anchor reference is not dangling, and the rung mismatch is exactly the
    one flagged in the docstring — nothing else."""
    (relocation,) = [t for t in custody.TEMPLATES if t["name"] == "relocation_notice"]
    assert relocation["anchor"] == "move_date"
    assert relocation["anchor"] in custody.SCHEMA
    assert custody.FIELDS[relocation["anchor"]] is Rung.L3
    assert relocation["status"] == "UNCERTAIN"
    assert "operator enters" in relocation["note"]

    # the full check, at full strictness, does flag exactly this row and
    # nothing else — proving the exception is narrow, not a loophole.
    errors = _template_errors(custody.TEMPLATES, custody.SCHEMA, custody.JURISDICTIONS)
    assert len(errors) == 1
    assert "anchor 'move_date' is not L1" in errors[0]


def test_the_check_refuses_a_planted_bad_template():
    """A scan that has never fired has not been shown to check anything.
    Five independent plants, each violating exactly one rule, against the
    real pack's schema/jurisdictions — the check must name a violation for
    every one of them."""
    base = dict(custody.TEMPLATES[0])

    missing_key = {k: v for k, v in base.items() if k != "note"}
    bad_anchor_field = {**base, "anchor": "not_a_real_field"}
    bad_anchor_rung = {**base, "anchor": "move_date"}
    bad_direction = {**base, "direction": "sideways"}
    bad_jurisdiction = {**base, "jurisdiction": "US-CA"}
    bad_status = {**base, "status": "PROBABLY"}

    for label, plant in [
        ("missing key", missing_key),
        ("bad anchor field", bad_anchor_field),
        ("bad anchor rung", bad_anchor_rung),
        ("bad direction", bad_direction),
        ("bad jurisdiction", bad_jurisdiction),
        ("bad status", bad_status),
    ]:
        errors = _template_errors([plant], custody.SCHEMA, custody.JURISDICTIONS)
        assert errors, f"the check did not fire on a planted {label}"

    # the unmodified real templates (minus the one documented exception)
    # must not trip the same check the plants above did.
    clean = [t for t in custody.TEMPLATES if t["name"] != "relocation_notice"]
    assert not _template_errors(clean, custody.SCHEMA, custody.JURISDICTIONS)


def test_the_or_templates_are_uncertain_and_nm_registration_is_verified():
    """House style: UNCERTAIN → refuse, never guess. Both `US-OR` rows are
    `UNCERTAIN` (20 vs 21 days; "reasonable notice" with no fixed count);
    `US-NM`'s `registration_contest` is the one `VERIFIED` row, carrying a
    dated `PROVENANCE` note for the source this build could not reach
    directly."""
    by_jurisdiction = {(t["jurisdiction"], t["name"]): t for t in custody.TEMPLATES}

    nm = by_jurisdiction[("US-NM", "registration_contest")]
    assert nm["status"] == "VERIFIED"
    assert nm["days"] == 20
    assert "PROVENANCE" in nm["source"]

    or_contest = by_jurisdiction[("US-OR", "registration_contest")]
    assert or_contest["status"] == "UNCERTAIN"
    assert or_contest["days"] == 21

    or_relocation = by_jurisdiction[("US-OR", "relocation_notice")]
    assert or_relocation["status"] == "UNCERTAIN"


def test_no_nm_relocation_notice_template():
    """The plan is explicit: New Mexico has no relocation-notice template —
    only the receiving forum's (`US-OR`) counts under UCCJEA once the family
    has actually moved."""
    nm_relocation = [
        t for t in custody.TEMPLATES
        if t["name"] == "relocation_notice" and t["jurisdiction"] == "US-NM"
    ]
    assert nm_relocation == []


# ── the registry still validates, and the I-23 scan is still clean ───────────

def test_the_registry_still_validates_with_the_grown_schema():
    """`_validate` (`registry.py`, untouched by this bite) still accepts the
    grown custody pack — every new L3/L4 field carries a `derived` sentence,
    `REPEATABLE` names only real fields, and `JURISDICTION`/`JURISDICTIONS`
    are unchanged."""
    registry_mod._validate(registry_mod.REGISTRY, registry_mod._discover_packs())
    assert set(registry_mod.all_matters()) == {"custody"}


def test_i23_scan_is_still_clean_against_the_grown_pack():
    """The structural guard from `tests/test_registry.py` — imported rather
    than re-implemented, so this cannot drift from what it actually checks —
    run again against the package as it stands after this bite. Still fires
    on a plant, still silent on the real tree."""
    from tests.test_registry import PKG, _matter_name_enumerations
    import ast

    names = set(registry_mod.all_matters())
    offenders = []
    for mod in sorted(PKG.rglob("*.py")):
        if "__pycache__" in mod.parts:
            continue
        if mod == PKG / "registry.py" or "packs" in mod.relative_to(PKG).parts:
            continue
        for lineno in _matter_name_enumerations(ast.parse(mod.read_text("utf-8")), names):
            offenders.append(f"{mod}:{lineno}")
    assert not offenders

    # the guard still fires on a plant — re-checked here rather than assumed
    # to still work just because `test_registry.py` says so elsewhere.
    tree = ast.parse("MATTERS = ['custody', 'bankruptcy']\n")
    assert _matter_name_enumerations(tree, names | {"bankruptcy"})


# ── the demo still composes ───────────────────────────────────────────────────

def test_the_demo_still_composes_unchanged():
    """`app/demo.py` seeds a fixed field list (`_DEMO`), not every field the
    pack declares, so this bite's additions need no change there — asserted
    here rather than assumed, and the demo's courthouse stays Bernalillo
    County."""
    from homestead_law.app import demo

    store = Sidecar()
    text = demo.compose_demo(store)
    # L1's `courthouse` payload renders verbatim on S1_LIST, and the demo's
    # own seed data names Bernalillo County.
    assert "Bernalillo County" in text
    assert demo._DEMO["courthouse"][0] == "Dept 4, Second Judicial District Court, Bernalillo County"
    assert "list (S1_LIST)" in text
    assert "detail child_name (S1_DETAIL)" in text

    queue_store = Sidecar()
    queue_text = demo.compose_queue(queue_store)
    assert "what's due" in queue_text
