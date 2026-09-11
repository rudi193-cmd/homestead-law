"""`homestead_law.rules` — deadline templates (decision 4, L3-deadline-templates).

Two halves, tested separately. `validate_templates` (and its registry hook,
`registry._validate`'s one addition for this bite) is a build-time guard: every
plant below constructs a fake pack with exactly one contract violation and
shows the guard names it. `compute`/`accept` are the runtime half: `compute`
never stores (every test that calls it and then inspects the store finds
nothing new there unless `accept` was also called), and `accept` writes only
once a token proves what was shown.

~~No sibling pack (custody, bankruptcy, workers' comp) is read here — those
land in parallel bites and `custody.py` on this branch has no `TEMPLATES`
yet.~~ (struck when the wave-3 branches were stacked: all three packs are on
this branch now.) Every test below still builds its own fake pack, the same
way `tests/test_registry.py` does for its own guard-fire tests — a guard-fire
plant must not depend on what a real pack happens to declare this week. The
one exception is the last section, which reads `packs/bankruptcy.py` on
purpose: the household's own case is in the District of New Mexico, and the
claim that its claims bar lands on a different day for that reason is only
worth anything if it is made against the real table.
"""
from __future__ import annotations

import types

import pytest

from homestead.keep.dates import UnparseableDate, add_mail_days, court_days, court_days_before
from homestead.keep.rungs import Classified, Rung
from homestead_law import instances
from homestead_law import registry as registry_mod
from homestead_law import rules
from homestead_law.jurisdiction import JurisdictionAbsent, set_jurisdiction
from homestead_law.store import RecordExists, Sidecar


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    yield


# ── the engine floor (pyproject.toml: homestead-affairs>=0.6.0) ─────────────

def test_the_engine_floor_carries_backward_counting_and_state_jurisdictions():
    """This bite raises the pinned floor from 0.3.0 to 0.6.0 — the release
    that first ships `court_days_before`, `add_mail_days`, `business_days`
    and the `US-NM`/`US-OR` rows of `dates.RULES` `compute()` depends on
    (decision 4). A version *number* in `pyproject.toml` is not proof; this
    import and assertion is what actually fails, on a version below the
    floor, before any other test in this file gets the chance to."""
    from homestead.keep import dates
    from homestead.keep.dates import court_days_before

    assert callable(court_days_before)
    assert "US-NM" in dates.JURISDICTIONS
    assert "US-OR" in dates.JURISDICTIONS


# ── a fake pack, the way test_registry.py builds one ─────────────────────────

def _fake_pack(
    name: str = "_fake_tpl",
    *,
    jurisdiction: str = "US-NM",
    jurisdictions: tuple[str, ...] = ("US-NM", "US-OR", "US-federal"),
    anchor: str = "move_date",
    templates: tuple[dict, ...] = (),
    extra_fields: dict | None = None,
) -> types.ModuleType:
    """A stand-in pack with one `L1` anchor field and whatever `TEMPLATES`
    the caller wants — never a real future pack name (bankruptcy and workers'
    comp land in parallel bites), so a plant here can never collide with a
    real one landing later."""
    mod = types.ModuleType(f"homestead_law.packs.{name}")
    mod.MATTER = name
    mod.JURISDICTION = jurisdiction
    mod.JURISDICTIONS = jurisdictions
    mod.FIELDS = {anchor: Rung.L1, "jurisdiction": Rung.L1, "notes": Rung.L4}
    mod.SCHEMA = {
        anchor: {"rung": Rung.L1, "matter": name, "why": "test"},
        "jurisdiction": {"rung": Rung.L1, "matter": name, "why": "test"},
        "notes": {"rung": Rung.L4, "matter": name, "why": "test", "derived": "A note is on file"},
    }
    # A pack that declares its own `district_state` field (the second of the
    # two sources `rules._district_state_for` reads, and the only one a pack
    # rather than a template can offer) opts in here, at whatever rung the
    # test wants to plant.
    for extra, rung in (extra_fields or {}).items():
        mod.FIELDS[extra] = rung
        decl = {"rung": rung, "matter": name, "why": "test"}
        if rung in (Rung.L3, Rung.L4):
            decl["derived"] = "On file"
        mod.SCHEMA[extra] = decl
    mod.TEMPLATES = templates
    return mod


def _template(**over) -> dict:
    """One valid `TEMPLATES` entry — `move_date` + 20 forward court_days,
    the shape every validation-plant test starts from and breaks one field
    of at a time."""
    base = dict(
        name="notice", anchor="move_date", days=20, direction="forward",
        rule="court_days", mail=False, jurisdiction="US-NM",
        source="NMSA 40-10A-305", status="VERIFIED", note="",
    )
    base.update(over)
    return base


def _registered(mt) -> "types.SimpleNamespace":
    """Context manager: register `mt` under its own name for the duration of
    a `with` block, and remove it again even if the body raises — the same
    teardown discipline `test_server.py::_register_second_matter` gets from
    `monkeypatch.setitem`, done by hand here since these tests build the
    `MatterType` themselves rather than going through `registry._entry`."""
    import contextlib

    @contextlib.contextmanager
    def _cm():
        registry_mod.REGISTRY[mt.name] = mt
        try:
            yield mt
        finally:
            del registry_mod.REGISTRY[mt.name]

    return _cm()


def _mt(pack: types.ModuleType) -> registry_mod.MatterType:
    return registry_mod._entry(pack)


# ── validate_templates — plant every violation ────────────────────────────

def test_a_pack_with_no_templates_attribute_validates_clean():
    """Custody's own shape today: templates are optional pack data. A pack
    that never sets `TEMPLATES` at all — not even an empty tuple — validates
    without complaint (`hasattr`, not a required attribute)."""
    pack = types.ModuleType("homestead_law.packs._fake_no_templates")
    pack.MATTER = "_fake_no_templates"
    pack.JURISDICTION = "US-NM"
    pack.JURISDICTIONS = ("US-NM",)
    pack.FIELDS = {"move_date": Rung.L1}
    assert not hasattr(pack, "TEMPLATES")
    rules.validate_templates(pack)          # does not raise
    assert rules.templates_of(_mt(pack)) == ()


def test_an_empty_templates_tuple_validates_clean():
    pack = _fake_pack(templates=())
    rules.validate_templates(pack)
    assert rules.templates_of(_mt(pack)) == ()


def test_templates_must_be_a_tuple():
    pack = _fake_pack()
    pack.TEMPLATES = [_template()]          # a list, not a tuple
    with pytest.raises(rules.InvalidTemplate) as exc:
        rules.validate_templates(pack)
    assert "tuple" in str(exc.value)


def test_an_entry_must_be_a_mapping():
    pack = _fake_pack(templates=("not-a-dict",))
    with pytest.raises(rules.InvalidTemplate) as exc:
        rules.validate_templates(pack)
    assert "mapping" in str(exc.value)


