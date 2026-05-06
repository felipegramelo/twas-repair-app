"""
BM (Boletim de Medição) regression tests.

Covers critical calculation rules:
1. Day shift detection: 06:30 = day, 19:00 = night, 08:00 = day
2. No extras when total hours == base hours (12h offshore, 8h onshore)
3. Day discount applies only to day_rate, never to night or extras
"""
import os
import requests

BASE_URL = os.environ.get(
    'REACT_APP_BACKEND_URL',
    'https://twas-repair-app-1.preview.emergentagent.com'
).rstrip('/')

ADMIN_EMAIL = "admin@twasrepair.com"
ADMIN_PASSWORD = "admin123"


def _login() -> str:
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    r.raise_for_status()
    return r.json()["access_token"]


def _find_os_with_employees(token: str) -> tuple:
    r = requests.get(f"{BASE_URL}/api/service-orders",
                     headers={"Authorization": f"Bearer {token}"}, timeout=15)
    for os_ in r.json():
        if os_.get("employees"):
            return os_["id"], os_["employees"][0]
    # Fallback: use first OS + employee from any timesheet
    ts = requests.get(f"{BASE_URL}/api/timesheets",
                      headers={"Authorization": f"Bearer {token}"}, timeout=15).json()
    for t in ts:
        for e in t.get("entries", []):
            if e.get("employee_id"):
                return t["os_id"], {"employee_id": e["employee_id"],
                                    "employee_name": e["employee_name"],
                                    "function": e.get("employee_function", "T")}
    return None, None


def _calc_bm(token: str, os_id: str, ts_id: str, mode: str) -> dict:
    r = requests.post(f"{BASE_URL}/api/bm/calculate/{os_id}",
                      headers={"Authorization": f"Bearer {token}"},
                      json={"calc_mode": mode, "timesheet_ids": [ts_id]}, timeout=15)
    r.raise_for_status()
    return r.json()


def _create_ts(token: str, os_id: str, emp: dict, entries: list) -> str:
    payload = {"os_id": os_id, "entries": [
        {**e, "employee_id": emp["employee_id"],
         "employee_name": emp.get("employee_name", "X"),
         "employee_function": emp.get("function", "T"),
         "travel_start": e.get("travel_start", "-"),
         "travel_end": e.get("travel_end", "-")}
        for e in entries
    ]}
    r = requests.post(f"{BASE_URL}/api/timesheets",
                      headers={"Authorization": f"Bearer {token}"},
                      json=payload, timeout=15)
    r.raise_for_status()
    return r.json()["id"]


def _delete_ts(token: str, ts_id: str):
    requests.delete(f"{BASE_URL}/api/timesheets/{ts_id}",
                    headers={"Authorization": f"Bearer {token}"}, timeout=10)


class TestBMShiftDetection:
    """Day shift window must catch typical maritime shifts: 5am-13h start."""

    def test_0630_to_1830_offshore_is_day_no_extras(self):
        """REGRESSION: 06:30-18:30 (12h offshore) should be DAY shift with NO extras.

        Bug history: stale `schedule_type` field defaulted day_start=7,
        so 06:30 was being misclassified as night and the user saw
        "TÉCNICO NOTURNO" instead of "TÉCNICO" in BM PDFs.
        """
        token = _login()
        os_id, emp = _find_os_with_employees(token)
        assert os_id, "No OS found in DB"
        ts_id = _create_ts(token, os_id, emp, [
            {"date": "05/05/2026", "service_start": "06:30", "service_end": "18:30"}
        ])
        try:
            result = _calc_bm(token, os_id, ts_id, "offshore")
            shifts = [(it["shift"], it["category"], it.get("function_name", "")) for it in result["items"]]
            # Must have exactly one item: a day-shift diaria, no extras
            day_diarias = [s for s in shifts if s[0] == "day" and s[1] == "diaria"]
            night_items = [s for s in shifts if s[0] == "night"]
            extras = [s for s in shifts if "extras" in s[1]]
            assert len(day_diarias) == 1, f"Expected 1 day diaria, got: {shifts}"
            assert len(night_items) == 0, f"06:30-18:30 should NOT be night: {shifts}"
            assert len(extras) == 0, f"12h offshore = base, no extras expected: {shifts}"
        finally:
            _delete_ts(token, ts_id)

    def test_night_shift_1900_to_0700_is_night(self):
        """19:00-07:00 must be NIGHT shift."""
        token = _login()
        os_id, emp = _find_os_with_employees(token)
        ts_id = _create_ts(token, os_id, emp, [
            {"date": "05/05/2026", "service_start": "19:00", "service_end": "07:00"}
        ])
        try:
            result = _calc_bm(token, os_id, ts_id, "offshore")
            shifts = [it["shift"] for it in result["items"] if it["category"] == "diaria"]
            assert "night" in shifts, f"19:00-07:00 must be night: {result['items']}"
            assert "day" not in shifts, f"19:00-07:00 must NOT be day: {result['items']}"
        finally:
            _delete_ts(token, ts_id)

    def test_late_afternoon_1600_is_day(self):
        """REGRESSION: 16:00-18:30 (with travel before) must be DAY shift.

        Real case from Blue OOS OS 19-2604-35 24/04/2026: travel 11:00-16:00
        + service 16:00-18:30 = a daytime work period (embarque + last service hours),
        not a night shift.
        """
        token = _login()
        os_id, emp = _find_os_with_employees(token)
        ts_id = _create_ts(token, os_id, emp, [
            {"date": "24/04/2026", "service_start": "16:00", "service_end": "18:30",
             "travel_start": "11:00", "travel_end": "16:00"}
        ])
        try:
            result = _calc_bm(token, os_id, ts_id, "offshore")
            shifts = [it["shift"] for it in result["items"] if it["category"] == "diaria"]
            assert "day" in shifts, f"16:00 start must be DAY: {result['items']}"
            assert "night" not in shifts, f"16:00 start must NOT be night: {result['items']}"
        finally:
            _delete_ts(token, ts_id)


