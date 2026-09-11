"""I-23 — the registry is the only enumeration.

Promoted out of `test_invariants_pending.py` when `homestead.keep.registry`
landed, which is what `test_pending_liveness` is for: the moment the module
existed the pending file failed by name, and would not go green again until the
Phase 3 test was promoted out, unmarked. This is the fourth occasion of that
same promotion — dates, surfaces, record, now the registry — and it went
through the same door: the `"homestead.keep.registry"` key comes out of
`UNBUILT`, and the pending `test_i23…` moves here with its body and docstring
kept.

BUG-6 is the failure this whole file exists against. The predecessor advertised
three matter types and enumerated them by hand in three places — navigation, the
urgent queue, the briefing. The lists drifted, workers' comp fell out of the
queue's copy, and a deadline in a workers'-comp matter could not become urgent
because the loop that raised urgency never iterated that type. Every test that
asked "are all matters handled?" asked its own hand-kept list, so none caught
it. The answer is one enumeration — `all_matters()` over `REGISTRY` — and a
structural guard that a matter which exists but is not registered stops the
build rather than going silently unhandled.
"""
from __future__ import annotations

import ast
import types
from pathlib import Path

import pytest

from homestead_law import registry as registry_mod
from homestead_law.registry import (
    REGISTRY,
    MatterType,
    all_matters,
    matter,
)
from homestead.keep.rungs import Rung, derived_of
from homestead_law.packs import custody

PKG = Path(__file__).resolve().parent.parent / "homestead_law"


# ── promoted from test_invariants_pending.py ─────────────────────────────────

def test_i23_the_registry_is_the_only_enumeration():
    """BUG-6: workers' comp — one of three advertised matter types — was
    structurally absent from the urgent queue, because three types were
    enumerated by hand in three places."""
    from homestead_law.registry import REGISTRY, all_matters

    assert set(all_matters()) == set(REGISTRY)


# ── what the registry holds ──────────────────────────────────────────────────

def test_every_registered_matter_has_a_pack_on_disk_and_no_phantom():
    """Registry-relative, not a literal set: every matter `all_matters()` names
    is a `REGISTRY` key, and every `REGISTRY` key is a pack `_discover_packs()`
    finds on disk — the same three-way equality `_validate` enforces at import,
    held here as a behavioural assertion so it stays true no matter how many
    packs are built. A literal `{"custody"}` here would be exactly the kind of
    hand-kept assumption that breaks the moment a second pack (bankruptcy,
    workers' comp — Phase 5) is registered, which is the failure this whole
    bite exists to keep from happening."""
    assert set(all_matters()) == set(REGISTRY) == set(registry_mod._discover_packs())


def test_all_matters_iterates_the_registry_and_nothing_else():
    """The one function everything that needs 'all matter types' calls. It reads
    `REGISTRY` at call time, so it cannot hold a stale copy — and it hands back a
    tuple, so a caller cannot mutate the enumeration by keeping what it returns.
    """
    assert set(all_matters()) == set(REGISTRY)
    assert isinstance(all_matters(), tuple)
    assert all(isinstance(name, str) for name in all_matters())


def test_an_entry_ties_a_matter_to_its_pack():
    """The value shape: a `MatterType` carrying the name, the jurisdiction and
    the pack — the host holding the thing it consumes (Article IV's injected
    seam), never the reverse."""
    entry = matter("custody")
    assert isinstance(entry, MatterType)
    assert entry.name == custody.MATTER == "custody"
    assert entry.jurisdiction == custody.JURISDICTION == "US-NM"
    assert entry.pack is custody


def test_the_registry_does_not_hardcode_the_field_list_it_reads_it():
    """The pack is reachable through the registry without the registry copying
    the pack's field list. `fields` is a property over `pack.FIELDS`, so it *is*
    the pack's one list — identity, not equality — and there is nowhere for a
    second copy to drift from the first, which is BUG-6's mechanism removed."""
    entry = matter("custody")
    assert entry.fields is custody.FIELDS
    assert entry.schema is custody.SCHEMA
    assert entry.fields["ssn"] is Rung.L5
    assert set(entry.fields) == set(custody.SCHEMA)


def test_matter_is_strict_about_an_unknown_name():
    """Like `surfaces.facts`: a caller holding a name that is not registered has
    skipped a step, and a `KeyError` here is cheaper than the missing schema read
    it would otherwise have caused downstream.

    `"not_a_matter"` rather than `"bankruptcy"`: bankruptcy is a real future
    pack (Wave 3), and a test that asserts it is *unregistered* would itself
    become the thing that breaks the moment it is built — the exact test
    rewrite this bite exists to make unnecessary."""
    with pytest.raises(KeyError):
        matter("not_a_matter")


