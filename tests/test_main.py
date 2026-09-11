"""The entry point's argument handling — `--help` and the headless fallback.

`python -m homestead_law` with no recognized flag used to fall straight through
to `view.run()`, so a box with no tkinter (or no display) got a raw
`ModuleNotFoundError` / `TclError` traceback instead of a legible message. This
file locks in the fix: `--help` prints usage and exits 0 without ever touching
tkinter, and the default path degrades to a one-line message and a non-zero
exit rather than raising, when the window can't be opened.

`--smoke` is the other half: it is what CI runs against the *built artifact*, so
whatever it does not import cannot fail there.  It used to import `patterns`,
`registry`, `store`, the `app` package and the custody pack — and nothing from
the entry/UI layer, so a packaging break in `server`, `cli` or `intake` shipped
green.  The scan below reads the `--smoke` block out of `__main__.py` and holds
it against the package's own file list, and a second test plants an omission in
a copy to prove the scan fires.
"""
from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

from homestead_law import __main__ as entry

ENTRY = Path(entry.__file__).resolve()
PKG = ENTRY.parent

#: Not modules to import: the package's own `__init__`, and `__main__` itself —
#: the block cannot import the file it lives in.
NOT_IMPORTED = {"__init__", "__main__"}


def test_help_prints_usage_and_exits_zero_without_tkinter(capsys, monkeypatch):
    # If `--help` imported `homestead_law.app.view` (which imports tkinter
    # inside `run()`), this would blow up on a box with no tkinter — so guard
    # by making a tkinter import explode, and prove `--help` never gets there.
    monkeypatch.setitem(sys.modules, "tkinter", None)  # any import raises ImportError

    rc = entry.main(["--help"])

    assert rc == 0
    out = capsys.readouterr().out
    assert "usage" in out
    assert "--smoke" in out
    assert "--demo" in out
    assert "--help" in out

    # -h is the same door.
    rc = entry.main(["-h"])
    assert rc == 0


def test_missing_tkinter_returns_nonzero_with_guidance(capsys, monkeypatch):
    # Simulate a Python build with no tkinter: importing it raises
    # ModuleNotFoundError(name="tkinter"), exactly what happens on most of the
    # boxes this suite runs on.
    real_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "tkinter" or name.startswith("tkinter."):
            raise ModuleNotFoundError("No module named 'tkinter'", name="tkinter")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)

    rc = entry.main([])

    assert isinstance(rc, int)
    assert rc != 0
    err = capsys.readouterr().err
    assert "--demo" in err
    assert "--smoke" in err


def test_no_display_returns_nonzero_with_guidance(capsys, monkeypatch):
    # tkinter is importable, but opening a window fails the way it does on a
    # headless server/container: TclError "couldn't connect to display". Stub
    # tkinter itself so this doesn't require tkinter to actually be installed
    # (most boxes this suite runs on don't have it) — only that `__main__`
    # catches whatever class its own `import tkinter; tkinter.TclError` is.
    import types

    fake_tkinter = types.ModuleType("tkinter")

    class FakeTclError(Exception):
        pass

    fake_tkinter.TclError = FakeTclError
    monkeypatch.setitem(sys.modules, "tkinter", fake_tkinter)

    def fake_run() -> int:
        raise FakeTclError('couldn\'t connect to display ""')

    monkeypatch.setattr("homestead_law.app.view.run", fake_run)

    rc = entry.main([])

    assert isinstance(rc, int)
    assert rc != 0
    err = capsys.readouterr().err
    assert "--demo" in err
    assert "--smoke" in err


# ── `--smoke` imports every top-level module ────────────────────────────────


def _top_level_modules() -> set[str]:
    """Every top-level module in `homestead_law/` — the package's own file list,
    read live.  A module added tomorrow is in this set the moment it exists, so
    the scan below has nothing to keep in step with by hand."""
    return {p.stem for p in PKG.glob("*.py") if p.stem not in NOT_IMPORTED}


def _smoke_block(source: str) -> ast.If:
    """The `if "--smoke" in argv:` branch of `main()`, as an AST node."""
    tree = ast.parse(source)
    main_fn = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "main"
    )
    for node in ast.walk(main_fn):
        if isinstance(node, ast.If) and any(
            isinstance(c, ast.Constant) and c.value == "--smoke"
            for c in ast.walk(node.test)
        ):
            return node
    raise AssertionError("main() has no `--smoke` branch to scan")


def _smoke_imports(source: str) -> set[str]:
    """The top-level `homestead_law` modules the `--smoke` branch imports.

    `from homestead_law import cli, server` contributes `cli` and `server`;
    `from homestead_law.app import view` contributes nothing (it is not a
    top-level module), and neither does `import homestead_law.app.window`.
    """
    names: set[str] = set()
    for node in ast.walk(_smoke_block(source)):
        if isinstance(node, ast.ImportFrom) and node.module == "homestead_law":
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                head, _, rest = alias.name.partition(".")
                if head == "homestead_law" and rest and "." not in rest:
                    names.add(rest)
    return names


def _missing(source: str) -> set[str]:
    """Which top-level modules the `--smoke` block leaves out."""
    return _top_level_modules() - _smoke_imports(source)


def test_smoke_imports_every_top_level_module():
    """`--smoke` is the packaging check CI runs against the built wheel, so a
    module it does not import is a module whose packaging is not checked.  The
    entry and UI layer — `server`, `cli`, `intake` — was exactly that: importable
    only from a real run, so a missing dependency or a bad relative import in it
    reached a household before it reached CI."""
    missing = _missing(ENTRY.read_text("utf-8"))
    assert not missing, (
        f"--smoke does not import {sorted(missing)}. Every top-level module in "
        "homestead_law/ belongs in that block; what it skips, CI does not check."
    )


def test_the_smoke_import_scan_catches_a_planted_omission(tmp_path):
    """A scan that has never fired has not been shown to check anything.  Plant
    the omission the real bug had — `server` dropped from the block — in a copy
    of `__main__.py`, and the scan must name it."""
    planted = ENTRY.read_text("utf-8").replace("\n            server,", "", 1)
    assert planted != ENTRY.read_text("utf-8"), "the plant did not change the source"
    copy = tmp_path / "__main__.py"
    copy.write_text(planted, "utf-8")

    missing = _missing(copy.read_text("utf-8"))

    assert "server" in missing, (
        "the scan did not notice `server` missing from the --smoke block — it "
        "is passing because the tree happens to be complete, not because it checks."
    )


def test_smoke_runs_green_as_a_subprocess(tmp_path):
    """End to end, in a fresh interpreter — the shape CI runs.  An import error
    in any of the modules the block now names fails here rather than on a
    household's machine."""
    env = dict(os.environ, HOMESTEAD_HOME=str(tmp_path))
    result = subprocess.run(
        [sys.executable, "-m", "homestead_law", "--smoke"],
        capture_output=True, text=True, env=env,
    )
    assert result.returncode == 0, result.stderr
    assert "smoke ok" in result.stdout
