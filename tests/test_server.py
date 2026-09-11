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
import time
import types

import pytest

from homestead.keep.rungs import Rung
from homestead_law import nestor_seam, server
from homestead_law import registry as registry_mod


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
    fake.SCHEMA = {"case_number": {"rung": Rung.L1, "matter": name, "why": "fake"}}
    monkeypatch.setitem(registry_mod.REGISTRY, name, registry_mod._entry(fake))


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


@pytest.mark.parametrize("with_second_matter", [False, True])
def test_matters_lists_every_registered_matter(with_second_matter, ui, monkeypatch):
    """`/api/matters` reads the registry live (I-23), not a hand-kept list of
    one. Custody is real and stays named by hand; the `with_second_matter` case
    injects a fake one and checks `/api/matters` lists both, so this test does
    not quietly stop proving the loop once a second matter is real."""
    if with_second_matter:
        _register_second_matter(monkeypatch)

    status, data = ui.json("/api/matters")
    assert status == 200
    names = {m["name"] for m in data["matters"]}
    assert "custody" in names
    if with_second_matter:
        assert "_fake_second" in names


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
    # `id` with no `sub` is the deadline's name under the default instance, so
    # the stored key is instance-addressed: `primary.hearing`.
    assert any(
        r["item_type"] == "deadline" and r["item_id"] == "primary.hearing"
        for r in data["rows"]
    )


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


# ── L2b-instances: /api/instances and /api/matter/open ──────────────────────

def test_matter_open_stores_jurisdiction_and_instances_lists_it(ui):
    status, data = ui.json(
        "/api/matter/open", {"matter": "custody", "id": "primary", "jurisdiction": "US-NM"})
    assert status == 200 and data == {"ok": True, "replaced": False}

    status, data = ui.json("/api/instances?matter=custody")
    assert status == 200
    assert data["instances"] == [{"id": "primary", "jurisdiction": "US-NM"}]


def test_instances_lists_a_matter_with_nothing_open_as_empty(ui):
    status, data = ui.json("/api/instances?matter=custody")
    assert status == 200 and data["instances"] == []


def test_instances_never_carries_l3_or_higher_content(ui):
    """The endpoint's own contract: codes only. A field entered under the
    instance must not leak into `/api/instances`, whatever its rung."""
    ui.json("/api/matter/open", {"matter": "custody", "id": "primary", "jurisdiction": "US-NM"})
    ui.json("/api/store", {"matter": "custody", "field": "child_name", "value": "A. Rivera"})

    status, data = ui.json("/api/instances?matter=custody")
    assert status == 200
    assert "A. Rivera" not in json.dumps(data)
    assert data["instances"] == [{"id": "primary", "jurisdiction": "US-NM"}]


def test_instances_refuses_an_unknown_matter(ui):
    status, data = ui.json("/api/instances?matter=bogus")
    assert status == 400 and "bogus" in data["error"]


def test_matter_open_refuses_a_code_outside_the_pack(ui):
    status, data = ui.json(
        "/api/matter/open", {"matter": "custody", "id": "primary", "jurisdiction": "US-CA"})
    assert status == 400 and data["ok"] is False
    assert "US-CA" in data["error"]

    status, data = ui.json("/api/instances?matter=custody")
    assert data["instances"] == []


def test_matter_open_twice_refuses_without_replace(ui):
    ui.json("/api/matter/open", {"matter": "custody", "id": "primary", "jurisdiction": "US-NM"})
    status, data = ui.json(
        "/api/matter/open", {"matter": "custody", "id": "primary", "jurisdiction": "US-OR"})
    assert status == 409 and data["ok"] is False

    status, data = ui.json("/api/instances?matter=custody")
    assert data["instances"] == [{"id": "primary", "jurisdiction": "US-NM"}]

    status, data = ui.json(
        "/api/matter/open",
        {"matter": "custody", "id": "primary", "jurisdiction": "US-OR", "replace": True})
    assert status == 200 and data["replaced"] is True
    status, data = ui.json("/api/instances?matter=custody")
    assert data["instances"] == [{"id": "primary", "jurisdiction": "US-OR"}]


