from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
import logging
import os

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

app = FastAPI(title="TWAS REPAIR API")

# Serve generated graphics (logo / feature graphic) for download via /api/static
_assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "assets", "images")
if os.path.isdir(_assets_dir):
    app.mount("/api/static-assets", StaticFiles(directory=_assets_dir), name="static-assets")

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


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
