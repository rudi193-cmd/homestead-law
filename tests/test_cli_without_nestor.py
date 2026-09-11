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
import types

import pytest

from homestead.keep.rungs import Rung
from homestead_law import nestor_seam
from homestead_law import registry as registry_mod
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


def _register_second_matter(monkeypatch, name: str = "_fake_second") -> None:
    """Add a second matter to the registry — a real module, keyed by its own
    `MATTER`, injected for the test. `"_fake_second"`, never a real future pack
    name (bankruptcy/workers' comp land in Wave 3), so this stays a fake second
    matter even after they are registered for real. `monkeypatch.setitem`
    removes it again at teardown, so the registry a later test reads is the real
    one no matter what order the suite runs in. It declares `JURISDICTIONS`
    alongside `JURISDICTION` — the pack contract decision 1 settles — so this
    fake stays a stand-in for a real pack once the registry validates that
    tuple."""
    fake = types.ModuleType(f"homestead_law.packs.{name}")
    fake.MATTER = name
    fake.JURISDICTION = "US-NM"
    fake.JURISDICTIONS = ("US-NM",)
    fake.FIELDS = {"case_number": Rung.L1}
    fake.SCHEMA = {"case_number": {"rung": Rung.L1, "matter": name}}
    monkeypatch.setitem(registry_mod.REGISTRY, name, registry_mod._entry(fake))


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

    assert run_cli(["show", "custody", "--id", "primary"]) == 0
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

    # `--id primary` lists that instance's fields, in the pre-instances flat
    # form — `child_name`/`ssn` were `put` under the default instance.
    assert run_cli(["show", "custody", "--id", "primary"]) == 0
    out = capsys.readouterr().out
    assert "[L4]  child_name: A minor child is named in this matter" in out
    assert "ssn" not in out and "123-45-6789" not in out      # L5: no row, no trace
    assert "A. Rivera" not in out                             # L4 payload never on the list

    # `deadline custody hearing …` is unchanged on the command line and now
    # files `primary.hearing`: every deadline is addressed to an instance, so
    # the key is attributable and `instances_of` can read it.
    assert run_cli(["show", "custody", "deadline", "primary.hearing"]) == 0
    assert "2099-10-01" in capsys.readouterr().out

    # and the instance listing names it — the thing a free-form id made
    # impossible.
    assert run_cli(["show", "custody"]) == 0
    assert "primary" in capsys.readouterr().out

    assert run_cli(["show", "custody", "child_name"]) == 0
    assert "A. Rivera" in capsys.readouterr().out             # …but renders in the detail

    assert run_cli(["show", "custody", "ssn"]) == 0
    out = capsys.readouterr().out
    assert "sealed" in out and "123-45-6789" not in out

    assert run_cli(["queue", "--today", "2099-09-25"]) == 0
    assert "2099-10-01" in capsys.readouterr().out


def test_show_with_no_id_lists_instances_not_records(capsys):
    """L2b's own behaviour change: `show <matter>` with no `--id` now lists the
    matter's instances (a label per instance, plus its jurisdiction if any —
    never content, I-15) rather than dumping every record flat. `--id` gets
    the old flat listing back, scoped to one instance."""
    assert run_cli(["put", "custody", "courthouse", "Dept 4"]) == 0
    capsys.readouterr()

    assert run_cli(["show", "custody"]) == 0
    out = capsys.readouterr().out
    assert "custody instances:" in out
    assert "primary" in out
    assert "no jurisdiction set" in out
    assert "Dept 4" not in out, "an instance listing is not a record listing"

    assert run_cli(["show", "custody", "--id", "primary"]) == 0
    assert "Dept 4" in capsys.readouterr().out


