import sys, json, urllib.request, os
import fitz

BASE = "http://localhost:8001/api"
n_entries = int(sys.argv[1]) if len(sys.argv) > 1 else 14
n_lines = int(sys.argv[2]) if len(sys.argv) > 2 else 11
chars = int(sys.argv[3]) if len(sys.argv) > 3 else 115


def req(path, data=None, token=None):
    r = urllib.request.Request(BASE + path, data=json.dumps(data).encode() if data else None,
                               headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})},
                               method="POST" if data else "GET")
    with urllib.request.urlopen(r) as resp:
        return resp.read()


tok = json.loads(req("/auth/login", {"email": "supervisor@twasrepair.com", "password": "super123"}))["access_token"]
sos = json.loads(req("/service-orders", token=tok))
so = sos[0]
line = ("Auxilio ao mecanico de sonda e desmontagem de componentes mecanicos e hidraulicos para desmobilizacao do equipamento da torre. " * 3)[:chars]
obs = "\n".join(f"{i+1:02d}/09 {line[6:]}" for i in range(n_lines))
entries = [{"date": "18/09/2026", "employee_id": "x", "employee_name": f"Funcionario Teste {i+1}", "employee_function": "T",
            "service_start": "17:00", "service_end": "07:00", "travel_start": "", "travel_end": ""} for i in range(n_entries)]
ts = json.loads(req("/timesheets", {"os_id": so["id"], "entries": entries, "observations": obs, "supervisor_function": "Técnico (T)"}, tok))
pdf = req(f"/timesheets/{ts['id']}/pdf?token={tok}")
docp = fitz.open(stream=pdf, filetype="pdf")
print("pages:", len(docp))
[docp[i].get_pixmap(dpi=60).save(f"/tmp/ts_layout_{i+1}.png") for i in range(len(docp))]
urllib.request.urlopen(urllib.request.Request(BASE + f"/timesheets/{ts['id']}", headers={"Authorization": f"Bearer {tok}"}, method="DELETE")).read()