def test_matter_open_refuses_a_missing_matter_id_or_jurisdiction(ui):
    for payload in (
        {"id": "primary", "jurisdiction": "US-NM"},
        {"matter": "custody", "jurisdiction": "US-NM"},
        {"matter": "custody", "id": "primary"},
    ):
        status, data = ui.json("/api/matter/open", payload)
        assert status == 400, f"{payload!r} was accepted"
        assert data["ok"] is False


def test_the_queue_names_the_instance_by_reference(ui):
    ui.json("/api/deadline", {"matter": "custody", "id": "primary", "sub": "hearing",
                              "date": "2099-10-01"})
    status, data = ui.json("/api/queue")
    assert status == 200
    assert data["items"][0]["instance"] == "primary"


def test_deadline_sub_composes_a_dotted_item_id(ui):
    """`sub` is new and optional; given, the stored item id is
    `instances.item_id(id, sub)` — `"<id>.<sub>"` — so a second instance can
    carry its own `hearing` without colliding with the first."""
    ui.json("/api/deadline", {"matter": "custody", "id": "primary", "sub": "hearing",
                              "date": "2099-10-01"})
    status, data = ui.json("/api/records?matter=custody")
    assert any(r["item_id"] == "primary.hearing" for r in data["rows"])


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


class _Sock:
    """A socket that hands out the chunks it was given, then whatever
    `then` is — `b""` for a peer that closed, or an exception to raise."""

    def __init__(self, chunks, then=b""):
        self.chunks = list(chunks)
        self.then = then
        self.timeout = None
        self.asked = []

    def settimeout(self, t):
        self.timeout = t

    def recv(self, n):
        self.asked.append(n)
        if self.chunks:
            head, rest = self.chunks[0][:n], self.chunks[0][n:]
            if rest:
                self.chunks[0] = rest
            else:
                self.chunks.pop(0)
            return head
        if isinstance(self.then, BaseException):
            raise self.then
        return self.then


def test_a_refused_body_is_drained_before_the_socket_closes():
    """Closing a socket with unread bytes in its receive buffer turns the
    close into a reset, and on Windows a reset discards the 400 the client
    has not read yet (`WinError 10053`, seen on the release PR's Windows leg
    for exactly this test's neighbour).  The drain reads what arrived, waits
    only `DRAIN_TIMEOUT_SECONDS` for more, is bounded by the body cap, and
    swallows the socket's own errors — the answer is already sent."""
    # the whole body arrived, then the peer closed
    sock = _Sock([b"{}", b"more"])
    assert server._drain(sock) == 6
    assert sock.timeout == server.DRAIN_TIMEOUT_SECONDS
    # nothing more arrives within the wait: the timeout is swallowed
    sock = _Sock([b"{}"], then=TimeoutError())
    assert server._drain(sock) == 2
    # a peer that never stops sending is cut off at the cap, never read past it
    sock = _Sock([b"x" * 65536] * 40)
    assert server._drain(sock, limit=100_000) == 100_000
    assert max(sock.asked) <= 65536 and sum(sock.asked) >= 100_000
    # a socket that is already gone is not an error
    sock = _Sock([], then=OSError())
    assert server._drain(sock) == 0


@pytest.mark.parametrize(
    "path", ["/api/store", "/api/deadline", "/api/matter/open"])
def test_a_refused_content_length_reaches_the_drain(path, ui, monkeypatch):
    """The refusal path must actually call the drain on the live connection —
    the unit test above proves what draining does, this proves it happens,
    once, after the answer is on the wire (the client read a 400).  The client
    can hold its 400 before the handler thread reaches the drain, so the check
    waits for the call rather than asserting the instant the answer lands.

    Over every POST door, including the one L2b added: they share one
    `try`/`except _BadRequest` today, and a door added outside it would refuse
    without draining and reset the socket — which is exactly the shape this
    test exists to catch, so it enumerates the doors rather than one of them."""
    calls = []
    real = server._drain

    def _spy(sock, **kw):
        calls.append(sock)
        return real(sock, **kw)

    monkeypatch.setattr(server, "_drain", _spy)
    status, raw = _request(
        ui, "POST", path, body=b"{}",
        headers={"Content-Type": "application/json", "Content-Length": "abc"},
    )
    assert status == 400 and json.loads(raw)["error"]
    deadline = time.monotonic() + 5
    while not calls and time.monotonic() < deadline:
        time.sleep(0.01)
    assert len(calls) == 1 and hasattr(calls[0], "recv")


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