@pytest.mark.parametrize("with_second_matter", [False, True])
def test_show_with_no_args_lists_every_registered_matter(with_second_matter, capsys, monkeypatch):
    """`show` with no args iterates `all_matters()` (I-23), not a hand-kept list
    of one. Custody is real and stays named by hand; the `with_second_matter`
    case injects a fake one and checks it appears too, so this test does not
    quietly stop proving the loop once a second matter is real."""
    if with_second_matter:
        _register_second_matter(monkeypatch)
        assert run_cli(["put", "_fake_second", "case_number", "BK-1"]) == 0

    assert run_cli(["put", "custody", "courthouse", "Dept 4"]) == 0
    capsys.readouterr()

    assert run_cli(["show"]) == 0
    out = capsys.readouterr().out
    assert "custody: 1 record(s)" in out
    if with_second_matter:
        assert "_fake_second: 1 record(s)" in out


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

    assert run_cli(["show", "custody", "deadline", "primary.hearing"]) == 0
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


# ── L2b-instances: matter open, --id/--sub ──────────────────────────────────

def test_matter_open_stores_the_jurisdiction_and_show_lists_it(capsys):
    assert run_cli(["matter", "open", "custody", "--id", "primary", "--jurisdiction", "US-NM"]) == 0
    out = capsys.readouterr().out
    assert "opened: custody/primary" in out and "US-NM" in out

    assert run_cli(["show", "custody"]) == 0
    out = capsys.readouterr().out
    assert "primary" in out and "US-NM" in out


def test_matter_open_refuses_a_code_outside_the_pack_by_name(capsys):
    assert run_cli(["matter", "open", "custody", "--id", "primary", "--jurisdiction", "US-CA"]) == 1
    err = capsys.readouterr().err
    assert "refused:" in err and "US-CA" in err

    assert run_cli(["show", "custody"]) == 0
    assert "nothing on file" in capsys.readouterr().out


def test_matter_open_twice_refuses_without_replace(capsys):
    assert run_cli(["matter", "open", "custody", "--id", "primary", "--jurisdiction", "US-NM"]) == 0
    capsys.readouterr()

    assert run_cli(["matter", "open", "custody", "--id", "primary", "--jurisdiction", "US-OR"]) == 1
    err = capsys.readouterr().err
    assert "refused:" in err and "--replace" in err

    assert run_cli([
        "matter", "open", "custody", "--id", "primary",
        "--jurisdiction", "US-OR", "--replace",
    ]) == 0
    out = capsys.readouterr().out
    assert "replaced" in out


def test_matter_open_refuses_a_malformed_id(capsys):
    assert run_cli(["matter", "open", "custody", "--id", "Not Valid", "--jurisdiction", "US-NM"]) == 1
    err = capsys.readouterr().err
    assert "refused:" in err
    assert "Not Valid" not in err


def test_put_id_and_sub_compose_the_stored_item_id(capsys):
    assert run_cli(["put", "custody", "courthouse", "Dept 4", "--id", "nm-order"]) == 0
    out = capsys.readouterr().out
    assert "stored: custody/courthouse/nm-order" in out


def test_put_sub_on_a_non_repeatable_field_is_refused_by_name(capsys):
    assert run_cli(["put", "custody", "courthouse", "Dept 4", "--sub", "1"]) == 1
    err = capsys.readouterr().err
    assert "refused:" in err and "courthouse" in err and "REPEATABLE" in err

    assert run_cli(["show", "custody", "courthouse"]) == 1   # nothing was stored


def test_deadline_sub_composes_a_dotted_item_id(capsys):
    assert run_cli(["deadline", "custody", "primary", "2099-10-01", "--sub", "hearing"]) == 0
    out = capsys.readouterr().out
    assert "stored: custody/deadline/primary.hearing" in out

    assert run_cli(["show", "custody", "deadline", "primary.hearing"]) == 0
    assert "2099-10-01" in capsys.readouterr().out


