"""Entering and reading records needs only the engine — never the `entity` extra.

`tests/test_cli.py` skips wholesale when `nestor-meaning` is not installed, which
left the household's own commands — `put`, `deadline`, `show`, `queue` — untested
on exactly the checkout most households have. This file poisons the `nestor`
import so it runs the *absent* branch on every checkout, installed or not:

* the seam's `bind()` degrades to `None` and binds nothing (its docstring's
  promise, now held);
* every record command works end to end without it; and
* every Nestor-backed command refuses in one line naming the extra, exit 1,
  rather than a traceback.
"""
from __future__ import annotations

import sys

import pytest

from homestead_law import nestor_seam
from homestead_law.cli import run_cli


@pytest.fixture(autouse=True)
def _no_nestor(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    # `None` in sys.modules makes `import nestor` raise ImportError and makes
    # `importlib.util.find_spec("nestor")` return None — the extra is absent.
    monkeypatch.setitem(sys.modules, "nestor", None)
    monkeypatch.setattr(nestor_seam, "_bound", False)
    monkeypatch.setattr(nestor_seam, "_ledger_path", None)
    yield


def test_available_is_false_and_bind_degrades_to_nothing_bound(tmp_path):
    assert nestor_seam.available() is False
    assert nestor_seam.bind(tmp_path) is None
    with pytest.raises(nestor_seam.SeamNotBoundError):
        nestor_seam.resolver_for("party", object())


def test_put_stores_without_nestor(capsys):
    assert run_cli(["put", "custody", "courthouse", "Dept 4"]) == 0
    out = capsys.readouterr().out
    assert "stored: custody/courthouse/primary" in out and "L1" in out


def test_put_uses_the_packs_derived_form(capsys):
    """Decision 3: the derived sentence `show` lists for an L3/L4 field is the
    pack's own `SCHEMA[field]["derived"]`, read through `derived_of` — not a
    second table the CLI used to keep (`_default_derived`, deleted by this
    bite). Held by comparison to the pack, not by retyping the sentence, so a
    future edit to the pack is what this test tracks."""
    from homestead.keep.rungs import derived_of
    from homestead_law.packs import custody

    assert run_cli(["put", "custody", "child_name", "X"]) == 0
    capsys.readouterr()

    assert run_cli(["show", "custody"]) == 0
    out = capsys.readouterr().out
    sentence = derived_of(custody.SCHEMA, "child_name")
    assert sentence in out
    assert "X" not in out, "the L4 payload must not appear on the list, only its derived form"


def test_the_packs_derived_form_is_what_the_gate_substitutes(capsys):
    """Decision 3, checked at the gate rather than at the print. What `put`
    stores must be the `Classified` the engine's own ceilings then act on: an
    `L3` payload still *renders* on the operator's own list (the derived form
    is not a second, quieter rendering of the record they are entitled to see),
    the same record derives to the pack's exact sentence on an `S2` prompt, and
    the payload never crosses there. `L4` is the pair the other way round —
    derived on the list, rendered in the detail the operator opened on purpose
    — and `L5` crosses nowhere. Read straight off `serve()` so this is the
    crossing, not the CLI's formatting of it."""
    from homestead.keep.rungs import Disposition, Surface, derived_of, serve

    from homestead_law.packs import custody
    from homestead_law.store import Sidecar

    assert run_cli(["put", "custody", "case_number", "FL-2026-00777"]) == 0
    assert run_cli(["put", "custody", "notes", "smelled of alcohol on the 3rd"]) == 0
    assert run_cli(["put", "custody", "ssn", "123-45-6789"]) == 0
    capsys.readouterr()

    stored = dict(Sidecar().records("custody"))
    l3 = stored[("custody", "case_number", "primary")]
    l4 = stored[("custody", "notes", "primary")]
    l5 = stored[("custody", "ssn", "primary")]

    # the L3 payload renders on the operator's own list; the pack's sentence is
    # what an S2 prompt gets instead, and the payload does not reach it
    listed = serve(l3, Surface.S1_LIST)
    assert listed.disposition is Disposition.RENDER
    assert listed.value == "FL-2026-00777"
    prompted = serve(l3, Surface.S2_PROMPT)
    assert prompted.disposition is Disposition.DERIVE
    assert prompted.value == derived_of(custody.SCHEMA, "case_number")
    assert "FL-2026-00777" not in str(prompted.value)

    # L4: the pack's sentence on the list, the payload only in the detail
    assert serve(l4, Surface.S1_LIST).value == derived_of(custody.SCHEMA, "notes")
    assert serve(l4, Surface.S1_DETAIL).value == "smelled of alcohol on the 3rd"
    assert serve(l4, Surface.S2_PROMPT).value == derived_of(custody.SCHEMA, "notes")

    # L5 declares no derived form and crosses nowhere — not even as a stand-in
    assert derived_of(custody.SCHEMA, "ssn") is None
    for surface in (Surface.S1_LIST, Surface.S1_DETAIL, Surface.S2_PROMPT):
        served = serve(l5, surface)
        assert served.disposition is not Disposition.RENDER
        assert served.value is None or "123-45-6789" not in str(served.value)


def test_put_a_party_name_stores_and_skips_the_resolver_quietly(capsys):
    assert run_cli(["put", "custody", "opposing_party", "Jordan Rivera"]) == 0
    captured = capsys.readouterr()
    assert "stored" in captured.out
    assert "proposed" not in captured.out
    assert "Traceback" not in captured.err


def test_deadline_show_and_queue_round_trip(capsys):
    assert run_cli(["put", "custody", "child_name", "A. Rivera"]) == 0
    assert run_cli(["put", "custody", "ssn", "123-45-6789"]) == 0
    assert run_cli(["deadline", "custody", "hearing", "2099-10-01", "Custody hearing"]) == 0
    capsys.readouterr()

    assert run_cli(["show"]) == 0
    assert "custody: 3 record(s)" in capsys.readouterr().out

    assert run_cli(["show", "custody"]) == 0
    out = capsys.readouterr().out
    assert "[L4]  child_name: A minor child is named in this matter" in out
    assert "[L1]  deadline/hearing: 2099-10-01" in out
    assert "ssn" not in out and "123-45-6789" not in out      # L5: no row, no trace
    assert "A. Rivera" not in out                             # L4 payload never on the list

    assert run_cli(["show", "custody", "child_name"]) == 0
    assert "A. Rivera" in capsys.readouterr().out             # …but renders in the detail

    assert run_cli(["show", "custody", "ssn"]) == 0
    out = capsys.readouterr().out
    assert "sealed" in out and "123-45-6789" not in out

    assert run_cli(["queue", "--today", "2099-09-25"]) == 0
    assert "2099-10-01" in capsys.readouterr().out


def test_show_an_empty_matter_points_at_put(capsys):
    assert run_cli(["show", "custody"]) == 0
    assert "homestead-law put custody" in capsys.readouterr().out


def test_show_refuses_an_unknown_matter_and_a_missing_record(capsys):
    assert run_cli(["show", "bogus"]) == 1
    assert "unknown matter" in capsys.readouterr().err
    assert run_cli(["show", "custody", "courthouse"]) == 1
    assert "no such record" in capsys.readouterr().err


@pytest.mark.parametrize("argv", [
    ["resolve", "party", "Someone"],
    ["propose", "party", "Someone", "Someone Else"],
    ["orders", "list"],
    ["verify"],
])
def test_nestor_backed_commands_refuse_in_one_line_naming_the_extra(argv, capsys):
    assert run_cli(argv) == 1
    captured = capsys.readouterr()
    assert "homestead-law[entity]" in captured.err
    assert "Traceback" not in captured.err


# ── the audit's attack list on the command line ────────────────────────────


def test_deadline_parses_the_date_and_stores_its_iso_form(capsys):
    """The CLI stored whatever was typed; only the browser UI parsed. Two doors
    onto one store wrote two different things, and the unparsed one came back
    weeks later as a gap on the queue — I-1/I-2 say there is one strict parser,
    at the edge, on every edge."""
    assert run_cli(["deadline", "custody", "hearing", "August 10, 2099", "Custody hearing"]) == 0
    capsys.readouterr()

    assert run_cli(["show", "custody", "deadline", "hearing"]) == 0
    assert "2099-08-10" in capsys.readouterr().out

    # …and it is a real date on the queue, not a gap
    assert run_cli(["queue", "--today", "2099-08-01"]) == 0
    out = capsys.readouterr().out
    assert "in 9d" in out and "unreadable" not in out


@pytest.mark.parametrize("date", ["next Tuesday", "2026-13-45", "08/11/2026", "", "TBD"])
def test_deadline_refuses_a_date_it_cannot_read_in_one_line(date, capsys):
    """A date the queue could not read is refused here, where the operator can
    still fix it — one line on stderr, exit 1, nothing stored."""
    assert run_cli(["deadline", "custody", "hearing", date]) == 1
    err = capsys.readouterr().err
    assert err.startswith("refused:")
    assert len(err.strip().splitlines()) == 1
    assert "Traceback" not in err

    assert run_cli(["show", "custody", "deadline", "hearing"]) == 1
    assert "no such record" in capsys.readouterr().err


@pytest.mark.parametrize("item_id", ["../x", "a/b", "a\\b", ".", ".."])
def test_deadline_refuses_a_key_the_engine_refuses(item_id, capsys):
    """`InvalidKey` out of `homestead.keep.store.key()` reached the terminal as a
    traceback — the store refused correctly and the CLI turned that into a crash."""
    assert run_cli(["deadline", "custody", item_id, "2099-10-01"]) == 1
    err = capsys.readouterr().err
    assert "refused:" in err and "Traceback" not in err


@pytest.mark.parametrize("item_id", ["../x", "a/b", "   "])
def test_show_refuses_a_key_the_engine_refuses(item_id, capsys):
    """Same on the read door: `sidecar.has(*ref)` validates the key and raised
    straight through `_cmd_show`."""
    assert run_cli(["show", "custody", "deadline", item_id]) == 1
    err = capsys.readouterr().err
    assert "refused:" in err and "Traceback" not in err


def test_queue_refuses_a_today_it_cannot_read(capsys):
    """`--today` reached `Deadline.from_text` deep inside `_urgency`, so an
    unreadable one was a traceback — and only when a deadline happened to exist
    to compare against, so an empty store hid it."""
    assert run_cli(["deadline", "custody", "hearing", "2099-10-01"]) == 0
    capsys.readouterr()

    assert run_cli(["queue", "--today", "next Tuesday"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("refused:") and "Traceback" not in err


def test_ui_refuses_a_port_that_is_not_a_port(capsys):
    """`int(args[i + 1])` on whatever followed `--port`. Refused before anything
    binds — and refusing here is why this test can run at all."""
    for bad in ("abc", "-1", "99999"):
        assert run_cli(["ui", "--port", bad]) == 1
        err = capsys.readouterr().err
        assert "refused:" in err and "Traceback" not in err


def test_a_party_name_is_never_echoed_back_to_stdout(capsys, monkeypatch):
    """`put custody child_name …` printed "proposed to party resolver: <value>".
    `child_name` is L4 and `opposing_party` L3; the gate decides where either may
    be rendered, and a confirmation line printed straight from `argv` is a second
    door onto the same datum that scored nothing (I-16). The line names the
    field — a reference (I-15)."""
    proposed = []

    class _Resolver:
        def propose(self, surface, canonical, reason=None):
            proposed.append((surface, canonical))
            return {"draft": True}

    monkeypatch.setattr(nestor_seam, "available", lambda: True)
    monkeypatch.setattr(nestor_seam, "bind", lambda root=None: root)
    monkeypatch.setattr(nestor_seam, "resolver_for", lambda domain, store: _Resolver())
    monkeypatch.setattr("homestead_law.cli.get_store", lambda *a, **k: object())

    assert run_cli(["put", "custody", "child_name", "A. Rivera"]) == 0
    out = capsys.readouterr().out

    assert proposed == [("A. Rivera", "A. Rivera")], "the proposal itself still happens"
    assert "proposed to party resolver: child_name" in out
    assert "A. Rivera" not in out, "an L4 payload was printed by the write door"


def test_the_two_doors_store_the_same_string_for_the_same_date(tmp_path, monkeypatch):
    """The CLI and the browser UI are two doors onto one store. Given the same
    typed date they must write the same bytes, or `show` and the queue disagree
    depending on which door the operator used."""
    import http.client
    import json as _json
    import threading

    from homestead_law import server
    from homestead_law.app.window import Window
    from homestead_law.store import Sidecar

    assert run_cli(["deadline", "custody", "by-cli", "Aug 10 2099"]) == 0

    srv = server.build_server(host="127.0.0.1", port=0)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        conn = http.client.HTTPConnection(*srv.server_address, timeout=5)
        conn.request("POST", "/api/deadline",
                     body=_json.dumps({"matter": "custody", "id": "by-ui",
                                       "date": "Aug 10 2099"}),
                     headers={"Content-Type": "application/json"})
        assert conn.getresponse().status == 200
        conn.close()
    finally:
        srv.shutdown()
        srv.server_close()

    window = Window()
    window.open_list(Sidecar().records("custody"))
    texts = {row.ref[2]: row.text for row in window.rows}
    assert texts["by-cli"] == texts["by-ui"] == "2099-08-10"


def test_boot_makes_no_directory_outside_the_household_root(tmp_path, monkeypatch):
    """I-19: `homestead.keep.paths.home()` is the one resolver, and `_boot()` is
    the only thing in the CLI that creates a directory. A command that mkdirs
    anywhere else has written outside everything this module's rules reach —
    the unbound-ledger failure `nestor_seam.bind` exists to close, in another
    coordinate."""
    from pathlib import Path

    from homestead_law import cli

    root = tmp_path / "root"
    monkeypatch.setenv("HOMESTEAD_HOME", str(root))
    made: list[Path] = []
    real_mkdir = Path.mkdir

    def spy(self, *a, **kw):
        made.append(self)
        return real_mkdir(self, *a, **kw)

    monkeypatch.setattr(Path, "mkdir", spy)

    cli._boot()

    assert made, "_boot() no longer creates the root — has the spy stopped firing?"
    outside = [p for p in made if p != root and root not in p.parents]
    assert not outside, f"_boot() created {outside} outside the household root"
    assert (root / "keep").is_dir()


def test_every_record_command_writes_only_inside_the_household_root(tmp_path, monkeypatch):
    """The same property over the commands themselves — `put`, `deadline`,
    `show`, `queue` — because `_boot()` being well behaved says nothing about a
    command that resolves a path of its own."""
    from pathlib import Path

    root = tmp_path / "root"
    monkeypatch.setenv("HOMESTEAD_HOME", str(root))
    made: list[Path] = []
    real_mkdir = Path.mkdir

    def spy(self, *a, **kw):
        made.append(self)
        return real_mkdir(self, *a, **kw)

    monkeypatch.setattr(Path, "mkdir", spy)

    assert run_cli(["put", "custody", "courthouse", "Dept 4"]) == 0
    assert run_cli(["deadline", "custody", "hearing", "2099-10-01"]) == 0
    assert run_cli(["show", "custody"]) == 0
    assert run_cli(["queue", "--today", "2099-01-01"]) == 0

    outside = [p for p in made if p != root and root not in p.parents]
    assert not outside, f"a record command created {outside} outside the household root"
