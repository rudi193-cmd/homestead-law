"""`homestead_law.sync` — sync as an operator act (Decision 5, Wave 5 L5-sync).

`SyncScope`/`compose`/`Envelope`/`deliver` are the engine's
(`homestead.keep.sync`, floor 0.11.0, I-37/I-38/I-40 ratified by the
E4-sync-core audit). This module adds the one thing the engine cannot do
for itself — read `homestead_law.registry` to turn `--matters a,b` into a
scope the engine will accept (I-23) — and decides *where* a sync goes
without ever deciding *whether* one may.

Accepted-delivery tests drive the real `deliver()` — a FILE drop under a
throwaway `HOMESTEAD_HOME`, or a URL leg with `homestead.keep.egress.send`
replaced (the engine's own seam, never a real socket). "Exactly one
`IntegrityLog` row" is read through `IntegrityLog._entries()`, filtering
`BOUNDARY_ACT`/`SEAL_BOUNDARY_ACT` explicitly rather than trusting that
`_entries()` already does.
"""
from __future__ import annotations

import json
import sys
import types

import pytest

from homestead.keep.egress import EgressRefused, Wire
from homestead.keep.household import household_id
from homestead.keep.logs import BOUNDARY_ACT, IntegrityLog, SEAL_BOUNDARY_ACT
from homestead.keep import paths as engine_paths
from homestead.keep.rungs import Classified, Rung
from homestead.keep.sync import AlreadyDelivered, UnnamedScope
from homestead_law import sync as law_sync
from homestead_law import registry as registry_mod
from homestead_law.cli import run_cli
from homestead_law.store import Sidecar


def _seed_courthouse_and_opposing_party(store: Sidecar) -> None:
    store.put("custody", "courthouse", "primary", Classified(Rung.L1, "Dept 4"))
    store.put(
        "custody", "opposing_party", "primary",
        Classified(Rung.L3, "Jordan Rivera", derived="The other parent is named"),
    )


def _register_fake_matter(monkeypatch, name: str = "_fake_sync_matter") -> None:
    fake = types.ModuleType(f"homestead_law.packs.{name}")
    fake.MATTER = name
    fake.JURISDICTION = "US-NM"
    fake.JURISDICTIONS = ("US-NM",)
    fake.FIELDS = {"deadline": Rung.L1}
    fake.SCHEMA = {"deadline": {"rung": Rung.L1, "matter": name}}
    monkeypatch.setitem(registry_mod.REGISTRY, name, registry_mod._entry(fake))


def _fake_egress_send(sent: dict):
    """A stand-in for `homestead.keep.egress.send` — the engine's own seam
    for this — that checks `confirm` the same way the real one does but
    never opens a socket."""

    def send(url, payload, *, confirm=None, transport=None, method="POST"):
        wire = Wire(method=method, url=url, body=json.dumps(payload, sort_keys=True))
        if confirm is None or not confirm(wire):
            raise EgressRefused("declined at the mocked transport")
        sent["url"] = url
        sent["payload"] = payload
        return b"ok"

    return send


# ── the floor ─────────────────────────────────────────────────────────────

def test_the_engine_floor_carries_sync_and_cover_by_matter():
    """This bite's floor bump, pinned by name (I-1 style): the engine version
    installed actually carries the sync module and the cover's `by_matter`."""
    from homestead.app.cover import cover_counts
    from homestead.keep.sync import SyncScope

    assert SyncScope is not None
    by_matter = {"a": {"x": 1}, "b": {"x": 1}}
    assert cover_counts(["a", "b"], by_matter=by_matter, x=2) == {"x": 2}


# ── scope_from — refusals (I-40) and the registry (I-23) ────────────────────

def test_scope_from_refuses_all_by_name():
    """There is no --matters all (I-40) — refused before the registry check
    even runs, with its own message naming why."""
    with pytest.raises(UnnamedScope, match="all"):
        law_sync.scope_from(("all",), None, "L3")


def test_scope_from_refuses_empty_matters():
    with pytest.raises(UnnamedScope):
        law_sync.scope_from((), None, "L3")


def test_scope_from_refuses_an_unregistered_matter():
    with pytest.raises(law_sync.UnknownMatter):
        law_sync.scope_from(("not-a-real-matter",), None, "L3")


def test_scope_from_refuses_an_l5_ceiling_ratified_by_the_engine():
    """L5 is refused by the engine's own `SyncScope` (I-13, I-40); this pins
    that the refusal reaches a law consumer unchanged."""
    with pytest.raises(UnnamedScope):
        law_sync.scope_from(("custody",), None, "L5")