# ── the import-time guard fires — BUG-6's shape, from each side ───────────────

def _fake_pack(
    name: str = "_fake_second",
    *,
    jurisdiction: str = "US-NM",
    jurisdictions: tuple[str, ...] | None = None,
) -> types.ModuleType:
    """A stand-in pack with the attributes `_entry`/`_validate` read. Built for
    the guard tests the way `test_invariants_surfaces` builds fake modules for
    the schema scan — a real module object, not a mock.

    Defaults to `"_fake_second"`, never a real future pack name: bankruptcy and
    workers' comp are Phase 5 and become real registry entries in Wave 3, and a
    guard-fire plant named after either would itself start failing (or, worse,
    silently stop exercising the guard) the day that pack lands. `"_fake_second"`
    can never collide with a pack this repo actually ships.

    It declares `JURISDICTIONS` (defaulting to a tuple holding just
    `jurisdiction`) even though *this* branch's `_validate` does not read it:
    a fake pack is a pack, and the moment the pack contract requires the tuple
    (decision 1, the parallel L2a bite) a fake without one stops being a stand-in
    for a real pack and starts failing `_validate` for a reason the test that
    built it never meant to assert. Declaring it here costs one line and keeps
    every `_validate` plant below testing the thing it names."""
    mod = types.ModuleType(f"homestead_law.packs.{name}")
    mod.MATTER = name
    mod.JURISDICTION = jurisdiction
    mod.JURISDICTIONS = jurisdictions if jurisdictions is not None else (jurisdiction,)
    mod.FIELDS = {"case_number": Rung.L3}
    mod.SCHEMA = {
        "case_number": {
            "rung": Rung.L3,
            "matter": name,
            # L3 is served as a stand-in somewhere, so `_validate` requires a
            # derived sentence (decision 3); a fixture without one would trip
            # that guard instead of the one each test below is aiming at.
            "derived": "A case number is on file",
        }
    }
    return mod


def test_a_pack_on_disk_with_no_entry_fails_the_build():
    """BUG-6 exactly: a matter type that exists and is not enumerated. The guard
    is run here against a registry that omits a discovered pack, so it is shown
    to fire and not merely asserted to exist."""
    fake_second = _fake_pack()
    on_disk = {"custody": custody, "_fake_second": fake_second}
    with pytest.raises(RuntimeError) as exc:
        registry_mod._validate(dict(REGISTRY), on_disk)
    assert "_fake_second" in str(exc.value)
    # and it names the failure it is, not a bare "invalid"
    assert "no registry entry" in str(exc.value)


def test_a_registry_entry_with_no_pack_is_a_phantom_and_fails_the_build():
    """The other half of BUG-6: a name in the enumeration with nothing behind it.
    Inventing an entry before its pack exists is the exact thing that would let
    `all_matters()` advertise a type no pack can serve."""
    phantom = registry_mod._entry(_fake_pack())
    broken = {**REGISTRY, "_fake_second": phantom}
    with pytest.raises(RuntimeError) as exc:
        registry_mod._validate(broken, {"custody": custody})
    assert "_fake_second" in str(exc.value)
    assert "no pack" in str(exc.value)


def test_a_key_that_disagrees_with_its_packs_matter_fails_the_build():
    """A key kept by hand next to a name set in the pack is a transcription that
    can drift — so it is not allowed to. The registry is keyed by the pack's own
    `MATTER`, read once, and a mismatch stops the build."""
    misfiled = registry_mod.MatterType(
        name="custardy", jurisdiction="US-CA", pack=custody  # typo'd key
    )
    broken = {"custardy": misfiled}
    with pytest.raises(RuntimeError) as exc:
        registry_mod._validate(broken, {"custody": custody})
    assert "disagrees" in str(exc.value)


def test_an_entry_that_is_not_a_matter_type_fails_the_build():
    """The table holds `MatterType`s, the way `FACTS` holds `SurfaceFacts` — a
    bare string or a raw pack in the value slot is caught at import."""
    with pytest.raises(RuntimeError):
        registry_mod._validate({"custody": "custody"}, {"custody": custody})


def test_the_real_registry_passes_its_own_guard():
    """The positive side: what actually ships is consistent with the packs that
    actually exist. Run here so the guard is exercised on the real inputs on
    every invocation, not only at import."""
    registry_mod._validate(REGISTRY, registry_mod._discover_packs())
    assert set(registry_mod._discover_packs()) == set(REGISTRY)


# ── the Phase-3 exit criterion, held behaviourally ───────────────────────────