def test_wrong_keys_missing_is_named():
    entry = _template()
    del entry["note"]
    pack = _fake_pack(templates=(entry,))
    with pytest.raises(rules.InvalidTemplate) as exc:
        rules.validate_templates(pack)
    assert "note" in str(exc.value) and "missing" in str(exc.value)


def test_wrong_keys_extra_is_named():
    entry = _template()
    entry["extra_field"] = "x"
    pack = _fake_pack(templates=(entry,))
    with pytest.raises(rules.InvalidTemplate) as exc:
        rules.validate_templates(pack)
    assert "extra_field" in str(exc.value) and "unexpected" in str(exc.value)


def test_name_must_be_a_non_empty_string():
    pack = _fake_pack(templates=(_template(name=""),))
    with pytest.raises(rules.InvalidTemplate):
        rules.validate_templates(pack)


def test_name_must_match_the_id_pattern():
    """A template name is stored as a repeatable sub-id
    (`instances.item_id(instance, template)`) — an underscore or an
    uppercase letter would build a key `item_id` itself refuses, later and
    less legibly, at `accept` time."""
    pack = _fake_pack(templates=(_template(name="Not_Valid"),))
    with pytest.raises(rules.InvalidTemplate) as exc:
        rules.validate_templates(pack)
    assert "Not_Valid" in str(exc.value)     # a pack author's own label, echoed


def test_duplicate_template_names_are_refused():
    """Two rows, same name, same jurisdiction — the repeat `compute` could
    not choose between. (A repeat across *different* jurisdictions is the
    ordinary shape of a rule that differs by forum and is allowed; see
    `test_one_name_declared_for_two_jurisdictions_validates`.)"""
    pack = _fake_pack(templates=(_template(), _template()))
    with pytest.raises(rules.InvalidTemplate) as exc:
        rules.validate_templates(pack)
    assert "more than once" in str(exc.value)


def test_anchor_must_be_a_field_the_pack_declares():
    pack = _fake_pack(templates=(_template(anchor="no_such_field"),))
    with pytest.raises(rules.InvalidTemplate) as exc:
        rules.validate_templates(pack)
    assert "no_such_field" in str(exc.value)


def test_anchor_must_be_l1_not_l4():
    """`notes` is `L4` on the fake pack — a real field, just not a public
    one, which is exactly the case a template must never anchor on."""
    pack = _fake_pack(templates=(_template(anchor="notes"),))
    with pytest.raises(rules.InvalidTemplate) as exc:
        rules.validate_templates(pack)
    assert "notes" in str(exc.value) and "L4" in str(exc.value)


@pytest.mark.parametrize("bad_days", [0, -1, 20.0, True, "20"])
def test_days_must_be_a_positive_int(bad_days):
    pack = _fake_pack(templates=(_template(days=bad_days),))
    with pytest.raises(rules.InvalidTemplate) as exc:
        rules.validate_templates(pack)
    assert "days" in str(exc.value)


def test_direction_must_be_forward_or_backward():
    pack = _fake_pack(templates=(_template(direction="sideways"),))
    with pytest.raises(rules.InvalidTemplate) as exc:
        rules.validate_templates(pack)
    assert "sideways" in str(exc.value)


def test_rule_must_be_one_of_the_four():
    pack = _fake_pack(templates=(_template(rule="guess"),))
    with pytest.raises(rules.InvalidTemplate) as exc:
        rules.validate_templates(pack)
    assert "guess" in str(exc.value)


def test_backward_direction_requires_court_days_before():
    pack = _fake_pack(
        templates=(_template(direction="backward", rule="court_days"),)
    )
    with pytest.raises(rules.InvalidTemplate) as exc:
        rules.validate_templates(pack)
    assert "disagree" in str(exc.value)


def test_court_days_before_requires_backward_direction():
    pack = _fake_pack(
        templates=(_template(direction="forward", rule="court_days_before"),)
    )
    with pytest.raises(rules.InvalidTemplate) as exc:
        rules.validate_templates(pack)
    assert "disagree" in str(exc.value)


def test_mail_must_be_a_bool():
    pack = _fake_pack(templates=(_template(mail="yes"),))
    with pytest.raises(rules.InvalidTemplate) as exc:
        rules.validate_templates(pack)
    assert "mail" in str(exc.value)


def test_calendar_days_never_has_mail():
    pack = _fake_pack(
        templates=(_template(rule="calendar_days", direction="forward", mail=True),)
    )
    with pytest.raises(rules.InvalidTemplate) as exc:
        rules.validate_templates(pack)
    assert "calendar_days" in str(exc.value)


def test_jurisdiction_must_be_none_or_a_member_of_the_packs_tuple():
    pack = _fake_pack(templates=(_template(jurisdiction="US-CA"),))
    with pytest.raises(rules.InvalidTemplate) as exc:
        rules.validate_templates(pack)
    assert "US-CA" in str(exc.value)


def test_jurisdiction_none_is_allowed():
    pack = _fake_pack(templates=(_template(jurisdiction=None),))
    rules.validate_templates(pack)           # does not raise


def test_source_must_be_a_non_empty_string():
    pack = _fake_pack(templates=(_template(source="   "),))
    with pytest.raises(rules.InvalidTemplate) as exc:
        rules.validate_templates(pack)
    assert "source" in str(exc.value)


def test_status_must_be_verified_or_uncertain():
    pack = _fake_pack(templates=(_template(status="MAYBE"),))
    with pytest.raises(rules.InvalidTemplate) as exc:
        rules.validate_templates(pack)
    assert "MAYBE" in str(exc.value)


def test_note_must_be_a_string():
    pack = _fake_pack(templates=(_template(note=123),))
    with pytest.raises(rules.InvalidTemplate) as exc:
        rules.validate_templates(pack)
    assert "note" in str(exc.value)


def test_a_valid_template_round_trips_through_templates_of():
    pack = _fake_pack(templates=(_template(),))
    mt = _mt(pack)
    found = rules.templates_of(mt)
    assert len(found) == 1
    template = found[0]
    assert isinstance(template, rules.Template)
    assert template.name == "notice"
    assert template.days == 20
    assert template.status == "VERIFIED"


# ── the registry hook fires (registry._validate's one addition) ─────────────

def test_registrys_own_validate_fires_the_template_guard():
    """`registry._validate` is directly callable against a deliberately broken
    registry, the way `tests/test_registry.py` already exercises every other
    guard in it — this is the same guard, aimed at a pack whose `TEMPLATES`
    is broken rather than whose `SCHEMA` is."""
    from homestead_law.packs import custody

    bad_pack = _fake_pack(templates=(_template(anchor="no_such_field"),))
    broken = {"custody": registry_mod.REGISTRY["custody"], bad_pack.MATTER: _mt(bad_pack)}
    on_disk = {"custody": custody, bad_pack.MATTER: bad_pack}
    with pytest.raises(rules.InvalidTemplate) as exc:
        registry_mod._validate(broken, on_disk)
    assert "no_such_field" in str(exc.value)


