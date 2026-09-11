"""X7-drift-law — the meta-scan: every AST/grep-guard helper this suite
carries has been shown to catch something, by a test that *calls it*.

*A scan that has never fired has not been shown to check anything* is the
repo's own rule (`tests/test_i44_no_drafting.py`'s own docstring cites it,
and every `_offenders`/`_reaches`/`_hits` helper here follows it). This file
is that rule turned into a test that reads the *other* files in `tests/`: it
finds every module-level helper shaped like a violation-scanner and asserts
that some planted-violation test runs it — directly, or through another
helper it calls, in its own file or in a file that imported it.

The rule below is the one the engine's, health's and the ledger's own X7
sweeps settled on; this file carries it rather than a narrower variant of it,
for the same "one definition, not two that can drift apart" reason
`tests/_strikethrough.py`'s docstring gives.

**Discovery is structural, not a naming convention.** A first cut of this
kind of file looked for helpers whose *name* carried one of the repo's own
stems (`_payload_reaches`, `_banned_phrase_hits`) or required a leading
underscore. Both restrictions missed real scans: a public
`check_payload_reach(...)` that walks `ast` (missed on the underscore rule —
and its name carries `check`, which no stem list held either), and a
grep-shaped `forbidden_word_hits(path)` that reads a file and asks
`"payload" in text` with no `ast` and no matching stem at all. So the rule is
what a scan *does*:

* it parses or walks source (`ast.parse`, `ast.walk`), **or**
* it matches text with a pattern (`re.search`/`findall`/`finditer`/`match`/
  `fullmatch`/`compile`, or a method of a name this module can see was bound
  by `re.compile` — which is how `_strikethrough.live`'s `_STRUCK.sub(...)`
  is counted), **or**
* it reads a file's text (`.read_text()`/`.read_bytes()`) *and* asks a
  membership question of it (`x in text`, `x not in parts`) — the grep shape
  with no regex in it, which `tests/test_docs_drift.py::_contains` is.

The name stems and the `_is_` prefix are kept on top of that, not instead of
it: they still catch helpers that hand their work to a caller without
themselves matching a pattern (`test_registry.py::_is_pack` is one).
Discovery is a union, so it is strictly wider than either half alone.

**Having a plant means a plant test calls the scan.** A cut that reads names
and docstrings only lets a test called `test_the_guard_fires` that never
touches the guard clear the whole file. A helper counts as planted only when
a plant test *reaches* it — through the module's own helpers, and through an
import, so a plant that calls a wrapper has exercised the helper underneath
it too.

**Two corrections this repo's own audit made (2026-09-11), both kept:**

* *The sweep reads `tests/*.py`, not `tests/test_*.py`.* An earlier cut
  globbed test files only, so `tests/_strikethrough.py::live` — a real
  `re`-driven scan, imported by `test_docs_drift.py` and
  `test_plan_affairs_face.py` — sat outside the sweep entirely. Reach is
  cross-module for the same reason: a helper that lives in one file and is
  planted from another is planted.
* *A plant is a test that plants, not a test that says "plant".* An earlier
  cut counted a test as a plant if the word appeared in its **docstring**,
  which let `test_no_module_outside_the_packs_keeps_a_derived_form_table` —
  whose docstring merely explains the plant rule — clear `_is_pack`, a
  helper no plant had ever run. The marker is now read off the test's
  *name*, or off the literal word `planted` in its body (this repo's other
  convention, the local variable a test composes its violation into).

**Honest about what it still cannot see.** A helper that reaches `ast.parse`
through an alias (`from ast import parse as p`), one that shells out to
`grep`, or one whose whole check is a comparison of two already-read strings
with no membership test and no pattern, is outside the rule above. Closing
those needs an interpreter, not a reader. Scans written inline in a test body
rather than as a helper are invisible to it too — a test is its own only
caller, so "does a plant call it" has no answer; the remedy, used twice by
this bite's audit (`test_plan_period.py`'s `SIGNAL_FIELDS` layout guard and
`test_server.py`'s Accept structural check), is to factor the scan into a
helper, which puts it in this sweep, and plant it.
"""
from __future__ import annotations