def test_adding_a_pack_to_the_registry_needs_no_other_code_change(monkeypatch):
    """*"Adding a pack touches no navigation, queue, or briefing code."*

    The whole point of one enumeration: a second matter type appears everywhere
    that iterates `all_matters()` the instant it is in `REGISTRY`, with nothing
    else edited. Demonstrated by injecting a second entry into the registry and
    reading it back out of `all_matters()` — the function reads `REGISTRY` at
    call time, so the addition is reflected with no change to the function and no
    second list to keep in step. Registry-relative (`set(registry_mod.REGISTRY)`),
    not a literal `{"custody", "bankruptcy"}` — this test must keep passing
    unchanged the day a real second pack is registered."""
    fake_second = registry_mod._entry(_fake_pack())
    monkeypatch.setitem(registry_mod.REGISTRY, "_fake_second", fake_second)

    assert set(all_matters()) == set(registry_mod.REGISTRY)
    assert matter("_fake_second").fields == {"case_number": Rung.L3}


# ── the structural guard: the registry is the ONLY enumeration ───────────────

MATTER_ENUM_ALLOWED = {
    PKG / "registry.py",
    # packs/*.py: a pack declares its own MATTER ("custody"); it is the source of
    # the name, so it is where the string is allowed to live.
}


def _matter_name_enumerations(tree: ast.AST, names: set[str]) -> list[int]:
    """Every place a matter name appears *as an enumeration* — an element of a
    list/set/tuple literal, or an operand of an `in`/`==` test. That is BUG-6's
    literal shape: `["custody", "bankruptcy", "workers_comp"]`, or
    `if m in ("custody", ...)`. Bare display strings (`Label(text="custody")`)
    and prose in a docstring are *not* enumerations and are not caught — the ban
    is on hand-keeping the set, not on the word appearing."""
    hits: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.List, ast.Set, ast.Tuple)):
            for elt in node.elts:
                if isinstance(elt, ast.Constant) and elt.value in names:
                    hits.append(node.lineno)
        elif isinstance(node, ast.Compare):
            for operand in (node.left, *node.comparators):
                if isinstance(operand, ast.Constant) and operand.value in names:
                    hits.append(node.lineno)
    return hits


def _is_pack(mod: Path) -> bool:
    return "packs" in mod.relative_to(PKG).parts


def test_no_module_outside_the_registry_hardcodes_the_set_of_matters():
    """I-23 held structurally. No navigation, queue or briefing keeps its own
    matter list — the failure was three of them, and with one matter built we
    cannot watch three drift, so we hold the seam instead: a matter name used as
    an *enumeration* (in a collection literal, or an `in`/`==` test) may appear
    only where the enumeration legitimately lives — this registry, and the packs
    that declare their own names. Everywhere else it is a build failure.

    Vacuous the day it is written, on purpose: there is no consumer iterating
    matters yet (navigation, the queue and the briefing are Phase 3+). It is here
    so it is *not* vacuous the moment someone writes `matters = ["custody",
    "bankruptcy"]` in the queue instead of calling `all_matters()` — which is the
    exact line BUG-6 was."""
    names = set(all_matters())
    offenders: list[str] = []
    for mod in sorted(PKG.rglob("*.py")):
        if "__pycache__" in mod.parts:
            continue
        if mod in MATTER_ENUM_ALLOWED or _is_pack(mod):
            continue
        for lineno in _matter_name_enumerations(ast.parse(mod.read_text("utf-8")), names):
            offenders.append(f"{mod.relative_to(PKG.parent)}:{lineno}")
    assert not offenders, (
        f"a matter name is enumerated by hand outside the registry at {offenders}. "
        "I-23 — the registry is the only enumeration; iterate all_matters() "
        "rather than keeping a list, because a second list is one that can drift "
        "from this one, and workers' comp fell out of exactly such a list (BUG-6)."
    )


def test_the_structural_guard_fires_on_a_planted_enumeration(tmp_path):
    """A scan that has never fired has not been shown to check anything — Phase
    0's lesson, applied. BUG-6's own line is planted in a fake non-registry
    module and the guard must catch it, in each of the two shapes an enumeration
    takes: a collection literal, and a membership test."""
    names = {"custody", "bankruptcy", "workers_comp"}

    literal = tmp_path / "queue.py"
    literal.write_text(
        "URGENT_MATTERS = ['custody', 'bankruptcy', 'workers_comp']\n", "utf-8"
    )
    membership = tmp_path / "nav.py"
    membership.write_text(
        "def is_matter(m):\n    return m in ('custody', 'bankruptcy')\n", "utf-8"
    )
    clean = tmp_path / "view.py"
    clean.write_text(
        "import tkinter as tk\n"
        "def draw(w):\n    tk.Label(w, text='custody').pack()\n",  # a display string, not an enum
        "utf-8",
    )

    assert _matter_name_enumerations(ast.parse(literal.read_text()), names)
    assert _matter_name_enumerations(ast.parse(membership.read_text()), names)
    assert not _matter_name_enumerations(ast.parse(clean.read_text()), names), (
        "a bare display string is not an enumeration and must not be caught — "
        "the ban is on hand-keeping the set, not on the word appearing"
    )


