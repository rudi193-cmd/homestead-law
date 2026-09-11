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

import ast
import json
import re
import sys
import types
from pathlib import Path

import pytest

from homestead.keep.egress import EgressRefused, Wire
from homestead.keep.household import household_id
from homestead.keep.logs import (
    BOUNDARY_ACT, IntegrityLog, IntegritySealError, SEAL_BOUNDARY_ACT,
)
from homestead.keep import paths as engine_paths
from homestead.keep.rungs import Classified, Rung
from homestead.keep.sync import AlreadyDelivered, UnnamedScope
from homestead_law import sync as law_sync
from homestead_law import registry as registry_mod
from homestead_law.cli import run_cli
from homestead_law.store import Sidecar

SYNC_MODULE = Path(law_sync.__file__)


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

    monkeypatch.setenv("HOMESTEAD_FLEET_URL", "https://env.example/ingest")
    assert law_sync._destination_url("https://flag.example/ingest") == (
        "https://flag.example/ingest"
    )
    assert law_sync.resolve_destination(url="https://flag.example/ingest") == (
        "https://flag.example/ingest", None
    )
    monkeypatch.delenv("HOMESTEAD_FLEET_URL")
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


# ── --types: refused by name, never a silently empty narrowing (I-11) ───────

def test_scope_from_refuses_an_item_type_no_named_matter_holds():
    """`compose()` narrows by item type, so an unknown one is not an error
    there — it matches nothing, and the operator is handed an envelope of
    zero rows for a scope they believe they named. Refused by name."""
    with pytest.raises(law_sync.UnknownItemType, match="not-a-real-type"):
        law_sync.scope_from(("custody",), ("not-a-real-type",), "L3")


def test_scope_from_refuses_a_type_that_belongs_only_to_another_matter(monkeypatch):
    """The check is against the *named* matters' own types, not every type
    in the registry: a field only the second matter declares is refused for
    a scope over the first."""
    _register_fake_matter(monkeypatch)
    assert "courthouse" in law_sync.item_types_for(("custody",))
    assert "courthouse" not in law_sync.item_types_for(("_fake_sync_matter",))
    with pytest.raises(law_sync.UnknownItemType):
        law_sync.scope_from(("_fake_sync_matter",), ("courthouse",), "L3")


def test_item_types_for_reads_the_registry_and_carries_deadline():
    """I-23: the answer is each named pack's own classified fields, read
    live, plus the one computed type every matter may hold."""
    types = law_sync.item_types_for(("custody",))
    assert "deadline" in types
    assert types - {"deadline"} == set(registry_mod.matter("custody").fields)
    with pytest.raises(law_sync.UnknownMatter):
        law_sync.item_types_for(("not-a-real-matter",))


def test_the_l5_ceiling_refusal_names_the_rung():
    """The engine makes this refusal; pinning here that its *message* names
    L5, so an operator who typed `--ceiling L5` reads why."""
    with pytest.raises(UnnamedScope, match="L5"):
        law_sync.scope_from(("custody",), None, "L5")


# ── nothing to sync — refused before the confirm, never ledgered ────────────

