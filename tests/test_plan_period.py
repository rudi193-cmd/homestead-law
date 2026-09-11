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
    """`"safe"`/`"equity_grant"` were the field names pinned here before
    L8-venture built the actual producer — corrected to
    `"safe.amount"`/`"equity_grant.amount"`, the dotted field names the real
    (REPEATABLE) venture pack stores under; see plan_period.py's own note."""
    assert plan_period.SIGNAL_FIELDS == frozenset(
        {
            "award_amount",
            "disbursement",
            "safe.amount",
            "equity_grant.amount",
            "revenue_start",
        }
    )


# ── audit additions (L3-bankruptcy-ch13 audit, 2026-09-12) ──────────────────

def test_three_signals_still_make_exactly_one_line(tmp_path, monkeypatch):
    """The flag reads *presence*, and presence does not have a count. Three
    signal records in another matter are one fact — "there is something to
    confirm" — said once per confirmed instance. A line per signal would be
    a count, and a count is a number the flag has promised never to carry."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _register_signal_matter(monkeypatch)
    _confirmed_bankruptcy(store)
    store.put("_fake_second", "award_amount", "grant-1", _signal_record())
    store.put("_fake_second", "award_amount", "grant-2", _signal_record("55"))
    store.put("_fake_second", "award_amount", "grant-3", _signal_record("7"))

    assert plan_period.flag(store) == (EXPECTED_LINE,)


def test_a_signal_inside_the_bankruptcy_matter_itself_is_not_a_signal(tmp_path, monkeypatch):
    """The flag is about income or assets arising in *another* matter — that
    is what "cross-matter" means and what §§ 541(a)(7)/1306(a) are being
    cited about. A stray `award_amount` filed under `bankruptcy` (a
    mis-addressed `put`, or a future field of this pack that happens to share
    a name) must not flag the case against itself: `_any_signal_elsewhere`
    skips the bankruptcy matter, and this is the check that it does."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _register_signal_matter(monkeypatch)
    _confirmed_bankruptcy(store)
    store.put(
        "bankruptcy", "award_amount", "stray",
        Classified(Rung.L3, "1000", derived="An award amount is on file"),
    )

    assert plan_period.flag(store) == ()


def test_two_instances_one_confirmed_one_not_gets_one_line(tmp_path, monkeypatch):
    """Two bankruptcy instances is the ordinary shape of a dismissed case and
    a refiling. Each is asked independently; only the confirmed, undischarged
    one contributes."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _register_signal_matter(monkeypatch)
    _confirmed_bankruptcy(store, "refiled")
    store.put("bankruptcy", "petition_date", "dismissed", Classified(Rung.L1, "2024-02-02"))
    store.put("_fake_second", "award_amount", "grant-1", _signal_record())

    lines = plan_period.flag(store)
    assert len(lines) == 1
    assert lines[0].startswith("bankruptcy/refiled:")


def test_a_confirmation_date_stored_at_the_wrong_rung_is_read_as_absent(tmp_path, monkeypatch):
    """`plan_confirmation_date` is L1 in the pack, so the ordinary case
    renders. Hand-stored at L4 — by a mis-typed `--rung`, or by I-11 reading
    a corrupt row closed — it *derives* instead: the gate hands back "A
    confirmation date is on file", a string that is not a date and was never
    read. Taking that as proof of confirmation would be this module inferring
    a case's posture from a sentence written to avoid showing it one. Treated
    as absent: no line. The honest fail-closed answer, and the same one the
    sibling `rules.compute` gives an anchor it cannot read."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _register_signal_matter(monkeypatch)
    store.put(
        "bankruptcy", "plan_confirmation_date", "primary",
        Classified(Rung.L4, "2026-06-01", derived="A confirmation date is on file"),
    )
    store.put("_fake_second", "award_amount", "grant-1", _signal_record())

    assert plan_period.flag(store) == ()


def test_a_discharge_date_stored_at_the_wrong_rung_does_not_suppress_the_line(tmp_path, monkeypatch):
    """The same rule — only a rendered value is on file — applied to the
    other condition, and it lands conservative in the other direction. An
    unreadable discharge date is not proof of discharge, so the reference
    line stands rather than being hidden on the strength of a sentence
    nothing read. A flag that shows when it need not is a reference the
    operator can ignore; one that hides when it should not is the failure
    this bite exists to prevent."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _register_signal_matter(monkeypatch)
    _confirmed_bankruptcy(store)
    store.put(
        "bankruptcy", "discharge_date", "primary",
        Classified(Rung.L4, "2027-01-01", derived="A discharge date is on file"),
    )
    store.put("_fake_second", "award_amount", "grant-1", _signal_record())

    assert plan_period.flag(store) == (EXPECTED_LINE,)


def test_the_line_carries_no_number_and_no_stored_value(tmp_path, monkeypatch):
    """"Never a number" as a check rather than a promise: the only digits the
    line may contain are the fixed statutory citation, and no digit in it
    comes from the store. Held by stripping the citation and asserting what
    is left has none — a stored amount, date or count that leaked in would
    survive the strip."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _register_signal_matter(monkeypatch)
    _confirmed_bankruptcy(store)
    store.put("_fake_second", "award_amount", "grant-1", _signal_record("4242"))
    store.put("bankruptcy", "petition_date", "primary", Classified(Rung.L1, "2025-03-09"))

    (line,) = plan_period.flag(store)
    citation = "11 U.S.C. §§ 541(a)(7), 1306(a), 1329"
    assert citation in line
    assert not any(ch.isdigit() for ch in line.replace(citation, ""))


def test_the_flag_is_computed_not_logged(tmp_path, monkeypatch):
    """A notice is a computed reference, not an event: it is derived fresh on
    every read from records that were themselves logged when they were
    written, and nothing about *reading* it is a fact about the household.
    Logging it would put a line in the visible log for something nobody did,
    and put it there again on every refresh. Held structurally — this module
    has no write path at all — rather than by counting log rows, which would
    only prove it did not happen to write one today."""
    import ast
    from pathlib import Path

    tree = ast.parse(Path(plan_period.__file__).read_text("utf-8"))
    on_store = sorted(
        {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "store"
        }
    )
    assert set(on_store) <= {"has", "get", "records"}, (
        f"plan_period calls {on_store} on the store — a notice is computed "
        "from records, never written or logged"
    )


# ── L8-venture: the real producer, not the fake-pack fixture ────────────────

def test_a_safe_on_the_real_venture_pack_flags_a_confirmed_case(tmp_path, monkeypatch):
    """The fake `_fake_second` fixture above proves the mechanism; this proves
    the actual producer L8-venture ships. One SAFE record — investor and
    amount both filled in — makes exactly one reference line, and the line
    carries neither the investor's name nor the amount (I-15): 'presence,
    never value' held against real data, not a stand-in."""
    from homestead_law.packs import venture

    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _confirmed_bankruptcy(store)
    store.put(
        venture.MATTER, "safe.investor", "seed-1",
        Classified(Rung.L4, "Acme Ventures", derived="A SAFE investor is on file"),
    )
    store.put(
        venture.MATTER, "safe.amount", "seed-1",
        Classified(Rung.L4, "250000", derived="A SAFE amount is on file"),
    )

    lines = plan_period.flag(store)

    assert lines == (EXPECTED_LINE,)
    assert "Acme Ventures" not in lines[0]
    assert "250000" not in lines[0]
    assert "250,000" not in lines[0]
