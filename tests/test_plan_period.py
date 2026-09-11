"""The plan-period interaction flag (L3-bankruptcy-ch13, added 2026-09-11).

Wave 8's producers (`grant`/`venture` packs) do not exist yet, so this bite's
own test is against a `_fake_second` pack — the same fixture shape
`tests/test_queue.py::_register_second_matter` uses — declaring one
`SIGNAL_FIELDS` item type (`award_amount`) and a stored record under it. The
five required scenarios, each its own test: present; absent when not
confirmed; absent when discharged; absent when no signal; absent when the
signal is at L5 (the gate drops it).
"""
from __future__ import annotations

import types

from homestead.keep.rungs import Classified, Rung
from homestead_law import plan_period, registry as registry_mod
from homestead_law.store import Sidecar

EXPECTED_LINE = (
    "bankruptcy/primary: income or assets arising during the plan: confirm "
    "with your attorney (11 U.S.C. §§ 541(a)(7), 1306(a), 1329; disclosure "
    "duties under the plan and local rules)"
)


def _register_signal_matter(monkeypatch, name: str = "_fake_second") -> None:
    """A second matter that declares one `SIGNAL_FIELDS` item type
    (`award_amount`) — the same construction `test_queue.py`'s own
    `_register_second_matter` uses, so this fixture keeps exercising 'a
    matter the registry did not have before' even after Wave 8's real
    producers land."""
    fake = types.ModuleType(f"homestead_law.packs._fake_{name}")
    fake.MATTER = name
    fake.JURISDICTION = "US-NM"
    fake.JURISDICTIONS = ("US-NM",)
    fake.FIELDS = {"award_amount": Rung.L3}
    fake.SCHEMA = {
        "award_amount": {
            "rung": Rung.L3, "matter": name,
            "derived": "An award amount is on file",
        }
    }
    monkeypatch.setitem(registry_mod.REGISTRY, name, registry_mod._entry(fake))


def _confirmed_bankruptcy(store: Sidecar, instance: str = "primary") -> None:
    store.put("bankruptcy", "plan_confirmation_date", instance, Classified(Rung.L1, "2026-06-01"))


def _signal_record(value: str = "1000") -> Classified:
    return Classified(Rung.L3, value, derived="An award amount is on file")


def test_flag_present_when_confirmed_undischarged_and_a_signal_exists(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _register_signal_matter(monkeypatch)
    _confirmed_bankruptcy(store)
    store.put("_fake_second", "award_amount", "grant-1", _signal_record())

    assert plan_period.flag(store) == (EXPECTED_LINE,)


def test_flag_absent_when_not_confirmed(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _register_signal_matter(monkeypatch)
    # No plan_confirmation_date at all — but the instance exists via some
    # other bankruptcy record, so instances_of still finds it.
    store.put("bankruptcy", "petition_date", "primary", Classified(Rung.L1, "2026-01-05"))
    store.put("_fake_second", "award_amount", "grant-1", _signal_record())

    assert plan_period.flag(store) == ()


def test_flag_absent_when_discharged(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _register_signal_matter(monkeypatch)
    _confirmed_bankruptcy(store)
    store.put("bankruptcy", "discharge_date", "primary", Classified(Rung.L1, "2027-01-01"))
    store.put("_fake_second", "award_amount", "grant-1", _signal_record())

    assert plan_period.flag(store) == ()


def test_flag_absent_when_no_signal_anywhere(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _register_signal_matter(monkeypatch)
    _confirmed_bankruptcy(store)
    # the second matter exists but holds no SIGNAL_FIELDS record
    store.put("_fake_second", "notes", "grant-1", Classified(Rung.L4, "unrelated", derived="An operator note is on file"))

    assert plan_period.flag(store) == ()


def test_flag_absent_when_no_other_matter_at_all(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _confirmed_bankruptcy(store)

    assert plan_period.flag(store) == ()


def test_flag_absent_when_the_signal_is_at_l5_the_gate_drops_it(tmp_path, monkeypatch):
    """The rung model, not this module, decides what counts as a signal: an
    L5 `award_amount` is denied on S1_LIST, so it is not a signal at all —
    the exact 'gate drops it → absent' case the bite spec names."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _register_signal_matter(monkeypatch)
    _confirmed_bankruptcy(store)
    store.put("_fake_second", "award_amount", "grant-1", Classified(Rung.L5, "1000"))

    assert plan_period.flag(store) == ()


def test_flag_line_does_not_vary_with_the_signals_own_value(tmp_path, monkeypatch):
    """'Never a value, never a number' means never the *payload* — the fixed
    citation in the template text (§§ 541(a)(7), 1306(a), 1329) is not that.
    Proven by changing the underlying signal's stored value and showing the
    line is byte-identical either way: the flag reads presence, not content."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path / "a"))
    store_a = Sidecar()
    _register_signal_matter(monkeypatch)
    _confirmed_bankruptcy(store_a)
    store_a.put("_fake_second", "award_amount", "grant-1", _signal_record("1000"))
    line_a = plan_period.flag(store_a)

    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path / "b"))
    store_b = Sidecar()
    _confirmed_bankruptcy(store_b)
    store_b.put("_fake_second", "award_amount", "grant-1", _signal_record("999999"))
    line_b = plan_period.flag(store_b)

    assert line_a == line_b == (EXPECTED_LINE,)


def test_flag_reads_through_the_gate_never_the_payload():
    """I-16, pinned for this module the way test_chokepoint.py pins it
    package-wide: no `.payload` anywhere in plan_period.py."""
    import ast
    from pathlib import Path

    src = Path(plan_period.__file__).read_text("utf-8")
    reaches = [
        n.lineno for n in ast.walk(ast.parse(src))
        if isinstance(n, ast.Attribute) and n.attr == "payload"
    ]
    assert not reaches


def test_multiple_confirmed_instances_each_get_their_own_line(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _register_signal_matter(monkeypatch)
    _confirmed_bankruptcy(store, "primary")
    _confirmed_bankruptcy(store, "second-case")
    store.put("_fake_second", "award_amount", "grant-1", _signal_record())

    lines = plan_period.flag(store)
    assert len(lines) == 2
    assert {"bankruptcy/primary", "bankruptcy/second-case"} == {
        line.split(":")[0] for line in lines
    }


def test_signal_fields_is_the_frozenset_wave_8_names():
    assert plan_period.SIGNAL_FIELDS == frozenset(
        {"award_amount", "disbursement", "safe", "equity_grant", "revenue_start"}
    )