import ast
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent

#: This file, excluded from its own sweep — its own helpers are proven by the
#: planted fixtures below, run against synthetic files rather than against
#: itself, so a passing sweep can never mean "this file plants nothing and
#: also declines to check that."
SELF = Path(__file__).resolve()

#: Word-stems the repo's own scan helpers already use, split on "_" so
#: `_payload_reaches` (reaches is the *last* word) and
#: `_banned_phrase_hits` (hits is the *last* word) both match without
#: over-firing on unrelated names.
_NAME_TOKENS = frozenset(
    {"scan", "scans", "reads", "calls", "offenders", "uses", "check", "checks",
     "guard", "guards", "reaches", "hits"}
)

#: The repo's own naming convention for a planted-violation test, read off
#: the tests that already exist rather than guessed — `plant`/`planted`,
#: `fires`, `catches`, and `regression`, this project's word for "the exact
#: bug, replayed". Checked against the test *name*; the literal word
#: `planted` appearing in the test's own body is the second, independent way
#: a test qualifies (the shape where the violation is composed into a local
#: called `planted` and the test's name says something else).
_NAME_MARKERS = ("plant", "fires", "catches", "regression")

#: Pattern-matching functions of `re`.
_MATCH_CALLS = frozenset(
    {"search", "findall", "finditer", "match", "fullmatch", "compile"}
)

#: Reading a repo file's text. The grep half of a grep-shaped scan.
_TEXT_READS = frozenset({"read_text", "read_bytes"})


def _calls_in(node: ast.AST):
    """Every `Call` anywhere inside `node`."""
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            yield sub


def _compiled_pattern_names(node: ast.AST) -> set[str]:
    """Names bound to `re.compile(...)` anywhere under `node` — module-level
    constants (`_STRUCK`, `_PINNED_COUNT_RE`, `_CODE_SPAN_MODULE`) and locals
    alike. Knowing them is what lets a compiled pattern's `.sub(...)` count
    as pattern matching without counting every `str.split` in the suite."""
    names: set[str] = set()
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Assign):
            continue
        value = sub.value
        if (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Attribute)
            and value.func.attr == "compile"
            and isinstance(value.func.value, ast.Name)
            and value.func.value.id == "re"
        ):
            names |= {t.id for t in sub.targets if isinstance(t, ast.Name)}
    return names


def _scan_kinds(node: ast.FunctionDef, compiled: set[str]) -> list[str]:
    """Why this function is a scan, or `[]` if it is not — the three shapes
    every guard in this suite takes, plus the two name conventions kept on
    top of them."""
    walks = matches = reads = membership = False
    for sub in ast.walk(node):
        if isinstance(sub, ast.Compare) and any(
            isinstance(op, (ast.In, ast.NotIn)) for op in sub.ops
        ):
            membership = True
        if not isinstance(sub, ast.Call):
            continue
        func = sub.func
        if isinstance(func, ast.Attribute):
            receiver = func.value.id if isinstance(func.value, ast.Name) else None
            if func.attr in ("parse", "walk") and receiver == "ast":
                walks = True
            if func.attr in _MATCH_CALLS and receiver == "re":
                matches = True
            if receiver is not None and receiver in compiled:
                matches = True
            if func.attr in _TEXT_READS:
                reads = True
        elif isinstance(func, ast.Name) and func.id == "compile":
            matches = True

    kinds: list[str] = []
    if walks:
        kinds.append("walks source")
    if matches:
        kinds.append("matches a pattern")
    if reads and membership:
        kinds.append("reads text and asks membership")
    name = node.name
    if name.startswith("_is_"):
        kinds.append("named `_is_…`")
    tokens = _NAME_TOKENS & set(name.strip("_").split("_"))
    if tokens:
        kinds.append(f"name stem {sorted(tokens)}")
    return kinds


