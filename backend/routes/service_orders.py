from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime

from database import db
from dependencies import get_current_user, get_admin_user
from models import ServiceOrder, ServiceOrderCreate

router = APIRouter()

@router.post("/service-orders", response_model=ServiceOrder)
async def create_service_order(so_data: ServiceOrderCreate, current_user: Dict[str, Any] = Depends(get_admin_user)):
    so_dict = so_data.model_dump()
    so_dict["created_at"] = datetime.utcnow()
    
    result = await db.service_orders.insert_one(so_dict)
    so_dict["_id"] = str(result.inserted_id)
    
    return ServiceOrder(**so_dict)


@router.get("/service-orders", response_model=List[dict])
async def get_service_orders(month: Optional[int] = Query(None), year: Optional[int] = Query(None), current_user: Dict[str, Any] = Depends(get_current_user)):
    query = {}
    if month and year:
        start = datetime(year, month, 1)
        if month == 12:
            end = datetime(year + 1, 1, 1)
        else:
            end = datetime(year, month + 1, 1)
        query["created_at"] = {"$gte": start, "$lt": end}
    elif year:
        start = datetime(year, 1, 1)
        end = datetime(year + 1, 1, 1)
        query["created_at"] = {"$gte": start, "$lt": end}
    service_orders = await db.service_orders.find(query).sort("os_number", 1).to_list(500)
    for so in service_orders:
        so["id"] = str(so.pop("_id"))
        if "proposal_id" not in so:
            so["proposal_id"] = ""
        if "po_number" not in so:
            so["po_number"] = ""
        if "embarcacao" not in so:
            so["embarcacao"] = ""
    return service_orders


@router.get("/service-orders/{so_id}", response_model=dict)
async def get_service_order(so_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    so = await db.service_orders.find_one({"_id": ObjectId(so_id)})
    if not so:
        raise HTTPException(status_code=404, detail="Service Order not found")
    so["id"] = str(so.pop("_id"))
    return so


@router.put("/service-orders/{so_id}", response_model=ServiceOrder)
async def update_service_order(so_id: str, so_data: ServiceOrderCreate, current_user: Dict[str, Any] = Depends(get_admin_user)):
    so_dict = so_data.model_dump()
    
    result = await db.service_orders.update_one(
        {"_id": ObjectId(so_id)},
        {"$set": so_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Service Order not found")
    
    updated_so = await db.service_orders.find_one({"_id": ObjectId(so_id)})
    updated_so["_id"] = str(updated_so["_id"])
    return ServiceOrder(**updated_so)


@router.delete("/service-orders/{so_id}")
async def delete_service_order(so_id: str, current_user: Dict[str, Any] = Depends(get_admin_user)):
    result = await db.service_orders.delete_one({"_id": ObjectId(so_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Service Order not found")
    return {"message": "Service Order deleted successfully"}



# ==================== OS ARCHIVE ENDPOINT ====================

@router.get("/admin/os-archive")
async def get_os_archive(current_user: Dict[str, Any] = Depends(get_admin_user)):
    """Get all service orders with their related documents (timesheets + reports)"""
    service_orders = await db.service_orders.find().sort("os_number", 1).to_list(500)
    
    result = []
    for so in service_orders:
        so_id = str(so["_id"])
        
        # Get timesheets for this OS (all timesheets, not just finalized)
        timesheets = await db.timesheets.find({"os_id": so_id}).sort("created_at", 1).to_list(100)
        ts_list = []
        for idx, ts in enumerate(timesheets):
            ts["id"] = str(ts.pop("_id"))
            ts.pop("_id", None)
            if "sequence_number" not in ts or not ts.get("sequence_number"):
                ts["sequence_number"] = idx + 1
            ts["created_at"] = ts.get("created_at", "").isoformat() if hasattr(ts.get("created_at", ""), "isoformat") else str(ts.get("created_at", ""))
            ts["updated_at"] = ts.get("updated_at", "").isoformat() if hasattr(ts.get("updated_at", ""), "isoformat") else str(ts.get("updated_at", ""))
            ts_list.append(ts)
        
        # Get reports for this OS (only finalized ones for admin archive)
        reports = await db.reports.find({"os_id": so_id, "status": "finalized"}).sort("created_at", -1).to_list(100)
        report_list = []
        for r in reports:
            r["id"] = str(r.pop("_id"))
            r.pop("_id", None)
            r["created_at"] = r.get("created_at", "").isoformat() if hasattr(r.get("created_at", ""), "isoformat") else str(r.get("created_at", ""))
            r["updated_at"] = r.get("updated_at", "").isoformat() if hasattr(r.get("updated_at", ""), "isoformat") else str(r.get("updated_at", ""))
            report_list.append(r)
        
        service_reports = [r for r in report_list if r.get("report_type") == "service"]
        daily_reports = [r for r in report_list if r.get("report_type") == "daily"]
        
        result.append({
            "id": so_id,
            "os_number": so.get("os_number", ""),
            "client": so.get("client", ""),
            "location": so.get("location", ""),
            "service": so.get("service", ""),
            "employees": so.get("employees", []),
            "timesheets": ts_list,
            "service_reports": service_reports,
            "daily_reports": daily_reports,
            "total_documents": len(ts_list) + len(report_list),
        })
    
    return result
