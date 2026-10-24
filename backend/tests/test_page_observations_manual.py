import os, sys, requests, fitz

BASE = os.environ.get("BASE", "http://localhost:8001")
r = requests.post(f"{BASE}/api/auth/login", json={"email": "admin@twasrepair.com", "password": "admin123"})
tok = r.json().get("access_token") or r.json().get("token")
H = {"Authorization": f"Bearer {tok}"}
so = requests.get(f"{BASE}/api/service-orders", headers=H).json()
so = so[0] if isinstance(so, list) else so["service_orders"][0]

def entry(i, page):
    return {"employee_id": f"e{i}", "employee_name": f"Colaborador {i}", "employee_function": "M", "date": "23/10/2026",
            "service_start": "11:00", "service_end": "19:00", "travel_start": "07:00", "travel_end": "11:00", "page": page}

entries = [entry(i, 1) for i in range(14)] + [entry(i, 2) for i in range(14, 20)] + [entry(i, 3) for i in range(20, 22)]
body = {"os_id": so["id"], "entries": entries, "observations": "OBS PAGINA 1 texto base", "supervisor_function": "Supervisor",
        "page_observations": {"3": "OBS PROPRIA DA PAGINA 3"}}
c = requests.post(f"{BASE}/api/timesheets", headers=H, json=body)
print("create:", c.status_code, c.text[:200] if c.status_code != 200 else "")
ts = c.json()
print("page_observations salvo:", ts.get("page_observations"))
pdf = requests.get(f"{BASE}/api/timesheets/{ts['id']}/pdf", headers=H)
print("pdf:", pdf.status_code, len(pdf.content))
d = fitz.open(stream=pdf.content, filetype="pdf")
print("paginas:", len(d))
for i, p in enumerate(d):
    t = p.get_text()
    print(f"  pag {i+1}: base={'OBS PAGINA 1' in t} propria={'OBS PROPRIA DA PAGINA 3' in t}")
    p.get_pixmap(dpi=45).save(f"/tmp/tsnew{i+1}.png")
# update: override page 2 too, remove page 3 override
u = requests.put(f"{BASE}/api/timesheets/{ts['id']}", headers=H, json={**body, "page_observations": {"2": "OBS DA PAGINA 2"}})
print("update:", u.status_code, u.json().get("page_observations"))
pdf2 = fitz.open(stream=requests.get(f"{BASE}/api/timesheets/{ts['id']}/pdf", headers=H).content, filetype="pdf")
print("apos update:", [("OBS DA PAGINA 2" in p.get_text(), "OBS PAGINA 1" in p.get_text()) for p in pdf2])
requests.delete(f"{BASE}/api/timesheets/{ts['id']}", headers=H)