def test_scope_from_refuses_an_unparseable_ceiling():
    with pytest.raises(ValueError, match="ceiling"):
        law_sync.scope_from(("custody",), None, "L9")


def test_scope_from_accepts_registered_matters_and_narrows_item_types():
    scope = law_sync.scope_from(("custody",), ("deadline",), "L3")
    assert scope.matters == ("custody",)
    assert scope.item_types == ("deadline",)
    assert scope.ceiling.value == "L3"
    assert scope.tables == ("sidecar",)  # law has one table


def test_scope_from_reads_the_registry_live_i23(monkeypatch):
    """The registry is the only enumeration (I-23): a matter registered only
    for this test is accepted, and removing it again is refused — never a
    list this module keeps of its own."""
    _register_fake_matter(monkeypatch)
    scope = law_sync.scope_from(("_fake_sync_matter",), None, "L3")
    assert scope.matters == ("_fake_sync_matter",)

    monkeypatch.delitem(registry_mod.REGISTRY, "_fake_sync_matter")
    with pytest.raises(law_sync.UnknownMatter):
        law_sync.scope_from(("_fake_sync_matter",), None, "L3")


# ── preview / compose — the ceiling drops, never derives ────────────────────

def test_preview_drops_rows_above_the_scope_ceiling(tmp_path, monkeypatch):
    """Planting an L3 value: at ceiling L1 it never appears; at ceiling L3 it
    crosses as itself (`compose()` drops above the ceiling, never derives)."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _seed_courthouse_and_opposing_party(store)

    env_l1 = law_sync.preview(store, law_sync.scope_from(("custody",), None, "L1"))
    types_l1 = {row["item_type"] for row in env_l1.rows}
    assert "courthouse" in types_l1
    assert "opposing_party" not in types_l1

    env_l3 = law_sync.preview(store, law_sync.scope_from(("custody",), None, "L3"))
    matching = [row for row in env_l3.rows if row["item_type"] == "opposing_party"]
    assert [row["value"] for row in matching] == ["Jordan Rivera"]


# ── the destination — never a permission ────────────────────────────────────

def test_destination_resolution_order_and_preview_never_delivers(tmp_path, monkeypatch):
    """`--url` beats `HOMESTEAD_FLEET_URL` beats `home()/fleet.url`; none of
    them is read unless a caller is about to call `send()`, and
    `preview_destination()` only describes — it never delivers."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    assert law_sync._destination_url(None) is None
    assert law_sync.preview_destination("abc123").endswith("abc123.json")

    monkeypatch.setenv("HOMESTEAD_FLEET_URL", "https://env.example/ingest")
    assert law_sync._destination_url(None) == "https://env.example/ingest"

    (engine_paths.home() / "fleet.url").write_text("https://file.example/ingest\n")
    assert law_sync._destination_url(None) == "https://env.example/ingest"
    assert law_sync.preview_destination("abc123") == "POST https://env.example/ingest"

    monkeypatch.delenv("HOMESTEAD_FLEET_URL")
    assert law_sync._destination_url(None) == "https://file.example/ingest"

    assert law_sync._destination_url("https://flag.example/ingest") == (
        "https://flag.example/ingest"
    )
    assert not (engine_paths.exports_dir() / "sync").exists()


