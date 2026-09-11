"""The browser UI — the door a household enters its own records through.

`server.build_server()` binds the real handlers on an ephemeral port without
serving, so this suite drives them end to end with `http.client`: store a field,
add a deadline, read both back through the gate. No Nestor is needed for any of
it (the `entity` extra is optional, and entering records never depended on it).

The invariants hold at the browser exactly as on the window: an L4 field lists
as its derived form and renders in the detail; an L5 field is never a row and the
detail refuses it; a deadline whose date the engine cannot read is refused at
entry rather than stored as a gap.
"""
from __future__ import annotations

import contextlib
import http.client
import json
import sys
import threading

import pytest

from homestead_law import nestor_seam, server


@pytest.fixture
def ui(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    srv = server.build_server(host="127.0.0.1", port=0)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()

    class _Client:
        host, port = srv.server_address[0], srv.server_address[1]

        def get(self, path):
            conn = http.client.HTTPConnection(self.host, self.port, timeout=5)
            conn.request("GET", path)
            resp = conn.getresponse()
            body = resp.read()
            conn.close()
            return resp.status, body

        def json(self, path, payload=None):
            conn = http.client.HTTPConnection(self.host, self.port, timeout=5)
            if payload is None:
                conn.request("GET", path)
            else:
                conn.request(
                    "POST", path, body=json.dumps(payload),
                    headers={"Content-Type": "application/json"},
                )
            resp = conn.getresponse()
            data = json.loads(resp.read())
            conn.close()
            return resp.status, data

    try:
        yield _Client()
    finally:
        srv.shutdown()
        srv.server_close()


def test_the_page_serves_and_carries_the_entry_form(ui):
    status, body = ui.get("/")
    assert status == 200
    page = body.decode()
    assert 'id="rmatter"' in page and 'id="rfield"' in page and 'id="rvalue"' in page
    assert "/api/store" in page and "/api/deadline" in page


def test_matters_lists_every_registered_field_with_its_declared_rung(ui):
    status, data = ui.json("/api/matters")
    assert status == 200
    custody = next(m for m in data["matters"] if m["name"] == "custody")
    fields = {f["name"]: f["rung"] for f in custody["fields"]}
    assert fields["courthouse"] == "L1"
    assert fields["child_name"] == "L4"
    assert fields["ssn"] == "L5"
    assert all(f["why"] for f in custody["fields"])


def test_matters_reports_the_supported_jurisdictions(ui):
    """Decision 1: `/api/matters` names each matter's default jurisdiction and
    the full set it may be filed in, read live off the registry (I-23) rather
    than a copy this handler keeps — the household's custody order moved from
    New Mexico to a registration in Oregon, and the browser UI's matter form
    needs both to ever offer a jurisdiction switch (Wave 3)."""
    status, data = ui.json("/api/matters")
    assert status == 200
    custody = next(m for m in data["matters"] if m["name"] == "custody")
    assert custody["jurisdiction"] == "US-NM"
    assert custody["jurisdictions"] == ["US-NM", "US-OR"]
    assert custody["jurisdiction"] in custody["jurisdictions"]


def test_store_then_records_round_trips_through_the_gate(ui):
    status, data = ui.json("/api/store", {"matter": "custody", "field": "courthouse", "value": "Dept 4"})
    assert status == 200 and data == {"ok": True, "rung": "L1", "replaced": False}
    status, data = ui.json("/api/store", {"matter": "custody", "field": "child_name", "value": "A. Rivera"})
    assert data["rung"] == "L4"
    status, data = ui.json("/api/store", {"matter": "custody", "field": "ssn", "value": "123-45-6789"})
    assert data["rung"] == "L5"

    status, data = ui.json("/api/records?matter=custody")
    rows = {r["item_type"]: r for r in data["rows"]}
    assert rows["courthouse"]["text"] == "Dept 4"
    assert rows["child_name"]["text"] == "A minor child is named in this matter"  # L4 derived
    assert "ssn" not in rows                                                       # L5, no row
    assert "123-45-6789" not in json.dumps(data)
    assert "A. Rivera" not in json.dumps(data)


def test_a_second_store_reports_the_replacement(ui):
    ui.json("/api/store", {"matter": "custody", "field": "courthouse", "value": "Dept 4"})
    status, data = ui.json("/api/store", {"matter": "custody", "field": "courthouse", "value": "Dept 5"})
    assert data["replaced"] is True
    status, data = ui.json("/api/records?matter=custody")
    assert [r["text"] for r in data["rows"]] == ["Dept 5"]


def test_the_detail_renders_the_l4_and_refuses_the_l5(ui):
    ui.json("/api/store", {"matter": "custody", "field": "child_name", "value": "A. Rivera"})
    ui.json("/api/store", {"matter": "custody", "field": "ssn", "value": "123-45-6789"})

    status, data = ui.json("/api/record?matter=custody&item_type=child_name")
    assert status == 200
    assert data["rendered"] is True and data["value"] == "A. Rivera" and data["rung"] == "L4"

    status, data = ui.json("/api/record?matter=custody&item_type=ssn")
    assert status == 200
    assert data["rendered"] is False and data["value"] is None
    assert "123-45-6789" not in json.dumps(data)


def test_the_detail_surfaces_an_advisory_for_hot_content_in_a_note(ui):
    ui.json("/api/store", {"matter": "custody", "field": "notes", "value": "SSN 123-45-6789 on the form"})
    status, data = ui.json("/api/record?matter=custody&item_type=notes")
    assert data["advisories"], "an SSN-shaped note declared L4 should draw an advisory"
    assert "123-45-6789" not in json.dumps(data["advisories"])


def test_store_refuses_an_unknown_field_an_unknown_matter_and_an_empty_value(ui):
    status, data = ui.json("/api/store", {"matter": "custody", "field": "bogus", "value": "x"})
    assert status == 400 and data["ok"] is False
    status, data = ui.json("/api/store", {"matter": "bogus", "field": "courthouse", "value": "x"})
    assert status == 400
    status, data = ui.json("/api/store", {"matter": "custody", "field": "courthouse", "value": "   "})
    assert status == 400


def test_a_deadline_lands_on_the_queue_and_in_the_records(ui):
    status, data = ui.json(
        "/api/deadline",
        {"matter": "custody", "id": "hearing", "date": "2099-10-01", "instruction": "Custody hearing"},
    )
    assert status == 200 and data == {"ok": True, "rung": "L1"}

    status, data = ui.json("/api/queue")
    assert [i["shown"] for i in data["items"]] == ["2099-10-01"]
    assert data["items"][0]["overdue"] is False

    status, data = ui.json("/api/records?matter=custody")
    assert any(r["item_type"] == "deadline" and r["item_id"] == "hearing" for r in data["rows"])


def test_an_l4_deadline_shows_its_instruction_on_the_queue_never_its_date(ui):
    ui.json("/api/deadline", {"matter": "custody", "id": "evaluation", "date": "2099-08-12",
                              "rung": "L4", "instruction": "A submission is due"})
    status, data = ui.json("/api/queue")
    assert data["items"][0]["shown"] == "A submission is due"
    assert "2099-08-12" not in json.dumps(data)


def test_a_deadline_with_an_unreadable_date_is_refused_at_entry(ui):
    status, data = ui.json("/api/deadline", {"matter": "custody", "id": "x", "date": "next Tuesday"})
    assert status == 400 and data["ok"] is False
    status, data = ui.json("/api/deadline", {"matter": "custody", "id": "x", "date": "2026-13-45"})
    assert status == 400
    status, data = ui.json("/api/queue")
    assert data["items"] == []


def test_a_deadline_needs_an_id_and_refuses_l5(ui):
    status, data = ui.json("/api/deadline", {"matter": "custody", "id": "", "date": "2099-01-01"})
    assert status == 400
    status, data = ui.json("/api/deadline", {"matter": "custody", "id": "a", "date": "2099-01-01", "rung": "L5"})
    assert status == 400
    status, data = ui.json("/api/deadline", {"matter": "custody", "id": "../x", "date": "2099-01-01"})
    assert status == 400


def test_status_says_whether_nestor_is_available(ui):
    status, data = ui.json("/api/status")
    assert status == 200
    assert isinstance(data["nestor"], bool)
    assert "custody" in data["matters"]


def test_intake_extracts_without_storing(ui):
    status, data = ui.json("/api/extract", {"text": "Hearing on 2026-09-15, Case No. FL-2026-00123"})
    kinds = {i["kind"] for i in data["items"]}
    assert "date" in kinds and "case_number" in kinds
    status, data = ui.json("/api/records?matter=custody")
    assert data["rows"] == []


def test_the_server_is_bound_to_localhost_only(ui):
    assert ui.host == "127.0.0.1"


# ── the audit's attack list ────────────────────────────────────────────────
#
# Everything below is a way in that the first version of this door left open.
# The `matter` default is the headline (BUG-6's shape: a matter name written
# down outside the registry), and the rest are the shapes a local HTTP handler
# fails in — a body it cannot read, a body too large to read, a value that is
# not the type it was assumed to be, and a stored key spliced into the page's
# own JavaScript.


@contextlib.contextmanager
def _serve():
    """A second door onto `build_server`, for tests that must patch something
    *before* the handlers close over it — the Nestor seam is bound inside
    `build_server`, so by the time the `ui` fixture yields, it has decided."""
    srv = server.build_server(host="127.0.0.1", port=0)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()

    class _C:
        host, port = srv.server_address[0], srv.server_address[1]

        def json(self, path, payload=None):
            return _request(self, "GET" if payload is None else "POST", path,
                            body=None if payload is None else json.dumps(payload),
                            parse=True)

    try:
        yield _C()
    finally:
        srv.shutdown()
        srv.server_close()


def _request(client, method, path, body=None, headers=None, parse=False):
    """One request, answered as (status, bytes) — no JSON assumed, because half
    of these are about bodies that are not JSON."""
    conn = http.client.HTTPConnection(client.host, client.port, timeout=5)
    try:
        conn.request(method, path, body=body, headers=headers or {})
        resp = conn.getresponse()
        raw = resp.read()
        return resp.status, (json.loads(raw) if parse else raw)
    finally:
        conn.close()


def test_store_and_deadline_refuse_a_missing_matter_rather_than_defaulting(ui):
    """A matter is required on both writing doors. `body.get("matter", "custody")`
    was BUG-6's shape in miniature — a matter name written down outside the
    registry — and it meant a caller that forgot the field, or sent an empty one,
    silently filed the record under custody. A household with a bankruptcy and a
    workers' comp claim would find the record in the wrong matter, with nothing
    anywhere saying so. Absence refuses by name (I-11); it never defaults."""
    for payload in (
        {"field": "courthouse", "value": "Dept 4"},                    # absent
        {"matter": "", "field": "courthouse", "value": "Dept 4"},      # empty
        {"matter": "   ", "field": "courthouse", "value": "Dept 4"},   # whitespace
        {"matter": None, "field": "courthouse", "value": "Dept 4"},    # null
    ):
        status, data = ui.json("/api/store", payload)
        assert status == 400, f"{payload!r} was accepted"
        assert data["ok"] is False
        assert "matter" in data["error"]

    for payload in (
        {"id": "hearing", "date": "2099-10-01"},
        {"matter": "", "id": "hearing", "date": "2099-10-01"},
        {"matter": None, "id": "hearing", "date": "2099-10-01"},
    ):
        status, data = ui.json("/api/deadline", payload)
        assert status == 400, f"{payload!r} was accepted"
        assert data["ok"] is False
        assert "matter" in data["error"]

    # and nothing was filed under the default
    status, data = ui.json("/api/records?matter=custody")
    assert data["rows"] == []
    status, data = ui.json("/api/queue")
    assert data["items"] == []


def test_the_page_names_no_matter_of_its_own(ui):
    """The JS fallback was `||'custody'` — the same literal, in the other half of
    the same door. It now reads the selected matter, else the first matter
    `/api/matters` returned (the registry, I-23), and refuses when there is
    none."""
    page = ui.get("/")[1].decode()
    assert "'custody'" not in page and '"custody"' not in page, (
        "the page names a matter; the registry is the only enumeration (I-23)"
    )
    assert "function currentMatter()" in page
    assert page.count("currentMatter()") >= 4      # both forms, intake, the list


def test_a_body_the_server_cannot_read_is_refused_not_a_traceback(ui):
    """Malformed JSON, a non-object body, and bytes that are not UTF-8. Each used
    to raise out of `do_POST` — a traceback on the console and a reset connection,
    which the page shows as a bare 'Error' with no reason."""
    for path in ("/api/store", "/api/deadline", "/api/extract"):
        for body in (b"{not json", b'"a string"', b"[1,2,3]", b"\xff\xfe\x00"):
            conn = http.client.HTTPConnection(ui.host, ui.port, timeout=5)
            conn.request("POST", path, body=body,
                         headers={"Content-Type": "application/json"})
            resp = conn.getresponse()
            payload = json.loads(resp.read())
            conn.close()
            assert resp.status == 400, f"{path} accepted {body!r}"
            assert payload["error"]


def test_a_content_length_that_is_not_a_number_is_refused(ui):
    """`int(self.headers.get("Content-Length", 0))` raised `ValueError` on
    anything else a client chose to put there — again a traceback, not an answer."""
    for length in ("abc", "-1", "1e6", ""):
        status, raw = _request(
            ui, "POST", "/api/store", body=b"{}",
            headers={"Content-Type": "application/json", "Content-Length": length},
        )
        assert status == 400, f"Content-Length {length!r} was accepted"
        assert json.loads(raw)["error"]


def test_an_oversized_body_is_refused_with_413_and_never_read(ui):
    """A local page has no use for a megabyte of JSON, and reading whatever
    `Content-Length` claims is the one place it can spend the household's RAM.
    The cap refuses before the read, so the claim costs nothing to make."""
    oversized = server.MAX_BODY_BYTES + 1
    status, raw = _request(
        ui, "POST", "/api/store", body=b"{}",
        headers={"Content-Type": "application/json", "Content-Length": str(oversized)},
    )
    assert status == 413
    assert str(server.MAX_BODY_BYTES) in json.loads(raw)["error"]

    # a body just under the cap is still read, and refused on its merits
    status, data = ui.json(
        "/api/store", {"matter": "custody", "field": "bogus", "value": "x" * 2048})
    assert status == 400 and "bogus" in data["error"]


def test_a_post_with_no_body_at_all_refuses_by_name(ui):
    """No `Content-Length` is an empty object, which then fails the `matter`
    check — a refusal naming the missing field, not a 500."""
    status, raw = _request(ui, "POST", "/api/store")
    assert status == 400
    assert "matter" in json.loads(raw)["error"]


def test_a_value_that_is_not_a_string_is_refused_rather_than_coerced(ui):
    """`str(value)` turned `["custody"]` into `"['custody']"` and a dict into a
    key the store would have taken. A surface that coerces has decided something
    the operator did not type; worse, `matter(["custody"])` reached `REGISTRY[…]`
    with an unhashable key and died with a `TypeError` on the console."""
    for payload in (
        {"matter": ["custody"], "field": "courthouse", "value": "x"},
        {"matter": {"n": "custody"}, "field": "courthouse", "value": "x"},
        {"matter": "custody", "field": ["courthouse"], "value": "x"},
        {"matter": "custody", "field": "courthouse", "value": 42},
        {"matter": "custody", "field": "courthouse", "value": {"a": 1}},
    ):
        status, data = ui.json("/api/store", payload)
        assert status == 400, f"{payload!r} was accepted"
        assert "must be a string" in data["error"]

    for payload in (
        {"matter": "custody", "id": 7, "date": "2099-01-01"},
        {"matter": "custody", "id": "a", "date": ["2099-01-01"]},
        {"matter": "custody", "id": "a", "date": "2099-01-01", "rung": ["L1"]},
        # a dict instruction reached `Classified(…, derived=…)`, whose
        # `UnclassifiedField` is caught nowhere here — a 500 with a traceback.
        {"matter": "custody", "id": "a", "date": "2099-01-01", "rung": "L4",
         "instruction": {"text": "x"}},
    ):
        status, data = ui.json("/api/deadline", payload)
        assert status == 400, f"{payload!r} was accepted"
        assert "must be a string" in data["error"]

    status, data = ui.json("/api/extract", {"text": 5})
    assert status == 400 and "must be a string" in data["error"]


def test_a_key_the_engine_refuses_is_a_400_on_every_door_that_builds_one(ui):
    """`InvalidKey` is a `ValueError` out of `homestead.keep.store.key()`. Every
    place this module hands a caller-supplied component to the store catches it:
    unstopped it is a traceback on the write door and a 500 on the read door."""
    for bad in ("../x", "a/b", "a\\b", ".", "..", "a\x00b"):
        status, data = ui.json(
            "/api/deadline", {"matter": "custody", "id": bad, "date": "2099-01-01"})
        assert status == 400, f"id {bad!r} was accepted"
        assert data["ok"] is False

    for bad in ("../x", "a%2Fb", "", "%20%20"):
        status, data = ui.json(
            f"/api/record?matter=custody&item_type=deadline&item_id={bad}")
        assert status in (400, 404), f"item_id {bad!r} was accepted"
        assert data["error"]


def test_a_stored_key_never_reaches_the_page_as_javascript(ui):
    """The engine's `key()` refuses separators, NUL and surrounding whitespace —
    and nothing else. A quote is a legal item id, so `deadline/it's-due` is a
    record a household can really create; the list used to splice that id into
    `onclick="openRecord('…')"`, where an attribute value is entity-decoded
    *before* the script is parsed. No escaping of the id survives that, so the id
    does not go there at all: the key rides in `data-` attributes and the click
    is bound afterwards."""
    # A quote and nothing the key validator refuses: no separator, no NUL, no
    # surrounding whitespace.  Spliced into `openRecord('…')` this closes the
    # literal and runs.
    hostile = "x');alert(1);a='"
    status, data = ui.json(
        "/api/deadline",
        {"matter": "custody", "id": hostile, "date": "2099-10-01"})
    assert status == 200, "a quote is a valid key component — this id is reachable"

    status, data = ui.json("/api/records?matter=custody")
    assert any(r["item_id"] == hostile for r in data["rows"])

    page = ui.get("/")[1].decode()
    assert 'onclick="openRecord(' not in page and "onclick='openRecord(" not in page
    assert "data-id=\"'+esc(row.item_id)+'\"" in page
    assert "addEventListener('click'" in page


def test_the_esc_helper_escapes_every_character_that_ends_an_attribute():
    """The old `esc` was a textContent/innerHTML round-trip, which escapes `&`,
    `<` and `>` and leaves both quotes alone — so any value reaching a quoted
    attribute could close it. Read the table out of the page rather than trusting
    the prose."""
    import re

    table = re.search(r"var _ESC=\{(.*?)\};", server._PAGE, re.S)
    assert table, "the page has no escape table to check"
    for char, entity in (("&", "amp"), ("<", "lt"), (">", "gt"),
                         ('"', "quot"), ("'", "#39")):
        assert entity in table.group(1), f"{char!r} is not escaped by esc()"


# ── the Nestor seam, absent and failing ────────────────────────────────────


def test_without_the_entity_extra_the_nestor_doors_refuse_and_the_rest_works(
    tmp_path, monkeypatch,
):
    """`nestor_ok=False` is the checkout most households have. `/api/resolve`
    must say so with a 503 and `/api/orders` must answer an empty list — neither
    may raise, and neither may take the *record* doors down with it, which is the
    whole promise of the extra being optional."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    # `None` in sys.modules makes `import nestor` raise and `find_spec` return
    # None — the extra is absent, on an installed checkout too.
    monkeypatch.setitem(sys.modules, "nestor", None)
    monkeypatch.setattr(nestor_seam, "_bound", False)

    with _serve() as client:
        status, data = client.json("/api/status")
        assert status == 200 and data["nestor"] is False

        status, data = client.json("/api/resolve?domain=party&surface=Someone")
        assert status == 503
        assert "nestor-meaning" in data["error"]

        status, data = client.json("/api/orders")
        assert status == 200 and data["decisions"] == []

        # the record doors are untouched
        status, data = client.json(
            "/api/store", {"matter": "custody", "field": "courthouse", "value": "Dept 4"})
        assert status == 200 and data["ok"] is True
        status, data = client.json("/api/records?matter=custody")
        assert [r["text"] for r in data["rows"]] == ["Dept 4"]


def test_a_failure_inside_the_seam_never_echoes_its_exception_text(
    tmp_path, monkeypatch,
):
    """I-15, on the error path. Nestor's store holds the household's own party
    and court names, so an exception raised out of it can carry one; `str(exc)`
    in a JSON body is a value crossing a surface that never scored it. The
    refusal names *where* it happened — a reference — and nothing else."""
    monkeypatch.setenv("HOMESTEAD_HOME", str(tmp_path))
    monkeypatch.setattr(nestor_seam, "bind", lambda root=None: tmp_path / "ledger.jsonl")

    secret = "A. Rivera"

    def boom(*_a, **_k):
        raise RuntimeError(f"no alias sealed for {secret}")

    # Patched before `build_server`, which closes over these names.
    import homestead_law.nestor_store as nestor_store

    monkeypatch.setattr(nestor_store, "get_store", boom)

    with _serve() as client:
        status, data = client.json("/api/resolve?domain=party&surface=Someone")
        assert status == 500
        assert secret not in json.dumps(data), "the resolver echoed a stored name"
        assert "party" in data["error"]

        status, data = client.json("/api/orders")
        assert data["decisions"] == []
        assert secret not in json.dumps(data)


# ── I-19: the server writes only inside the household root ─────────────────


def test_build_server_makes_no_directory_outside_the_household_root(
    tmp_path, monkeypatch,
):
    """`build_server()` mkdirs the root and `<root>/keep` on the way up. I-19
    says `paths.home()` is the one resolver, and a surface that mkdirs anywhere
    else has written outside everything this module's rules reach — which is
    exactly the unbound-ledger failure `nestor_seam.bind` exists to close."""
    root = tmp_path / "root"
    monkeypatch.setenv("HOMESTEAD_HOME", str(root))
    made = []
    real_mkdir = type(tmp_path).mkdir

    def spy(self, *a, **kw):
        made.append(self)
        return real_mkdir(self, *a, **kw)

    monkeypatch.setattr(type(tmp_path), "mkdir", spy)

    srv = server.build_server(host="127.0.0.1", port=0)
    srv.server_close()

    assert made, "build_server no longer creates the root — has the spy stopped firing?"
    outside = [p for p in made if root != p and root not in p.parents]
    assert not outside, f"build_server created {outside} outside the household root"


# ── I-16: nothing crosses below its rung, by any route ─────────────────────


def test_a_replacement_never_carries_the_previous_value(ui):
    """`Sidecar.put(overwrite=True)` hands back a `Replaced`, which carries the
    displaced `Classified` — payload and all. The response says *that* something
    was replaced and never what: reaching `replaced.previous` here would put an
    L4 payload into a JSON body that scored nothing."""
    ui.json("/api/store", {"matter": "custody", "field": "child_name", "value": "A. Rivera"})
    status, data = ui.json(
        "/api/store", {"matter": "custody", "field": "child_name", "value": "B. Okafor"})

    assert status == 200 and data == {"ok": True, "rung": "L4", "replaced": True}
    assert "A. Rivera" not in json.dumps(data)

    ui.json("/api/store", {"matter": "custody", "field": "ssn", "value": "123-45-6789"})
    status, data = ui.json(
        "/api/store", {"matter": "custody", "field": "ssn", "value": "987-65-4321"})
    assert data == {"ok": True, "rung": "L5", "replaced": True}
    assert "123-45-6789" not in json.dumps(data)


def test_a_sealed_deadline_planted_by_hand_never_reaches_the_queue_json(ui, tmp_path):
    """The write door refuses an L5 deadline, so the read door is never asked to
    gate one — which is exactly the assumption worth breaking. Plant it straight
    into the store, under the door, and read the queue back: a sealed deadline
    leaves no row and no count, not even a placeholder saying one was withheld."""
    from homestead.keep.rungs import Classified, Rung
    from homestead_law.store import Sidecar

    Sidecar().put("custody", "deadline", "sealed",
                  Classified(Rung.L5, "2099-03-04"), overwrite=True)
    Sidecar().put("custody", "deadline", "open",
                  Classified(Rung.L1, "2099-03-05"), overwrite=True)

    status, data = ui.json("/api/queue")
    assert [i["shown"] for i in data["items"]] == ["2099-03-05"]
    assert "2099-03-04" not in json.dumps(data)
    assert "sealed" not in json.dumps(data)

    status, data = ui.json("/api/records?matter=custody")
    assert [r["item_id"] for r in data["rows"]] == ["open"]
    assert "2099-03-04" not in json.dumps(data)

    status, data = ui.json(
        "/api/record?matter=custody&item_type=deadline&item_id=sealed")
    assert status == 200
    assert data["rendered"] is False and data["value"] is None
    assert "2099-03-04" not in json.dumps(data)
