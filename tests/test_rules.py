"""`homestead_law.rules` — deadline templates (decision 4, L3-deadline-templates).

Two halves, tested separately. `validate_templates` (and its registry hook,
`registry._validate`'s one addition for this bite) is a build-time guard: every
plant below constructs a fake pack with exactly one contract violation and
shows the guard names it. `compute`/`accept` are the runtime half: `compute`
never stores (every test that calls it and then inspects the store finds
nothing new there unless `accept` was also called), and `accept` writes only
once a token proves what was shown.

No sibling pack (custody, bankruptcy, workers' comp) is read here — those land
in parallel bites and `custody.py` on this branch has no `TEMPLATES` yet. Every
test below builds its own fake pack, the same way `tests/test_registry.py`
does for its own guard-fire tests.
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
        "confirm against the court's notice"
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