def test_the_real_registry_still_validates_clean():
    """The guard runs against the live `REGISTRY` on every import already —
    this just re-asserts it, so a change to custody's (currently empty)
    `TEMPLATES` that breaks the contract fails here too, not only at the next
    cold interpreter start."""
    registry_mod._validate(registry_mod.REGISTRY, registry_mod._discover_packs())


def test_rules_calls_the_gate_directly_so_the_chokepoint_scan_covers_it():
    """L3-deadline-templates' own confirmation, not a new rule:
    `tests/test_chokepoint.py`'s `_is_surface` counts any module that calls
    `serve()`/`serve_all()`/`ambient_rows()` as a surface automatically, so
    `rules.py` — which calls `serve()` in `_read_anchor` — is swept into the
    reflection ban with no edit to that file needed. Checked directly against
    `rules.py`'s own source (rather than importing `test_chokepoint`'s
    helpers — this directory has no `tests/__init__.py`, so this file avoids
    a cross-test import)."""
    import ast
    from pathlib import Path

    tree = ast.parse(Path(rules.__file__).read_text("utf-8"))
    calls_serve = any(
        isinstance(node, ast.Call)
        and (
            (isinstance(node.func, ast.Name) and node.func.id == "serve")
            or (isinstance(node.func, ast.Attribute) and node.func.attr == "serve")
        )
        for node in ast.walk(tree)
    )
    assert calls_serve, (
        "rules.py no longer calls serve() directly — the chokepoint scan "
        "would stop treating it as a surface"
    )


# ── compute — reads, never writes ────────────────────────────────────────

@pytest.fixture
def nm_instance():
    """A fake matter, registered, with `move_date` on file and the instance
    opened in `US-NM` — the shared starting point for most `compute` tests."""
    pack = _fake_pack(templates=(_template(),))
    mt = _mt(pack)
    with _registered(mt):
        store = Sidecar()
        set_jurisdiction(store, mt.name, "primary", "US-NM")
        store.put(mt.name, "move_date", "primary", Classified(Rung.L1, "2026-01-01"))
        yield store, mt


def test_compute_matches_the_engines_own_court_days(nm_instance):
    """The cross-check the brief asks for: `compute`'s result is not a
    reimplementation, it is `court_days` under the template's own numbers."""
    store, mt = nm_instance
    computed = rules.compute(store, mt.name, "primary", "notice")

    direct = court_days("2026-01-01", 20, jurisdiction="US-NM")
    assert computed.result_iso == direct.iso
    assert computed.anchor_field == "move_date"
    assert computed.anchor_iso == "2026-01-01"
    assert computed.source == "NMSA 40-10A-305"
    assert computed.jurisdiction == "US-NM"
    assert computed.mail is False


def test_compute_stores_nothing():
    pack = _fake_pack(templates=(_template(),))
    mt = _mt(pack)
    with _registered(mt):
        store = Sidecar()
        set_jurisdiction(store, mt.name, "primary", "US-NM")
        store.put(mt.name, "move_date", "primary", Classified(Rung.L1, "2026-01-01"))
        before = store.records(mt.name)
        rules.compute(store, mt.name, "primary", "notice")
        after = store.records(mt.name)
        assert before == after


def test_a_template_scoped_to_one_jurisdiction_refuses_a_different_instance(nm_instance):
    """decision 1: OR is one of the pack's jurisdictions; the template is
    scoped to NM. The instance is opened OR here instead."""
    store, mt = nm_instance
    set_jurisdiction(store, mt.name, "primary", "US-OR", replace=True)

    with pytest.raises(rules.TemplateJurisdictionMismatch) as exc:
        rules.compute(store, mt.name, "primary", "notice")
    message = str(exc.value)
    assert "US-NM" in message and "US-OR" in message
    assert "this template is for US-NM; the instance is US-OR" in message


def test_a_template_with_no_jurisdiction_accepts_any_instance():
    pack = _fake_pack(templates=(_template(jurisdiction=None),))
    mt = _mt(pack)
    with _registered(mt):
        store = Sidecar()
        set_jurisdiction(store, mt.name, "primary", "US-OR")
        store.put(mt.name, "move_date", "primary", Classified(Rung.L1, "2026-01-01"))
        computed = rules.compute(store, mt.name, "primary", "notice")
        assert computed.jurisdiction == "US-OR"


def test_an_instance_with_no_jurisdiction_refuses_i42():
    pack = _fake_pack(templates=(_template(),))
    mt = _mt(pack)
    with _registered(mt):
        store = Sidecar()
        store.put(mt.name, "move_date", "primary", Classified(Rung.L1, "2026-01-01"))
        with pytest.raises(JurisdictionAbsent):
            rules.compute(store, mt.name, "primary", "notice")


def test_an_absent_anchor_refuses_by_name(nm_instance):
    store, mt = nm_instance
    set_jurisdiction(store, mt.name, "second", "US-NM")   # opened, no move_date filed
    with pytest.raises(rules.AnchorUnavailable) as exc:
        rules.compute(store, mt.name, "second", "notice")
    message = str(exc.value)
    assert mt.name in message and "second" in message and "move_date" in message


def test_an_anchor_planted_above_l1_refuses_through_the_gate(nm_instance):
    """The gate check, not the pack contract: even though the pack declares
    `move_date` L1, a hand-planted record at `L4` must not be readable as an
    anchor — and the refusal must not echo the planted value."""
    store, mt = nm_instance
    store.put(
        mt.name, "move_date", "primary",
        Classified(Rung.L4, "2026-01-01", derived="A date is on file"),
        overwrite=True,
    )
    with pytest.raises(rules.AnchorUnavailable) as exc:
        rules.compute(store, mt.name, "primary", "notice")
    message = str(exc.value)
    assert "2026-01-01" not in message           # never echoed (I-15)
    assert "move_date" in message


def test_uncertain_template_refuses_before_any_arithmetic(monkeypatch):
    """`status == "UNCERTAIN"` must refuse *before* a counting function is
    ever called — proved by making `court_days` itself fail if reached."""
    pack = _fake_pack(templates=(_template(status="UNCERTAIN", source="unclear rule"),))
    mt = _mt(pack)

    def _boom(*a, **k):
        raise AssertionError("court_days must not be called for an UNCERTAIN template")

    monkeypatch.setattr("homestead.keep.dates.court_days", _boom)

    with _registered(mt):
        store = Sidecar()
        set_jurisdiction(store, mt.name, "primary", "US-NM")
        store.put(mt.name, "move_date", "primary", Classified(Rung.L1, "2026-01-01"))
        with pytest.raises(rules.UncertainTemplate) as exc:
            rules.compute(store, mt.name, "primary", "notice")
        assert str(exc.value) == "UNCERTAIN: unclear rule"


