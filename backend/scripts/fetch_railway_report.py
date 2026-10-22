"""Copia um relatório (dados + fotos) do Railway para o banco local, para gerar o PDF com o código novo.
Uso: python scripts/fetch_railway_report.py <os_number> <trecho do serviço>
"""
import os, sys, asyncio, requests
from datetime import datetime, timezone
from bson import ObjectId
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
from motor.motor_asyncio import AsyncIOMotorClient
from config import put_object

BASE = "https://twas-repair-app-production.up.railway.app"
os_number, service_part = sys.argv[1], sys.argv[2].upper()
email, password = os.environ["RAILWAY_ADMIN_EMAIL"], os.environ["RAILWAY_ADMIN_PASSWORD"]


async def main():
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    r.raise_for_status()
    tok = r.json().get("access_token") or r.json().get("token")
    H = {"Authorization": f"Bearer {tok}"}

    reports = requests.get(f"{BASE}/api/reports", headers=H, timeout=60).json()["reports"]
    match = [x for x in reports if x["os_number"] == os_number and service_part in x["service"].upper()]
    print(f"encontrados: {[(m['id'], m['service'][:50], m['periodo_inicio']) for m in match]}")
    if not match:
        return
    rep = match[0]
    rid = rep["id"]
    photos = requests.get(f"{BASE}/api/reports/{rid}/photos", headers=H, timeout=60).json()["photos"]
    print(f"fotos: {len(photos)}")

    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    doc = {k: v for k, v in rep.items() if k != "id"}
    doc.update({
        "_id": ObjectId(rid),
        "embarcacao": os.environ.get("REPORT_EMBARCACAO", ""),
        "language": "pt",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })
    await db.reports.replace_one({"_id": doc["_id"]}, doc, upsert=True)

    await db.report_photos.delete_many({"report_id": rid})
    for p in photos:
        img = requests.get(f"{BASE}/api/photos/{p['storage_path']}", params={"auth": tok}, timeout=120)
        img.raise_for_status()
        put_object(p["storage_path"], img.content, p.get("content_type", "image/jpeg"))
        await db.report_photos.insert_one({
            "_id": ObjectId(p["id"]), "report_id": rid, "section_key": p["section_key"],
            "storage_path": p["storage_path"], "original_filename": p["original_filename"],
            "content_type": p.get("content_type", "image/jpeg"), "caption": p.get("caption", ""),
            "is_deleted": False, "uploaded_at": datetime.now(timezone.utc),
        })
        print("  foto ok:", p["section_key"], len(img.content))
    print("REPORT_ID", rid)


asyncio.run(main())