def test_the_guard_would_catch_the_registry_itself_if_it_were_not_exempt():
    """The exemption is load-bearing, so it is pinned: the registry and the packs
    are *allowed* to name matters, and everything else is not. If the allow-list
    were dropped the registry could still enumerate (it builds from
    `custody.MATTER`, an attribute, not a literal today) — but a future authored
    `REGISTRY = {"custody": ...}` with a literal key is exactly the enumeration
    this file is *for*, so it must be exempt, and this test states that it is."""
    assert PKG / "registry.py" in MATTER_ENUM_ALLOWED
    assert _is_pack(PKG / "packs" / "custody.py")
    assert not _is_pack(PKG / "store.py")


# ── the Wave-3 exit criterion: registering a second matter breaks no test ────


def test_registering_a_second_matter_breaks_no_test(monkeypatch):
    """L2c's own *"done when"*, held as a test: with a second matter injected
    into the registry, every registry-relative assertion in this file still
    holds, computed fresh against the two-matter registry rather than reasserted
    by hand. This is what makes the other tests in this module — rewritten
    above to read `set(REGISTRY)`/`set(_discover_packs())` instead of a literal
    `{"custody"}` — actually registry-relative rather than merely renamed."""
    fake_second = _fake_pack()
    monkeypatch.setitem(registry_mod.REGISTRY, "_fake_second", registry_mod._entry(fake_second))

    # test_every_registered_matter_has_a_pack_on_disk_and_no_phantom's rule,
    # against the two-matter registry — the discovered pack is a real module
    # on disk (`_fake_second` is not; `_discover_packs()` cannot see it, so it
    # is passed alongside what is actually on disk, standing in for a real
    # Wave-3 pack file the way the guard tests above do).
    on_disk = {**registry_mod._discover_packs(), "_fake_second": fake_second}
    assert set(all_matters()) == set(REGISTRY) == set(on_disk)

    # test_matter_is_strict_about_an_unknown_name's rule: an unregistered name
    # still raises, and the newly registered one no longer does.
    with pytest.raises(KeyError):
        matter("not_a_matter")
    assert matter("_fake_second").fields == {"case_number": Rung.L3}

    # test_the_registry_does_not_hardcode_the_field_list_it_reads_it's rule,
    # for both matters — identity, not a copy, for each.
    assert matter("custody").fields is custody.FIELDS
    assert matter("_fake_second").fields is fake_second.FIELDS

    # the import-time guard itself still passes, held against the augmented
    # on-disk set standing in for `_fake_second`'s pack file.
    registry_mod._validate(dict(REGISTRY), on_disk)

# ── L2a-pack-contract: JURISDICTIONS (decision 1) ────────────────────────────

def test_jurisdictions_is_read_live_from_the_pack():
    """`MatterType.jurisdictions` is a property over `pack.JURISDICTIONS`, the
    same shape as `fields`/`schema` — identity with the pack's own tuple, not a
    copy, so the registry cannot carry a stale second copy of it (BUG-6's
    mechanism, applied to this third pack attribute)."""
    entry = matter("custody")
    assert entry.jurisdictions is custody.JURISDICTIONS
    assert entry.jurisdiction in entry.jurisdictions


def test_a_default_jurisdiction_outside_the_supported_tuple_fails_the_build():
    """Decision 1's planted violation: a pack whose default `JURISDICTION` is
    not itself a member of its own `JURISDICTIONS`. Fired against `_validate`
    directly, on a fake pack, so the guard is shown to catch it rather than
    merely asserted to."""
    broken_pack = _fake_pack(
        "workers_comp", jurisdiction="US-OR", jurisdictions=("US-NM",)
    )
    entry = registry_mod._entry(broken_pack)
    broken_registry = {**REGISTRY, "workers_comp": entry}
    on_disk = {"custody": custody, "workers_comp": broken_pack}
    with pytest.raises(RuntimeError) as exc:
        registry_mod._validate(broken_registry, on_disk)
    assert "workers_comp" in str(exc.value)
    # the membership message specifically — "JURISDICTION" alone also matches
    # the shape message above it, so the plant could pass on the wrong refusal
    assert "is not in" in str(exc.value)
    assert "'US-OR'" in str(exc.value) and "('US-NM',)" in str(exc.value)