def test_mail_on_a_federal_forward_template_equals_add_mail_days():
    pack = _fake_pack(
        jurisdiction="US-federal", jurisdictions=("US-federal",),
        templates=(_template(jurisdiction="US-federal", source="FRBP 9006(f)"),),
    )
    mt = _mt(pack)
    with _registered(mt):
        store = Sidecar()
        set_jurisdiction(store, mt.name, "primary", "US-federal")
        store.put(mt.name, "move_date", "primary", Classified(Rung.L1, "2026-01-01"))

        computed = rules.compute(store, mt.name, "primary", "notice", mail=True)
        expected = add_mail_days(
            court_days("2026-01-01", 20, jurisdiction="US-federal"),
            jurisdiction="US-federal",
        )
        assert computed.result_iso == expected.iso
        assert computed.mail is True


def test_a_backward_template_uses_court_days_before():
    pack = _fake_pack(
        jurisdiction="US-federal", jurisdictions=("US-federal",),
        templates=(_template(
            name="objection", anchor="move_date", days=7, direction="backward",
            rule="court_days_before", jurisdiction="US-federal", source="FRBP 3015(f)",
        ),),
    )
    mt = _mt(pack)
    with _registered(mt):
        store = Sidecar()
        set_jurisdiction(store, mt.name, "primary", "US-federal")
        store.put(mt.name, "move_date", "primary", Classified(Rung.L1, "2026-03-01"))

        computed = rules.compute(store, mt.name, "primary", "objection")
        expected = court_days_before("2026-03-01", 7, jurisdiction="US-federal")
        assert computed.result_iso == expected.iso


def test_calendar_days_ignores_holidays_and_never_rolls():
    """2026-01-02 + 30 calendar days is 2026-02-01, a Sunday — and it stays
    that Sunday. `court_days` under the same 30 days would roll it to the
    next open day; `calendar_days` must not, by construction (no calendar
    read, no roll — the module docstring's own claim, held here)."""
    import datetime as dt

    anchor = "2026-01-02"
    assert (dt.date(2026, 1, 2) + dt.timedelta(days=30)).isoformat() == "2026-02-01"
    assert dt.date(2026, 2, 1).weekday() == 6      # Sunday

    pack = _fake_pack(
        templates=(_template(
            name="span", anchor="move_date", days=30, direction="forward",
            rule="calendar_days", jurisdiction=None, source="test",
        ),),
    )
    mt = _mt(pack)
    with _registered(mt):
        store = Sidecar()
        set_jurisdiction(store, mt.name, "primary", "US-NM")
        store.put(mt.name, "move_date", "primary", Classified(Rung.L1, anchor))

        computed = rules.compute(store, mt.name, "primary", "span")
        assert computed.result_iso == "2026-02-01"

        # court_days, over the same anchor and days, would roll off the Sunday
        rolled = court_days(anchor, 30, jurisdiction="US-NM")
        assert rolled.iso != computed.result_iso


def test_mail_is_refused_on_a_backward_template():
    pack = _fake_pack(
        jurisdiction="US-federal", jurisdictions=("US-federal",),
        templates=(_template(
            name="objection", anchor="move_date", days=7, direction="backward",
            rule="court_days_before", jurisdiction="US-federal", source="FRBP 3015(f)",
        ),),
    )
    mt = _mt(pack)
    with _registered(mt):
        store = Sidecar()
        set_jurisdiction(store, mt.name, "primary", "US-federal")
        store.put(mt.name, "move_date", "primary", Classified(Rung.L1, "2026-03-01"))
        with pytest.raises(rules.MailUnsupported) as exc:
            rules.compute(store, mt.name, "primary", "objection", mail=True)
        assert "court_days_before" in str(exc.value)


def test_mail_is_refused_on_a_calendar_days_template():
    pack = _fake_pack(
        templates=(_template(
            name="span", anchor="move_date", days=30, direction="forward",
            rule="calendar_days", jurisdiction=None, source="test",
        ),),
    )
    mt = _mt(pack)
    with _registered(mt):
        store = Sidecar()
        set_jurisdiction(store, mt.name, "primary", "US-NM")
        store.put(mt.name, "move_date", "primary", Classified(Rung.L1, "2026-01-02"))
        with pytest.raises(rules.MailUnsupported) as exc:
            rules.compute(store, mt.name, "primary", "span", mail=True)
        assert "calendar_days" in str(exc.value)


def test_an_unknown_template_name_refuses_by_name(nm_instance):
    store, mt = nm_instance
    with pytest.raises(rules.TemplateNotFound) as exc:
        rules.compute(store, mt.name, "primary", "no-such-template")
    assert "no-such-template" in str(exc.value)


def test_an_unknown_matter_refuses_with_key_error():
    store = Sidecar()
    with pytest.raises(KeyError):
        rules.compute(store, "not_a_matter", "primary", "notice")


def test_a_malformed_instance_id_refuses_by_name(nm_instance):
    store, mt = nm_instance
    with pytest.raises(instances.InvalidId):
        rules.compute(store, mt.name, "Not Valid", "notice")


def test_an_anchor_that_will_not_parse_refuses_and_may_echo_it_l1(nm_instance):
    """The anchor is `L1` (validated at registry time) — echoing the
    unparseable text in the engine's own message is not an I-15 violation
    the way it would be for `L3`+ content."""
    store, mt = nm_instance
    store.put(mt.name, "move_date", "primary", Classified(Rung.L1, "next week"), overwrite=True)
    with pytest.raises(UnparseableDate) as exc:
        rules.compute(store, mt.name, "primary", "notice")
    assert "next week" in str(exc.value)


# ── accept — the only writer ─────────────────────────────────────────────

def test_accept_writes_the_same_two_field_shape_the_deadline_command_uses(nm_instance):
    store, mt = nm_instance
    computed = rules.compute(store, mt.name, "primary", "notice")

    replaced = rules.accept(store, computed, token=computed.preview_token)
    assert replaced is None                      # first write, nothing displaced

    item_id = instances.item_id("primary", "notice")
    record = store.get(mt.name, "deadline", item_id)
    assert record.rung is Rung.L1
    assert record.payload == computed.result_iso
    assert record.derived == (
        "computed from move_date under NMSA 40-10A-305; "
        "confirm against the source above"
    )


def test_the_queue_reads_an_accepted_deadline_by_reference(nm_instance):
    store, mt = nm_instance
    computed = rules.compute(store, mt.name, "primary", "notice")
    rules.accept(store, computed, token=computed.preview_token)

    from homestead_law import queue as queue_mod

    # `nm_instance` holds its own `with _registered(mt)` open across the
    # whole test (the fixture yields from inside it), so `mt.name` is still
    # enumerable here without registering it again.
    items = queue_mod.queue(store, today="2026-01-01")
    found = [i for i in items if i.matter == mt.name and i.instance == "primary"]
    assert len(found) == 1
    assert found[0].shown == computed.result_iso


def test_a_token_mismatch_refuses_and_stores_nothing(nm_instance):
    store, mt = nm_instance
    computed = rules.compute(store, mt.name, "primary", "notice")

    with pytest.raises(rules.StaleToken):
        rules.accept(store, computed, token="not-the-real-token")

    item_id = instances.item_id("primary", "notice")
    assert not store.has(mt.name, "deadline", item_id)


