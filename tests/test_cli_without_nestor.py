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