def test_deadline_without_sub_files_under_the_default_instance(capsys):
    """The audit's ruling on this bite: a deadline id is never free-form. The
    command line an operator already knows is unchanged — `deadline custody
    hearing …` — and what it writes is `primary.hearing`, an id
    `instances.split_item_id` can attribute to an instance. Without this, the
    key scan this same bite adds reads `hearing` as a *phantom instance* that
    no door can address (`matter open --id hearing` and `show --id hearing`
    both refuse it), and L3-deadline-templates'
    `(matter, "deadline", "<inst>.<template>")` has no consistent addressing to
    grow into."""
    from homestead_law import instances
    from homestead_law.store import Sidecar

    assert run_cli(["deadline", "custody", "hearing", "2099-10-01"]) == 0
    assert "stored: custody/deadline/primary.hearing" in capsys.readouterr().out
    assert instances.instances_of(Sidecar(), "custody") == ("primary",)


@pytest.mark.parametrize("bad", ["it's-due", "Hearing", "has_underscore", "a.b"])
def test_deadline_refuses_a_free_form_id_by_name_without_echoing_it(bad, capsys):
    """Engine-legal, instance-illegal. `homestead.keep.store.key()` would hold
    every one of these; this door will not write one, because an id it cannot
    split is a deadline that cannot be attributed to an instance. Refused in
    one line, naming the shape, never repeating what was typed (I-15)."""
    assert run_cli(["deadline", "custody", bad, "2099-10-01"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("refused:")
    assert "Traceback" not in err
    assert bad not in err


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
    # Both doors compose the same instance-addressed key from the same typed
    # id, so the two are comparable at all: `primary.<id>`.
    assert texts["primary.by-cli"] == texts["primary.by-ui"] == "2099-08-10"


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


def test_show_refuses_a_matter_holding_an_unaddressable_id_in_one_line(capsys):
    """On the branch as built this was a traceback out of `_cmd_show`: the
    instance listing called `jurisdiction_of` on every id the key scan returned,
    and the scan returned ids `item_id` refuses. One free-form deadline —
    exactly what the pre-instances `deadline` door wrote — and `show custody`
    crashed. It refuses by name now, one line, no id echoed."""
    from homestead.keep.rungs import Classified, Rung
    from homestead_law.store import Sidecar

    Sidecar().put(
        "custody", "deadline", "it's-due",
        Classified(Rung.L1, "2099-10-01"), overwrite=True,
    )
    assert run_cli(["show", "custody"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("refused:")
    assert "Traceback" not in err
    assert "it's-due" not in err
    assert "deadline" in err          # the item type — a reference


def test_help_says_an_id_is_a_label_never_a_name(capsys):
    """The sentence the plan asks `--help` to carry (I-15). Asserted rather
    than trusted: a doc line nothing reads is a doc line that quietly goes."""
    from homestead_law.__main__ import main

    assert main(["--help"]) == 0
    assert "is a label, never a name" in capsys.readouterr().out


def test_deadline_refuses_an_option_it_does_not_take(capsys):
    """An unconsumed `--flag` was swept into the positionals and stored *inside
    the instruction* — `deadline custody hearing 2026-11-01 "Hearing" --id
    or-order` filed the instruction "Hearing --id or-order". `--id` is the one
    an operator will reach for here, since `put` and `show` both take it and
    this command names its instance with the positional instead."""
    assert run_cli([
        "deadline", "custody", "hearing", "2099-11-01", "Hearing",
        "--id", "or-order",
    ]) == 1
    err = capsys.readouterr().err
    assert err.startswith("refused:") and "--id" in err and "Traceback" not in err

    assert run_cli(["show", "custody", "deadline", "primary.hearing"]) == 1
    assert "no such record" in capsys.readouterr().err


# ── deadline compute / deadline templates (L3-deadline-templates) ───────────
#
# These tests monkeypatch a template onto the real custody pack rather than
# building a fake matter, so the CLI wiring is proven against the same pack
# every other test in this file already uses — and they set `TEMPLATES`
# rather than adding to it, so what the sibling custody bite declares in
# parallel never changes what a door test here is asserting about.

_NOTICE_TEMPLATE = {
    "name": "notice", "anchor": "hearing_date", "days": 20,
    "direction": "forward", "rule": "court_days", "mail": False,
    "jurisdiction": "US-NM", "source": "NMSA 40-10A-305",
    "status": "VERIFIED", "note": "",
}


def test_deadline_templates_lists_nothing_for_a_pack_with_none(monkeypatch, capsys):
    """The empty case. Custody's own `TEMPLATES` is emptied for the duration
    rather than assumed empty: the sibling custody bite fills it in in
    parallel, and a test that reads "the listing is empty" as "this pack
    declares none" would start failing the day it lands — which is a test
    about the merge order, not about the door."""
    from homestead_law.packs import custody

    monkeypatch.setattr(custody, "TEMPLATES", (), raising=False)
    assert run_cli(["deadline", "templates", "custody"]) == 0
    assert "no deadline templates declared" in capsys.readouterr().out


def test_deadline_templates_lists_a_packs_declared_templates(monkeypatch, capsys):
    from homestead_law.packs import custody

    monkeypatch.setattr(custody, "TEMPLATES", (_NOTICE_TEMPLATE,), raising=False)
    assert run_cli(["deadline", "templates", "custody"]) == 0
    out = capsys.readouterr().out
    assert "notice" in out and "VERIFIED" in out and "court_days" in out


def test_deadline_compute_prints_the_preview_and_stores_nothing(monkeypatch, capsys):
    from homestead_law.packs import custody
    from homestead_law.store import Sidecar

    monkeypatch.setattr(custody, "TEMPLATES", (_NOTICE_TEMPLATE,), raising=False)
    assert run_cli(["matter", "open", "custody", "--id", "primary", "--jurisdiction", "US-NM"]) == 0
    capsys.readouterr()
    assert run_cli(["put", "custody", "hearing_date", "2026-01-01"]) == 0
    capsys.readouterr()

    assert run_cli(["deadline", "compute", "custody", "notice", "--id", "primary"]) == 0
    out = capsys.readouterr().out
    assert "anchor:  hearing_date = 2026-01-01" in out
    assert "result:  2026-01-21" in out
    assert "token:" in out

    assert not Sidecar().has("custody", "deadline", "primary.notice")


def test_deadline_compute_accept_stores_and_a_second_accept_refuses(monkeypatch, capsys):
    from homestead_law.packs import custody
    from homestead_law.store import Sidecar

    monkeypatch.setattr(custody, "TEMPLATES", (_NOTICE_TEMPLATE,), raising=False)
    assert run_cli(["matter", "open", "custody", "--id", "primary", "--jurisdiction", "US-NM"]) == 0
    capsys.readouterr()
    assert run_cli(["put", "custody", "hearing_date", "2026-01-01"]) == 0
    capsys.readouterr()

    assert run_cli(["deadline", "compute", "custody", "notice", "--id", "primary", "--accept"]) == 0
    out = capsys.readouterr().out
    assert "accepted: custody/deadline/primary.notice" in out

    record = Sidecar().get("custody", "deadline", "primary.notice")
    assert record.payload == "2026-01-21"
    assert "confirm against the court's notice" in record.derived

    assert run_cli(["deadline", "compute", "custody", "notice", "--id", "primary", "--accept"]) == 1
    err = capsys.readouterr().err
    assert "already on file" in err and "--replace" in err


def test_deadline_compute_refuses_an_uncertain_template_naming_the_source(monkeypatch, capsys):
    from homestead_law.packs import custody

    monkeypatch.setattr(custody, "TEMPLATES", ({
        "name": "guess", "anchor": "hearing_date", "days": 5,
        "direction": "forward", "rule": "court_days", "mail": False,
        "jurisdiction": None, "source": "unclear rule",
        "status": "UNCERTAIN", "note": "",
    },), raising=False)
    assert run_cli(["matter", "open", "custody", "--id", "primary", "--jurisdiction", "US-NM"]) == 0
    capsys.readouterr()
    assert run_cli(["put", "custody", "hearing_date", "2026-01-01"]) == 0
    capsys.readouterr()

    assert run_cli(["deadline", "compute", "custody", "guess", "--id", "primary"]) == 1
    err = capsys.readouterr().err
    assert "UNCERTAIN: unclear rule" in err


def test_deadline_compute_says_whether_mail_and_district_days_were_applied(
    monkeypatch, capsys,
):
    """Both are part of the answer, so the preview prints both — including
    the "not applied" case, which is the one an operator would otherwise
    assume in their own favour."""
    from homestead_law.packs import custody

    monkeypatch.setattr(custody, "TEMPLATES", (_NOTICE_TEMPLATE,), raising=False)
    assert run_cli(["matter", "open", "custody", "--id", "primary", "--jurisdiction", "US-NM"]) == 0
    assert run_cli(["put", "custody", "hearing_date", "2026-01-01"]) == 0
    capsys.readouterr()

    assert run_cli(["deadline", "compute", "custody", "notice", "--id", "primary"]) == 0
    out = capsys.readouterr().out
    assert "forum:   US-NM" in out
    assert "mail:    no" in out
    # US-NM is a state court: FRBP 9006(a)(6)(C) has no application at all
    # there, so the line is absent rather than saying a calendar that never
    # existed was "not applied".
    assert "district holidays" not in out


def test_a_federal_forum_says_when_no_district_calendar_was_applied(
    monkeypatch, capsys,
):
    """The case the line is for: a federal count *could* have carried a
    district's state holidays and did not."""
    from homestead_law.packs import custody

    monkeypatch.setattr(custody, "TEMPLATES", (
        dict(_NOTICE_TEMPLATE, jurisdiction="US-federal"),), raising=False)
    monkeypatch.setattr(
        custody, "JURISDICTIONS", ("US-NM", "US-OR", "US-federal"))
    assert run_cli([
        "matter", "open", "custody", "--id", "primary",
        "--jurisdiction", "US-federal",
    ]) == 0
    assert run_cli(["put", "custody", "hearing_date", "2026-01-01"]) == 0
    capsys.readouterr()

    assert run_cli(["deadline", "compute", "custody", "notice", "--id", "primary"]) == 0
    assert "district holidays not applied" in capsys.readouterr().out


def test_deadline_compute_counts_a_federal_template_under_its_district_state(
    monkeypatch, capsys,
):
    """The pinned case: 2026-11-27 is a working day on the federal calendar
    and a legal holiday in New Mexico, so a 70-day claims bar from a
    2026-09-18 petition is 2026-11-27 without the district's state and
    2026-11-30 with it. The CLI names which one it used."""
    from homestead_law.packs import custody

    monkeypatch.setattr(custody, "TEMPLATES", ({
        "name": "claims-bar", "anchor": "hearing_date", "days": 70,
        "direction": "forward", "rule": "court_days", "mail": False,
        "jurisdiction": None, "source": "FRBP 3002(c)",
        "status": "VERIFIED", "note": "", "district_state": "NM",
    },), raising=False)
    # Custody's own tuple is NM/OR; a *federal* forum is what 9006(a)(6)(C)
    # is about, so this test widens the pack's published set for its own
    # duration rather than reaching past `set_jurisdiction`'s closed check.
    monkeypatch.setattr(
        custody, "JURISDICTIONS", ("US-NM", "US-OR", "US-federal"))
    assert run_cli([
        "matter", "open", "custody", "--id", "primary",
        "--jurisdiction", "US-federal",
    ]) == 0
    assert run_cli(["put", "custody", "hearing_date", "2026-09-18"]) == 0
    capsys.readouterr()

    assert run_cli(["deadline", "compute", "custody", "claims-bar", "--id", "primary"]) == 0
    out = capsys.readouterr().out
    assert "result:  2026-11-30" in out
    assert "district holidays: NM" in out


def test_deadline_compute_picks_the_template_written_for_this_instances_forum(
    monkeypatch, capsys,
):
    """One name, two forums — the custody shape, through the CLI door."""
    from homestead_law.packs import custody

    monkeypatch.setattr(custody, "TEMPLATES", (
        {"name": "contest", "anchor": "hearing_date", "days": 20,
         "direction": "forward", "rule": "court_days", "mail": False,
         "jurisdiction": "US-NM", "source": "NMSA 40-10A-305",
         "status": "VERIFIED", "note": ""},
        {"name": "contest", "anchor": "hearing_date", "days": 21,
         "direction": "forward", "rule": "court_days", "mail": False,
         "jurisdiction": "US-OR", "source": "ORS 109.787",
         "status": "VERIFIED", "note": ""},
    ), raising=False)

    assert run_cli(["matter", "open", "custody", "--id", "nm-order", "--jurisdiction", "US-NM"]) == 0
    assert run_cli(["matter", "open", "custody", "--id", "or-order", "--jurisdiction", "US-OR"]) == 0
    assert run_cli(["put", "custody", "hearing_date", "2026-01-01", "--id", "nm-order"]) == 0
    assert run_cli(["put", "custody", "hearing_date", "2026-01-01", "--id", "or-order"]) == 0
    capsys.readouterr()

    assert run_cli(["deadline", "compute", "custody", "contest", "--id", "nm-order"]) == 0
    nm = capsys.readouterr().out
    assert run_cli(["deadline", "compute", "custody", "contest", "--id", "or-order"]) == 0
    orr = capsys.readouterr().out

    assert "NMSA 40-10A-305" in nm and "ORS 109.787" in orr
    assert "result:  2026-01-21" in nm         # 20 court days, NM
    assert "result:  2026-01-22" in orr        # 21 court days, OR


def test_deadline_compute_refuses_mail_on_a_backward_template_without_echoing_the_anchor(
    monkeypatch, capsys,
):
    from homestead_law.packs import custody

    monkeypatch.setattr(custody, "TEMPLATES", ({
        "name": "objection", "anchor": "hearing_date", "days": 7,
        "direction": "backward", "rule": "court_days_before", "mail": False,
        "jurisdiction": "US-NM", "source": "FRBP 3015(f)",
        "status": "VERIFIED", "note": "",
    },), raising=False)
    assert run_cli(["matter", "open", "custody", "--id", "primary", "--jurisdiction", "US-NM"]) == 0
    assert run_cli(["put", "custody", "hearing_date", "2026-03-01"]) == 0
    capsys.readouterr()

    assert run_cli([
        "deadline", "compute", "custody", "objection", "--id", "primary", "--mail",
    ]) == 1
    err = capsys.readouterr().err
    assert err.startswith("refused:") and "objection" in err
    assert "2026-03-01" not in err and "Traceback" not in err


def test_deadline_doors_refuse_a_broken_template_by_name_rather_than_tracebacking(
    monkeypatch, capsys,
):
    """`templates_of` re-validates, so a pack reached outside the registry —
    here, one whose `TEMPLATES` was set after import — still refuses by name
    at the door instead of raising through it (I-11)."""
    from homestead_law.packs import custody

    monkeypatch.setattr(custody, "TEMPLATES", ({
        "name": "broken", "anchor": "case_number", "days": 5,
        "direction": "forward", "rule": "court_days", "mail": False,
        "jurisdiction": None, "source": "test", "status": "VERIFIED", "note": "",
    },), raising=False)      # case_number is L3 on custody, not L1

    assert run_cli(["deadline", "templates", "custody"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("refused:") and "Traceback" not in err

    assert run_cli(["deadline", "compute", "custody", "broken", "--id", "primary"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("refused:") and "Traceback" not in err