def test_a_second_accept_without_replace_refuses(nm_instance):
    store, mt = nm_instance
    computed = rules.compute(store, mt.name, "primary", "notice")
    rules.accept(store, computed, token=computed.preview_token)

    with pytest.raises(RecordExists):
        rules.accept(store, computed, token=computed.preview_token)

    item_id = instances.item_id("primary", "notice")
    assert store.get(mt.name, "deadline", item_id).payload == computed.result_iso


def test_replace_true_overwrites_the_accepted_deadline(nm_instance):
    store, mt = nm_instance
    first = rules.compute(store, mt.name, "primary", "notice")
    rules.accept(store, first, token=first.preview_token)

    store.put(mt.name, "move_date", "primary", Classified(Rung.L1, "2026-02-01"), overwrite=True)
    second = rules.compute(store, mt.name, "primary", "notice")
    replaced = rules.accept(store, second, token=second.preview_token, replace=True)

    assert replaced is not None
    item_id = instances.item_id("primary", "notice")
    assert store.get(mt.name, "deadline", item_id).payload == second.result_iso


def test_preview_token_is_stable_for_the_same_fields_and_changes_when_one_does(nm_instance):
    store, mt = nm_instance
    a = rules.compute(store, mt.name, "primary", "notice")
    b = rules.compute(store, mt.name, "primary", "notice")
    assert a.preview_token == b.preview_token    # same inputs, same hash

    store.put(mt.name, "move_date", "primary", Classified(Rung.L1, "2026-02-01"), overwrite=True)
    c = rules.compute(store, mt.name, "primary", "notice")
    assert c.preview_token != a.preview_token    # the anchor moved


# ── one name, two jurisdictions (the custody shape) ──────────────────────
#
# The audit finding this section pins: `validate_templates` refused *any*
# repeated template name, and `compute` took the first row whose name
# matched, ignoring which forum it was written for. The custody pack
# declares `registration-contest` twice — 20 court days under NMSA
# 40-10A-305 for `US-NM`, 21 under the OR reading — so the first behaviour
# made that pack unimportable and the second would have counted an OR
# instance's contest window under New Mexico's statute.

def _two_forum_pack(**over):
    """The custody shape, as a fake pack: one name, two jurisdictions,
    different periods. Never the real pack — that lands in a parallel bite."""
    return _fake_pack(
        templates=(
            _template(name="contest", days=20, jurisdiction="US-NM",
                      source="NMSA 40-10A-305"),
            _template(name="contest", days=21, jurisdiction="US-OR",
                      source="ORS 109.787", **over),
        ),
    )


def test_one_name_declared_for_two_jurisdictions_validates():
    """Not a duplicate — the ordinary shape of a rule that differs by forum."""
    rules.validate_templates(_two_forum_pack())
    names = [t.name for t in rules.templates_of(_mt(_two_forum_pack()))]
    assert names == ["contest", "contest"]


def test_compute_picks_the_template_for_the_instances_own_jurisdiction():
    """The whole point of allowing the repeat: an OR instance is counted
    under the OR row's 21 days, an NM instance under the NM row's 20 — and
    `source` follows, so the stored instruction cites the right statute."""
    pack = _two_forum_pack()
    mt = _mt(pack)
    with _registered(mt):
        store = Sidecar()
        store.put(mt.name, "move_date", "primary", Classified(Rung.L1, "2026-01-01"))

        set_jurisdiction(store, mt.name, "primary", "US-NM")
        nm = rules.compute(store, mt.name, "primary", "contest")
        assert nm.result_iso == court_days("2026-01-01", 20, jurisdiction="US-NM").iso
        assert nm.source == "NMSA 40-10A-305"

        set_jurisdiction(store, mt.name, "primary", "US-OR", replace=True)
        orr = rules.compute(store, mt.name, "primary", "contest")
        assert orr.result_iso == court_days("2026-01-01", 21, jurisdiction="US-OR").iso
        assert orr.source == "ORS 109.787"

        assert nm.result_iso != orr.result_iso
        assert nm.preview_token != orr.preview_token


def test_a_name_declared_both_for_all_forums_and_for_one_is_refused():
    """`jurisdiction=None` fits every instance, so pairing it with a specific
    row makes every NM instance ambiguous. Refused at import, not at the
    operator's first compute."""
    pack = _fake_pack(templates=(
        _template(name="contest", jurisdiction=None),
        _template(name="contest", jurisdiction="US-NM"),
    ))
    with pytest.raises(rules.InvalidTemplate) as exc:
        rules.validate_templates(pack)
    assert "jurisdiction=None" in str(exc.value)


def test_a_name_that_fits_no_declared_forum_refuses_naming_the_ones_it_does():
    """Two rows, neither for `US-federal`: the refusal lists both codes the
    pack does declare — published labels, never stored content (I-15)."""
    pack = _two_forum_pack()
    mt = _mt(pack)
    with _registered(mt):
        store = Sidecar()
        set_jurisdiction(store, mt.name, "primary", "US-federal")
        store.put(mt.name, "move_date", "primary", Classified(Rung.L1, "2026-01-01"))
        with pytest.raises(rules.TemplateJurisdictionMismatch) as exc:
            rules.compute(store, mt.name, "primary", "contest")
        message = str(exc.value)
        assert "US-NM" in message and "US-OR" in message
        assert "the instance is US-federal" in message


def test_two_templates_fitting_one_forum_refuse_rather_than_pick(monkeypatch):
    """`AmbiguousTemplate` — the runtime half of the validation rule above,
    planted by handing `compute` a template list `validate_templates` would
    never have passed (the only way to reach it, which is the point)."""
    pack = _fake_pack(templates=(_template(name="contest"),))
    mt = _mt(pack)
    doubled = (
        rules.Template(**_template(name="contest", days=20)),
        rules.Template(**_template(name="contest", days=99)),
    )
    monkeypatch.setattr(rules, "templates_of", lambda _mt: doubled)
    with _registered(mt):
        store = Sidecar()
        set_jurisdiction(store, mt.name, "primary", "US-NM")
        store.put(mt.name, "move_date", "primary", Classified(Rung.L1, "2026-01-01"))
        with pytest.raises(rules.AmbiguousTemplate) as exc:
            rules.compute(store, mt.name, "primary", "contest")
        assert "more than one template of this name" in str(exc.value)


# ── mail days never extend a period that does not run from service ───────

def test_mail_true_on_a_backward_template_is_refused_at_import():
    """dates-a's rule, re-stated where a pack can trip over it: the three
    days of FRBP 9006(f)/FRCP 6(d) extend a period that runs from *service*.
    A period counted backward from a hearing runs from the hearing, so there
    is nothing to extend — and adding three days anyway would move an
    objection deadline three days *later*, past the point the rule protects.
    The bankruptcy pack's `objection` row (−7 court days, `mail: True`) is
    exactly this shape, which is what this guard is for."""
    pack = _fake_pack(templates=(_template(
        name="objection", days=7, direction="backward",
        rule="court_days_before", mail=True,
    ),))
    with pytest.raises(rules.InvalidTemplate) as exc:
        rules.validate_templates(pack)
    message = str(exc.value)
    assert "mail must be false on a backward" in message
    assert "9006(f)" in message