def test_send_refuses_a_zero_row_envelope_before_the_confirm(tmp_path, monkeypatch):
    """A scope that composes nothing is not an act to approve. Before this,
    a zero-row envelope was written to disk, appended one `record_synced`
    row to the integrity chain and showed one `RECORD_SYNCED` line — the
    household's own record then said a sync happened, of nothing."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _seed_courthouse_and_opposing_party(store)
    # `courthouse` is L1 and `opposing_party` L3 — a ceiling of L1 over the
    # deadline type alone matches neither.
    scope = law_sync.scope_from(("custody",), ("deadline",), "L1")
    envelope = law_sync.preview(store, scope)
    assert envelope.count == 0

    asked = []
    with pytest.raises(law_sync.NothingToSync, match="nothing to sync"):
        law_sync.send(envelope, confirm=lambda wire: asked.append(wire) or True)

    assert asked == [], "the confirm was never shown"
    assert not (engine_paths.exports_dir() / "sync").exists()
    assert not (engine_paths.logs_dir() / "visible.jsonl").exists()


def test_cli_sync_refuses_a_scope_that_composes_nothing(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _seed_courthouse_and_opposing_party(store)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt="": "yes")

    rc = run_cli(["sync", "--matters", "custody", "--types", "deadline",
                  "--ceiling", "L1"])

    assert rc == 1
    assert "nothing to sync" in capsys.readouterr().err
    assert not (tmp_path / "exports" / "sync").exists()


def test_cli_sync_refuses_an_unknown_type_by_name(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    rc = run_cli(["sync", "--matters", "custody", "--types", "nope",
                  "--ceiling", "L3"])
    assert rc == 1
    assert "nope" in capsys.readouterr().err


# ── the envelope is frozen: what leaves is what was shown ───────────────────

def test_a_store_write_between_preview_and_send_changes_nothing_that_leaves(
    tmp_path, monkeypatch
):
    """The held preview is the engine's frozen `Envelope`. A record written
    after it was composed is not in the bytes that leave, the id does not
    move, and the `head` the envelope carries is the head as it was at
    compose time — the envelope is what the operator was shown.

    A send after further writes therefore ships a *stale* pre-sync head. That
    is deliberate and is the receiving fleet's to notice: `homestead-fleet
    ingest` is where a stale head is refused, and `--allow-stale` is its
    flag, not one this side has. Silently recomposing to freshen the head
    would send an envelope nobody previewed."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _seed_courthouse_and_opposing_party(store)
    envelope = law_sync.preview(store, law_sync.scope_from(("custody",), None, "L3"))
    frozen_bytes = envelope.to_bytes()
    frozen_id = envelope.envelope_id
    frozen_head = envelope.head

    store.put("custody", "docket", "primary",
              Classified(Rung.L3, "later entry", derived="A docket entry is on file"))
    recomposed = law_sync.preview(store, law_sync.scope_from(("custody",), None, "L3"))
    assert recomposed.envelope_id != frozen_id, "the store really did change"

    receipt = law_sync.send(envelope, confirm=lambda wire: True)

    assert envelope.to_bytes() == frozen_bytes
    assert receipt.envelope_id == frozen_id
    dropped = Path(receipt.destination).read_bytes()
    assert dropped == frozen_bytes
    assert b"later entry" not in dropped
    assert json.loads(dropped)["head"] == frozen_head


def test_what_leaves_at_ceiling_l3_drops_l4_and_l5_without_deriving_them(
    tmp_path, monkeypatch
):
    """Plant one row per rung and grep the envelope's own bytes: the L4 and
    L5 values are absent — and so are their *derived* forms, because
    Decision 5 drops above the ceiling rather than deriving (open item 5).
    The L3 row crosses as itself."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    store.put("custody", "custody_type", "primary",
              Classified(Rung.L3, "joint legal",
                         derived="A custody arrangement type is on file"))
    store.put("custody", "child.name", "primary.a",
              Classified(Rung.L4, "Rowan-planted-L4",
                         derived="A child's name is on file"))
    store.put("custody", "ssn", "primary", Classified(Rung.L5, "planted-L5-key"))

    envelope = law_sync.preview(store, law_sync.scope_from(("custody",), None, "L3"))
    raw = envelope.to_bytes().decode()

    assert "planted-L5-key" not in raw
    assert "Rowan-planted-L4" not in raw
    assert "A child's name is on file" not in raw
    assert {row["item_type"] for row in envelope.rows} == {"custody_type"}
    assert "joint legal" in raw


# ── L9-child-name: a retired field's rows still in a household's store ──────

def test_a_retired_fields_rows_cross_on_a_matter_scope_and_cannot_be_named(
    tmp_path, monkeypatch
):
    """The ruling this bite owes a household that has a pre-L9
    `("custody", "child_name", "primary")` row on disk, pinned rather than
    assumed, because the two halves of `--matters`/`--types` answer it
    differently and both answers are deliberate.

    `--matters custody --ceiling L4` **carries it**: `scope_from` leaves
    `item_types` at `None`, so the scope names a matter and not a list of
    types, and the engine composes every row of that matter under the
    ceiling. A retired declaration is not a retired *record* — the row is
    still the household's, still classified at the rung it was written with,
    and dropping it silently from a sync the operator asked for at L4 would
    lose data no door ever told them was gone.

    `--types child_name` **refuses it**, by name: `item_types_for` reads each
    pack's live `fields` (I-23), and `child_name` is no longer one of them,
    so naming it is the "a type no named matter holds" refusal rather than a
    scope that narrows to nothing. The asymmetry is the point: a household
    can still *send* what it has, and cannot *ask for* a name the registry
    no longer knows.
    """
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    planted = "Rivera-planted-legacy-L4"
    store.put("custody", "child_name", "primary",
              Classified(Rung.L4, planted,
                         derived="A minor child is named in this matter"))

    assert "child_name" not in law_sync.item_types_for(("custody",))

    scope = law_sync.scope_from(("custody",), None, "L4")
    assert scope.item_types is None
    envelope = law_sync.preview(store, scope)
    assert {row["item_type"] for row in envelope.rows} == {"child_name"}
    assert envelope.rows[0]["value"] == planted

    # …and at a ceiling below its rung it drops like any other L4 row.
    below = law_sync.preview(store, law_sync.scope_from(("custody",), None, "L3"))
    assert below.rows == () and planted not in below.to_bytes().decode()

    # Naming the retired type is refused, by name, with no row in the message.
    with pytest.raises(law_sync.UnknownItemType) as caught:
        law_sync.scope_from(("custody",), ("child_name",), "L4")
    assert "child_name" in str(caught.value)
    assert planted not in str(caught.value)


# ── the destination is a place, never a permission ──────────────────────────

def test_the_fleet_url_file_is_read_stripped(tmp_path, monkeypatch):
    """A file an operator edits ends in a newline, and may hold stray
    spaces; neither is part of the URL."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    monkeypatch.delenv("HOMESTEAD_FLEET_URL", raising=False)
    (engine_paths.home() / "fleet.url").write_text("  https://file.example/ingest \n\n")
    assert law_sync._destination_url(None) == "https://file.example/ingest"

    (engine_paths.home() / "fleet.url").write_text("   \n")
    assert law_sync._destination_url(None) is None


def test_a_plain_http_url_is_the_engines_rule_to_make_not_a_second_one_here(
    tmp_path, monkeypatch
):
    """`keep/egress.send` does not score a URL's scheme — a confirmed act to
    a named destination is the whole contract there. Law adds no second
    rule: an `http://` destination is passed through unchanged, and the
    operator sees the scheme in the `Wire` they confirm. If the engine ever
    refuses a scheme, it refuses here too and this test is where that
    shows."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _seed_courthouse_and_opposing_party(store)
    envelope = law_sync.preview(store, law_sync.scope_from(("custody",), None, "L3"))

    seen = []
    monkeypatch.setattr("homestead.keep.egress.send", _fake_egress_send({}))
    assert law_sync.preview_destination(
        envelope.envelope_id, url="http://127.0.0.1:9/ingest"
    ) == "POST http://127.0.0.1:9/ingest"

    def confirm(wire):
        seen.append(wire.url)
        return True

    law_sync.send(envelope, url="http://127.0.0.1:9/ingest", confirm=confirm)
    assert seen == ["http://127.0.0.1:9/ingest"]