def test_an_empty_jurisdictions_tuple_fails_the_build():
    """The other half of decision 1's validation: `JURISDICTIONS` itself must be
    a non-empty tuple of non-empty strings — an empty tuple, a blank member, or
    a non-tuple all read as absence and fail closed the way an unclassified
    field does (I-11's shape, applied here)."""
    for bad in ((), ("",), ("US-NM", "  "), ["US-NM"]):
        broken_pack = _fake_pack("workers_comp", jurisdiction="US-NM", jurisdictions=bad)
        entry = registry_mod._entry(broken_pack)
        broken_registry = {**REGISTRY, "workers_comp": entry}
        on_disk = {"custody": custody, "workers_comp": broken_pack}
        with pytest.raises(RuntimeError) as exc:
            registry_mod._validate(broken_registry, on_disk)
        assert "JURISDICTIONS" in str(exc.value), f"failed for {bad!r}"


def test_a_pack_with_no_jurisdictions_attribute_at_all_fails_the_build():
    """A pack that never declares `JURISDICTIONS` — not even an empty one — is
    the same absence as any other, read by `getattr(..., None)` rather than a
    bare attribute access that would raise the wrong exception type."""
    broken_pack = types.ModuleType("homestead_law.packs._fake_workers_comp")
    broken_pack.MATTER = "workers_comp"
    broken_pack.JURISDICTION = "US-NM"
    broken_pack.FIELDS = {"case_number": Rung.L3}
    broken_pack.SCHEMA = {
        "case_number": {
            "rung": Rung.L3,
            "matter": "workers_comp",
            "derived": "A case number is on file",
        }
    }
    entry = registry_mod._entry(broken_pack)
    broken_registry = {**REGISTRY, "workers_comp": entry}
    on_disk = {"custody": custody, "workers_comp": broken_pack}
    with pytest.raises(RuntimeError) as exc:
        registry_mod._validate(broken_registry, on_disk)
    assert "JURISDICTIONS" in str(exc.value)


def test_an_entrys_copied_jurisdiction_cannot_drift_from_its_pack():
    """`fields`, `schema` and `jurisdictions` are properties over the pack and
    cannot disagree with it. `jurisdiction` is a *copy*, taken by `_entry` at
    construction — the one field on an entry with BUG-6's mechanism still in
    it. Planted: an entry built by hand with a jurisdiction its pack does not
    declare."""
    drifted = registry_mod.MatterType(name="custody", jurisdiction="US-OR", pack=custody)
    broken_registry = {**REGISTRY, "custody": drifted}
    with pytest.raises(RuntimeError) as exc:
        registry_mod._validate(broken_registry, {"custody": custody})
    assert "disagrees with its pack" in str(exc.value)


def test_the_real_registry_passes_the_jurisdiction_checks():
    """The positive side, run against what actually ships — `_validate` already
    runs at import (registry.py's module body), so this re-runs it explicitly to
    keep the guard exercised by the suite on every invocation, not only once at
    collection."""
    registry_mod._validate(REGISTRY, registry_mod._discover_packs())


# ── L2a-pack-contract: no second derived-form table outside the packs ───────

def _derived_form_table_dicts(tree: ast.AST, field_names: set[str]) -> list[int]:
    """Every dict literal that is shaped like a derived-form table: at least
    three string keys drawn from a registered pack's field names, every value a
    plain string literal. That is the exact shape `cli._default_derived` and
    `server._derived` used to hand-keep (`{"case_number": "A case number is on
    file", ...}`) — a second copy of what a pack's `SCHEMA` already declares,
    free to drift from it the moment one copy is edited and the others are not.
    Restricted to string-valued dicts so a field-keyed table of a different
    shape (e.g. `homestead_law/app/demo.py`'s field → (payload, derived-or-None)
    tuples, which is real seed data, not a second derived-form table) is not a
    false positive."""
    hits: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict) or not node.values:
            continue
        if any(k is None for k in node.keys):  # a **spread entry
            continue
        if not all(isinstance(v, ast.Constant) and isinstance(v.value, str) for v in node.values):
            continue
        matched = sum(
            1 for k in node.keys
            if isinstance(k, ast.Constant) and isinstance(k.value, str) and k.value in field_names
        )
        if matched >= 3:
            hits.append(node.lineno)
    return hits


