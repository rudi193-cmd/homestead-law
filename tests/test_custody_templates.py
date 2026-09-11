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
from homestead_law.instances import ID_PATTERN
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


def test_sub_is_refused_on_an_l3_field_this_bite_added_too(capsys):
    """The same refusal at a different rung — `custody_type` is `L3`, so a
    `--sub` acceptance here would be a *derived*-bearing record filed under a
    sub-id nothing addresses. `REPEATABLE` membership, not the rung, is the
    whole test."""
    assert run_cli(["put", "custody", "custody_type", "joint legal", "--sub", "c1"]) == 1
    err = capsys.readouterr().err
    assert "refused:" in err and "custody_type" in err and "REPEATABLE" in err
    assert "joint legal" not in err          # I-15: a refusal names a field, never a value


def test_a_repeatable_field_without_sub_is_refused_by_name(capsys):
    """The other half of the `REPEATABLE` rule, added by this bite's audit
    (2026-09-11). Before it, `put custody child.name X --id primary` was
    *accepted* and filed at `primary` — the instance's single slot, where the
    second child overwrites the first, which is the exact failure the sub-id
    exists to abolish, and under a key `instances.split_item_id` then reads
    as a bare instance so nothing downstream can tell it from an
    instance-level record. It now refuses, naming the field and the remedy
    and never the value (I-15), and stores nothing."""
    assert run_cli(["put", "custody", "child.name", "Alex Rivera", "--id", "primary"]) == 1
    err = capsys.readouterr().err
    assert "refused:" in err
    assert "child.name" in err and "REPEATABLE" in err and "--sub" in err
    assert "Alex Rivera" not in err

    store = Sidecar()
    assert not store.has("custody", "child.name", "primary")
    assert list(store.records("custody")) == []


def test_every_repeatable_field_refuses_a_put_without_a_sub(capsys):
    """Not only `child.name`: the refusal is driven by `REPEATABLE`
    membership, so it must hold for every member the pack declares — planted
    by iterating the pack's own frozenset rather than a list retyped here,
    which cannot drift from it."""
    assert custody.REPEATABLE
    for field in sorted(custody.REPEATABLE):
        assert run_cli(["put", "custody", field, "a value", "--id", "primary"]) == 1
        err = capsys.readouterr().err
        assert field in err and "--sub" in err, field
    assert list(Sidecar().records("custody")) == []


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


def _template_errors(templates, schema, jurisdictions):
    """Every shape violation in `templates`, empty when there are none.

    A standalone check — this repo does not have the sibling `L3-deadline-
    templates` bite's `rules.py` to import, so this is the only thing that
    exercises the shape `custody.TEMPLATES` promises to that bite. It mirrors
    that bite's contract, and it runs at **full strictness with no exception
    and no parameter to loosen it** (audit, 2026-09-11): an anchor that is not
    `L1` is an error, full stop — the one row that used to be the exception
    (`relocation_notice`, anchored on the `L3` `move_date`) is struck from the
    pack, because ORS 107.159 fixes no day count for a computed template to
    count.

    Three rules beyond the per-key types, each of which would otherwise make
    this pack a build failure in the bite that reads it:

    * the anchor is one of this pack's own `L1` fields;
    * the `name` is a legal sub-id (`instances.ID_PATTERN`), because
      `--accept` files the computed date at `"<instance>.<template>"` — an
      underscore in a template name is a date that can never be stored;
    * the `name` is unique in the pack, because a template is looked up by
      name and the jurisdiction belongs to the *instance*, not the command.
    """
    errors: list[str] = []
    seen: set[str] = set()
    for i, tpl in enumerate(templates):
        if not isinstance(tpl, dict) or set(tpl.keys()) != _REQUIRED_KEYS:
            errors.append(f"[{i}] keys {set(tpl) if isinstance(tpl, dict) else tpl!r} "
                           f"!= {_REQUIRED_KEYS}")
            continue
        name = tpl["name"]
        if not isinstance(name, str) or not name.strip():
            errors.append(f"[{i}] name must be a non-empty str")
        else:
            if not ID_PATTERN.match(name):
                errors.append(
                    f"[{i}] name {name!r} is not a sub-id — it must match "
                    f"{ID_PATTERN.pattern}, since --accept files the computed "
                    'date at "<instance>.<template>"'
                )
            if name in seen:
                errors.append(f"[{i}] name {name!r} is declared more than once")
            seen.add(name)
        anchor = tpl["anchor"]
        if anchor not in schema:
            errors.append(f"[{i}] anchor {anchor!r} is not a field of this pack")
        elif schema[anchor].get("rung") is not Rung.L1:
            errors.append(f"[{i}] anchor {anchor!r} is not L1")
        if not isinstance(tpl["days"], int) or isinstance(tpl["days"], bool) or tpl["days"] <= 0:
            errors.append(f"[{i}] days must be a positive int")
        if tpl["direction"] not in _DIRECTIONS:
            errors.append(f"[{i}] direction {tpl['direction']!r} not in {_DIRECTIONS}")
        if tpl["rule"] not in _RULES:
            errors.append(f"[{i}] rule {tpl['rule']!r} not in {_RULES}")
        elif (tpl["direction"] == "backward") != (tpl["rule"] == "court_days_before"):
            errors.append(
                f"[{i}] direction {tpl['direction']!r} and rule {tpl['rule']!r} "
                "disagree — backward counting is court_days_before and nothing else"
            )
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
    """Two rows, the exact keys, no more and no fewer. Three, until the audit
    struck `relocation_notice` — ORS 107.159 states no day count, so there is
    no period for a template to count and nothing is lost by entering the
    date instead."""
    assert len(custody.TEMPLATES) == 2
    for tpl in custody.TEMPLATES:
        assert set(tpl.keys()) == _REQUIRED_KEYS


