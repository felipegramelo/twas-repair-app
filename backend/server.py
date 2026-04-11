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


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
