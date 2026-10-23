"""Testa se o Railway já roda o código novo (Importar PDF via Gemini). Cria e apaga um projeto de teste."""
import io, os, sys, time, requests
from reportlab.pdfgen import canvas

BASE = "https://twas-repair-app-production.up.railway.app"
r = requests.post(f"{BASE}/api/auth/login", json={"email": os.environ["RAILWAY_ADMIN_EMAIL"], "password": os.environ["RAILWAY_ADMIN_PASSWORD"]}, timeout=30)
if r.status_code != 200:
    print("login falhou", r.status_code, r.text[:200]); sys.exit()
tok = r.json().get("access_token") or r.json().get("token")
H = {"Authorization": f"Bearer {tok}"}

buf = io.BytesIO(); c = canvas.Canvas(buf); y = 800
for line in ["Cronograma de Projeto - Teste", "1. Desmontagem do thruster - 2 dias", "2. Inspecao dimensional - 1 dia", "3. Montagem e testes - 3 dias"]:
    c.drawString(50, y, line); y -= 20
c.save()

p = requests.post(f"{BASE}/api/projects", headers=H, json={"os_number": "TESTE-RAILWAY", "title": "Teste Railway import (apagar)"}, timeout=30)
pid = p.json().get("id") or p.json().get("_id")
imp = requests.post(f"{BASE}/api/projects/{pid}/import-pdf", headers=H, files={"file": ("t.pdf", buf.getvalue(), "application/pdf")}, timeout=60)
print("import:", imp.status_code)
for _ in range(12):
    time.sleep(5)
    d = requests.get(f"{BASE}/api/projects/{pid}", headers=H, timeout=30).json()
    if d.get("import_status") != "processing":
        print("status:", d.get("import_status"), "| erro:", (d.get("import_error") or "")[:160], "| tarefas:", len(d.get("tasks", [])))
        break
else:
    print("ainda processando")
requests.delete(f"{BASE}/api/projects/{pid}", headers=H, timeout=30)