def test_no_module_outside_the_packs_keeps_a_derived_form_table():
    """I-23's shape, one attribute over. Decision 3 puts the derived form on the
    pack; a second `{field: sentence}` table anywhere else is the exact drift
    this bite deleted two live copies of (`cli._default_derived`,
    `server._derived`) — so neither, nor anything new, may come back.

    Only the packs are exempt. `registry.py` is exempt from the *matter-name*
    scan above because the registry is where an enumeration of matter names
    legitimately lives; no such argument exists for a derived-form table, and
    the registry — which already holds every pack and every schema — is the
    most plausible place for someone to add a convenience default. So it is
    scanned like anything else, and
    `test_the_derived_form_table_guard_is_not_exempt_for_the_registry` plants
    one there to show it would be caught."""
    names: set[str] = set()
    for name in all_matters():
        names.update(matter(name).schema)
    assert names, "the scan needs the packs' field names to look for"

    offenders: list[str] = []
    for mod in sorted(PKG.rglob("*.py")):
        if "__pycache__" in mod.parts:
            continue
        if _is_pack(mod):
            continue
        for lineno in _derived_form_table_dicts(ast.parse(mod.read_text("utf-8")), names):
            offenders.append(f"{mod.relative_to(PKG.parent)}:{lineno}")
    assert not offenders, (
        f"a derived-form table is hand-kept outside the packs at {offenders}. "
        "Decision 3 puts a field's derived sentence on the pack "
        "(SCHEMA[field]['derived']) and every reader calls "
        "homestead.keep.rungs.derived_of(schema, field) — a second "
        "{field: sentence} table is free to drift from it the moment either "
        "is edited alone, which is exactly what cli.py's and server.py's own "
        "copies had already done before this bite deleted them."
    )


def test_the_derived_form_table_guard_fires_on_a_planted_table(tmp_path):
    """A scan that has never fired has not been shown to check anything.
    Planted in a tmp *copy of a real surface file* — `app/view.py` — appended
    with a hand-kept derived-form table, the shape this guard exists to catch;
    the unmodified surface must not trip it."""
    import shutil

    names = set(matter("custody").schema)
    surface = tmp_path / "view.py"
    shutil.copy(PKG / "app" / "view.py", surface)
    with surface.open("a", encoding="utf-8") as fh:
        fh.write(
            "\n\n_LEAKED_DERIVED = {\n"
            "    'case_number': 'A case number is on file',\n"
            "    'docket': 'A docket entry is on file',\n"
            "    'opposing_party': 'The other parent is named',\n"
            "}\n"
        )

    assert _derived_form_table_dicts(ast.parse(surface.read_text()), names)
    assert not _derived_form_table_dicts(
        ast.parse((PKG / "app" / "view.py").read_text()), names
    ), "the guard must not fire on the unmodified surface it was copied from"

    clean = tmp_path / "demo_shape.py"
    clean.write_text(
        "_DEMO = {'case_number': ('FL-2026-1', 'A case number is on file'),\n"
        "         'docket': ('Entry 1', 'A docket entry is on file'),\n"
        "         'opposing_party': ('J. Rivera', 'The other parent is named')}\n",
        "utf-8",
    )
    assert not _derived_form_table_dicts(ast.parse(clean.read_text()), names), (
        "a field -> (payload, derived) tuple table is seed data, not a second "
        "derived-form table, and must not be flagged"
    )


def test_the_derived_form_table_guard_is_not_exempt_for_the_registry(tmp_path):
    """The scan above skips only the packs. Planted in a tmp copy of the real
    `registry.py` — the module with every pack and every schema already in
    hand, and so the likeliest home for a "just a default" table — to show the
    guard reaches it; the unmodified registry must not trip it."""
    import shutil

    names = set(matter("custody").schema)
    planted = tmp_path / "registry.py"
    shutil.copy(PKG / "registry.py", planted)
    with planted.open("a", encoding="utf-8") as fh:
        fh.write(
            "\n\n_FALLBACK_DERIVED = {\n"
            "    'case_number': 'A case number is on file',\n"
            "    'docket': 'A docket entry is on file',\n"
            "    'notes': 'An operator note is on file',\n"
            "}\n"
        )

    assert _derived_form_table_dicts(ast.parse(planted.read_text()), names)
    assert not _derived_form_table_dicts(
        ast.parse((PKG / "registry.py").read_text()), names
    ), "the guard must not fire on the unmodified registry it was copied from"


# ── L2a-pack-contract: the "derived" key is required, not merely tested ──────