def test_mail_true_on_a_forward_court_rule_validates():
    """So the guard above is a rule and not a blanket ban on the key."""
    rules.validate_templates(_fake_pack(templates=(_template(mail=True),)))
    rules.validate_templates(
        _fake_pack(templates=(_template(rule="business_days", mail=True),)))


# ── arithmetic, cross-checked against the engine one case at a time ──────
#
# `compute` is not allowed to be a second implementation of anything. Each
# case below states the hand-checkable answer *as a literal* and then asserts
# the engine agrees, so a change in either this module or `homestead.keep.
# dates` has to break one of the two halves visibly.

_SERIAL = iter(range(1000))


def _computed(template, *, code, anchor="2026-01-01", extra_fields=None,
              district_record=None, mail=False):
    # A fresh pack name per call: two `_computed`s in one test share the
    # tmp_path store, and re-opening the same instance would hit I-9's
    # first-write rule rather than the behaviour under test.
    pack = _fake_pack(
        f"_fake_tpl{next(_SERIAL)}",
        jurisdiction=code, jurisdictions=("US-NM", "US-OR", "US-federal"),
        templates=(template,), extra_fields=extra_fields,
    )
    mt = _mt(pack)
    with _registered(mt):
        store = Sidecar()
        set_jurisdiction(store, mt.name, "primary", code)
        store.put(mt.name, "move_date", "primary", Classified(Rung.L1, anchor))
        if district_record is not None:
            rung, value = district_record
            store.put(mt.name, "district_state", "primary",
                      Classified(rung, value, "On file" if rung in (Rung.L3, Rung.L4) else None))
        return rules.compute(store, mt.name, "primary", template["name"], mail=mail)


def test_nm_forward_twenty_court_days_from_a_friday_uses_the_state_calendar():
    """2026-09-11 is a Friday. Twenty days is at or above NM's 11-day
    short-period threshold, so Rule 1-006's ordinary forward branch applies
    (the verified one) and the answer is 2026-10-01."""
    import datetime as dt
    assert dt.date(2026, 9, 11).weekday() == 4          # Friday

    computed = _computed(
        _template(name="contest", days=20, jurisdiction="US-NM"),
        code="US-NM", anchor="2026-09-11",
    )
    assert computed.result_iso == "2026-10-01"
    assert computed.result_iso == court_days(
        "2026-09-11", 20, jurisdiction="US-NM").iso
    # Not the federal calendar wearing NM's name: the two rows are different
    # rules, and a state count never carries a district_state.
    assert computed.district_state is None


def test_federal_forward_seventy_court_days_matches_the_engine():
    """FRBP 3002(c)'s claims bar, as the bankruptcy pack declares it."""
    computed = _computed(
        _template(name="claims-bar", days=70, jurisdiction="US-federal"),
        code="US-federal", anchor="2026-09-11",
    )
    assert computed.result_iso == "2026-11-20"
    assert computed.result_iso == court_days("2026-09-11", 70).iso


def test_federal_backward_seven_court_days_before_a_monday_hearing():
    """FRBP 3015(f)'s objection window. 2026-11-16 is a Monday; seven days
    back, excluding the event day and rolling backward off a closure, is
    2026-11-09 — and no mail days are added (see the import-time guard)."""
    import datetime as dt
    assert dt.date(2026, 11, 16).weekday() == 0         # Monday

    computed = _computed(
        _template(name="objection", days=7, direction="backward",
                  rule="court_days_before", jurisdiction="US-federal"),
        code="US-federal", anchor="2026-11-16",
    )
    assert computed.result_iso == "2026-11-09"
    assert computed.result_iso == court_days_before("2026-11-16", 7).iso
    assert computed.mail is False


# ── FRBP 9006(a)(6)(C) — the district's own state holidays ───────────────
#
# The case that makes this real: 2026-11-27, the Friday after Thanksgiving,
# is a working day on the federal calendar and a legal holiday in New
# Mexico. A Chapter 13 case in the District of New Mexico with a
# 2026-09-18 petition has its 70-day claims bar land exactly there, so the
# answer is 2026-11-27 without the district's state and 2026-11-30 with it.
# Three days apart after mail days. A computed deadline that silently picked
# the wrong one of those is the harm this whole section exists to stop.

_DISTRICT_ANCHOR = "2026-09-18"
_WITHOUT_NM = "2026-11-27"
_WITH_NM = "2026-11-30"


def test_the_pinned_case_actually_turns_on_a_new_mexico_holiday():
    """Guard for the guard: if `holidays` ever stops calling 2026-11-27 an
    NM closure, every assertion below would pass vacuously."""
    import datetime as dt
    import holidays

    assert dt.date(2026, 11, 27) in holidays.US(subdiv="NM", years=[2026])
    assert dt.date(2026, 11, 27) not in holidays.US(years=[2026])
    assert court_days(_DISTRICT_ANCHOR, 70).iso == _WITHOUT_NM
    assert court_days(_DISTRICT_ANCHOR, 70, district_state="NM").iso == _WITH_NM


def test_a_template_naming_a_district_state_counts_that_states_holidays():
    computed = _computed(
        _template(name="claims-bar", days=70, jurisdiction="US-federal",
                  district_state="NM"),
        code="US-federal", anchor=_DISTRICT_ANCHOR,
    )
    assert computed.result_iso == _WITH_NM
    assert computed.district_state == "NM"


def test_without_a_district_state_the_computed_says_so_rather_than_assuming():
    computed = _computed(
        _template(name="claims-bar", days=70, jurisdiction="US-federal"),
        code="US-federal", anchor=_DISTRICT_ANCHOR,
    )
    assert computed.result_iso == _WITHOUT_NM
    assert computed.district_state is None


def test_an_l1_district_state_record_on_the_instance_is_read_through_the_gate():
    """The second source: a pack that declares an `L1` `district_state`
    field lets one instance say which district it is in. No district *name*
    is ever mapped to a code — that table is not this module's to keep."""
    computed = _computed(
        _template(name="claims-bar", days=70, jurisdiction="US-federal"),
        code="US-federal", anchor=_DISTRICT_ANCHOR,
        extra_fields={"district_state": Rung.L1},
        district_record=(Rung.L1, "NM"),
    )
    assert computed.result_iso == _WITH_NM
    assert computed.district_state == "NM"


def test_the_templates_own_district_state_wins_over_the_instance_record():
    computed = _computed(
        _template(name="claims-bar", days=70, jurisdiction="US-federal",
                  district_state="NM"),
        code="US-federal", anchor=_DISTRICT_ANCHOR,
        extra_fields={"district_state": Rung.L1},
        district_record=(Rung.L1, "TX"),
    )
    assert computed.district_state == "NM"


