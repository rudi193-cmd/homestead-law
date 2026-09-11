"""`homestead_law.instances` — matter instances, no engine change (decision 2).

`item_id`/`split_item_id` are the whole convention: an id shape closed enough
that the two are always inverses of each other, laid over the store's existing
`(matter, item_type, item_id)` key. `instances_of`/`records_of` are the two
things anything above the store needs to ask of it: which instances exist, and
what one of them holds.
"""
from __future__ import annotations

import pytest

from homestead.keep.rungs import Classified, Rung
from homestead_law import instances
from homestead_law.store import Sidecar


# ── item_id / split_item_id — id shape and round-trip ────────────────────────

@pytest.mark.parametrize("value", [
    "primary", "a", "nm-order", "z" * 40, "a-b-c-9", "0", "9z",
])
def test_a_well_shaped_id_is_accepted_as_instance_and_as_sub(value):
    assert instances.item_id(value) == value
    assert instances.item_id("primary", value) == f"primary.{value}"


@pytest.mark.parametrize("value", [
    "",              # empty
    "Primary",       # uppercase
    "primary_1",     # underscore
    "-primary",      # leading hyphen
    "a.b",           # a dot — the one character the shape must exclude
    "a/b",           # separator
    "a b",           # space
    "z" * 41,        # over the length cap
    "opposing_party",  # a real field name — not itself a valid id (underscore)
])
def test_a_malformed_id_is_refused_by_name_never_echoing_the_value(value):
    with pytest.raises(instances.InvalidId) as exc:
        instances.item_id(value)
    # names the component, states the shape — never repeats what was typed
    # (I-15): a refusal that echoed the value would be a second, unscored
    # surface for exactly the string this module is being careful about.
    assert "instance" in str(exc.value)
    assert value not in str(exc.value) or value == ""  # "" trivially "in" any string

    with pytest.raises(instances.InvalidId) as exc:
        instances.item_id("primary", value)
    assert "sub" in str(exc.value)
    assert value not in str(exc.value) or value == ""


def test_item_id_with_no_sub_is_the_bare_instance():
    assert instances.item_id("primary", None) == "primary"
    assert instances.item_id("primary") == "primary"


def test_item_id_and_split_item_id_are_inverses():
    for instance, sub in [("primary", None), ("primary", "hearing"), ("nm-order", "1")]:
        built = instances.item_id(instance, sub)
        assert instances.split_item_id(built) == (instance, sub)


def test_split_item_id_reads_a_pre_instances_bare_id_as_its_own_instance():
    """A deadline stored before this bite (a freeform label, no dot) is not a
    crash or a guess when split — it reads as instance=<that label>, sub=None,
    the honest answer for a string with no dot in it."""
    assert instances.split_item_id("hearing") == ("hearing", None)


def test_split_item_id_splits_on_the_first_dot_only():
    """A sub itself may never contain a dot (`ID_PATTERN` excludes it), but
    `split_item_id` is handed whatever the store actually holds, and must not
    misparse a legacy id that happens to contain more than one dot-like
    artifact if one ever existed."""
    assert instances.split_item_id("primary.hearing.extra") == ("primary", "hearing.extra")


# ── instances_of / records_of ─────────────────────────────────────────────────

def test_instances_of_an_empty_matter_is_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    assert instances.instances_of(store, "custody") == ()


def test_instances_of_scans_every_item_type_under_the_matter(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    store.put("custody", "courthouse", "primary", Classified(Rung.L1, "Dept 4"))
    store.put("custody", "deadline", "secondary.hearing", Classified(Rung.L1, "2026-09-15"))

    assert instances.instances_of(store, "custody") == ("primary", "secondary")


def test_instances_of_ignores_other_matters(tmp_path, monkeypatch):
    """A second, unrelated matter's records must not leak into this matter's
    instance list — the scan is `store.records(matter)`, already filtered to
    one matter by the store's own key."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    store.put("custody", "courthouse", "primary", Classified(Rung.L1, "Dept 4"))
    store.put("_fake_second", "case_number", "primary", Classified(Rung.L1, "BK-1"))

    assert instances.instances_of(store, "custody") == ("primary",)
    assert instances.instances_of(store, "_fake_second") == ("primary",)


def test_instances_of_the_demo_matter_does_not_see_a_second_matter(tmp_path, monkeypatch):
    """Same guarantee from the other matter's point of view — registry-
    relative, using whatever `all_matters()` actually names rather than a
    literal, so this holds after a real second pack lands too."""
    from homestead_law.registry import all_matters

    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    demo_matter = all_matters()[0]
    store.put(demo_matter, "courthouse", "primary", Classified(Rung.L1, "Dept 4"))
    assert instances.instances_of(store, demo_matter) == ("primary",)


def test_records_of_filters_to_one_instance(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    store.put("custody", "courthouse", "primary", Classified(Rung.L1, "Dept 4"))
    store.put(
        "custody", "deadline", "secondary.hearing", Classified(Rung.L1, "2026-09-15")
    )

    primary = instances.records_of(store, "custody", "primary")
    assert [ref for ref, _ in primary] == [("custody", "courthouse", "primary")]

    secondary = instances.records_of(store, "custody", "secondary")
    assert [ref for ref, _ in secondary] == [
        ("custody", "deadline", "secondary.hearing")
    ]


def test_records_of_an_instance_with_nothing_on_file_is_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    assert instances.records_of(store, "custody", "primary") == []


def test_records_of_refuses_a_malformed_instance(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    with pytest.raises(instances.InvalidId):
        instances.records_of(store, "custody", "Not Valid")


# ── a stored id this convention cannot read ──────────────────────────────────

@pytest.mark.parametrize("stored", ["Upper", "has_underscore", "it's-due", "a.B"])
def test_instances_of_refuses_a_stored_id_that_does_not_name_an_instance(
    stored, tmp_path, monkeypatch
):
    """The audit's third attack. `homestead.keep.store.key()` is far wider than
    `ID_PATTERN` — every id here is one the engine will hold — so the key scan
    meets ids it cannot split. Neither silent answer is honest: *listing* it
    invents an instance no door can address (`item_id` refuses it, so
    `--id <that>`, `matter open` and `jurisdiction_of` all refuse the very id
    the list just offered — which is how `show <matter>` and `/api/instances`
    turned into an uncaught `InvalidId`), and *skipping* it hides a record from
    the list whose whole job is to say what is on file. I-11: refuse by name.

    The name is the matter and the item types involved — never the id."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    store.put("custody", "courthouse", "primary", Classified(Rung.L1, "Dept 4"))
    store.put("custody", "deadline", stored, Classified(Rung.L1, "2099-10-01"))

    with pytest.raises(instances.UnreadableStoredId) as exc:
        instances.instances_of(store, "custody")
    message = str(exc.value)
    assert "custody" in message and "deadline" in message   # references
    assert stored not in message                            # never the id itself
    assert exc.value.item_types == ("deadline",)


def test_instances_of_is_clean_when_every_stored_id_is_instance_shaped(
    tmp_path, monkeypatch
):
    """The positive side of the same scan, with a sub and a second instance —
    the shape the whole convention promises."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    store.put("custody", "courthouse", "primary", Classified(Rung.L1, "Dept 4"))
    store.put("custody", "deadline", "primary.child-1", Classified(Rung.L1, "2099-10-01"))
    store.put("custody", "courthouse", "oregon-2027", Classified(Rung.L1, "Dept 9"))

    assert instances.instances_of(store, "custody") == ("oregon-2027", "primary")