def test_an_l3_field_with_no_derived_form_fails_the_build():
    """Decision 3's planted violation. `classify_schema` ignores the `"derived"`
    key on purpose, so a pack that omits it on an `L3`/`L4` field imports
    clean — and the omission surfaces only at the first `put`, as an
    `UnclassifiedField` out of `Classified`, raised outside either door's
    `try`. `_validate` refuses it at import, naming the field, the way every
    other absence in this module is refused (I-11)."""
    broken_pack = _fake_pack("workers_comp")
    broken_pack.SCHEMA = {
        "claim_number": {"rung": Rung.L3, "matter": "workers_comp", "why": "step 2"}
    }
    broken_pack.FIELDS = {"claim_number": Rung.L3}
    entry = registry_mod._entry(broken_pack)
    broken_registry = {**REGISTRY, "workers_comp": entry}
    on_disk = {"custody": custody, "workers_comp": broken_pack}
    with pytest.raises(RuntimeError) as exc:
        registry_mod._validate(broken_registry, on_disk)
    assert "claim_number" in str(exc.value) and "derived" in str(exc.value)


def test_a_blank_derived_form_is_absence_too():
    """A whitespace-only sentence reads as present to `in` and as nothing to a
    reader — `derived_of` already returns `None` for it, so the build must
    refuse it exactly as it refuses the missing key."""
    for blank in ("", "   ", None, 7):
        broken_pack = _fake_pack("workers_comp")
        broken_pack.SCHEMA = {
            "claim_number": {"rung": Rung.L3, "matter": "workers_comp", "derived": blank}
        }
        broken_pack.FIELDS = {"claim_number": Rung.L3}
        entry = registry_mod._entry(broken_pack)
        with pytest.raises(RuntimeError) as exc:
            registry_mod._validate(
                {**REGISTRY, "workers_comp": entry},
                {"custody": custody, "workers_comp": broken_pack},
            )
        assert "claim_number" in str(exc.value), f"failed for {blank!r}"


def test_a_missing_default_jurisdiction_fails_the_build_by_name():
    """A pack that never declares `JURISDICTION`. Read through `getattr` so the
    refusal is this module's, naming the key — not an `AttributeError` from
    whichever consumer happened to touch it first."""
    broken_pack = _fake_pack("workers_comp")
    del broken_pack.JURISDICTION
    entry = registry_mod.MatterType(
        name="workers_comp", jurisdiction="US-NM", pack=broken_pack
    )
    with pytest.raises(RuntimeError) as exc:
        registry_mod._validate(
            {**REGISTRY, "workers_comp": entry},
            {"custody": custody, "workers_comp": broken_pack},
        )
    assert "JURISDICTION" in str(exc.value) and "workers_comp" in str(exc.value)


def test_the_derived_requirement_matches_the_engines():
    """`_validate` states which rungs must carry a derived form as a tuple of
    its own, because the engine's copy (`rungs._NEEDS_DERIVED`) is private. Two
    copies of a rule is the drift this whole file is about, so the two are
    pinned together *behaviourally*: for every rung, building a `Classified`
    with no derived form must refuse exactly when the registry would."""
    from homestead.keep.rungs import Classified, UnclassifiedField

    refused = set()
    for rung in Rung:
        try:
            Classified(rung, "a value", None)
        except UnclassifiedField:
            refused.add(rung)
    assert refused == {Rung.L3, Rung.L4}, (
        "the engine's set of rungs that must carry a derived form has moved; "
        "update `needs_derived` in registry.py::_validate to match"
    )


def test_the_real_packs_declare_a_derived_form_for_every_rung_that_needs_one():
    """The positive side, registry-relative rather than custody-only: every
    registered pack, every `L3`/`L4` field. A pack added in a later wave is
    covered the day it is registered, with no edit here."""
    for name in all_matters():
        mt = matter(name)
        for field, rung in mt.fields.items():
            if rung not in (Rung.L3, Rung.L4):
                continue
            sentence = derived_of(mt.schema, field)
            assert sentence, f"{name}/{field} ({rung.value}) declares no derived form"


# ── L2b-instances: REPEATABLE (decision 2) ───────────────────────────────────

def test_repeatable_is_read_live_and_defaults_to_empty():
    """`MatterType.repeatable` mirrors `jurisdictions` — read straight off the
    pack. Custody itself gained a `REPEATABLE` set in L3-custody-relocation
    (one per-child field per dotted name), so the "defaults to empty" half is
    demonstrated on a fake pack that declares none — the same fixture shape
    `_fake_pack` builds — rather than on custody, which is no longer that
    example; a pack with nothing repeatable still pays nothing for that."""
    bare = _fake_pack("_fake_no_repeatable")
    assert registry_mod._entry(bare).repeatable == frozenset()

    assert matter("custody").repeatable is custody.REPEATABLE
    assert matter("custody").repeatable == frozenset(
        {"child.name", "child.dob", "child.school"}
    )