def _is_fixture(node: ast.FunctionDef) -> bool:
    """`@pytest.fixture` — setup, not a scan, whatever it reads."""
    return any("fixture" in ast.dump(dec) for dec in node.decorator_list)


def _module_facts(path: Path) -> dict:
    """Everything one file in `tests/` contributes to the sweep: its
    module-level functions, which of them are scans, which of its tests are
    plants, and what it imported from its neighbours."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    compiled = _compiled_pattern_names(tree)
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    scans: dict[str, list[str]] = {}
    plants: list[str] = []
    for name, node in functions.items():
        if name.startswith("test_"):
            body = ast.get_source_segment(source, node) or ""
            if any(m in name for m in _NAME_MARKERS) or "planted" in body.lower():
                plants.append(name)
            continue
        if name.startswith("__") or _is_fixture(node):
            continue
        kinds = _scan_kinds(node, compiled | _compiled_pattern_names(node))
        if kinds:
            scans[name] = kinds

    imported: dict[str, tuple[str, str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            # `from _strikethrough import live` and `from tests.x import y`
            # both resolve to the neighbouring file's stem.
            origin = node.module.split(".")[-1]
            for alias in node.names:
                imported[alias.asname or alias.name] = (origin, alias.name)

    return {
        "path": path,
        "functions": functions,
        "scans": scans,
        "plants": plants,
        "imported": imported,
    }


def _called_names(node: ast.AST) -> set[str]:
    """Every name this function calls, by its last segment — `helper()` and
    `module.helper()` both count, which is what lets a plant reach a helper
    it imported under its own name."""
    called: set[str] = set()
    for call in _calls_in(node):
        func = call.func
        if isinstance(func, ast.Name):
            called.add(func.id)
        elif isinstance(func, ast.Attribute):
            called.add(func.attr)
    return called


def _planted_scans(facts: dict[str, dict]) -> set[tuple[str, str]]:
    """`{(module stem, helper name)}` reachable from some plant test by
    calls — the whole point. A plant that never calls the scan is a word in a
    name, not evidence."""
    reached: set[tuple[str, str]] = set()
    frontier = [(stem, plant) for stem, mod in facts.items() for plant in mod["plants"]]
    while frontier:
        stem, name = frontier.pop()
        if (stem, name) in reached:
            continue
        reached.add((stem, name))
        mod = facts.get(stem)
        if mod is None or name not in mod["functions"]:
            continue
        for called in _called_names(mod["functions"][name]):
            if called in mod["functions"]:
                frontier.append((stem, called))
            elif called in mod["imported"]:
                origin, original = mod["imported"][called]
                if origin in facts:
                    frontier.append((origin, original))
    return reached


def unplanted_scans(paths: list[Path]) -> dict[str, list[str]]:
    """`{"<file>::<helper>": [why it is a scan]}` for every scan no plant
    test reaches. Keyed by `.name`, never a full path — these are
    single-segment file names, so no Windows/posix separator can get into a
    key or a message."""
    facts = {p.stem: _module_facts(p) for p in paths if p.resolve() != SELF}
    planted = _planted_scans(facts)
    return {
        f"{mod['path'].name}::{name}": kinds
        for stem, mod in facts.items()
        for name, kinds in mod["scans"].items()
        if (stem, name) not in planted
    }


def test_every_scan_in_tests_has_a_planted_violation_test():
    """The house rule, run for real: no file in `tests/` may carry a helper
    that walks a source tree, matches text with a pattern, reads a file and
    asks a membership question of it, or is named like one of this repo's own
    guards, without a planted-violation test that actually *calls* it."""
    offenders = unplanted_scans(sorted(TESTS_DIR.glob("*.py")))
    assert not offenders, (
        f"these scans are never run against a violation: {offenders}. Add a "
        f"test that calls the scan on a planted violation — name it with one "
        f"of {_NAME_MARKERS}, or call the composed value 'planted' (this "
        "repo's two conventions). A scan that has never fired has not been "
        "shown to check anything."
    )


# ── the discovery half, planted three ways ───────────────────────────────────


def _write(tmp_path: Path, name: str, *lines: str) -> Path:
    """A fake tests module on disk, read back the way `unplanted_scans()`
    reads a real one."""
    path = tmp_path / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_the_meta_scan_fires_on_an_ast_scan_under_a_public_name(tmp_path):
    """Plant 1 of 3 — the AST shape, deliberately named *without* a leading
    underscore. An earlier cut swept `_`-prefixed helpers by habit;
    `_strikethrough.live` is a real scan in this repo with a public name, so
    a public name must not be a way out."""
    planted = _write(
        tmp_path,
        "test_fake_public_ast_scan.py",
        "import ast",
        "",
        "def check_payload_reach(source):",
        "    return [n for n in ast.walk(ast.parse(source))",
        "            if isinstance(n, ast.Attribute) and n.attr == 'payload']",
        "",
        "def test_nothing_reaches_a_payload():",
        "    assert not check_payload_reach('x = 1')",
    )
    assert unplanted_scans([planted]) == {
        "test_fake_public_ast_scan.py::check_payload_reach": [
            "walks source", "name stem ['check']"
        ]
    }


def test_the_meta_scan_fires_on_a_grep_shaped_scan(tmp_path):
    """Plant 2 of 3 — the shape an AST-only discovery could not see at all: a
    guard that greps. `test_docs_drift.py::_contains` is the real one (no
    `re` in it whatever), and `_strikethrough.live` is the compiled-pattern
    one; both shapes are here in miniature, and neither name carries a
    stem."""
    planted = _write(
        tmp_path,
        "test_fake_grep_scan.py",
        "import re",
        "from pathlib import Path",
        "",
        "_BANNED = re.compile(r'TODO')",
        "",
        "def banned_words_in(path):",
        "    return _BANNED.findall(Path(path).read_text('utf-8'))",
        "",
        "def sentence_is_still_claimed(path):",
        "    return 'the old claim' in Path(path).read_text('utf-8')",
        "",
        "def test_no_banned_words(tmp_path):",
        "    assert not banned_words_in(tmp_path / 'x.txt')",
    )
    assert unplanted_scans([planted]) == {
        "test_fake_grep_scan.py::banned_words_in": ["matches a pattern"],
        "test_fake_grep_scan.py::sentence_is_still_claimed": [
            "reads text and asks membership"
        ],
    }


def test_the_meta_scan_fires_on_a_plant_that_only_names_itself_one(tmp_path):
    """Plant 3 of 3, and the hole this file exists to close: a file whose
    plant-named test does not *call* the scan. Under a cut that asked only
    "does this file contain a test named for the convention", this passed."""
    planted = _write(
        tmp_path,
        "test_fake_name_only_plant.py",
        "import ast",
        "",
        "def _reflection_reaches(tree):",
        "    return [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call)]",
        "",
        "def _something_else(value):",
        "    return value * 2",
        "",
        "def test_the_guard_fires_on_a_violation():",
        "    assert _something_else(1) == 2",
    )
    assert unplanted_scans([planted]) == {
        "test_fake_name_only_plant.py::_reflection_reaches": [
            "walks source", "name stem ['reaches']"
        ]
    }


# ── the controls: a meta-scan that called everything guilty is an opinion ────


def test_the_meta_scan_clears_a_plant_that_reaches_the_scan_through_a_wrapper(tmp_path):
    """Negative control 1. The identical helper, this time reached by a test
    named for the convention through a wrapper, must NOT be flagged —
    transitivity is the property, and a sweep that flagged this would be
    unusable."""
    clean = _write(
        tmp_path,
        "test_fake_fired_scan.py",
        "import ast",
        "",
        "def _reflection_reaches(tree):",
        "    return [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call)]",
        "",
        "def _offenders(source):",
        "    return _reflection_reaches(ast.parse(source))",
        "",
        "def test_the_guard_fires_on_a_planted_call():",
        "    assert _offenders('f()')",
    )
    assert unplanted_scans([clean]) == {}


def test_the_meta_scan_clears_a_fixture_and_an_unnamed_plant(tmp_path):
    """Negative control 2, two ways at once. A `@pytest.fixture` that parses
    a tree is scaffolding, not a guard, and must not be swept; and a test
    with no marker word in its *name* still counts as a plant if it composes
    the violation into a local called `planted` — this repo's other
    convention, and the one the CI lesson about CodeQL made universal."""
    clean = _write(
        tmp_path,
        "test_fake_fixture_and_unnamed_plant.py",
        "import ast",
        "import pytest",
        "",
        "@pytest.fixture",
        "def parsed():",
        "    return ast.parse('x = 1')",
        "",
        "def _constants(tree):",
        "    return [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Constant)]",
        "",
        "def test_nothing_is_hardcoded(parsed):",
        "    assert not _constants(ast.parse('pass'))",
        "    planted = ast.parse('x = 1')",
        "    assert _constants(planted)",
    )
    assert unplanted_scans([clean]) == {}


# ── the two corrections this repo's own audit made, each planted ─────────────


def test_a_helper_planted_from_another_file_is_not_reported(tmp_path):
    """The cross-module half, planted. `tests/_strikethrough.py::live` is a
    real scan with no test of its own in its own file — every plant that
    runs it lives in `test_docs_drift.py` and `test_plan_affairs_face.py`.
    A same-file-only sweep reports it forever and can never be satisfied
    except by moving the plant next to the helper, which is the opposite of
    sharing one definition."""
    helper = _write(
        tmp_path,
        "_fake_shared.py",
        "import re",
        "",
        "_STRUCK = re.compile(r'~~.*?~~')",
        "",
        "def live(text):",
        "    return _STRUCK.sub('', text)",
    )
    caller = _write(
        tmp_path,
        "test_fake_importer.py",
        "from _fake_shared import live",
        "",
        "def test_the_reader_fires_on_a_planted_strike():",
        "    assert live('a ~~b~~ c') == 'a  c'",
    )
    assert unplanted_scans([helper, caller]) == {}
    # and with the plant gone, the shared helper is reported again — the
    # sweep clears it because it was *reached*, not because it was imported.
    lonely = _write(
        tmp_path,
        "test_fake_no_plant.py",
        "from _fake_shared import live",
        "",
        "def test_it_renders():",
        "    assert live('a') == 'a'",
    )
    assert unplanted_scans([helper, lonely]) == {
        "_fake_shared.py::live": ["matches a pattern"]
    }


def test_a_docstring_that_merely_says_plant_does_not_clear_a_scan(tmp_path):
    """The second correction, planted. An earlier cut read the plant marker
    off the test's *docstring*, so a test whose prose explains the plant rule
    — `test_registry.py::test_no_module_outside_the_packs_keeps_a_derived_
    form_table` is the real one — silently cleared every helper it called,
    including `_is_pack`, which no plant had ever run."""
    planted = _write(
        tmp_path,
        "test_fake_docstring_plant.py",
        "from pathlib import Path",
        "",
        "def _is_exempt(path):",
        "    return 'packs' in Path(path).parts",
        "",
        "def test_no_module_hardcodes_the_list():",
        '    """A scan with no plant has not been shown to check anything."""',
        "    assert not _is_exempt('homestead_law/store.py')",
    )
    assert unplanted_scans([planted]) == {
        "test_fake_docstring_plant.py::_is_exempt": ["named `_is_…`"]
    }


def test_the_sweep_does_not_fire_on_a_real_guarded_file():
    """The whole thing against a real file of this repo's:
    `tests/test_i44_no_drafting.py` defines several scan helpers and plants
    each one, so the sweep must clear it — or it would be crying wolf on the
    very files it exists to clear."""
    path = TESTS_DIR / "test_i44_no_drafting.py"
    facts = {path.stem: _module_facts(path)}
    assert facts[path.stem]["scans"], "test_i44_no_drafting.py defines scan helpers"
    assert unplanted_scans([path]) == {}
