"""
Holidays CRUD endpoints (regional holidays).

National Brazilian holidays are computed automatically (see holidays_util.py).
Use these endpoints only to add regional/state/municipal holidays
that should be considered as 100% (Sunday-equivalent) in BM calculations.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime
from typing import Dict, Any, List

from database import db
from dependencies import get_bm_admin_user
from holidays_util import national_holidays

router = APIRouter()


class HolidayCreate(BaseModel):
    date: str  # DD/MM/YYYY
    description: str = ""


def _validate_date(d: str) -> None:
    try:
        parts = d.split("/")
        if len(parts) != 3:
            raise ValueError()
        day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
        datetime(year, month, day)
    except Exception:
        raise HTTPException(status_code=400, detail="Data inválida (use DD/MM/AAAA)")


@router.get("/holidays")
async def list_holidays(
    year: int | None = None,
    current_user: Dict[str, Any] = Depends(get_bm_admin_user),
):
    """List national (auto) + regional (DB) holidays.

    If `year` is provided, returns the merged set for that year.
    Otherwise returns only regional holidays (no national auto-generation).
    """
    regional = await db.holidays.find().sort("date", 1).to_list(500)
    for h in regional:
        h["id"] = str(h.pop("_id"))
        h["type"] = "regional"
        h.pop("_id", None)
        if isinstance(h.get("created_at"), datetime):
            h["created_at"] = h["created_at"].isoformat()

    items: List[dict] = list(regional)

    if year:
        existing_dates = {h["date"] for h in regional}
        for d in sorted(national_holidays(year)):
            if d not in existing_dates:
                items.append({
                    "id": f"national_{d}",
                    "date": d,
                    "description": "Feriado Nacional",
                    "type": "national",
                })

        # Sort by sortable date
        def _key(h: dict) -> str:
            try:
                p = h["date"].split("/")
                return f"{p[2]}-{p[1]}-{p[0]}"
            except Exception:
                return h["date"]

        items.sort(key=_key)

    return items


@router.post("/holidays")
async def create_holiday(
    data: HolidayCreate,
    current_user: Dict[str, Any] = Depends(get_bm_admin_user),
):
    _validate_date(data.date)
    existing = await db.holidays.find_one({"date": data.date})
    if existing:
        raise HTTPException(status_code=400, detail="Feriado já cadastrado para esta data")
    doc = {
        "date": data.date,
        "description": data.description or "",
        "created_at": datetime.utcnow(),
    }
    result = await db.holidays.insert_one(doc)
    return {
        "id": str(result.inserted_id),
        "date": doc["date"],
        "description": doc["description"],
        "type": "regional",
    }


@router.delete("/holidays/{holiday_id}")
async def delete_holiday(
    holiday_id: str,
    current_user: Dict[str, Any] = Depends(get_bm_admin_user),
):
    if holiday_id.startswith("national_"):
        raise HTTPException(status_code=400, detail="Feriados nacionais não podem ser removidos")
    try:
        oid = ObjectId(holiday_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID inválido")
    result = await db.holidays.delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Feriado não encontrado")
    return {"message": "Feriado removido"}