def test_every_template_passes_every_check_with_no_exception():
    """The whole contract, at full strictness, over the whole tuple — no
    `relocation_notice` carve-out and no parameter that could reintroduce
    one. This is the check the module docstring's three rules point at."""
    assert _template_errors(
        custody.TEMPLATES, custody.SCHEMA, custody.JURISDICTIONS) == []


def test_every_template_anchor_is_an_l1_field_of_this_pack():
    """The invariant, pinned by itself and not only inside the bulk check:
    `rules.py` (the sibling bite) makes a non-`L1` anchor a build failure at
    import, and `compute()` *names* the anchor field in a refusal, which only
    the public-in-this-forum rung can survive (I-15)."""
    assert custody.TEMPLATES, "a pack with no templates would pass this vacuously"
    for tpl in custody.TEMPLATES:
        assert tpl["anchor"] in custody.FIELDS, tpl["name"]
        assert custody.FIELDS[tpl["anchor"]] is Rung.L1, (
            f"{tpl['name']}'s anchor {tpl['anchor']!r} is "
            f"{custody.FIELDS[tpl['anchor']].value}, not L1"
        )


def test_every_template_name_is_a_storable_unique_sub_id():
    """`--accept` files the computed date at `(matter, "deadline",
    "<instance>.<template>")`, and `instances.item_id` validates both halves
    against `ID_PATTERN` — so a template name with an underscore in it names
    a date that can never be stored. Names are also unique in the pack: a
    template is found by name, and the jurisdiction is a property of the
    *instance*, so two rows sharing a name would silently count one forum's
    period for the other's instance (which `registration_contest` × {NM, OR}
    did before the audit renamed them)."""
    names = [t["name"] for t in custody.TEMPLATES]
    assert len(names) == len(set(names)), names
    for name in names:
        assert ID_PATTERN.match(name), name
        assert "_" not in name, name


def test_the_check_refuses_a_planted_bad_template():
    """A scan that has never fired has not been shown to check anything.
    Each plant violates exactly one rule, against the real pack's
    schema/jurisdictions — the check must name a violation for every one."""
    base = dict(custody.TEMPLATES[0])

    plants = [
        ("missing key", {k: v for k, v in base.items() if k != "note"}),
        ("bad anchor field", {**base, "anchor": "not_a_real_field"}),
        # the exact shape the struck `relocation_notice` row had.
        ("bad anchor rung", {**base, "anchor": "move_date"}),
        ("bad direction", {**base, "direction": "sideways"}),
        ("bad jurisdiction", {**base, "jurisdiction": "US-CA"}),
        ("bad status", {**base, "status": "PROBABLY"}),
        ("underscore in name", {**base, "name": "registration_contest"}),
        ("direction and rule disagree",
         {**base, "direction": "backward", "rule": "court_days"}),
    ]
    for label, plant in plants:
        errors = _template_errors([plant], custody.SCHEMA, custody.JURISDICTIONS)
        assert errors, f"the check did not fire on a planted {label}"

    # duplicate names need two rows to show up at all.
    duplicated = [base, {**base, "jurisdiction": "US-OR"}]
    errors = _template_errors(duplicated, custody.SCHEMA, custody.JURISDICTIONS)
    assert any("declared more than once" in e for e in errors), errors

    # the unmodified real templates must not trip the same check the plants did.
    assert not _template_errors(
        custody.TEMPLATES, custody.SCHEMA, custody.JURISDICTIONS)


def test_the_nm_row_is_verified_with_provenance_and_the_or_row_is_uncertain():
    """House style: UNCERTAIN → refuse, never guess; and (the dates-a ruling)
    a row may only be `VERIFIED` on a `source` that says *against what* it
    was checked, in a dated PROVENANCE sentence. Both primary hosts were
    blocked on this build, so the NM row's PROVENANCE says so by name and
    says what converging restatements were read instead. The Oregon row
    carries `days: 21` — the number the restatements actually give — while
    staying `UNCERTAIN`, because the uniform section and every other
    enactment read here say 20 and the primary was never read."""
    by_name = {t["name"]: t for t in custody.TEMPLATES}

    nm = by_name["nm-registration-contest"]
    assert nm["jurisdiction"] == "US-NM"
    assert nm["status"] == "VERIFIED"
    assert nm["days"] == 20
    assert "PROVENANCE, 2026-09-11" in nm["source"]
    assert "40-10A-305" in nm["source"]
    # the honest half of a VERIFIED-secondary row: it names the hosts it
    # could not reach, rather than implying a primary was read.
    assert "egress proxy" in nm["source"]
    assert "NOT read here" in nm["source"]

    orr = by_name["or-registration-contest"]
    assert orr["jurisdiction"] == "US-OR"
    assert orr["status"] == "UNCERTAIN"
    assert orr["days"] == 21
    assert "109.787" in orr["source"]
    assert "secondary sources say 21; primary unread" in orr["note"]