def test_a_stored_key_never_reaches_the_page_as_javascript(ui, tmp_path):
    """The engine's `key()` refuses separators, NUL and surrounding whitespace —
    and nothing else. A quote is a legal item id, so `deadline/it's-due` is a
    record that can really sit in this store; the list used to splice that id
    into `onclick="openRecord('…')"`, where an attribute value is entity-decoded
    *before* the script is parsed. No escaping of the id survives that, so the id
    does not go there at all: the key rides in `data-` attributes and the click
    is bound afterwards.

    **The plant moved from the deadline door to the store** when L2b's audit
    ruled that every deadline id must be instance-shaped: `/api/deadline` now
    refuses this id (see the 400 asserted below), so posting it would no longer
    put it on disk. That makes this regression *stronger*, not weaker — the
    guarantee was never "the write doors are strict", it was "whatever key is
    on disk, the page does not execute it", and a key can reach this store from
    a database written before the instance convention, another tool, or a
    restore. Planting through `Sidecar` is exactly that key, with no door's
    validation standing in for the page's escaping."""
    from homestead.keep.rungs import Classified, Rung
    from homestead_law.store import Sidecar

    # A quote and nothing the key validator refuses: no separator, no NUL, no
    # surrounding whitespace.  Spliced into `openRecord('…')` this closes the
    # literal and runs.
    hostile = "x');alert(1);a='"

    # The write door refuses it — an id that cannot be split is a deadline no
    # instance can own (L2b audit, decision 2).
    status, data = ui.json(
        "/api/deadline",
        {"matter": "custody", "id": hostile, "date": "2099-10-01"})
    assert status == 400 and data["ok"] is False
    assert hostile not in data["error"], "a refusal never echoes what was typed"

    # …and it is still on disk-reachable, so the page still has to be safe.
    # `ui` points HOMESTEAD_HOME at tmp_path, so this is the server's own store.
    Sidecar().put(
        "custody", "deadline", hostile,
        Classified(Rung.L1, "2099-10-01"), overwrite=True,
    )
    status, data = ui.json("/api/records?matter=custody")
    assert any(r["item_id"] == hostile for r in data["rows"])

    page = ui.get("/")[1].decode()
    assert 'onclick="openRecord(' not in page and "onclick='openRecord(" not in page
    assert "data-id=\"'+esc(row.item_id)+'\"" in page
    assert "addEventListener('click'" in page


def test_a_hostile_value_reaches_the_page_only_through_esc(ui):
    """The other half, where the XSS surface actually is now that keys are
    shaped: a *value* is free text at any rung the pack declares, so an L1
    field really can hold `<img src=x onerror=…>`. It must leave `/api/records`
    unmangled (the store is not an escaper) and reach the page only through
    `esc`, never spliced into an attribute or a script."""
    hostile = "\"><img src=x onerror=alert(1)>"
    status, _ = ui.json(
        "/api/store",
        {"matter": "custody", "field": "courthouse", "value": hostile})
    assert status == 200

    status, data = ui.json("/api/records?matter=custody")
    row = next(r for r in data["rows"] if r["item_type"] == "courthouse")
    assert row["text"] == hostile, "the store neither escapes nor strips"

    page = ui.get("/")[1].decode()
    # every row field the list draws goes through esc(), and esc() escapes both
    # quotes (pinned by test_the_esc_helper_escapes_every_character_…).
    assert "esc(row.text)" in page or "esc(r.text)" in page


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


