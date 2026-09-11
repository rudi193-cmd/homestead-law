"""`homestead_law.jurisdiction` — per-matter-instance jurisdiction (decision 1).

No date arithmetic lives here and none is imported; the whole contract is:
accept a code only from the matter's own `JURISDICTIONS`, and hand one back
only through the gate, refusing (provisional I-42) whenever nothing was
actually rendered — whether because nothing was ever stored, or because what
was stored does not read back as itself.
"""
from __future__ import annotations

import pytest

from homestead.keep.rungs import Classified, Rung
from homestead_law import instances
from homestead_law.jurisdiction import (
    JurisdictionAbsent,
    UnsupportedJurisdiction,
    jurisdiction_of,
    set_jurisdiction,
)
from homestead_law.store import RecordExists, Sidecar


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    yield


# ── set_jurisdiction ──────────────────────────────────────────────────────────

def test_set_jurisdiction_stores_at_l1_under_the_instance():
    store = Sidecar()
    set_jurisdiction(store, "custody", "primary", "US-NM")

    assert store.has("custody", "jurisdiction", "primary")
    record = store.get("custody", "jurisdiction", "primary")
    assert record.rung is Rung.L1
    assert record.payload == "US-NM"


def test_set_jurisdiction_refuses_a_code_outside_the_pack_and_stores_nothing():
    store = Sidecar()
    with pytest.raises(UnsupportedJurisdiction) as exc:
        set_jurisdiction(store, "custody", "primary", "US-CA")

    assert "US-CA" in str(exc.value)          # the pack's own JURISDICTIONS
    assert "US-NM" in str(exc.value) or "US-OR" in str(exc.value)
    assert not store.has("custody", "jurisdiction", "primary")


def test_set_jurisdiction_refuses_a_malformed_instance_id_by_name():
    store = Sidecar()
    with pytest.raises(instances.InvalidId) as exc:
        set_jurisdiction(store, "custody", "Not Valid", "US-NM")
    assert "instance" in str(exc.value)
    assert "Not Valid" not in str(exc.value)   # a value, never echoed (I-15)
    assert not store.has("custody", "jurisdiction", "Not Valid")


def test_set_jurisdiction_refuses_an_unknown_matter():
    store = Sidecar()
    with pytest.raises(KeyError):
        set_jurisdiction(store, "not_a_matter", "primary", "US-NM")


def test_opening_the_same_instance_twice_refuses_without_replace():
    store = Sidecar()
    set_jurisdiction(store, "custody", "primary", "US-NM")

    with pytest.raises(RecordExists):
        set_jurisdiction(store, "custody", "primary", "US-OR")

    # unchanged — the refused write did not clobber the first
    assert jurisdiction_of(store, "custody", "primary") == "US-NM"


def test_replace_true_changes_an_already_open_instance():
    store = Sidecar()
    set_jurisdiction(store, "custody", "primary", "US-NM")
    replaced = set_jurisdiction(store, "custody", "primary", "US-OR", replace=True)

    assert replaced is not None
    assert jurisdiction_of(store, "custody", "primary") == "US-OR"


# ── jurisdiction_of — the gate, and provisional I-42 ─────────────────────────

def test_jurisdiction_of_reads_back_what_was_set():
    store = Sidecar()
    set_jurisdiction(store, "custody", "primary", "US-OR")
    assert jurisdiction_of(store, "custody", "primary") == "US-OR"


def test_jurisdiction_absent_refuses_naming_matter_and_instance_and_the_fix():
    store = Sidecar()
    with pytest.raises(JurisdictionAbsent) as exc:
        jurisdiction_of(store, "custody", "primary")

    message = str(exc.value)
    assert "custody" in message and "primary" in message
    assert "matter open" in message and "--jurisdiction" in message
    assert exc.value.matter == "custody" and exc.value.instance == "primary"


def test_a_hand_planted_l5_jurisdiction_record_reads_as_absent():
    """The audit's own attack: a jurisdiction written directly to the store at
    L5 — bypassing `set_jurisdiction` entirely — must not be readable through
    `jurisdiction_of`. The gate drops an L5 on `S1_LIST` (`Disposition.DENY`),
    so this reaches exactly the same refusal as no record at all — from an
    arithmetic caller's point of view, that is what it is."""
    store = Sidecar()
    store.put(
        "custody", "jurisdiction", "primary",
        Classified(Rung.L5, "US-NM"),
        overwrite=True,
    )
    assert store.has("custody", "jurisdiction", "primary")   # the record IS there

    with pytest.raises(JurisdictionAbsent):
        jurisdiction_of(store, "custody", "primary")


