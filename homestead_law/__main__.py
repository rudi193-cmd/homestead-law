"""homestead-law's entry point.

**I-21: no auto-render on start.** The resting state is the cover; `view.run`
opens on it and draws the list only when the operator opens a matter.

**I-29: the surface holds no domain logic.** The entry point routes to `view`,
which composes through `Window` over the SQLite store and calculates nothing.

Four ways in, plus `--help`:
  * `--help` / `-h` — print this usage and exit 0. Never opens a window.
  * `--smoke` — start, prove every import survived packaging, exit without a
    display. What CI runs against the built artifact.
  * `--demo` — seed a synthetic custody matter into a throwaway store and print
    the list and a detail, composed through the gate. The pipeline, headless, on
    SQLite.
  * a CLI command (put, deadline, show, queue, ui; and with the `entity`
    extra, resolve, propose, orders, verify) — real work on real data in the
    household root, not a throwaway. Entering and reading records needs only
    the engine; the Nestor-backed commands say so when the extra is missing.
  * default — open the tkinter view on the cover. On a box with no tkinter or
    no display, this fails legibly: a one-line message pointing at `--demo` and
    `--smoke`, and a non-zero exit — never a raw `ModuleNotFoundError` or
    `TclError` traceback.
"""
from __future__ import annotations

import sys

USAGE = """\
usage: python -m homestead_law [--help] [--smoke | --demo]
       homestead-law <command> [args...]

  --help, -h   show this message and exit
  --smoke      prove every import survived packaging; exit without a display
  --demo       seed a synthetic custody matter and print it, headless
  (default)    open the tkinter view on the cover

commands (real data, in the household root — $HOMESTEAD_HOME or ~/.homestead):
  put          put <matter> <field> <value> [--id inst] [--sub sub] — store a record
  deadline     deadline <matter> <id> <date> [--rung L1|L3|L4] [--sub sub] [instruction]
  show         show [matter] [item [id]] [--id inst] [--sub sub] — read records back, through the gate
  matter       matter open <matter> --id inst --jurisdiction code [--replace] — open an instance
  queue        queue [--today YYYY-MM-DD] — what's due
  ui           ui [--port N] — entry forms, intake and dashboard in the browser

  an id (--id/--sub, or matter open's --id) is a label, never a name: it is
  operator-chosen and may appear in logs by reference, but it is never itself
  the content a rung protects (I-15).

commands that need the `entity` extra (pip install 'homestead-law[entity]'):
  resolve      resolve <domain> <surface> — entity resolution
  propose      propose <domain> <surface> <canonical> — propose an alias
  orders       orders <propose|check|list> — court decisions
  verify       verify — check the Nestor ledger chain
"""

_CLI_COMMANDS = {
    "resolve", "propose", "orders", "put", "deadline", "show", "matter",
    "queue", "verify", "ui",
}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv

    if "--help" in argv or "-h" in argv:
        print(USAGE, end="")
        return 0

    if "--smoke" in argv:
        # Every top-level module in the package, not a hand-picked few: this is
        # what CI runs against the built artifact, and a packaging break in the
        # entry/UI layer (`server`, `cli`, `intake`) used to ship green because
        # nothing here imported it. `tests/test_main.py` scans this block
        # against the package's own file list, so a module added later cannot
        # quietly stay out of it.
        from homestead_law import (  # noqa: F401
            cli,
            instances,
            intake,
            jurisdiction,
            nestor_seam,
            nestor_store,
            patterns,
            queue,
            registry,
            server,
            store,
        )
        from homestead_law.app import advisories, cover, demo, view, window  # noqa: F401
        from homestead_law.packs import custody  # noqa: F401
        print("homestead-law: smoke ok")
        return 0

    if "--demo" in argv:
        import os
        import tempfile

        from homestead_law.app import demo
        from homestead_law.store import Sidecar

        with tempfile.TemporaryDirectory(prefix="homestead-law-demo-") as tmp:
            os.environ["HOMESTEAD_HOME"] = tmp
            store = Sidecar()
            print(demo.compose_demo(store))
            print()
            print(demo.compose_queue(store))
        return 0

    # CLI commands — real work on real data, through Nestor.
    if argv and argv[0] in _CLI_COMMANDS:
        from homestead_law.cli import run_cli
        return run_cli(argv)

    from homestead_law.app import view

    try:
        import tkinter
    except ModuleNotFoundError as exc:
        if exc.name not in ("tkinter", "_tkinter"):
            raise
        print(
            "homestead-law: tkinter is not available on this interpreter — "
            "try `--demo` (headless pipeline) or `--smoke` (import check) instead.",
            file=sys.stderr,
        )
        return 1

    try:
        return view.run()
    except tkinter.TclError:
        print(
            "homestead-law: no display available to open the window — "
            "try `--demo` (headless pipeline) or `--smoke` (import check) instead.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