def test_matter_open_refuses_a_replace_that_is_not_a_boolean(ui):
    """I-9 on the JSON door. `bool("false")` is `True`, so a coerced `replace`
    is unconsented overwrite: the operator (or the page) says the word "false"
    and the instance's jurisdiction is rewritten anyway. `_text` already refuses
    to coerce a string field for exactly this reason; the consent flag is held
    to the same rule."""
    assert ui.json(
        "/api/matter/open",
        {"matter": "custody", "id": "primary", "jurisdiction": "US-NM"})[0] == 200

    for bogus in ("false", "no", 0, 1, [], {}):
        status, data = ui.json(
            "/api/matter/open",
            {"matter": "custody", "id": "primary", "jurisdiction": "US-OR",
             "replace": bogus},
        )
        assert status == 400, f"replace={bogus!r} was coerced"
        assert data["ok"] is False and "replace" in data["error"]

    # …and nothing was rewritten by any of them.
    status, data = ui.json("/api/instances?matter=custody")
    assert data["instances"] == [{"id": "primary", "jurisdiction": "US-NM"}]

    status, data = ui.json(
        "/api/matter/open",
        {"matter": "custody", "id": "primary", "jurisdiction": "US-OR",
         "replace": True})
    assert status == 200 and data["replaced"] is True


def test_instances_refuses_a_matter_holding_an_unaddressable_id(ui):
    """On the branch as built this was a 500 and a dropped connection: the key
    scan returned an id `item_id` refuses, `jurisdiction_of` raised `InvalidId`
    through the handler, and one free-form deadline took `/api/instances` down.
    It is a 400 naming the matter and the item type now — and never the id."""
    from homestead.keep.rungs import Classified, Rung
    from homestead_law.store import Sidecar

    Sidecar().put(
        "custody", "deadline", "it's-due",
        Classified(Rung.L1, "2099-10-01"), overwrite=True,
    )
    status, data = ui.json("/api/instances?matter=custody")
    assert status == 400
    assert "deadline" in data["error"] and "it's-due" not in data["error"]


def test_the_deadline_door_is_instance_addressed(ui):
    """`id` with no `sub` is the deadline's *name* under the default instance,
    so the page's existing form is unchanged and what it writes is
    `primary.<id>`; `id` + `sub` names another instance. Either way the stored
    key splits, which is what `/api/instances` and L3-deadline-templates'
    `(matter, "deadline", "<inst>.<template>")` both need."""
    assert ui.json("/api/deadline", {
        "matter": "custody", "id": "hearing", "date": "2099-10-01"})[0] == 200
    assert ui.json("/api/deadline", {
        "matter": "custody", "id": "or-order", "sub": "hearing",
        "date": "2099-11-01"})[0] == 200

    status, data = ui.json("/api/records?matter=custody")
    stored = {r["item_id"] for r in data["rows"] if r["item_type"] == "deadline"}
    assert stored == {"primary.hearing", "or-order.hearing"}

    status, data = ui.json("/api/instances?matter=custody")
    assert {i["id"] for i in data["instances"]} == {"primary", "or-order"}
    # neither instance has been opened, so neither has a jurisdiction (I-42)
    assert all(i["jurisdiction"] is None for i in data["instances"])

    status, data = ui.json("/api/queue")
    assert {i["instance"] for i in data["items"]} == {"primary", "or-order"}


@pytest.mark.parametrize("bad", ["it's-due", "Hearing", "has_underscore", "a.b"])
def test_the_deadline_door_refuses_a_free_form_id_by_name(bad, ui):
    """Engine-legal, instance-illegal — refused with a 400 that names the shape
    and never repeats what was posted (I-15), and nothing stored."""
    status, data = ui.json(
        "/api/deadline", {"matter": "custody", "id": bad, "date": "2099-10-01"})
    assert status == 400 and data["ok"] is False
    assert bad not in data["error"]

    status, data = ui.json("/api/records?matter=custody")
    assert not [r for r in data["rows"] if r["item_type"] == "deadline"]


# ── L3-custody-relocation: repeatable fields at the browser door ─────────────

