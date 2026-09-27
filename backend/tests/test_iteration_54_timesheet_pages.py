"""Backend tests for Timesheet explicit-pages feature (iteration 54).

Covers:
- POST timesheet with entries across multiple pages -> PDF has N pages, correct grouping
- POST >14 entries on a single page -> 400
- POST entry with page=6 -> 400
- POST without page field (legacy compat) -> success, single-page PDF
- PUT applies same validations and updates pages
"""
import os

import fitz  # pymupdf
import pytest
import requests

BASE = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://twas-repair-app-1.preview.emergentagent.com").rstrip("/") + "/api"
SUP = {"email": "supervisor@twasrepair.com", "password": "super123"}


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE}/auth/login", json=SUP, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def os_id(headers):
    r = requests.get(f"{BASE}/service-orders", headers=headers, timeout=30)
    assert r.status_code == 200
    sos = r.json()
    assert sos, "need at least one SO"
    return sos[0]["id"]


def _entry(name, page=None, fn="T"):
    e = {
        "date": "18/09/2026",
        "employee_id": "x",
        "employee_name": name,
        "employee_function": fn,
        "service_start": "07:00",
        "service_end": "17:00",
        "travel_start": "",
        "travel_end": "",
    }
    if page is not None:
        e["page"] = page
    return e


@pytest.fixture
def cleanup(headers):
    created = []
    yield created
    for tid in created:
        try:
            requests.delete(f"{BASE}/timesheets/{tid}", headers=headers, timeout=15)
        except Exception:
            pass


# ============ POST across 2 pages -> PDF 2 pages, correct grouping ============
def test_create_multi_page_and_pdf_contents(headers, os_id, token, cleanup):
    entries = [
        _entry("TEST_P1_A", page=1),
        _entry("TEST_P1_B", page=1),
        _entry("TEST_P1_C", page=1),
        _entry("TEST_P2_A", page=2),
        _entry("TEST_P2_B", page=2),
    ]
    r = requests.post(f"{BASE}/timesheets", headers=headers, json={"os_id": os_id, "entries": entries}, timeout=30)
    assert r.status_code in (200, 201), r.text
    ts = r.json()
    tid = ts["id"]
    cleanup.append(tid)
    # verify persistence
    g = requests.get(f"{BASE}/timesheets/{tid}", headers=headers, timeout=30).json()
    pages = [e.get("page") for e in g["entries"]]
    assert pages == [1, 1, 1, 2, 2]
    # PDF
    r = requests.get(f"{BASE}/timesheets/{tid}/pdf?token={token}", timeout=60)
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")
    doc = fitz.open(stream=r.content, filetype="pdf")
    assert len(doc) == 2, f"expected 2 pages, got {len(doc)}"
    t1 = doc[0].get_text()
    t2 = doc[1].get_text()
    assert "TEST_P1_A" in t1 and "TEST_P1_B" in t1 and "TEST_P1_C" in t1
    assert "TEST_P2_A" in t2 and "TEST_P2_B" in t2
    # cross-contamination check
    assert "TEST_P2_A" not in t1
    assert "TEST_P1_A" not in t2
    # footer 'Página 1 de 2' / 'Página 2 de 2'
    assert "Página 1 de 2" in t1
    assert "Página 2 de 2" in t2


# ============ 15 entries on same page -> 400 ============
def test_max_14_entries_per_page(headers, os_id, cleanup):
    entries = [_entry(f"TEST_ROW_{i}", page=1) for i in range(15)]
    r = requests.post(f"{BASE}/timesheets", headers=headers, json={"os_id": os_id, "entries": entries}, timeout=30)
    assert r.status_code == 400, r.text
    assert "14" in r.json().get("detail", "")


# ============ page=6 -> 400 ============
def test_max_5_pages(headers, os_id, cleanup):
    entries = [_entry("TEST_P6", page=6)]
    r = requests.post(f"{BASE}/timesheets", headers=headers, json={"os_id": os_id, "entries": entries}, timeout=30)
    assert r.status_code == 400, r.text
    assert "5 páginas" in r.json().get("detail", "")


# ============ No page field (legacy) -> success + PDF 1 page ============
def test_no_page_field_legacy_compat(headers, os_id, token, cleanup):
    entries = [_entry("TEST_LEGACY_A"), _entry("TEST_LEGACY_B")]
    r = requests.post(f"{BASE}/timesheets", headers=headers, json={"os_id": os_id, "entries": entries}, timeout=30)
    assert r.status_code in (200, 201), r.text
    ts = r.json()
    tid = ts["id"]
    cleanup.append(tid)
    # entries should default page=1
    g = requests.get(f"{BASE}/timesheets/{tid}", headers=headers, timeout=30).json()
    for e in g["entries"]:
        assert (e.get("page") or 1) == 1
    r = requests.get(f"{BASE}/timesheets/{tid}/pdf?token={token}", timeout=60)
    assert r.status_code == 200
    doc = fitz.open(stream=r.content, filetype="pdf")
    assert len(doc) == 1
    t = doc[0].get_text()
    assert "TEST_LEGACY_A" in t and "TEST_LEGACY_B" in t
    assert "Página 1 de 1" in t


# ============ PUT updates pages with validations ============
def test_put_update_pages(headers, os_id, token, cleanup):
    # create 1 page ts
    entries = [_entry("TEST_PUT_A", page=1)]
    r = requests.post(f"{BASE}/timesheets", headers=headers, json={"os_id": os_id, "entries": entries}, timeout=30)
    assert r.status_code in (200, 201), r.text
    tid = r.json()["id"]
    cleanup.append(tid)

    # PUT expand to 3 pages
    new_entries = [
        _entry("TEST_PUT_P1", page=1),
        _entry("TEST_PUT_P2", page=2),
        _entry("TEST_PUT_P3", page=3),
    ]
    r = requests.put(f"{BASE}/timesheets/{tid}", headers=headers, json={"os_id": os_id, "entries": new_entries}, timeout=30)
    assert r.status_code == 200, r.text
    g = requests.get(f"{BASE}/timesheets/{tid}", headers=headers, timeout=30).json()
    assert [e.get("page") for e in g["entries"]] == [1, 2, 3]
    # PDF has 3 pages
    r = requests.get(f"{BASE}/timesheets/{tid}/pdf?token={token}", timeout=60)
    assert r.status_code == 200
    doc = fitz.open(stream=r.content, filetype="pdf")
    assert len(doc) == 3
    assert "TEST_PUT_P1" in doc[0].get_text()
    assert "TEST_PUT_P2" in doc[1].get_text()
    assert "TEST_PUT_P3" in doc[2].get_text()

    # PUT with 15 on page 1 -> 400
    bad = [_entry(f"TEST_PUT_BAD_{i}", page=1) for i in range(15)]
    r = requests.put(f"{BASE}/timesheets/{tid}", headers=headers, json={"os_id": os_id, "entries": bad}, timeout=30)
    assert r.status_code == 400

    # PUT with page=6 -> 400
    r = requests.put(f"{BASE}/timesheets/{tid}", headers=headers, json={"os_id": os_id, "entries": [_entry("TEST_PUT_P6", page=6)]}, timeout=30)
    assert r.status_code == 400
