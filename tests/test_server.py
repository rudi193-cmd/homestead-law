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

import http.client
import json
import threading

import pytest

from homestead_law import server


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
