"""I-16 — one authorization chokepoint. Bite 3, hardened after the bite-1-3 audit.

`serve()`, `serve_all()` and `ambient_rows()` are the *shape* of one door;
`rungs.py` says so about itself and adds the sentence this bite answers:

    A gate wired to one entry point is not a gate, and at Phase 2 it is wired to
    none.

The first version of this bite wired it by banning the literal `.payload`
attribute — and the audit broke it in the way the prior audits break things: the
scan enforced the *spelling* of the bypass, not the property. `getattr(record,
"payload")` in a surface file reached a sealed L5 payload and passed the suite,
exactly the desktop-leak-evasion shape ("the scan misses the leak it was written
to prevent"). A one-word change walked the SSN onto the screen, green.

So the rule is now stated as a property of the **surface layer** rather than of
one token. `Classified.payload` — the sensitive datum — may be reached in exactly
two engine modules:

  * `keep/rungs.py`, the gate, where `serve()` reads the payload to decide
    whether it may cross a surface; and
  * `keep/record.py`, the store, where persistence serializes it. Disk is not a
    surface (S1-S4).

Everywhere else that is the ban. And in the surface layer — `homestead/app/` —
the ban is wider, because a surface has no honest use for reflection at all: a
surface *renders what it is handed*, `Served.value` and `AmbientRow.text`, and
never reaches around the gate by any spelling. So `getattr`, `vars`, `__dict__`,
`dataclasses.astuple`/`asdict`/`fields` and `operator.attrgetter` are all a build
failure in a surface, whatever they name — the field-by-name reads the literal
scan could not see. `keep/dates.py` reflects over its own `Deadline`, which is
why the reflection ban is scoped to the surface layer and not the whole package;
an engine type reflecting over itself is not a gate bypass.

The regression fixtures are the important half, and they now plant the leak in a
real surface path and run the **package scan** over it — not the helper over a
string — so a passing suite means the actual enforcement caught the actual leak.
"""
from __future__ import annotations

import ast
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent / "homestead_law"

#: The gate (`serve`/`decide`) lives in the pinned engine — `homestead.keep.rungs`,
#: outside this package — so it is not among the modules scanned here. Within this
#: module the **store** is the one place a raw payload legitimately lives;
#: everything else — surfaces included — goes through the gate and receives
#: `Served.value`.
STORE = PKG / "store.py"
ALLOWED = {STORE}

#: Reflection primitives that read a field without naming it — the forms the
#: audit used to walk past the literal `.payload` scan. A surface has no honest
#: use for any of them. Matched on the leaf name, so `operator.attrgetter`,
#: `dataclasses.astuple` and a bare `getattr` are all caught.
REFLECTION_CALLS = {
    "getattr", "setattr", "vars", "astuple", "asdict", "attrgetter", "fields",
    "__getattribute__", "__getattr__",
}
REFLECTION_ATTRS = {"__dict__", "__getattribute__", "__getattr__"}


def _modules() -> list[Path]:
    return sorted(p for p in PKG.rglob("*.py") if "__pycache__" not in p.parts)


#: The gate's own doors. A module that calls one is consuming `Served.value`
#: for somebody else — which is what a surface *is*, whatever directory it
#: sits in. `jurisdiction.py` is the first such module outside `app/`
#: (L2b-instances: `jurisdiction_of` serves on `S1_LIST` so nothing downstream
#: can compute from a forum it was never shown), and `rules.py` will be the
#: next. Deriving the set from the call rather than listing the files is the
#: difference between a rule and a list that goes stale the day a bite adds a
#: module — the failure mode this whole file was written about.
DOORS = {"serve", "serve_all", "ambient_rows"}