def test_resolve_destination_returns_exactly_one_leg(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    monkeypatch.delenv("HOMESTEAD_FLEET_URL", raising=False)
    dest_url, dest_dir = law_sync.resolve_destination()
    assert dest_url is None and dest_dir is not None and dest_dir.is_absolute()
    with pytest.raises(ValueError, match="exactly one"):
        law_sync.send_to(object(), dest_url=None, dest_dir=None, confirm=lambda w: True)


# ── confirm_exactly — a confirm, not a permission ──────────────────────────

def test_confirm_exactly_declines_every_wire_but_the_one_that_was_shown(
    tmp_path, monkeypatch
):
    """The planted violation for the guard the audit added: a callback that
    returns `True` whatever it is handed cannot tell the approved envelope
    from any other, which is what let a previewed file drop leave over the
    network. This one is handed the shown `Wire`, then four that differ in
    exactly one way each."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _seed_courthouse_and_opposing_party(store)
    envelope = law_sync.preview(store, law_sync.scope_from(("custody",), None, "L3"))
    body = envelope.to_bytes()

    dest_url, dest_dir = law_sync.resolve_destination()
    shown = law_sync.describe_destination(
        envelope.envelope_id, dest_url=dest_url, dest_dir=dest_dir)
    confirm = law_sync.confirm_exactly(envelope, shown)
    path = shown.removeprefix("FILE ")

    assert confirm(Wire(method="FILE", url=path, body=f"{len(body)} bytes")) is True
    assert confirm(Wire(method="FILE", url=path, body=f"{len(body) + 1} bytes")) is False
    assert confirm(Wire(method="FILE", url="/tmp/elsewhere.json",
                        body=f"{len(body)} bytes")) is False
    assert confirm(Wire(method="POST", url="https://elsewhere.example/x",
                        body=json.dumps(envelope.to_dict()))) is False

    posted = law_sync.confirm_exactly(envelope, "POST https://fleet.example/ingest")
    assert posted(Wire(method="POST", url="https://fleet.example/ingest",
                       body=json.dumps(envelope.to_dict()))) is True
    assert posted(Wire(method="POST", url="https://fleet.example/ingest",
                       body=json.dumps({"envelope_id": "another"}))) is False
    assert posted(Wire(method="POST", url="https://fleet.example/ingest",
                       body="not json at all")) is False


# ── nothing here dials (I-17/I-30) ─────────────────────────────────────────

NETWORK_MODULES = {
    "urllib", "socket", "http", "httplib", "ssl", "ftplib", "smtplib",
    "requests", "httpx", "asyncio",
}


def _network_reaches(source: str) -> set[str]:
    """Every network module this source imports, and every dotted call into
    one. A *property* scan, not a spelling one: `import urllib.request` and
    `from urllib import request` and a bare `urlopen(...)` reached through
    an aliased module all land here, because the check is on the root name
    of the import and on the name a call's attribute chain starts from."""
    tree = ast.parse(source)
    found: set[str] = set()
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in NETWORK_MODULES:
                    found.add(alias.name)
                    aliases[(alias.asname or alias.name).split(".")[0]] = root
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in NETWORK_MODULES:
                found.add(node.module or "")
                for alias in node.names:
                    aliases[alias.asname or alias.name] = root
        elif isinstance(node, ast.Call):
            target = node.func
            while isinstance(target, ast.Attribute):
                target = target.value
            if isinstance(target, ast.Name) and target.id in aliases:
                found.add(f"{aliases[target.id]}(call)")
    return found


def test_homestead_law_sync_never_reaches_the_network_itself():
    """I-17/I-30: the one outbound path is the engine's `egress.send`, which
    lazy-imports `urllib` *inside* its own transport after a confirmed act.
    This module names a destination and hands it over; it opens nothing."""
    assert _network_reaches(SYNC_MODULE.read_text(encoding="utf-8")) == set()


def test_the_no_egress_scan_fires_on_a_planted_dial(tmp_path):
    """A scan that has never fired has not been shown to check anything.
    Plant the dial this module would be wrong to hold — a direct
    `urllib.request.urlopen` on the resolved destination — in a copy of the
    real file, and run the real scan over it."""
    planted = SYNC_MODULE.read_text(encoding="utf-8").replace(
        "def send_to(",
        "def _planted_dial(url, body):\n"
        "    import urllib.request\n"
        "    return urllib.request.urlopen(url, body)\n\n\n"
        "def send_to(",
        1,
    )
    assert "_planted_dial" in planted, "the plant must land in the real source"
    copy = tmp_path / "planted_sync.py"
    copy.write_text(planted, encoding="utf-8")

    reaches = _network_reaches(copy.read_text(encoding="utf-8"))
    assert "urllib.request" in reaches
    assert "urllib(call)" in reaches


def test_url_delivery_goes_only_through_the_engines_egress_send():
    """The one call that can dial is named, so a future edit that reaches
    past `keep/egress` shows up as a second one."""
    source = SYNC_MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    dialers = {
        node.func.id if isinstance(node.func, ast.Name) else node.func.attr
        for node in ast.walk(tree) if isinstance(node, ast.Call)
        and isinstance(node.func, (ast.Name, ast.Attribute))
    }
    assert "urlopen" not in dialers and "send" not in dialers
    assert "deliver" in dialers, "the engine's deliver() is the only outbound door"


# ── the household id ───────────────────────────────────────────────────────

def test_the_household_id_is_hh_plus_sixteen_hex_and_is_read_never_reminted(
    tmp_path, monkeypatch
):
    """I-9's shape: the file is created O_EXCL once and read back after. A
    second id would fork a household whose fleet rows are keyed by the
    first, so `--init-household` refuses rather than replacing it."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    minted = law_sync.init_household()
    assert re.fullmatch(r"hh-[0-9a-f]{16}", minted)

    with pytest.raises(law_sync.HouseholdAlreadyInitialized):
        law_sync.init_household()

    assert (tmp_path / "household.id").read_text().strip() == minted
    assert household_id() == minted == household_id()

    store = Sidecar()
    _seed_courthouse_and_opposing_party(store)
    envelope = law_sync.preview(store, law_sync.scope_from(("custody",), None, "L3"))
    assert envelope.household == minted


# ── a log that cannot be read refuses, by name, before delivering ──────────

def _seal_the_log() -> None:
    """One ciphertext-wrapper line in the integrity log, with no key beside
    it — the shape `keep/sealed.py` writes and `IntegrityLog._entries()`
    refuses to read without the key and the `sealed` extra."""
    engine_paths.logs_dir().mkdir(parents=True, exist_ok=True)
    (engine_paths.logs_dir() / "integrity.jsonl").write_text(
        json.dumps({"sealed": 1, "hash": "0" * 64, "prev": None,
                    "nonce": "x", "ct": "y"}) + "\n",
        encoding="utf-8",
    )


def test_a_sealed_log_refuses_by_name_before_anything_is_delivered(
    tmp_path, monkeypatch
):
    """The engine's `_already_delivered` cannot establish that an envelope
    was not already synced when the log is sealed and the key is absent, so
    `deliver()` raises rather than delivering twice (I-11/I-38). What this
    pins is that the refusal reaches a law caller *as a refusal*: nothing is
    written, and the CLI prints `refused:` instead of dying with a
    traceback."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _seed_courthouse_and_opposing_party(store)
    envelope = law_sync.preview(store, law_sync.scope_from(("custody",), None, "L3"))
    _seal_the_log()

    with pytest.raises(IntegritySealError):
        law_sync.send(envelope, confirm=lambda wire: True)
    assert not (engine_paths.exports_dir() / "sync").exists()


def test_cli_sync_refuses_a_sealed_log_by_name(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _seed_courthouse_and_opposing_party(store)
    _seal_the_log()
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt="": "yes")

    rc = run_cli(["sync", "--matters", "custody", "--ceiling", "L3"])

    assert rc == 1
    assert "refused:" in capsys.readouterr().err
    assert not (tmp_path / "exports" / "sync").exists()


# ── the CLI asks after it has shown the Wire, and shows the Wire itself ─────

def test_cli_sync_prints_the_wire_it_is_about_to_send_before_it_asks(
    tmp_path, monkeypatch, capsys
):
    """"The preview is the payload" (`keep/egress.py`), held at this door:
    the text printed before `input()` is `Wire.preview()` of the very object
    the engine hands its transport, not a separately-composed summary. The
    input is captured so the order — printed, then asked — is a fact of the
    test rather than a reading of the code."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    store = Sidecar()
    _seed_courthouse_and_opposing_party(store)
    envelope = law_sync.preview(store, law_sync.scope_from(("custody",), None, "L3"))
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

    seen_at_prompt = []

    def fake_input(prompt=""):
        seen_at_prompt.append(capsys.readouterr().out)
        return "yes"

    monkeypatch.setattr("builtins.input", fake_input)

    rc = run_cli(["sync", "--matters", "custody", "--ceiling", "L3"])

    assert rc == 0
    assert len(seen_at_prompt) == 1, "asked exactly once"
    shown = seen_at_prompt[0]
    expected = Wire(
        method="FILE",
        url=str(engine_paths.exports_dir().resolve() / "sync"
                / f"{envelope.envelope_id}.json"),
        body=f"{len(envelope.to_bytes())} bytes",
        content_type="text/plain",
    ).preview()
    assert expected in shown, "the Wire itself was shown before the yes"