def test_a_repeatable_name_the_pack_does_not_have_fails_the_build():
    """Decision 2's plant: `REPEATABLE` naming a field `FIELDS` does not
    declare — the same 'enumerated but not real' shape I-23 forbids for
    matters, one level down, at fields."""
    broken_pack = _fake_pack("workers_comp")
    broken_pack.REPEATABLE = frozenset({"not_a_real_field"})
    entry = registry_mod._entry(broken_pack)
    with pytest.raises(RuntimeError) as exc:
        registry_mod._validate(
            {**REGISTRY, "workers_comp": entry},
            {"custody": custody, "workers_comp": broken_pack},
        )
    assert "not_a_real_field" in str(exc.value)
    assert "REPEATABLE" in str(exc.value)


def test_a_repeatable_naming_a_real_field_passes():
    good_pack = _fake_pack("workers_comp")
    good_pack.REPEATABLE = frozenset({"case_number"})
    entry = registry_mod._entry(good_pack)
    registry_mod._validate(
        {**REGISTRY, "workers_comp": entry},
        {"custody": custody, "workers_comp": good_pack},
    )


def test_a_repeatable_of_the_wrong_shape_fails_the_build():
    broken_pack = _fake_pack("workers_comp")
    broken_pack.REPEATABLE = ["case_number"]   # a list, not a frozenset
    entry = registry_mod._entry(broken_pack)
    with pytest.raises(RuntimeError) as exc:
        registry_mod._validate(
            {**REGISTRY, "workers_comp": entry},
            {"custody": custody, "workers_comp": broken_pack},
        )
    assert "REPEATABLE" in str(exc.value)


def test_the_real_registry_passes_the_repeatable_check():
    registry_mod._validate(REGISTRY, registry_mod._discover_packs())


def test_no_derived_form_carries_a_digit():
    """A derived form stands in for a payload; a digit in it is the payload
    leaking through its own stand-in (a case number, a date, a count of
    children). Registry-relative, so it holds for every pack, not just the one
    that exists today."""
    for name in all_matters():
        mt = matter(name)
        for field in mt.schema:
            sentence = derived_of(mt.schema, field)
            if sentence is None:
                continue
            assert not any(ch.isdigit() for ch in sentence), (
                f"{name}/{field}'s derived form carries a digit: {sentence!r} — "
                "a schema-level stand-in is one sentence for every instance of "
                "the field, so anything that varies with the value is either "
                "false for some records or a restatement of the value it exists "
                "to withhold"
            )


def test_a_misspelled_repeatable_fails_the_build():
    """The audit's plant on the optional declaration itself. `REPEATABLE` is
    read with `getattr(pack, "REPEATABLE", frozenset())`, which cannot tell a
    pack that has none from a pack that spelled it `REPEATABLES` — so a
    misspelling is silently "nothing is repeatable", and the pack author finds
    out when `--sub` refuses a field they declared. An optional contract needs
    a spelling check or it is not a contract."""
    broken_pack = _fake_pack("workers_comp")
    broken_pack.REPEATABLES = frozenset({"case_number"})
    entry = registry_mod._entry(broken_pack)
    with pytest.raises(RuntimeError) as exc:
        registry_mod._validate(
            {**REGISTRY, "workers_comp": entry},
            {"custody": custody, "workers_comp": broken_pack},
        )
    assert "REPEATABLES" in str(exc.value) and "REPEATABLE" in str(exc.value)


@pytest.mark.parametrize("name", ["REPEATABLES", "REPEATABLE_FIELDS", "REPEAT"])
def test_every_near_miss_spelling_of_repeatable_fails_the_build(name):
    """The scan is a prefix rule, not a list of one typo — so it catches the
    plural, the decorated name and the truncation alike."""
    broken_pack = _fake_pack("workers_comp")
    setattr(broken_pack, name, frozenset({"case_number"}))
    entry = registry_mod._entry(broken_pack)
    with pytest.raises(RuntimeError) as exc:
        registry_mod._validate(
            {**REGISTRY, "workers_comp": entry},
            {"custody": custody, "workers_comp": broken_pack},
        )
    assert name in str(exc.value)


def test_the_real_packs_spell_repeatable_correctly():
    """The positive side over the registry as shipped — the scan fires on a
    plant above and stays silent here, which is the only pair that proves it
    checks anything."""
    registry_mod._validate(REGISTRY, registry_mod._discover_packs())
