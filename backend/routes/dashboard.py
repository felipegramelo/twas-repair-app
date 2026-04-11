from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from datetime import datetime
from bson import ObjectId

from database import db
from dependencies import get_admin_user
from models import UserRole

router = APIRouter()

# ==================== BM ACCESS MANAGEMENT ====================

@router.put("/users/admins/{user_id}/bm-access")
async def toggle_bm_access(user_id: str, current_user: Dict[str, Any] = Depends(get_admin_user)):
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user or user.get("role") != UserRole.ADMIN:
        raise HTTPException(status_code=404, detail="Administrador não encontrado")
    new_access = not user.get("bm_access", False)
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"bm_access": new_access}})
    return {"bm_access": new_access}

@router.put("/users/admins/{user_id}/os-archive-access")
async def toggle_os_archive_access(user_id: str, current_user: Dict[str, Any] = Depends(get_admin_user)):
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user or user.get("role") != UserRole.ADMIN:
        raise HTTPException(status_code=404, detail="Administrador não encontrado")
    new_access = not user.get("os_archive_access", False)
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"os_archive_access": new_access}})
    return {"os_archive_access": new_access}

@router.put("/users/admins/{user_id}/proposta-access")
async def toggle_proposta_access(user_id: str, current_user: Dict[str, Any] = Depends(get_admin_user)):
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user or user.get("role") != UserRole.ADMIN:
        raise HTTPException(status_code=404, detail="Administrador não encontrado")
    new_access = not user.get("proposta_access", False)
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"proposta_access": new_access}})
    return {"proposta_access": new_access}

@router.put("/users/admins/{user_id}/dashboard-access")
async def toggle_dashboard_access(user_id: str, current_user: Dict[str, Any] = Depends(get_admin_user)):
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user or user.get("role") != UserRole.ADMIN:
        raise HTTPException(status_code=404, detail="Administrador não encontrado")
    new_access = not user.get("dashboard_access", False)
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"dashboard_access": new_access}})
    return {"dashboard_access": new_access}


# ==================== DASHBOARD SUMMARY ====================

@router.get("/dashboard/summary")
async def get_dashboard_summary(current_user: Dict[str, Any] = Depends(get_admin_user)):
    if not current_user.get("dashboard_access", False):
        raise HTTPException(status_code=403, detail="Acesso ao dashboard negado")

    now = datetime.utcnow()

    # --- BMs by month (last 12 months) ---
    bm_by_month = []
    for i in range(11, -1, -1):
        year = now.year
        month = now.month - i
        while month <= 0:
            month += 12
            year -= 1
        month_start = datetime(year, month, 1)
        if month == 12:
            month_end = datetime(year + 1, 1, 1)
        else:
            month_end = datetime(year, month + 1, 1)

        pipeline = [
            {"$match": {"created_at": {"$gte": month_start, "$lt": month_end}}},
            {"$group": {"_id": None, "total": {"$sum": "$valor_total"}, "count": {"$sum": 1}}},
        ]
        result = await db.boletins_medicao.aggregate(pipeline).to_list(1)
        month_label = f"{month:02d}/{year}"
        if result:
            bm_by_month.append({"month": month_label, "total": round(result[0]["total"], 2), "count": result[0]["count"]})
        else:
            bm_by_month.append({"month": month_label, "total": 0, "count": 0})

    # --- Proposals by status ---
    proposal_statuses = await db.propostas.aggregate([
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]).to_list(20)
    proposals_by_status = {}
    for ps in proposal_statuses:
        status_key = ps["_id"] or "pendente"
        proposals_by_status[status_key] = ps["count"]

    # --- Totals ---
    total_bm_pipeline = [{"$group": {"_id": None, "total": {"$sum": "$valor_total"}, "count": {"$sum": 1}}}]
    total_bm = await db.boletins_medicao.aggregate(total_bm_pipeline).to_list(1)
    total_proposals = await db.propostas.count_documents({})
    total_os = await db.service_orders.count_documents({})
    total_timesheets = await db.timesheets.count_documents({})

    # --- Top clients by BM value ---
    top_clients = await db.boletins_medicao.aggregate([
        {"$group": {"_id": "$client", "total": {"$sum": "$valor_total"}, "count": {"$sum": 1}}},
        {"$sort": {"total": -1}},
        {"$limit": 5},
    ]).to_list(5)

    return {
        "bm_by_month": bm_by_month,
        "proposals_by_status": proposals_by_status,
        "totals": {
            "bm_total_value": round(total_bm[0]["total"], 2) if total_bm else 0,
            "bm_count": total_bm[0]["count"] if total_bm else 0,
            "proposals_count": total_proposals,
            "os_count": total_os,
            "timesheets_count": total_timesheets,
        },
        "top_clients": [{"client": c["_id"] or "N/A", "total": round(c["total"], 2), "count": c["count"]} for c in top_clients],
    }