def test_api_matters_says_which_fields_take_a_sub_id(ui):
    """The form has to know, and it may not keep its own copy of the answer
    (I-23): `repeatable` comes off the pack's own `REPEATABLE`, live. Without
    it the page would offer `child.name` in the field list and then be
    refused by `/api/store` with no way for the operator to comply."""
    status, data = ui.json("/api/matters")
    assert status == 200
    custody = next(m for m in data["matters"] if m["name"] == "custody")
    flags = {f["name"]: f["repeatable"] for f in custody["fields"]}
    assert flags["child.name"] is True
    assert flags["child.dob"] is True
    assert flags["child.school"] is True
    assert flags["courthouse"] is False
    assert flags["child_name"] is False       # the singular field being retired
    assert "id=\"rsub\"" in ui.get("/")[1].decode()


def test_store_refuses_a_repeatable_field_without_a_sub_id(ui):
    """The browser half of the CLI's refusal. Filing `child.name` at the
    instance's single slot is the overwrite-the-first-child failure the
    sub-id exists to abolish, so the door refuses by field name, echoes no
    value (I-15), and stores nothing."""
    status, data = ui.json(
        "/api/store",
        {"matter": "custody", "field": "child.name", "value": "Alex Rivera"})
    assert status == 400
    assert data["ok"] is False
    assert "child.name" in data["error"] and "sub id" in data["error"]
    assert "Alex Rivera" not in json.dumps(data)

    status, records = ui.json("/api/records?matter=custody")
    assert status == 200
    assert records["rows"] == []


def test_store_accepts_a_repeatable_field_with_a_sub_id(ui):
    """…and the same field with a sub id goes on file under
    `"<instance>.<sub>"`, one record per child, listed as its derived form
    because it is L4."""
    for sub, value in (("c1", "Alex Rivera"), ("c2", "Robin Rivera")):
        status, data = ui.json(
            "/api/store",
            {"matter": "custody", "field": "child.name", "value": value, "sub": sub})
        assert status == 200 and data["ok"] is True, data
        assert data["rung"] == "L4"

    status, data = ui.json("/api/records?matter=custody")
    ids = {r["item_id"] for r in data["rows"] if r["item_type"] == "child.name"}
    assert ids == {"primary.c1", "primary.c2"}
    assert "Rivera" not in json.dumps(data)       # L4 lists as its stand-in only

# ── /api/queue carries the plan-period reference lines (audit, 2026-09-12) ──

def test_the_queue_endpoint_carries_notices_alongside_items(ui, monkeypatch):
    """`notices` is a sibling key to `items`, never an entry in it: a
    reference line has no date, rung or urgency, so a client that folded it
    into `items` would have to invent all three. The page's own rendering of
    it is L4-surfaces' (the bankruptcy pane); this bite ships the data."""
    from homestead.keep.rungs import Rung
    from homestead_law import registry as registry_mod

    fake = types.ModuleType("homestead_law.packs._fake_signal")
    fake.MATTER = "_fake_signal"
    fake.JURISDICTION = "US-NM"
    fake.JURISDICTIONS = ("US-NM",)
    fake.FIELDS = {"award_amount": Rung.L3}
    fake.SCHEMA = {"award_amount": {"rung": Rung.L3, "matter": "_fake_signal",
                                    "derived": "An award amount is on file"}}
    monkeypatch.setitem(registry_mod.REGISTRY, "_fake_signal", registry_mod._entry(fake))

    status, data = ui.json("/api/queue")
    assert status == 200 and data["notices"] == []

    ui.json("/api/store", {"matter": "bankruptcy", "field": "plan_confirmation_date",
                           "value": "2026-06-01"})
    ui.json("/api/store", {"matter": "_fake_signal", "field": "award_amount",
                           "value": "1000", "id": "grant-1"})

    status, data = ui.json("/api/queue")
    assert status == 200
    assert data["notices"] == [
        "bankruptcy/primary: income or assets arising during the plan: "
        "confirm with your attorney (11 U.S.C. §§ 541(a)(7), 1306(a), 1329; "
        "disclosure duties under the plan and local rules)"
    ]
    assert data["items"] == []
    # the line is a reference: no stored value reaches it
    assert "1000" not in json.dumps(data)