class TestBMDiscount:
    """day_discount_pct must apply only to day_rate diaria."""

    def test_day_discount_applies_only_to_day_rate(self):
        """A 10% discount on TÉCNICO must reduce day diaria but leave night intact."""
        token = _login()
        # Find a price table with TECNICO + add 10% discount
        r = requests.get(f"{BASE_URL}/api/client-prices",
                         headers={"Authorization": f"Bearer {token}"}, timeout=15)
        tables = r.json()
        target = None
        for t in tables:
            for p in t.get("prices", []):
                if p["function_code"] == "T" and p.get("day_rate", 0) > 0:
                    target = t
                    break
            if target:
                break
        if not target:
            return  # No price table to test against

        original_disc = None
        for p in target["prices"]:
            if p["function_code"] == "T":
                original_disc = p.get("day_discount_pct", 0)
                p["day_discount_pct"] = 10
                day_rate = p["day_rate"]
                night_rate = p["night_rate"]
                break

        # Find an OS for this client
        os_list = requests.get(f"{BASE_URL}/api/service-orders",
                               headers={"Authorization": f"Bearer {token}"}, timeout=15).json()
        os_for_client = next((o for o in os_list
                              if o.get("client", "").strip() == target["client_name"].strip()), None)
        if not os_for_client:
            return  # No OS for this client; skip

        # Save discount
        requests.put(f"{BASE_URL}/api/client-prices/{target['id']}",
                     headers={"Authorization": f"Bearer {token}"},
                     json={"client_name": target["client_name"], "prices": target["prices"]},
                     timeout=15)

        emp = {"employee_id": "test_emp", "employee_name": "X", "function": "T"}
        ts_id = _create_ts(token, os_for_client["id"], emp, [
            {"date": "05/05/2026", "service_start": "08:00", "service_end": "20:00"},
            {"date": "06/05/2026", "service_start": "19:00", "service_end": "07:00"},
        ])
        try:
            result = _calc_bm(token, os_for_client["id"], ts_id, "offshore")
            day_unit = next((it["valor_und"] for it in result["items"]
                             if it["shift"] == "day" and it["category"] == "diaria"), None)
            night_unit = next((it["valor_und"] for it in result["items"]
                               if it["shift"] == "night" and it["category"] == "diaria"), None)
            expected_day = round(day_rate * 0.9, 2)
            assert day_unit == expected_day, f"Day with 10% disc: expected {expected_day}, got {day_unit}"
            assert night_unit == night_rate, f"Night unchanged: expected {night_rate}, got {night_unit}"
        finally:
            _delete_ts(token, ts_id)
            # Restore original discount
            for p in target["prices"]:
                if p["function_code"] == "T":
                    p["day_discount_pct"] = original_disc
                    break
            requests.put(f"{BASE_URL}/api/client-prices/{target['id']}",
                         headers={"Authorization": f"Bearer {token}"},
                         json={"client_name": target["client_name"], "prices": target["prices"]},
                         timeout=15)
