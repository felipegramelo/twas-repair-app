from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
import logging

from database import client
from config import init_storage

from routes.auth import router as auth_router
from routes.employees import router as employees_router
from routes.service_orders import router as service_orders_router
from routes.timesheets import router as timesheets_router
from routes.reports import router as reports_router
from routes.proposals import router as proposals_router
from routes.boletim import router as boletim_router
from routes.dashboard import router as dashboard_router
from routes.sharing import router as sharing_router
from routes.translate import router as translate_router
from routes.holidays import router as holidays_router
from routes.projects import router as projects_router

app = FastAPI(title="TWAS REPAIR API")

# Include all route modules under /api prefix
api_prefix = "/api"
app.include_router(auth_router, prefix=api_prefix)
app.include_router(employees_router, prefix=api_prefix)
app.include_router(service_orders_router, prefix=api_prefix)
app.include_router(timesheets_router, prefix=api_prefix)
app.include_router(reports_router, prefix=api_prefix)
app.include_router(proposals_router, prefix=api_prefix)
app.include_router(boletim_router, prefix=api_prefix)
app.include_router(dashboard_router, prefix=api_prefix)
app.include_router(sharing_router, prefix=api_prefix)
app.include_router(translate_router, prefix=api_prefix)
app.include_router(holidays_router, prefix=api_prefix)
app.include_router(projects_router, prefix=api_prefix)

# App version (diagnostics)
APP_VERSION = "2.0.0"


@app.get(f"{api_prefix}/version")
async def get_app_version():
    return {"version": APP_VERSION}


app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def startup_event():
    try:
        init_storage()
        logging.info("Object storage initialized")
    except Exception as e:
        logging.error(f"Storage init failed (will retry on first upload): {e}")

    # Ensure critical indexes for query performance
    try:
        from database import db
        await db.timesheets.create_index("os_id")
        await db.reports.create_index("os_id")
        await db.reports.create_index([("os_id", 1), ("status", 1)])
        await db.service_orders.create_index("os_number")
        logging.info("Indexes ensured")
    except Exception as e:
        logging.error(f"Index creation failed: {e}")

    # One-time normalization: remove spaces around hyphens in os_number
    try:
        import re as _re
        from database import db
        for col in ("service_orders", "timesheets", "reports", "projects", "propostas"):
            async for doc in db[col].find({"os_number": {"$regex": r"\s"}}, {"os_number": 1}):
                clean = _re.sub(r"\s*-\s*", "-", str(doc["os_number"]).strip())
                if clean != doc["os_number"]:
                    await db[col].update_one({"_id": doc["_id"]}, {"$set": {"os_number": clean}})
        logging.info("OS number normalization done")
    except Exception as e:
        logging.error(f"OS number normalization failed: {e}")

    # Seed admin user if not exists
    try:
        from database import db
        from config import get_password_hash
        admin = await db.users.find_one({"email": "admin@twasrepair.com"})
        if not admin:
            await db.users.insert_one({
                "name": "Administrador",
                "email": "admin@twasrepair.com",
                "password_hash": get_password_hash("admin123"),
                "role": "admin",
                "bm_access": True,
                "os_archive_access": True,
                "proposta_access": True,
                "dashboard_access": True,
                "created_at": __import__('datetime').datetime.utcnow()
            })
            logging.info("Admin user seeded")
        else:
            # Ensure admin has all permissions
            await db.users.update_one(
                {"email": "admin@twasrepair.com"},
                {"$set": {"bm_access": True, "os_archive_access": True, "proposta_access": True, "dashboard_access": True}}
            )
            logging.info("Admin permissions updated")
    except Exception as e:
        logging.error(f"Admin seed failed: {e}")

    # One-off migration: backfill embarcacao/client/location/service on existing reports from their OS
    # Also fix legacy introduction text that has "da embarcação {location}" → "da embarcação {embarcacao}"
    try:
        from database import db
        from bson import ObjectId
        cursor = db.reports.find({})
        migrated = 0
        intro_fixed = 0
        async for rep in cursor:
            os_id = rep.get("os_id")
            if not os_id:
                continue
            try:
                os_data = await db.service_orders.find_one({"_id": ObjectId(os_id)})
            except Exception:
                os_data = None
            if not os_data:
                continue
            update_data = {}
            os_emb = (os_data.get("embarcacao") or "").strip()
            os_loc = (os_data.get("location") or "").strip()
            # 1) Backfill top-level fields if missing
            for key in ("embarcacao", "client", "location", "service"):
                val = (os_data.get(key) or "")
                if isinstance(val, str): val = val.strip()
                if val and not (rep.get(key) or "").strip():
                    update_data[key] = val
            # 2) Fix introduction text in sections (replace "embarcação <location>" with "embarcação <embarcacao>")
            if os_emb and os_loc and os_emb != os_loc:
                sections = rep.get("sections") or []
                changed = False
                for sec in sections:
                    if sec.get("key") == "introduction":
                        content = sec.get("content") or ""
                        old_phrase = f"embarcação {os_loc}"
                        new_phrase = f"embarcação {os_emb}"
                        if old_phrase in content and new_phrase not in content:
                            sec["content"] = content.replace(old_phrase, new_phrase)
                            changed = True
                if changed:
                    update_data["sections"] = sections
                    intro_fixed += 1
            if update_data:
                await db.reports.update_one({"_id": rep["_id"]}, {"$set": update_data})
                migrated += 1
        if migrated:
            logging.info(f"Backfilled OS fields on {migrated} report(s); intro text fixed on {intro_fixed}")
    except Exception as e:
        logging.error(f"Reports OS field backfill failed: {e}")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