def _calls_a_door(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        leaf = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        if leaf in DOORS:
            return True
    return False


def _is_surface(mod: Path) -> bool:
    """`homestead_law/app/`, plus any module that calls the gate itself."""
    if "app" in mod.relative_to(PKG).parts:
        return True
    return _calls_a_door(ast.parse(mod.read_text("utf-8")))


def _payload_reaches(tree: ast.AST) -> list[int]:
    """Every `.payload` attribute access in a tree, by line. A dict key
    (`{"payload": ...}`) is an `ast.Constant`, not an `ast.Attribute`, so the
    store's serialization is not a reach — only `something.payload` is."""
    return [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr == "payload"
    ]


def _reflection_reaches(tree: ast.AST) -> list[tuple[int, str]]:
    """Every reflection primitive in a tree — a call to `getattr`/`vars`/
    `astuple`/… or an access of `.__dict__`/`.__getattribute__`. These read a
    field by computed name, which is how the literal `.payload` scan was walked
    past."""
    hits: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            leaf = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if leaf in REFLECTION_CALLS:
                hits.append((node.lineno, leaf))
        elif isinstance(node, ast.Attribute) and node.attr in REFLECTION_ATTRS:
            hits.append((node.lineno, node.attr))
    return hits


def test_i16_only_the_store_reaches_a_payload():
    """The chokepoint, across this package. The gate is the pinned engine's; here
    the store is the only module that may touch a raw payload, and any other
    module reaching one has walked past the one door."""
    offenders = []
    for mod in _modules():
        if mod in ALLOWED:
            continue
        for lineno in _payload_reaches(ast.parse(mod.read_text("utf-8"))):
            offenders.append(f"{mod.relative_to(PKG.parent)}:{lineno}")
    assert not offenders, (
        "a payload is reached outside the store, at "
        f"{offenders}. I-16 — the payload crosses a surface only through "
        "serve()/serve_all()/ambient_rows(), which hand back Served.value; a "
        "direct .payload read is the gate wired to nothing."
    )


def test_i16_the_surface_layer_does_not_reflect():
    """The audit's finding, closed as a property rather than a spelling. A
    surface renders what it is handed and never reaches around the gate — so in
    `homestead/app/` there is no getattr, no vars, no __dict__, no astuple/
    asdict/fields, no attrgetter. Those are the by-computed-name reads that made
    `getattr(record, "payload")` invisible to the literal scan; here they are a
    build failure whatever they name, because a surface that needs one is a
    surface reaching for a payload it was not handed."""
    offenders = []
    for mod in _modules():
        if not _is_surface(mod):
            continue
        for lineno, how in _reflection_reaches(ast.parse(mod.read_text("utf-8"))):
            offenders.append(f"{mod.relative_to(PKG.parent)}:{lineno} {how}")
    assert not offenders, (
        f"the surface layer reflects at {offenders}. A surface renders "
        "Served.value and AmbientRow.text; reflection is how a payload is read "
        "without naming it, and the audit proved getattr(record, 'payload') "
        "reached a sealed datum while passing the literal scan. No reflection "
        "on a surface — ask serve()."
    )


def test_i16_the_surface_layer_reaches_no_payload():
    """The plan's original words, kept as their own named check for the surface
    layer, where the failure would actually ship."""
    offenders = []
    for mod in _modules():
        if not _is_surface(mod):
            continue
        for lineno in _payload_reaches(ast.parse(mod.read_text("utf-8"))):
            offenders.append(f"{mod.relative_to(PKG.parent)}:{lineno}")
    assert not offenders, (
        f"the surface layer reaches a payload directly at {offenders}."
    )


def _scan_surface_dir(app_dir: Path) -> list[str]:
    """The real package scan, pointed at a directory: both the payload reach and
    the reflection ban, as the two surface-layer tests apply them together."""
    offenders = []
    for mod in sorted(app_dir.rglob("*.py")):
        tree = ast.parse(mod.read_text("utf-8"))
        for lineno in _payload_reaches(tree):
            offenders.append(f"{mod.name}:{lineno} .payload")
        for lineno, how in _reflection_reaches(tree):
            offenders.append(f"{mod.name}:{lineno} {how}")
    return offenders


def test_i16_regression_every_bypass_the_audit_found_is_caught(tmp_path):
    """The audit's eight bypasses, planted in a surface file and run through the
    real scan — not the helper over a string. Each must be caught, or the guard
    is passing only because `app/` happens to be clean today. This is the test
    whose weakness let finding #1 through: it now exercises the enforcement, on
    every form, in a surface path."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    bypasses = [
        "record.payload",
        'getattr(record, "payload")',
        'getattr(record, "pay" + "load")',
        'record.__dict__["payload"]',
        'vars(record)["payload"]',
        "dataclasses.astuple(record)[1]",
        'dataclasses.asdict(record)["payload"]',
        'operator.attrgetter("payload")(record)',
        "[getattr(record, f.name) for f in dataclasses.fields(record)]",
    ]
    for i, expr in enumerate(bypasses):
        (app_dir / f"leak_{i}.py").write_text(
            "import dataclasses, operator\n"
            f"def draw(record):\n    return {expr}\n"
        )
    offenders = _scan_surface_dir(app_dir)
    # every planted file must raise at least one offence
    caught_files = {o.split(":")[0].split(" ")[0] for o in offenders}
    missed = [
        f"leak_{i}.py" for i in range(len(bypasses))
        if f"leak_{i}.py" not in caught_files
    ]
    assert not missed, (
        f"these audit bypasses passed the surface scan: {missed}. Each is a way "
        "to read a payload a surface was not handed; none may be invisible."
    )


def test_i16_serve_is_the_obvious_path():
    """The doors are exported and callable, and what they hand back is *not* a
    payload. A surface that only ever sees `Served.value` and `AmbientRow.text`
    has no expression that reaches a withheld datum — I-35's structural argument,
    generalized to the chokepoint."""
    from homestead.keep import rungs
    from homestead.keep.rungs import AmbientRow, Served

    for door in ("serve", "serve_all", "ambient_rows"):
        assert door in rungs.__all__, f"{door} is a door and must be exported"
        assert callable(getattr(rungs, door))

    assert "value" in Served.__dataclass_fields__
    assert "payload" not in Served.__dataclass_fields__
    assert set(AmbientRow.__dataclass_fields__) == {"rung", "text"}


def test_the_surface_set_is_derived_from_the_gate_not_a_list_of_directories():
    """The set this file scans must actually contain the module that serves.
    `jurisdiction.py` lives at the package root and hands `Served.value` to
    every future counting rule — if the reflection ban stopped at `app/`, the
    one new gate consumer in L2b would have been outside it, and the next bite
    to add one would be too."""
    surfaces = {m.name for m in _modules() if _is_surface(m)}
    assert "jurisdiction.py" in surfaces, (
        "jurisdiction.py calls serve() and is not in the surface set — the set "
        "is a directory list again"
    )
    assert "window.py" in surfaces          # the original surface layer, still in
    assert "store.py" not in surfaces       # the payload boundary is not a surface


def test_a_serving_module_outside_app_is_held_to_the_reflection_ban(tmp_path):
    """The plant for the rule above: a module at the package root that both
    calls the gate and reflects. Written to a temp package and run through the
    same two helpers the package tests use, so a pass means the enforcement
    caught it, not that the tree happens to be clean."""
    mod = tmp_path / "rules.py"
    mod.write_text(
        "from homestead.keep.rungs import serve\n"
        "def anchor(record, surface):\n"
        "    served = serve(record, surface)\n"
        '    return getattr(served, "payload")\n'
    )
    tree = ast.parse(mod.read_text("utf-8"))
    assert _calls_a_door(tree), "the plant serves"
    # `getattr(served, "payload")` is invisible to the literal `.payload` scan —
    # the audit's original bypass — and caught by the reflection ban, which is
    # the whole reason a gate consumer has to be inside the surface set.
    assert not _payload_reaches(tree)
    assert _reflection_reaches(tree), "the reflection must be caught"

    spelled = tmp_path / "rules_literal.py"
    spelled.write_text(
        "from homestead.keep.rungs import serve\n"
        "def anchor(record, surface):\n"
        "    serve(record, surface)\n"
        "    return record.payload\n"
    )
    literal = ast.parse(spelled.read_text("utf-8"))
    assert _calls_a_door(literal) and _payload_reaches(literal)


def test_a_non_serving_module_outside_app_may_still_reflect(tmp_path):
    """The other side of the rule, so it is a rule and not a blanket ban:
    `registry.py` reads an optional pack attribute with `getattr` and is not a
    surface — a module that never calls the gate is not reaching around one."""
    mod = tmp_path / "registry_like.py"
    mod.write_text(
        "def repeatable(pack):\n"
        '    return getattr(pack, "REPEATABLE", frozenset())\n'
    )
    assert not _calls_a_door(ast.parse(mod.read_text("utf-8")))