def test_no_verified_row_hides_where_its_text_came_from():
    """The rule the engine's own `RuleStatus` docstring states, applied to
    this pack's data: a row may never be `VERIFIED` on a `source` that does
    not say where its text was read. Every VERIFIED row here carries a dated
    PROVENANCE sentence; every UNCERTAIN one says what is unread."""
    for tpl in custody.TEMPLATES:
        if tpl["status"] == "VERIFIED":
            assert "PROVENANCE" in tpl["source"], tpl["name"]
            assert "2026-" in tpl["source"], tpl["name"]
        else:
            assert "UNCERTAIN" in tpl["source"] or "unread" in tpl["source"], tpl["name"]


def test_there_is_no_relocation_notice_template_in_either_forum():
    """New Mexico has none by the plan's own account, and Oregon's (ORS
    107.159) states only "reasonable notice" — no day count, so no period to
    compute and nothing for `compute()` to do but refuse. The date the
    operator actually gave notice is *entered*, as `relocation_notice_date`,
    which is a real field of this pack: the absence of a template is the
    refusal (I-11), and the field is where the answer goes."""
    assert [t for t in custody.TEMPLATES if "relocation" in t["name"]] == []
    assert "relocation_notice_date" in custody.FIELDS
    assert "107.159" in custody.__doc__
    assert "entered, not computed" in custody.__doc__


# ── derived forms say nothing that varies with the value ─────────────────────

_MONTHS = {
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct",
    "nov", "dec",
}
_SEASONS = {"spring", "summer", "autumn", "fall", "winter"}
#: Every state this pack could name — the two in `JURISDICTIONS` and the
#: `US-CA` default it was struck away from — in the forms a sentence could
#: carry them. Bare `"or"` is deliberately absent: it is an English word, and
#: a check that fired on it would be a check nobody could keep.
_STATE_WORDS = {
    "new mexico", "oregon", "california", "us-nm", "us-or", "us-ca",
    " nm ", " ca ",
}


def _words(sentence):
    import re
    return set(re.findall(r"[a-z]+", sentence.lower()))


def test_no_derived_form_in_this_pack_carries_a_digit_a_month_or_a_state():
    """A schema-level derived form is one sentence for *every* record of that
    field, so anything that varies with the value is either false for some
    records or restates exactly what the stand-in exists to withhold. Three
    concrete shapes this pack could plausibly have leaked, checked over the
    whole pack rather than only the fields this bite added: a digit (a date, a
    count, a case number), a month or season name (`move_date`,
    `child.dob`, every date field), and a state name (`new_residence_state`
    is `L2` and renders its own payload, so it needs no stand-in — but the
    relocation fields around it must not name the destination either)."""
    checked = 0
    for field, spec in custody.SCHEMA.items():
        sentence = spec.get("derived")
        if sentence is None:
            continue
        checked += 1
        assert not any(ch.isdigit() for ch in sentence), (field, sentence)
        words = _words(sentence)
        assert not (words & _MONTHS), (field, sorted(words & _MONTHS))
        assert not (words & _SEASONS), (field, sorted(words & _SEASONS))
        low = f" {sentence.lower()} "
        named = sorted(st for st in _STATE_WORDS if st in low)
        assert not named, (field, sentence, named)
    assert checked == 13, (
        "expected a derived sentence on each of custody's seven L3 and six L4 "
        f"fields, found {checked}"
    )


def test_new_residence_state_renders_itself_and_names_no_state_anywhere_else():
    """`new_residence_state` is `L2` (decision: a destination state is a
    coarse household fact that resolves to nobody), so the gate renders its
    payload and it carries no derived form at all — nothing to leak. The
    check that matters is the other way round: no *other* field's stand-in
    may name the state, which the pack-wide scan above covers."""
    assert custody.FIELDS["new_residence_state"] is Rung.L2
    assert custody.SCHEMA["new_residence_state"].get("derived") is None


def test_custody_type_and_move_date_stand_ins_reveal_neither_type_nor_timing():
    """The two fields whose stand-ins are easiest to get wrong, pinned by
    name: `custody_type`'s must not say *which* arrangement (sole, joint,
    legal, physical — the value itself), and `move_date`'s must not say
    *when* (a month, a season, a year)."""
    arrangement = _words(custody.SCHEMA["custody_type"]["derived"])
    assert not (arrangement & {"sole", "joint", "legal", "physical", "shared"})

    when = custody.SCHEMA["move_date"]["derived"]
    assert not any(ch.isdigit() for ch in when)
    assert not (_words(when) & (_MONTHS | _SEASONS))


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