def test_a_district_state_field_below_l1_is_not_read_at_all():
    """A pack that files the code at `L3` has said it is not public in this
    forum; a counting rule may not reach past that, and the answer falls
    back to the federal calendar alone rather than to a refusal — nothing is
    missing, the pack simply did not publish one."""
    computed = _computed(
        _template(name="claims-bar", days=70, jurisdiction="US-federal"),
        code="US-federal", anchor=_DISTRICT_ANCHOR,
        extra_fields={"district_state": Rung.L3},
        district_record=(Rung.L3, "NM"),
    )
    assert computed.result_iso == _WITHOUT_NM
    assert computed.district_state is None


def test_a_backward_template_never_reads_a_district_state():
    """9006(a)(6)(C) is "after an event" only — `court_days_before` takes no
    such argument, so the instance's own code is not resolved for it and the
    `Computed` does not claim it was applied."""
    computed = _computed(
        _template(name="objection", days=7, direction="backward",
                  rule="court_days_before", jurisdiction="US-federal"),
        code="US-federal", anchor="2026-11-16",
        extra_fields={"district_state": Rung.L1},
        district_record=(Rung.L1, "NM"),
    )
    assert computed.district_state is None
    assert computed.result_iso == court_days_before("2026-11-16", 7).iso


def test_mail_days_are_added_over_the_districts_calendar_too():
    computed = _computed(
        _template(name="claims-bar", days=70, jurisdiction="US-federal",
                  district_state="NM"),
        code="US-federal", anchor=_DISTRICT_ANCHOR, mail=True,
    )
    expected = add_mail_days(
        court_days(_DISTRICT_ANCHOR, 70, district_state="NM"), district_state="NM")
    assert computed.result_iso == expected.iso == "2026-12-03"


def test_the_district_state_is_part_of_the_preview_token():
    """Two computations that differ only in which calendar was applied must
    not share a token — otherwise an `accept` could file the date the
    operator did not see."""
    with_nm = _computed(
        _template(name="claims-bar", days=70, jurisdiction="US-federal",
                  district_state="NM"),
        code="US-federal", anchor=_DISTRICT_ANCHOR,
    )
    without = _computed(
        _template(name="claims-bar", days=70, jurisdiction="US-federal"),
        code="US-federal", anchor=_DISTRICT_ANCHOR,
    )
    assert with_nm.district_state != without.district_state
    assert with_nm.preview_token != without.preview_token


def test_a_state_jurisdiction_with_a_district_state_refuses_through_the_engine():
    """A pack may leave `jurisdiction` `None` and still name a
    `district_state`; if such a template is computed on a *state* instance
    the engine refuses by name (6(a)(6)(C) is a federal rule) rather than
    quietly dropping the second calendar."""
    with pytest.raises(UnparseableDate) as exc:
        _computed(
            _template(name="claims-bar", days=70, jurisdiction=None,
                      district_state="NM"),
            code="US-NM", anchor=_DISTRICT_ANCHOR,
        )
    assert "US-NM has no district-state rule" in str(exc.value)


@pytest.mark.parametrize("bad", ["nm", "N", "NMX", "New Mexico", 35])
def test_district_state_must_be_a_two_letter_upper_case_code(bad):
    pack = _fake_pack(templates=(_template(district_state=bad),))
    with pytest.raises(rules.InvalidTemplate) as exc:
        rules.validate_templates(pack)
    assert "two-letter upper-case USPS code" in str(exc.value)


@pytest.mark.parametrize("rule,direction", [
    ("court_days_before", "backward"), ("business_days", "forward"),
    ("calendar_days", "forward"),
])
def test_district_state_is_refused_on_every_rule_but_court_days(rule, direction):
    pack = _fake_pack(templates=(_template(
        rule=rule, direction=direction, district_state="NM"),))
    with pytest.raises(rules.InvalidTemplate) as exc:
        rules.validate_templates(pack)
    assert "9006(a)(6)(C)" in str(exc.value)


def test_district_state_is_refused_on_a_state_scoped_template():
    pack = _fake_pack(templates=(_template(jurisdiction="US-NM", district_state="NM"),))
    with pytest.raises(rules.InvalidTemplate) as exc:
        rules.validate_templates(pack)
    assert "federal" in str(exc.value)


def test_district_state_is_the_only_optional_key():
    """The key set stayed closed: one optional key was added, not a door."""
    pack = _fake_pack(templates=(_template(extra_key="x"),))
    with pytest.raises(rules.InvalidTemplate) as exc:
        rules.validate_templates(pack)
    assert "extra_key" in str(exc.value)


def test_a_template_without_the_optional_key_still_builds():
    """`Template.district_state` defaults, so the ten required keys are still
    a complete entry and no pack has to learn a new one."""
    pack = _fake_pack(templates=(_template(),))
    template, = rules.templates_of(_mt(pack))
    assert template.district_state is None


# ── a token proves *which* preview, not merely that one happened ──────────

def test_a_token_minted_for_another_instance_is_refused():
    """The token is a hash of the instance too, so a preview of `or-order`
    cannot be accepted as `primary` — the failure mode a bare "was something
    computed?" check would have let through."""
    pack = _fake_pack(templates=(_template(),))
    mt = _mt(pack)
    with _registered(mt):
        store = Sidecar()
        for inst in ("primary", "or-order"):
            set_jurisdiction(store, mt.name, inst, "US-NM")
            store.put(mt.name, "move_date", inst, Classified(Rung.L1, "2026-01-01"))

        here = rules.compute(store, mt.name, "primary", "notice")
        there = rules.compute(store, mt.name, "or-order", "notice")
        assert here.result_iso == there.result_iso        # same date …
        assert here.preview_token != there.preview_token  # … different preview

        with pytest.raises(rules.StaleToken):
            rules.accept(store, here, token=there.preview_token)
        assert not store.has(mt.name, "deadline", instances.item_id("primary", "notice"))


def test_a_token_minted_for_another_template_is_refused():
    pack = _fake_pack(templates=(
        _template(name="notice"), _template(name="contest", days=21),
    ))
    mt = _mt(pack)
    with _registered(mt):
        store = Sidecar()
        set_jurisdiction(store, mt.name, "primary", "US-NM")
        store.put(mt.name, "move_date", "primary", Classified(Rung.L1, "2026-01-01"))
        notice = rules.compute(store, mt.name, "primary", "notice")
        contest = rules.compute(store, mt.name, "primary", "contest")
        with pytest.raises(rules.StaleToken):
            rules.accept(store, notice, token=contest.preview_token)