def test_env_fleet_url_is_a_destination_never_a_permission(tmp_path, monkeypatch):
    """A URL named by the environment still needs the same confirm a
    directly-passed one does; a declined confirm writes and ledgers nothing,
    and both logs are byte-identical before and after (I-37)."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    monkeypatch.setenv("HOMESTEAD_FLEET_URL", "https://fleet.example/ingest")
    store = Sidecar()
    _seed_courthouse_and_opposing_party(store)
    scope = law_sync.scope_from(("custody",), None, "L3")
    envelope = law_sync.preview(store, scope)

    integrity_path = engine_paths.logs_dir() / "integrity.jsonl"
    visible_path = engine_paths.logs_dir() / "visible.jsonl"
    before_integrity = integrity_path.read_bytes() if integrity_path.exists() else b""
    before_visible = visible_path.read_bytes() if visible_path.exists() else b""

    with pytest.raises(EgressRefused):
        law_sync.send(envelope, confirm=lambda wire: False)

    after_integrity = integrity_path.read_bytes() if integrity_path.exists() else b""
    after_visible = visible_path.read_bytes() if visible_path.exists() else b""
    assert after_integrity == before_integrity
    assert after_visible == before_visible
    assert not (engine_paths.exports_dir() / "sync").exists()


# ── accepted delivery — FILE ─────────────────────────────────────────────────

def test_accepted_file_delivery_writes_one_row_in_each_log(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _seed_courthouse_and_opposing_party(store)
    scope = law_sync.scope_from(("custody",), None, "L3")
    envelope = law_sync.preview(store, scope)

    receipt = law_sync.send(envelope, confirm=lambda wire: True)

    target = engine_paths.exports_dir() / "sync" / f"{envelope.envelope_id}.json"
    assert target.exists()
    assert receipt.destination == str(target)
    assert receipt.rows == envelope.count

    log = IntegrityLog(
        engine_paths.logs_dir() / "integrity.jsonl",
        anchor_path=engine_paths.anchors_dir() / "integrity.head",
    )
    rows = [
        e for e in log._entries()
        if e.get("act") not in (BOUNDARY_ACT, SEAL_BOUNDARY_ACT)
    ]
    assert len(rows) == 1
    assert rows[0]["act"] == "record_synced"
    assert rows[0]["household"] == envelope.household
    assert rows[0]["envelope"] == envelope.envelope_id

    lines = (engine_paths.logs_dir() / "visible.jsonl").read_text().splitlines()
    assert len(lines) == 1
    visible = json.loads(lines[0])
    assert visible["event"] == "record_synced"
    assert visible["ref"] == f"{envelope.household}/{envelope.envelope_id}"


def test_send_refuses_a_second_delivery_of_the_same_envelope(tmp_path, monkeypatch):
    """I-38 — ledgered once. A second `send()` of the same composed envelope
    is refused before anything is written a second time."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _seed_courthouse_and_opposing_party(store)
    envelope = law_sync.preview(store, law_sync.scope_from(("custody",), None, "L3"))

    law_sync.send(envelope, confirm=lambda wire: True)
    with pytest.raises(AlreadyDelivered):
        law_sync.send(envelope, confirm=lambda wire: True)


# ── accepted delivery — URL, mocked at the engine's seam ─────────────────────

def test_url_delivery_is_mocked_at_egress_send_never_a_real_socket(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _seed_courthouse_and_opposing_party(store)
    envelope = law_sync.preview(store, law_sync.scope_from(("custody",), None, "L3"))

    sent: dict = {}
    monkeypatch.setattr("homestead.keep.egress.send", _fake_egress_send(sent))

    receipt = law_sync.send(
        envelope, url="https://fleet.example/ingest", confirm=lambda wire: True
    )

    assert sent["url"] == "https://fleet.example/ingest"
    assert sent["payload"]["envelope_id"] == envelope.envelope_id
    assert receipt.destination == "https://fleet.example/ingest"


# ── init_household ───────────────────────────────────────────────────────────

def test_init_household_mints_once_then_refuses(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    minted = law_sync.init_household()
    assert minted.startswith("hh-")
    assert (tmp_path / "household.id").exists()

    with pytest.raises(law_sync.HouseholdAlreadyInitialized):
        law_sync.init_household()

    assert household_id() == minted


# ── the CLI (Decision 5: an operator act, no --yes on this side) ────────────

def test_cli_sync_refuses_without_a_tty(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

    rc = run_cli(["sync", "--matters", "custody", "--ceiling", "L3"])

    assert rc == 1
    assert "interactive terminal" in capsys.readouterr().err


def test_cli_sync_refuses_all_through_the_same_scope_from(tmp_path, monkeypatch, capsys):
    """The CLI's own refusal path, not just `scope_from` in isolation — the
    argument parsing between them must not swallow the exception."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))

    rc = run_cli(["sync", "--matters", "all", "--ceiling", "L3"])

    assert rc == 1
    assert "all" in capsys.readouterr().err


def test_cli_sync_declined_writes_nothing(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _seed_courthouse_and_opposing_party(store)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt="": "no")

    rc = run_cli(["sync", "--matters", "custody", "--ceiling", "L3"])

    assert rc == 1
    assert not (tmp_path / "exports" / "sync").exists()


def test_cli_sync_happy_path_file_drop(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _seed_courthouse_and_opposing_party(store)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt="": "yes")

    rc = run_cli(["sync", "--matters", "custody", "--ceiling", "L3"])

    assert rc == 0
    out = capsys.readouterr().out
    assert "synced:" in out
    assert "head:" in out
    assert list((tmp_path / "exports" / "sync").iterdir())


def test_cli_sync_init_household(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))

    rc = run_cli(["sync", "--init-household"])
    assert rc == 0
    assert (tmp_path / "household.id").exists()

    rc = run_cli(["sync", "--init-household"])
    assert rc == 1
    assert "refused" in capsys.readouterr().err
