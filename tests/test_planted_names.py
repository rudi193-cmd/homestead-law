"""A planted marker is called `planted`, never `secret`/`password`/`token`/`ssn`.

X7-drift-law audit, 2026-09-11. **CodeQL runs on every PR in this repo's CI
matrix and blocks merge on a new high alert.** Its sensitive-data heuristic
keys on the *name a value is bound to* — a variable, a constant or a
parameter — not on what the value actually is. So a test that plants a
marker and calls it `ssn` teaches CodeQL that the string is an SSN; the taint
then spreads to every element of any collection the value rides in, and the
first `print`/log of anything downstream is reported as clear-text logging of
sensitive data. Nothing is wrong with the test; the build stops anyway, and
the fix is a rename nobody can find from the alert text.

This repo has now paid that twice — `tests/test_panes.py` and
`tests/test_server.py`'s `ssn = "123-45-6789"` locals (renamed by this bite's
builder) and `tests/test_window.py`'s module-level `SSN` constant riding in
the `MATTER` list (renamed by its audit, the shape the CI lesson describes
exactly). A scan is cheaper than a third round trip through CI, so the rule
is held here instead of remembered.

**Scope: `tests/` only, and binding sites only.**

* *`tests/` only*, because the package's own `token` is not a marker: it is
  the named parameter of `rules.accept(store, computed, *, token=...)` and
  the field `server.py` reads off the Accept request — the preview token that
  is this app's public API for "the operator accepted what they were shown".
  Renaming it to satisfy a heuristic would make the API worse to hide a
  false positive, and CodeQL has not in fact flagged it (it is compared, not
  logged: `rules.StaleToken` names matter/instance/template and no token).
* *Binding sites only* — assignment targets, `for` targets, `with ... as`,
  and function parameters. A string literal that happens to be a field name
  (`store.put(matter, "ssn", ...)`, `bankruptcy.FIELDS["ssn"]`) is the real
  schema this app declares, is what the L5 assertions check by name, and is
  not what the heuristic keys on.
"""
from __future__ import annotations

import ast
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent

#: The four names the CI lesson names, lowercased for comparison so `SSN`,
#: `Secret` and `ssn` are one rule and not three.
SENSITIVE_NAMES = frozenset({"secret", "password", "token", "ssn"})


def _bound_names(node: ast.AST) -> list[str]:
    """Every name this node *binds* — the sites CodeQL reads a value's
    meaning from. Not every name it mentions: a comparison against `token`
    or a subscript by `"ssn"` binds nothing and teaches the heuristic
    nothing."""
    names: list[str] = []
    if isinstance(node, ast.Assign):
        for target in node.targets:
            names += [n.id for n in ast.walk(target) if isinstance(n, ast.Name)]
    elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
        if isinstance(node.target, ast.Name):
            names.append(node.target.id)
    elif isinstance(node, (ast.For, ast.AsyncFor)):
        names += [n.id for n in ast.walk(node.target) if isinstance(n, ast.Name)]
    elif isinstance(node, ast.withitem) and node.optional_vars is not None:
        names += [
            n.id for n in ast.walk(node.optional_vars) if isinstance(n, ast.Name)
        ]
    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        args = node.args
        every = (
            args.posonlyargs + args.args + args.kwonlyargs
            + ([args.vararg] if args.vararg else [])
            + ([args.kwarg] if args.kwarg else [])
        )
        names += [a.arg for a in every]
    return names


def sensitive_bindings(source: str, where: str) -> list[str]:
    """`["<where>:<line> <name>"]` for every binding in `source` whose name is
    one CodeQL reads as sensitive data.

    `where` is a caller-supplied label, never a path this function builds:
    keys stay single-segment so no separator — posix or Windows — can reach a
    message this scan prints (the CI matrix runs Windows too)."""
    offenders: list[str] = []
    for node in ast.walk(ast.parse(source)):
        # `ast.withitem` carries no position of its own; its `optional_vars`
        # (the `as` target) does, and that is the binding being reported.
        lineno = getattr(node, "lineno", None)
        if lineno is None and isinstance(node, ast.withitem):
            lineno = getattr(node.optional_vars, "lineno", 0)
        for name in _bound_names(node):
            if name.lower() in SENSITIVE_NAMES:
                offenders.append(f"{where}:{lineno or 0} {name}")
    return sorted(offenders)


def _offenders_in_the_test_tree() -> list[str]:
    offenders: list[str] = []
    for path in sorted(TESTS_DIR.glob("*.py")):
        offenders += sensitive_bindings(path.read_text("utf-8"), path.name)
    return offenders


def test_no_test_binds_a_value_to_a_name_codeql_reads_as_sensitive():
    """The rule, run for real over `tests/`."""
    offenders = _offenders_in_the_test_tree()
    assert not offenders, (
        f"these test bindings use a name CodeQL's sensitive-data heuristic "
        f"keys on ({sorted(SENSITIVE_NAMES)}): {offenders}. Call a planted "
        "marker `planted` (or `planted_l5`, `planted_diagnosis`, …): the "
        "heuristic taints every element of any collection the value rides "
        "in and reports the first print downstream as clear-text logging, "
        "which is a new high alert and blocks the merge."
    )


def test_the_scan_fires_on_each_planted_binding_shape():
    """A scan that has never fired has not been shown to check anything.
    Every binding shape planted at once — a module constant, a local, an
    annotated assignment, a `for` target, a `with ... as`, a tuple unpack and
    a function parameter — because the one that matters is whichever one the
    next test happens to use."""
    planted = (
        "SSN = '123-45-6789'\n"
        "def leak(token):\n"
        "    secret = 1\n"
        "    password: str = 'x'\n"
        "    for ssn in ['a']:\n"
        "        pass\n"
        "    with open('f') as Secret:\n"
        "        pass\n"
        "    a, token = 1, 2\n"
    )
    offenders = sensitive_bindings(planted, "planted.py")
    found = {line.split(" ", 1)[1] for line in offenders}
    assert found == {"SSN", "token", "secret", "password", "ssn", "Secret"}, offenders


def test_the_scan_does_not_fire_on_a_field_name_or_a_comparison():
    """The negative control, and the reason the scan reads bindings only: the
    `"ssn"` *field* the bankruptcy pack really declares is what the L5 tests
    assert by name, and a value merely compared against must not be swept
    either — a scan that banned the word outright would ban the schema."""
    innocent = (
        "def test_it(store):\n"
        "    store.put('bankruptcy', 'ssn', 'primary', planted_l5)\n"
        "    assert rows['ssn'] is None\n"
        "    assert data['token'] != other\n"
        "    planted = '123-45-6789'\n"
        "    assert planted not in page\n"
    )
    assert sensitive_bindings(innocent, "innocent.py") == []