def test_mail_changes_the_token_so_a_preview_cannot_be_accepted_as_the_other():
    pack = _fake_pack(
        jurisdiction="US-federal", jurisdictions=("US-federal",),
        templates=(_template(jurisdiction="US-federal"),),
    )
    mt = _mt(pack)
    with _registered(mt):
        store = Sidecar()
        set_jurisdiction(store, mt.name, "primary", "US-federal")
        store.put(mt.name, "move_date", "primary", Classified(Rung.L1, "2026-01-01"))
        plain = rules.compute(store, mt.name, "primary", "notice")
        mailed = rules.compute(store, mt.name, "primary", "notice", mail=True)
        assert plain.result_iso != mailed.result_iso
        assert plain.preview_token != mailed.preview_token
        with pytest.raises(rules.StaleToken):
            rules.accept(store, plain, token=mailed.preview_token)


# ── the real bankruptcy pack, in the District of New Mexico ──────────────────
#
# Every other test in this file builds a fake pack on purpose. This section
# does not: the defect it pins was a real one in `packs/bankruptcy.py` — four
# forward templates counted on the federal calendar alone, with nothing on the
# pack for `_district_state_for` to find — and a fake pack cannot show that a
# real one is now wired up. The fix landed on the bankruptcy branch (an `L1`
# `district_state` field, plus the four notes); this is the half of it that
# needed `rules.py` and could only be written once the two were stacked.

#: The household's own petition date, and the two answers 70 court days from
#: it — the pinned pair this whole section exists for.
_PETITION = "2026-09-18"
_CLAIMS_BAR_FEDERAL_ONLY = "2026-11-27"
_CLAIMS_BAR_WITH_NM = "2026-11-30"


def _bankruptcy_case(*, district_state: str | None, instance: str = "primary"):
    """A `bankruptcy` instance in `US-federal` with a petition on file, and
    the district's state only when asked for. The pack is the registered one
    — no monkeypatching, nothing faked. `instance` is a parameter because a
    test that wants both answers needs two instances: re-opening one is I-9's
    first-write refusal, not a fixture detail."""
    store = Sidecar()
    set_jurisdiction(store, "bankruptcy", instance, "US-federal")
    store.put("bankruptcy", "petition_date", instance,
              Classified(Rung.L1, _PETITION))
    if district_state is not None:
        store.put("bankruptcy", "district_state", instance,
                  Classified(Rung.L1, district_state))
    return store


def test_2026_11_27_is_open_federally_and_closed_in_new_mexico():
    """The fact the rest of this section rests on, checked rather than
    asserted in prose: New Mexico keeps Presidents' Day on the Friday after
    Thanksgiving, so its district courts are closed on a day the federal
    calendar has open. If `holidays` ever changed that, everything below
    would still pass while meaning nothing — so it is pinned first."""
    import datetime as dt

    import holidays

    day = dt.date(2026, 11, 27)
    assert day.weekday() == 4                                   # a Friday
    assert day in holidays.US(subdiv="NM", years=[2026])
    assert day not in holidays.US(years=[2026])


def test_the_bankruptcy_pack_declares_the_district_state_compute_looks_for():
    """`_district_state_for`'s second source, from the pack's side: the field
    has to be named exactly this and classified exactly `L1`, or `compute`
    silently falls back to the federal calendar."""
    from homestead_law.packs import bankruptcy

    assert bankruptcy.FIELDS["district_state"] is Rung.L1


def test_a_new_mexico_chapter_13_claims_bar_counts_the_states_holidays():
    """The worked case, end to end through the real pack: a 2026-09-18
    petition, `claims-bar` (FRBP 3002(c), 70 days forward, court days), in a
    case whose instance carries `district_state = NM`. 2026-11-27 is the
    federal answer and a New Mexico court closure, so the deadline rolls to
    the next day that is neither — Monday 2026-11-30."""
    store = _bankruptcy_case(district_state="NM")

    computed = rules.compute(store, "bankruptcy", "primary", "claims-bar")

    assert computed.result_iso == _CLAIMS_BAR_WITH_NM
    assert computed.district_state == "NM"
    assert computed.result_iso == court_days(
        _PETITION, 70, jurisdiction="US-federal", district_state="NM").iso


def test_without_the_district_state_the_same_case_names_the_federal_date():
    """The other half of the pair, and the reason the field had to exist: the
    same pack, the same template, the same petition — a different date. The
    `Computed` says which calendar it used rather than leaving the operator to
    assume the district's closures were counted."""
    store = _bankruptcy_case(district_state=None)

    computed = rules.compute(store, "bankruptcy", "primary", "claims-bar")

    assert computed.result_iso == _CLAIMS_BAR_FEDERAL_ONLY
    assert computed.district_state is None
    assert computed.result_iso == court_days(
        _PETITION, 70, jurisdiction="US-federal").iso
    assert computed.result_iso != _CLAIMS_BAR_WITH_NM


def test_the_two_previews_are_not_interchangeable():
    """A date that depends on the district's calendar makes the calendar part
    of the answer, so it is part of the token — an operator cannot accept the
    federal-only preview against the one they were shown, or the reverse."""
    store = _bankruptcy_case(district_state="NM", instance="nm")
    _bankruptcy_case(district_state=None, instance="federal")

    with_nm = rules.compute(store, "bankruptcy", "nm", "claims-bar")
    without = rules.compute(store, "bankruptcy", "federal", "claims-bar")

    assert with_nm.result_iso != without.result_iso
    assert with_nm.preview_token != without.preview_token


def test_the_calendar_days_template_is_unmoved_by_the_district_state():
    """`first-plan-payment` counts calendar days, which read no calendar at
    all — so the field that moves `claims-bar` by three days moves this by
    none. Asserted, because the pack's `note` claims it."""
    store = _bankruptcy_case(district_state="NM", instance="nm")
    _bankruptcy_case(district_state=None, instance="federal")

    with_nm = rules.compute(store, "bankruptcy", "nm", "first-plan-payment")
    without = rules.compute(store, "bankruptcy", "federal", "first-plan-payment")

    assert with_nm.result_iso == without.result_iso == "2026-10-18"


def test_the_cli_says_which_calendar_the_real_pack_counted_on(capsys):
    """The notice an operator actually reads, on the real templates: the
    district's state when there was one, and "district holidays not applied"
    when there was not."""
    from homestead_law.cli import run_cli

    assert run_cli([
        "matter", "open", "bankruptcy", "--id", "primary",
        "--jurisdiction", "US-federal",
    ]) == 0
    assert run_cli(["put", "bankruptcy", "petition_date", _PETITION]) == 0
    capsys.readouterr()

    assert run_cli(
        ["deadline", "compute", "bankruptcy", "claims-bar", "--id", "primary"]) == 0
    out = capsys.readouterr().out
    assert _CLAIMS_BAR_FEDERAL_ONLY in out
    assert "district holidays not applied" in out

    assert run_cli(["put", "bankruptcy", "district_state", "NM"]) == 0
    capsys.readouterr()

    assert run_cli(
        ["deadline", "compute", "bankruptcy", "claims-bar", "--id", "primary"]) == 0
    out = capsys.readouterr().out
    assert _CLAIMS_BAR_WITH_NM in out
    assert "district holidays: NM" in out
    assert "district holidays not applied" not in out
