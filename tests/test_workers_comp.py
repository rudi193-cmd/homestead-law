"""`homestead_law.packs.workers_comp` — an active New Mexico WCA claim (wave 3,
decision 7). Same shape as `tests/test_packs.py` (the custody pack's own
suite): schema contract, the ladder, the derived-form rule — plus this pack's
own additions: the `ime` repeatable field, the `L4` length cap
(`validate_value`, not yet wired into any door), and `TEMPLATES`, the data the
parallel `L3-deadline-templates` bite reads.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from homestead.keep.rungs import Classified, Disposition, Rung, Surface, serve
from homestead_law import instances
from homestead_law.packs import workers_comp
from homestead_law.registry import all_matters, matter
from homestead_law.store import Sidecar

MATTER = workers_comp.MATTER  # "workers_comp"


# ── the pack classifies at import, and registers ─────────────────────────────

def test_the_pack_classifies_at_import():
    assert isinstance(workers_comp.FIELDS, dict)
    assert workers_comp.FIELDS
    assert all(isinstance(r, Rung) for r in workers_comp.FIELDS.values())
    assert set(workers_comp.FIELDS) == set(workers_comp.SCHEMA)


def test_the_pack_is_registered():
    assert MATTER in all_matters()
    entry = matter(MATTER)
    assert entry.pack is workers_comp
    assert entry.fields is workers_comp.FIELDS
    assert entry.jurisdiction == "US-NM"
    assert entry.jurisdictions == ("US-NM",)


def test_jurisdictions_is_a_single_nm_member():
    """Decision: the claim stays an NM claim after the move — treatment moves,
    the forum does not (unlike custody's US-NM -> US-OR)."""
    assert workers_comp.JURISDICTIONS == ("US-NM",)
    assert workers_comp.JURISDICTION == "US-NM"
    assert workers_comp.JURISDICTION in workers_comp.JURISDICTIONS


# ── the ladder, field by field (item 1's list) ────────────────────────────────

EXPECTED = {
    "jurisdiction": Rung.L1,
    "hcp_change_notice_date": Rung.L1,
    "hcp_selection_date": Rung.L1,
    "wca_case_number": Rung.L3,
    "claim_number": Rung.L3,
    "employer": Rung.L3,
    "insurer": Rung.L3,
    "adjuster": Rung.L3,
    "notice_of_accident_date": Rung.L3,
    "hcp_change_objection_deadline": Rung.L3,
    "mediation_date": Rung.L3,
    "hearing_date": Rung.L3,
    "complaint_date": Rung.L3,
    "date_of_injury": Rung.L4,
    "body_part": Rung.L4,
    "diagnosis": Rung.L4,
    "impairment_rating": Rung.L4,
    "mmi_date": Rung.L4,
    "treating_physician": Rung.L4,
    "ime": Rung.L4,
    "aww": Rung.L4,
    "benefit_rate": Rung.L4,
    "tt_benefit_start": Rung.L4,
    "oos_provider_affidavit_date": Rung.L4,
    "notes": Rung.L4,
    "ssn": Rung.L5,
}


def test_the_pack_spans_the_ladder_with_the_declared_rungs():
    assert workers_comp.FIELDS == EXPECTED


@pytest.mark.parametrize("field,rung", sorted(EXPECTED.items()))
def test_schema_contract_per_field(field, rung):
    """Every field: matter, jurisdiction, why recorded — step 5 of the
    classification procedure, the same contract custody's pack holds."""
    spec = workers_comp.SCHEMA[field]
    assert spec["rung"] is rung
    assert spec.get("matter") == MATTER
    assert spec.get("jurisdiction") == "US-NM"
    assert spec.get("why"), f"{field} declares a rung with no recorded reason"


def test_the_dangerous_rungs_are_where_they_must_be():
    assert workers_comp.FIELDS["ssn"] is Rung.L5, "an SSN is L5 — L5 has no override"
    assert workers_comp.FIELDS["date_of_injury"] is Rung.L4
    assert workers_comp.FIELDS["diagnosis"] is Rung.L4


def test_deleting_a_fields_rung_fails_the_build_naming_it():
    import copy

    from homestead.keep.rungs import classify_schema

    for victim in workers_comp.SCHEMA:
        wounded = copy.deepcopy(workers_comp.SCHEMA)
        del wounded[victim]["rung"]
        with pytest.raises(Exception) as caught:
            classify_schema(wounded)
        assert victim in str(caught.value)


# ── REPEATABLE (decision 2) ───────────────────────────────────────────────────

def test_repeatable_is_exactly_ime():
    assert workers_comp.REPEATABLE == frozenset({"ime"})
    assert matter(MATTER).repeatable == frozenset({"ime"})
    assert matter(MATTER).repeatable is workers_comp.REPEATABLE


def test_an_ime_sub_record_reads_back_derived_on_s1_list(tmp_path, monkeypatch):
    """`put workers_comp ime "<value>" --id primary --sub 2026-10` — the
    generic `put`/`show` doors already carry a plain L4 value through
    `--id`/`--sub` with no pack-specific writer (the module docstring's own
    note). Exercised here directly against the store, the way
    `tests/test_jurisdiction.py` and `tests/test_queue.py` exercise a write
    without going through the Nestor-gated CLI."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    item_id = instances.item_id("primary", "2026-10")
    assert item_id == "primary.2026-10"

    rung = workers_comp.FIELDS["ime"]
    derived = workers_comp.SCHEMA["ime"]["derived"]
    store.put(
        MATTER, "ime", item_id,
        Classified(rung, "2026-10-05 -- Dr. R. Chen -- no permanent restrictions", derived),
    )

    served = serve(store.get(MATTER, "ime", item_id), Surface.S1_LIST)
    assert served.disposition is Disposition.DERIVE
    assert served.value == derived
    assert "Chen" not in served.value  # the examiner never leaks onto S1_LIST


# ── derived forms: no digit, and date_of_injury carries no year at all ───────

def test_every_l3_l4_field_declares_a_non_empty_derived_form():
    checked = 0
    for field, rung in workers_comp.FIELDS.items():
        if rung in (Rung.L3, Rung.L4):
            sentence = workers_comp.SCHEMA[field].get("derived")
            assert isinstance(sentence, str) and sentence.strip(), field
            checked += 1
    l3 = sum(1 for r in EXPECTED.values() if r is Rung.L3)
    l4 = sum(1 for r in EXPECTED.values() if r is Rung.L4)
    assert checked == l3 + l4


def test_no_derived_form_carries_a_digit():
    for field in workers_comp.SCHEMA:
        sentence = workers_comp.SCHEMA[field].get("derived")
        if sentence is None:
            continue
        assert not any(ch.isdigit() for ch in sentence), f"{field}: {sentence!r}"


_MONTHS = (
    "january", "february", "march", "april", "may", "june", "july",
    "august", "september", "october", "november", "december",
)


def test_date_of_injurys_derived_form_carries_no_year_and_no_month_name():
    sentence = workers_comp.SCHEMA["date_of_injury"]["derived"]
    assert not any(ch.isdigit() for ch in sentence)
    lowered = sentence.lower()
    assert not any(month in lowered for month in _MONTHS)
    assert sentence == "A date of injury is on file"


# ── validate_value — the L4 length cap (item 2) ───────────────────────────────

def test_validate_value_accepts_200_chars_on_an_l4_field():
    workers_comp.validate_value("diagnosis", "x" * workers_comp.MAX_L4_CHARS)


def test_validate_value_refuses_201_chars_naming_the_field_never_echoing():
    marker = "UNIQUE-CLINICAL-NARRATIVE-MARKER"
    value = marker + ("x" * (workers_comp.MAX_L4_CHARS + 1 - len(marker)))
    assert len(value) == workers_comp.MAX_L4_CHARS + 1

    with pytest.raises(workers_comp.MedicalNarrativeTooLong) as exc:
        workers_comp.validate_value("diagnosis", value)

    message = str(exc.value)
    assert "diagnosis" in message
    assert "homestead-health" in message
    assert marker not in message  # I-15: never echo the value
    assert exc.value.field == "diagnosis"


def test_validate_value_ignores_non_l4_and_unknown_fields_regardless_of_length():
    long_value = "x" * 5000
    for field in ("wca_case_number", "jurisdiction", "ssn", "not_a_real_field"):
        workers_comp.validate_value(field, long_value)  # L3, L1, L5, unknown


def test_validate_value_refuses_every_l4_field_over_the_cap():
    for field, rung in workers_comp.FIELDS.items():
        if rung is not Rung.L4:
            continue
        with pytest.raises(workers_comp.MedicalNarrativeTooLong):
            workers_comp.validate_value(field, "x" * (workers_comp.MAX_L4_CHARS + 1))


def test_validate_value_is_not_yet_wired_into_either_door():
    """Documents the gap rather than papering over it (item 2). `L4-surfaces`
    (wave 4, depends on every L3-* pack) is the bite named to call
    `validate_value` from `cli.py`'s `_cmd_put` and `server.py`'s
    `/api/store`. This test fails, by design, the day that wiring lands —
    which is the signal to delete it, not to patch around it."""
    from homestead_law import cli, server

    cli_source = Path(cli.__file__).read_text("utf-8")
    server_source = Path(server.__file__).read_text("utf-8")
    assert "validate_value" not in cli_source
    assert "validate_value" not in server_source


# ── ssn never crosses S1_LIST or S2 ──────────────────────────────────────────

def test_ssn_never_crosses_s1_list_or_s2():
    record = Classified(Rung.L5, "123-45-6789")
    for surface in (Surface.S1_LIST, Surface.S2_PROMPT):
        served = serve(record, surface)
        assert served.disposition is Disposition.DENY
        assert served.value is None


# ── TEMPLATES (item 3) — data only ────────────────────────────────────────────

def test_templates_does_not_import_rules():
    """TEMPLATES is data the parallel `L3-deadline-templates` bite reads; this
    pack must not import that sibling's module (the two run side by side).
    An AST scan, not a text search, because the module's own docstring names
    `homestead_law.rules` in prose to explain exactly this."""
    import ast

    source = Path(workers_comp.__file__).read_text("utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("homestead_law.rules"), node.module
            assert node.module != "homestead_law.rules"
        elif isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("homestead_law.rules"), alias.name


def test_templates_is_a_tuple_of_two_uncertain_entries():
    assert isinstance(workers_comp.TEMPLATES, tuple)
    names = {t["name"] for t in workers_comp.TEMPLATES}
    assert names == {"hcp_selection", "hcp_change_objection"}
    for entry in workers_comp.TEMPLATES:
        assert entry["status"] == "UNCERTAIN"


def test_notice_of_accident_is_not_a_template():
    """The 15-day rule (§ 52-1-29) anchors on date_of_injury, which is L4 —
    entered, not computed (the module docstring's own section)."""
    names = {t["name"] for t in workers_comp.TEMPLATES}
    assert "notice_of_accident" not in names


def test_hcp_selection_template_shape():
    tpl = next(t for t in workers_comp.TEMPLATES if t["name"] == "hcp_selection")
    assert tpl["anchor"] == "hcp_selection_date"
    assert workers_comp.FIELDS[tpl["anchor"]] is Rung.L1
    assert tpl["days"] == 60
    assert tpl["direction"] == "forward"
    assert tpl["rule"] == "calendar_days"
    assert tpl["mail"] is False
    assert tpl["jurisdiction"] == "US-NM"
    assert "52-1-49" in tpl["source"]


def test_hcp_change_objection_template_shape():
    tpl = next(t for t in workers_comp.TEMPLATES if t["name"] == "hcp_change_objection")
    assert tpl["anchor"] == "hcp_change_notice_date"
    assert workers_comp.FIELDS[tpl["anchor"]] is Rung.L1
    assert tpl["days"] == 3


def test_every_template_anchor_is_a_real_l1_field():
    for tpl in workers_comp.TEMPLATES:
        assert tpl["anchor"] in workers_comp.FIELDS
        assert workers_comp.FIELDS[tpl["anchor"]] is Rung.L1


def test_the_real_templates_pass_their_own_shape_check():
    """Positive side — already run once at import; re-run explicitly so the
    suite keeps exercising it (registry.py's own `_validate` pattern)."""
    workers_comp._validate_templates(
        workers_comp.TEMPLATES, workers_comp.SCHEMA, workers_comp.FIELDS,
        workers_comp.JURISDICTIONS,
    )


# ── the shape check fires on planted violations ───────────────────────────────

def _good_template() -> dict:
    return dict(workers_comp.TEMPLATES[0])


def _check(templates):
    workers_comp._validate_templates(
        tuple(templates), workers_comp.SCHEMA, workers_comp.FIELDS,
        workers_comp.JURISDICTIONS,
    )


@pytest.mark.parametrize(
    "key,bad_value,needle",
    [
        ("extra_field", "surprise", "extra_field"),   # unexpected key (+ missing below)
        ("anchor", "not_a_real_field", "not_a_real_field"),
        ("direction", "sideways", None),
        ("rule", "moon_days", None),
        ("status", "PROBABLY", None),
        ("jurisdiction", "US-OR", None),
        ("mail", "no", None),
        ("days", 0, None),
        ("days", -3, None),
        ("days", "60", None),
        ("days", True, None),
        ("source", "   ", None),
        ("note", "   ", None),
        ("name", "   ", None),
    ],
)
def test_shape_check_fires_on_each_kind_of_planted_violation(key, bad_value, needle):
    bad = _good_template()
    bad[key] = bad_value
    with pytest.raises(workers_comp.TemplateShapeError) as exc:
        _check([bad])
    if needle:
        assert needle in str(exc.value)


def test_shape_check_fires_on_a_missing_key():
    bad = _good_template()
    del bad["source"]
    with pytest.raises(workers_comp.TemplateShapeError) as exc:
        _check([bad])
    assert "source" in str(exc.value)


def test_shape_check_fires_on_an_anchor_above_l1():
    """The audit's own attack, planted: an L4 field used as an anchor. Anchors
    must be L1 (item 3's shape rule) — a computed template cannot read an
    anchor a surface might withhold."""
    bad = _good_template()
    bad["anchor"] = "date_of_injury"  # L4
    with pytest.raises(workers_comp.TemplateShapeError) as exc:
        _check([bad])
    assert "date_of_injury" in str(exc.value)
    assert "L1" in str(exc.value)


def test_shape_check_accepts_a_none_jurisdiction():
    good = _good_template()
    good["jurisdiction"] = None
    _check([good])


def test_shape_check_fires_on_a_non_dict_entry():
    with pytest.raises(workers_comp.TemplateShapeError):
        _check(["not-a-dict"])


# ── I-23: the registry scan stays green with this pack on disk ──────────────

def test_registering_this_pack_did_not_break_the_i23_scan():
    from homestead_law import registry as registry_mod

    assert set(all_matters()) == set(registry_mod.REGISTRY) == set(registry_mod._discover_packs())
    registry_mod._validate(registry_mod.REGISTRY, registry_mod._discover_packs())