def test_a_hand_planted_record_at_a_derive_only_rung_also_reads_as_absent():
    """Anything short of RENDER is absent to this function — a jurisdiction
    hand-planted at L4 derives an unrelated sentence on S1_LIST, which is not
    a jurisdiction code, so it must refuse rather than hand back the derived
    text as if it were one."""
    store = Sidecar()
    store.put(
        "custody", "jurisdiction", "primary",
        Classified(Rung.L4, "US-NM", derived="A jurisdiction is on file"),
        overwrite=True,
    )
    with pytest.raises(JurisdictionAbsent):
        jurisdiction_of(store, "custody", "primary")


def test_jurisdiction_of_refuses_a_malformed_instance_id_by_name():
    store = Sidecar()
    with pytest.raises(instances.InvalidId) as exc:
        jurisdiction_of(store, "custody", "Not Valid")
    assert "instance" in str(exc.value)
    assert "Not Valid" not in str(exc.value)


def test_two_instances_carry_independent_jurisdictions():
    """The whole point of decision 1: one matter, two orders, two forums."""
    store = Sidecar()
    set_jurisdiction(store, "custody", "nm-order", "US-NM")
    set_jurisdiction(store, "custody", "or-order", "US-OR")

    assert jurisdiction_of(store, "custody", "nm-order") == "US-NM"
    assert jurisdiction_of(store, "custody", "or-order") == "US-OR"


# The chokepoint for this module is not re-implemented here: `jurisdiction.py`
# calls `serve()`, so `tests/test_chokepoint.py` now counts it a surface and
# holds it to both the `.payload` ban and the wider reflection ban — see
# `test_the_surface_set_is_derived_from_the_gate_not_a_list_of_directories`.
# A second, weaker copy of that scan here was the drift this repo keeps
# catching, one file over.


def test_a_rendered_code_outside_the_packs_tuple_refuses_on_read_too(monkeypatch):
    """The audit's plant, and the one the rung gate cannot catch. `L1` is the
    rung `set_jurisdiction` itself writes at, so a hand-planted `US-CA` renders
    perfectly on `S1_LIST` — `Disposition.RENDER`, a real string, nothing for
    the gate to object to. Only the pack's own `JURISDICTIONS` says it is not a
    forum this matter has; checking it on write alone leaves the read path
    handing arithmetic a jurisdiction no counting rule in this matter supports.

    Same shape as a pack whose tuple *shrank* after an instance was opened: the
    record was legal when written and is not now."""
    from homestead_law.registry import matter as matter_of

    store = Sidecar()
    outside = "US-CA"
    assert outside not in matter_of("custody").jurisdictions
    store.put(
        "custody", "jurisdiction", "primary",
        Classified(Rung.L1, outside), overwrite=True,
    )

    with pytest.raises(JurisdictionAbsent) as exc:
        jurisdiction_of(store, "custody", "primary")
    message = str(exc.value)
    assert "custody" in message and "primary" in message
    assert "US-NM" in message                      # the pack's own published set
    assert outside not in message                  # a record value, never echoed


def test_arbitrary_rendered_text_is_not_a_jurisdiction(monkeypatch):
    """The same hole with no pretence of being a code: whatever is on disk at
    L1 renders, so without the read-side check `jurisdiction_of` is just
    `store.get` with extra steps."""
    store = Sidecar()
    store.put(
        "custody", "jurisdiction", "primary",
        Classified(Rung.L1, "<script>alert(1)</script>"), overwrite=True,
    )
    with pytest.raises(JurisdictionAbsent) as exc:
        jurisdiction_of(store, "custody", "primary")
    assert "script" not in str(exc.value)


def test_jurisdiction_of_refuses_an_unregistered_matter():
    """`set_jurisdiction` refuses one (`registry.matter`'s own `KeyError`); the
    read path did not even ask, so an unregistered matter read back as a plain
    absence instead of the enumeration error I-23 wants."""
    store = Sidecar()
    with pytest.raises(KeyError):
        jurisdiction_of(store, "not_a_matter", "primary")


def test_replace_rewrites_only_the_jurisdiction_record(tmp_path, monkeypatch):
    """`matter open --replace` is consent to change *this instance's forum*, not
    to reset the instance. Every other record filed under the same instance id
    — a different item type, same third key component — is untouched."""
    from homestead_law import instances as instances_mod

    store = Sidecar()
    set_jurisdiction(store, "custody", "nm-order", "US-NM")
    store.put("custody", "courthouse", "nm-order", Classified(Rung.L1, "Dept 4"))
    store.put(
        "custody", "deadline", "nm-order.hearing", Classified(Rung.L1, "2099-10-01")
    )

    set_jurisdiction(store, "custody", "nm-order", "US-OR", replace=True)

    assert jurisdiction_of(store, "custody", "nm-order") == "US-OR"
    kept = {ref[1] for ref, _ in instances_mod.records_of(store, "custody", "nm-order")}
    assert kept == {"jurisdiction", "courthouse", "deadline"}
    assert store.get("custody", "courthouse", "nm-order").payload == "Dept 4"
