from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import Response
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage, PageBreak, Frame, PageTemplate, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
import io
import jwt
from pathlib import Path
from PIL import Image as PILImage

from database import db
from config import SECRET_KEY, ALGORITHM, get_object
from dependencies import get_current_user, get_admin_user
from models import UserRole

router = APIRouter()

ROOT_DIR = Path(__file__).parent.parent

from dependencies import get_bm_admin_user

# ==================== CLIENT PRICE TABLE ENDPOINTS ====================

class ClientPriceEntry(BaseModel):
    function_code: str
    function_name: str
    day_rate: float
    night_rate: float
    day_discount_pct: float = 0  # Discount % applied only to day_rate (0-100)

class ClientPriceTableCreate(BaseModel):
    client_name: str
    prices: List[ClientPriceEntry]
    label: str = ""  # Optional tag (e.g., "Padrão", "Promocional Q4") for multiple tables per client

@router.get("/client-prices")
async def get_client_prices(current_user: Dict[str, Any] = Depends(get_bm_admin_user)):
    tables = await db.client_prices.find().sort("client_name", 1).to_list(100)
    for t in tables:
        t["id"] = str(t.pop("_id"))
        t.pop("_id", None)
    return tables

@router.post("/client-prices")
async def create_client_price(data: ClientPriceTableCreate, current_user: Dict[str, Any] = Depends(get_bm_admin_user)):
    doc = data.model_dump()
    doc["created_at"] = datetime.utcnow()
    result = await db.client_prices.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    doc.pop("_id", None)
    doc["created_at"] = doc["created_at"].isoformat()
    return doc

@router.put("/client-prices/{price_id}")
async def update_client_price(price_id: str, data: ClientPriceTableCreate, current_user: Dict[str, Any] = Depends(get_bm_admin_user)):
    result = await db.client_prices.update_one(
        {"_id": ObjectId(price_id)},
        {"$set": data.model_dump()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Tabela não encontrada")
    return {"message": "Atualizado com sucesso"}

@router.delete("/client-prices/{price_id}")
async def delete_client_price(price_id: str, current_user: Dict[str, Any] = Depends(get_bm_admin_user)):
    result = await db.client_prices.delete_one({"_id": ObjectId(price_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Tabela não encontrada")
    return {"message": "Excluído com sucesso"}

# ==================== LOGISTICS PRICE TABLE ENDPOINTS ====================

class LogisticsRouteEntry(BaseModel):
    description: str
    price: float  # Price per collaborator

class LogisticsPriceTableCreate(BaseModel):
    client_name: str
    label: str = ""
    routes: List[LogisticsRouteEntry]

@router.get("/logistics-prices")
async def get_logistics_prices(current_user: Dict[str, Any] = Depends(get_bm_admin_user)):
    tables = await db.logistics_prices.find().sort("client_name", 1).to_list(200)
    for t in tables:
        t["id"] = str(t.pop("_id"))
        t.pop("_id", None)
    return tables

@router.post("/logistics-prices")
async def create_logistics_price(data: LogisticsPriceTableCreate, current_user: Dict[str, Any] = Depends(get_bm_admin_user)):
    doc = data.model_dump()
    doc["created_at"] = datetime.utcnow()
    result = await db.logistics_prices.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    doc.pop("_id", None)
    doc["created_at"] = doc["created_at"].isoformat()
    return doc

@router.put("/logistics-prices/{price_id}")
async def update_logistics_price(price_id: str, data: LogisticsPriceTableCreate, current_user: Dict[str, Any] = Depends(get_bm_admin_user)):
    result = await db.logistics_prices.update_one(
        {"_id": ObjectId(price_id)},
        {"$set": data.model_dump()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Tabela de logística não encontrada")
    return {"message": "Atualizado com sucesso"}

@router.delete("/logistics-prices/{price_id}")
async def delete_logistics_price(price_id: str, current_user: Dict[str, Any] = Depends(get_bm_admin_user)):
    result = await db.logistics_prices.delete_one({"_id": ObjectId(price_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Tabela de logística não encontrada")
    return {"message": "Excluído com sucesso"}

# ==================== BM CALCULATION ====================

FUNCTION_NAMES = {
    "E": "ENGENHEIRO",
    "EN": "ENCARREGADO",
    "Sup": "SUPERVISOR",
    "T": "TÉCNICO",
    "M": "MECÂNICO",
    "TS": "TÉCNICO DE SEGURANÇA",
}

def parse_date_sortable(d: str) -> str:
    try:
        parts = d.split("/")
        if len(parts) == 3:
            return f"{parts[2]}-{parts[1]}-{parts[0]}"
    except:
        pass
    return d

@router.get("/bm/timesheets/{os_id}")
async def list_timesheets_for_bm(os_id: str, current_user: Dict[str, Any] = Depends(get_bm_admin_user)):
    """List available timesheets for a specific OS so user can select which to include in BM."""
    so = await db.service_orders.find_one({"_id": ObjectId(os_id)})
    if not so:
        raise HTTPException(status_code=404, detail="O.S. não encontrada")
    timesheets = await db.timesheets.find({"os_id": os_id}).to_list(500)
    result = []
    for ts in timesheets:
        entries = ts.get("entries", [])
        dates = sorted(set(e.get("date", "") for e in entries if e.get("date")), key=parse_date_sortable)
        employees = sorted(set(e.get("employee_name", "") for e in entries if e.get("employee_name")))
        result.append({
            "id": str(ts["_id"]),
            "os_number": ts.get("os_number", ""),
            "supervisor_name": ts.get("supervisor_name", ""),
            "entries_count": len(entries),
            "dates": dates,
            "date_range": f"{dates[0]} - {dates[-1]}" if dates else "",
            "employees": employees,
            "created_at": str(ts.get("created_at", "")),
        })
    return result


class BMCalculateRequest(BaseModel):
    timesheet_ids: List[str] = []
    data_inicio: str = ""
    data_fim: str = ""
    calc_mode: str = "onshore"  # "onshore" (8h base, /7) or "offshore" (12h base, /11)
    price_table_id: str = ""  # Optional: override auto-detected price table
    daily_only: bool = False  # Diária fechada: ignora horas extras e noturno


def _time_to_minutes_safe(s: str) -> int:
    try:
        parts = (s or "").split(":")
        return int(parts[0]) * 60 + (int(parts[1]) if len(parts) > 1 else 0)
    except Exception:
        return 0


def _worked_minutes(start_str: str, end_str: str) -> int:
    """Compute worked minutes between two HH:MM, handling overnight shifts."""
    s = _time_to_minutes_safe(start_str)
    e = _time_to_minutes_safe(end_str)
    if not start_str or not end_str:
        return 0
    if e <= s:
        e += 24 * 60
    return max(0, e - s)


def _date_to_weekday(d: str) -> int:
    """DD/MM/YYYY -> 0=Mon...6=Sun. Returns -1 on parse error."""
    try:
        from datetime import date as _date
        parts = d.split("/")
        return _date(int(parts[2]), int(parts[1]), int(parts[0])).weekday()
    except Exception:
        return -1


@router.post("/bm/calculate/{os_id}")
async def calculate_bm(os_id: str, body: BMCalculateRequest, current_user: Dict[str, Any] = Depends(get_bm_admin_user)):
    so = await db.service_orders.find_one({"_id": ObjectId(os_id)})
    if not so:
        raise HTTPException(status_code=404, detail="O.S. não encontrada")

    # Shift detection rule (defined by client):
    # NIGHT shift only when BOTH: start_hour >= 16 AND total_minutes > 720 (12h)
    # Otherwise DAY. Enforced inside the loop below.

    # Onshore: base 8h, divisor 7 (subtract 1h lunch from 8h)
    # Offshore: base 12h, divisor 11 (subtract 1h lunch from 12h)
    is_offshore = body.calc_mode == "offshore"
    base_hours = 12 if is_offshore else 8
    base_minutes = base_hours * 60
    hour_divisor = 11 if is_offshore else 7

    # Fetch only selected timesheets or all if none specified
    if body.timesheet_ids:
        ts_object_ids = [ObjectId(tid) for tid in body.timesheet_ids]
        timesheets = await db.timesheets.find({"_id": {"$in": ts_object_ids}, "os_id": os_id}).to_list(500)
    else:
        timesheets = await db.timesheets.find({"os_id": os_id}).to_list(500)

    # Parse date filters if provided
    date_filter_start = None
    date_filter_end = None
    if body.data_inicio:
        date_filter_start = parse_date_sortable(body.data_inicio)
    if body.data_fim:
        date_filter_end = parse_date_sortable(body.data_fim)

    # Aggregations per (function, shift):
    #   diaria_count: int (number of unique employee+date pairs)
    #   extras_weekday: int (minutes Mon-Fri beyond base)
    #   extras_saturday: int (minutes Saturday beyond base)
    #   extras_sunday_holiday: int (minutes Sunday/Holiday beyond base)
    function_data: Dict[str, Dict[str, Any]] = {}
    all_dates: List[str] = []

    # Pre-compute holidays for the years involved
    from holidays_util import all_holidays_in_range
    candidate_dates = []
    for ts in timesheets:
        for entry in ts.get("entries", []):
            d = entry.get("date", "")
            if d:
                candidate_dates.append(d)
    holidays_set = await all_holidays_in_range(db, candidate_dates)

    for ts in timesheets:
        for entry in ts.get("entries", []):
            func = entry.get("employee_function", "T")
            date = entry.get("date", "")
            start_str = entry.get("service_start", "") or ""
            end_str = entry.get("service_end", "") or ""
            travel_s = entry.get("travel_start", "") or ""
            travel_e = entry.get("travel_end", "") or ""

            has_service = start_str and end_str and start_str not in ("-", "0") and end_str not in ("-", "0")
            has_travel = travel_s and travel_e and travel_s not in ("-", "0") and travel_e not in ("-", "0")

            # Skip if neither service nor travel and skip if no date
            if not date or (not has_service and not has_travel):
                continue
            if date_filter_start or date_filter_end:
                date_sortable = parse_date_sortable(date)
                if date_filter_start and date_sortable < date_filter_start:
                    continue
                if date_filter_end and date_sortable > date_filter_end:
                    continue

            all_dates.append(date)

            # Determine reference start hour (service if present, else travel)
            ref_time = start_str if has_service else travel_s
            try:
                start_hour = int(ref_time.split(":")[0])
            except Exception:
                continue

            # Compute total worked minutes (service + travel) — needed for shift detection
            service_min = _worked_minutes(start_str, end_str) if has_service else 0
            travel_min = _worked_minutes(travel_s, travel_e) if has_travel else 0
            total_min = service_min + travel_min

            # Shift detection rule (defined by client):
            # NIGHT shift only when BOTH conditions met:
            #   1) Start hour >= 16:00
            #   2) Total work time > 12h (720 min)
            # Otherwise DAY (covers 06:30-18:30, 16:00-18:30 short embarques,
            # 06:30-22:00 day shift with overtime, exact 12h overnight 19:00-07:00).
            is_night_shift = (start_hour >= 16 and total_min > 720) and not body.daily_only
            shift = "night" if is_night_shift else "day"
            key = f"{func}_{shift}"

            if key not in function_data:
                function_data[key] = {
                    "diaria_emp_dates": set(),
                    "extras_weekday": 0,
                    "extras_saturday": 0,
                    "extras_sunday_holiday": 0,
                }

            # Add this employee+date as a unique daily (counts as full diaria
            # regardless of whether the day is service-only, travel-only, or both)
            emp_date = f"{entry.get('employee_id', '')}_{date}"
            function_data[key]["diaria_emp_dates"].add(emp_date)

            # Extra hours beyond base (skipped in daily-only mode)
            if total_min > base_minutes and not body.daily_only:
                extra_min = total_min - base_minutes
                weekday = _date_to_weekday(date)
                is_holiday = date in holidays_set
                if is_holiday or weekday == 6:
                    function_data[key]["extras_sunday_holiday"] += extra_min
                elif weekday == 5:
                    function_data[key]["extras_saturday"] += extra_min
                elif 0 <= weekday <= 4:
                    function_data[key]["extras_weekday"] += extra_min

    sorted_dates = sorted(set(all_dates), key=parse_date_sortable)
    data_inicial = body.data_inicio if body.data_inicio else (sorted_dates[0] if sorted_dates else "")
    data_final = body.data_fim if body.data_fim else (sorted_dates[-1] if sorted_dates else "")

    client_name = so.get("client", "")
    price_table = None
    if body.price_table_id and ObjectId.is_valid(body.price_table_id):
        price_table = await db.client_prices.find_one({"_id": ObjectId(body.price_table_id)})
    if not price_table:
        price_table = await db.client_prices.find_one({"client_name": client_name})

    items = []
    for key in sorted(function_data.keys()):
        func_code, shift = key.rsplit("_", 1)
        func_name = FUNCTION_NAMES.get(func_code, func_code)
        data = function_data[key]

        # Lookup rates from client price table
        day_rate = 0.0
        night_rate = 0.0
        day_discount_pct = 0.0
        if price_table:
            for p in price_table.get("prices", []):
                if p["function_code"] == func_code:
                    day_rate = p.get("day_rate", 0) or 0
                    night_rate = p.get("night_rate", 0) or round(day_rate * 1.2, 2)
                    day_discount_pct = float(p.get("day_discount_pct", 0) or 0)
                    break

        # Apply day discount only to day_rate (does NOT affect night_rate or extras).
        # Hour rate (used for extras) is derived from the ORIGINAL day/night rate, no discount.
        if shift == "day" and day_discount_pct > 0:
            base_rate = round(day_rate * (1 - day_discount_pct / 100.0), 2)
        else:
            base_rate = day_rate if shift == "day" else night_rate

        # Extras hour rate uses the ORIGINAL rate without discount
        original_rate = day_rate if shift == "day" else night_rate
        hour_rate = round(original_rate / hour_divisor, 2) if hour_divisor else 0
        display_name = func_name if shift == "day" else f"{func_name} (NOTURNO)"

        diaria_qtd = len(data["diaria_emp_dates"])
        if diaria_qtd > 0:
            items.append({
                "function_code": func_code,
                "function_name": display_name,
                "shift": shift,
                "category": "diaria",
                "data_inicial": data_inicial,
                "data_final": data_final,
                "valor_und": base_rate,
                "qtd": diaria_qtd,
                "unit_label": "dia",
                "valor_total": round(base_rate * diaria_qtd, 2),
            })

        # Build extras line items if any
        extras_specs = [
            ("extras_weekday", "H. Extra Seg-Sex (+70%)", 1.70),
            ("extras_saturday", "H. Extra Sábado (+80%)", 1.80),
            ("extras_sunday_holiday", "H. Extra Dom/Feriado (+100%)", 2.00),
        ]
        for field, label_suffix, mult in extras_specs:
            mins = data[field]
            if mins <= 0:
                continue
            qtd_h = round(mins / 60.0, 2)
            rate = round(hour_rate * mult, 2)
            items.append({
                "function_code": func_code,
                "function_name": f"{display_name} - {label_suffix}",
                "shift": shift,
                "category": field,
                "data_inicial": data_inicial,
                "data_final": data_final,
                "valor_und": rate,
                "qtd": qtd_h,
                "unit_label": "h",
                "valor_total": round(rate * qtd_h, 2),
            })

    subtotal = sum(item["valor_total"] for item in items)
    return {
        "os_id": os_id,
        "os_number": so.get("os_number", ""),
        "client": client_name,
        "location": so.get("location", ""),
        "service": so.get("service", ""),
        "calc_mode": body.calc_mode,
        "daily_only": body.daily_only,
        "base_hours": base_hours,
        "hour_divisor": hour_divisor,
        "data_inicial": data_inicial,
        "data_final": data_final,
        "items": items,
        "subtotal": round(subtotal, 2),
        "has_price_table": price_table is not None,
        "holidays_considered": sorted(holidays_set),
    }

# ==================== BM CRUD ====================

class BMCreate(BaseModel):
    os_id: str
    periodo: str = ""
    data: str = ""
    rev: str = "0"
    po_number: str = ""
    proposta: str = ""
    cod: str = ""
    price_table_id: str = ""
    items: List[dict]
    logistics_items: List[dict] = []
    logistics_table_id: str = ""
    subtotal: float
    impostos: float = 0.0
    valor_total: float

@router.post("/bm")
async def create_bm(data: BMCreate, current_user: Dict[str, Any] = Depends(get_bm_admin_user)):
    so = await db.service_orders.find_one({"_id": ObjectId(data.os_id)})
    if not so:
        raise HTTPException(status_code=404, detail="O.S. não encontrada")
    doc = data.model_dump()
    doc["os_number"] = so.get("os_number", "")
    doc["client"] = so.get("client", "")
    doc["location"] = so.get("location", "")
    doc["service"] = so.get("service", "")
    doc["created_by"] = current_user["_id"]
    doc["created_at"] = datetime.utcnow()
    doc["updated_at"] = datetime.utcnow()
    result = await db.boletins_medicao.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    doc.pop("_id", None)
    doc["created_at"] = doc["created_at"].isoformat()
    doc["updated_at"] = doc["updated_at"].isoformat()
    return doc

@router.get("/bm")
async def list_bm(current_user: Dict[str, Any] = Depends(get_bm_admin_user)):
    bms = await db.boletins_medicao.find().sort("created_at", -1).to_list(500)
    for bm in bms:
        bm["id"] = str(bm.pop("_id"))
        bm.pop("_id", None)
        for field in ["created_at", "updated_at"]:
            val = bm.get(field, "")
            bm[field] = val.isoformat() if hasattr(val, "isoformat") else str(val)
    return bms

@router.get("/bm/{bm_id}")
async def get_bm_detail(bm_id: str, current_user: Dict[str, Any] = Depends(get_bm_admin_user)):
    bm = await db.boletins_medicao.find_one({"_id": ObjectId(bm_id)})
    if not bm:
        raise HTTPException(status_code=404, detail="BM não encontrado")
    bm["id"] = str(bm.pop("_id"))
    bm.pop("_id", None)
    for field in ["created_at", "updated_at"]:
        val = bm.get(field, "")
        bm[field] = val.isoformat() if hasattr(val, "isoformat") else str(val)
    return bm

@router.delete("/bm/{bm_id}")
async def delete_bm(bm_id: str, current_user: Dict[str, Any] = Depends(get_bm_admin_user)):
    result = await db.boletins_medicao.delete_one({"_id": ObjectId(bm_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="BM não encontrado")
    return {"message": "BM excluído com sucesso"}


@router.put("/bm/{bm_id}")
async def update_bm(bm_id: str, data: BMCreate, current_user: Dict[str, Any] = Depends(get_bm_admin_user)):
    existing = await db.boletins_medicao.find_one({"_id": ObjectId(bm_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="BM não encontrado")
    so = await db.service_orders.find_one({"_id": ObjectId(data.os_id)})
    if not so:
        raise HTTPException(status_code=404, detail="O.S. não encontrada")
    update_doc = data.model_dump()
    update_doc["os_number"] = so.get("os_number", "")
    update_doc["client"] = so.get("client", "")
    update_doc["location"] = so.get("location", "")
    update_doc["service"] = so.get("service", "")
    update_doc["updated_at"] = datetime.utcnow()
    await db.boletins_medicao.update_one({"_id": ObjectId(bm_id)}, {"$set": update_doc})
    update_doc["id"] = bm_id
    update_doc["updated_at"] = update_doc["updated_at"].isoformat()
    return update_doc

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

# ==================== BM PDF GENERATION ====================

def format_currency(value: float) -> str:
    formatted = f"{value:,.2f}"
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"

@router.get("/bm/{bm_id}/pdf")
async def generate_bm_pdf(bm_id: str, token: Optional[str] = Query(None), credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))):
    # Auth via token query param or header
    actual_token = token
    if not actual_token and credentials:
        actual_token = credentials.credentials
    if not actual_token:
        raise HTTPException(status_code=401, detail="Token required")
    try:
        payload = jwt.decode(actual_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user or user.get("role") != UserRole.ADMIN or not user.get("bm_access", False):
            raise HTTPException(status_code=403, detail="Acesso negado")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

    bm = await db.boletins_medicao.find_one({"_id": ObjectId(bm_id)})
    if not bm:
        raise HTTPException(status_code=404, detail="BM não encontrado")

    buf = io.BytesIO()
    page_w, page_h = A4[1], A4[0]  # Landscape
    border_margin = 1.0 * cm
    border_color = colors.HexColor('#AAAAAA')
    
    content_left = border_margin + 0.3 * cm
    content_right = border_margin + 0.3 * cm
    content_width = page_w - content_left - content_right
    
    page_counter = [0]
    
    def draw_bm_page(canvas_obj, doc_obj, page_num):
        canvas_obj.saveState()
        
        # === PAGE BORDER ===
        canvas_obj.setStrokeColor(border_color)
        canvas_obj.setLineWidth(1)
        canvas_obj.rect(border_margin, border_margin, page_w - 2 * border_margin, page_h - 2 * border_margin)
        
        # === HEADER BOX ===
        header_top = page_h - border_margin - 0.5 * cm
        header_height = 2.0 * cm
        header_bottom = header_top - header_height
        canvas_obj.setStrokeColor(colors.HexColor('#777777'))
        canvas_obj.setLineWidth(0.5)
        canvas_obj.rect(content_left, header_bottom, content_width, header_height)
        
        # Logo
        logo_path = ROOT_DIR / "../logo.bmp"
        if logo_path.exists():
            try:
                from reportlab.lib.utils import ImageReader
                pil_img = PILImage.open(logo_path)
                temp_logo = io.BytesIO()
                pil_img.save(temp_logo, format='JPEG')
                temp_logo.seek(0)
                logo_w = 4.0 * cm
                logo_h = 1.4 * cm
                canvas_obj.drawImage(ImageReader(temp_logo), content_left + 0.3 * cm, header_bottom + (header_height - logo_h) / 2, width=logo_w, height=logo_h, preserveAspectRatio=True, mask='auto')
            except Exception:
                pass
        
        # Vertical line after logo
        sep_x = content_left + 4.6 * cm
        canvas_obj.line(sep_x, header_bottom, sep_x, header_top)
        
        # Title "BOLETIM DE MEDIÇÃO" - centered between logo separator and right side info
        right_info_width = 3.5 * cm
        title_area_start = sep_x
        title_area_end = content_left + content_width - right_info_width
        title_x = title_area_start + (title_area_end - title_area_start) / 2
        canvas_obj.setFont("Helvetica-Bold", 11)
        canvas_obj.drawCentredString(title_x, header_top - 0.6 * cm, "BOLETIM DE MEDIÇÃO")
        canvas_obj.setFont("Helvetica", 7)
        canvas_obj.drawCentredString(title_x, header_top - 0.95 * cm, "Anexo 02_formulário - Boletim de Medição")
        
        # Right side details
        detail_x = page_w - content_right - 0.3 * cm
        line_h = 0.32 * cm
        detail_y = header_top - 0.4 * cm
        
        def _draw_right_label(label, value, y):
            canvas_obj.setFont("Helvetica-Bold", 7)
            canvas_obj.drawRightString(detail_x, y, f"{label} {value}")
        
        _draw_right_label("Data:", bm.get('data', ''), detail_y)
        detail_y -= line_h
        _draw_right_label("Rev.:", bm.get('rev', '0'), detail_y)
        detail_y -= line_h
        _draw_right_label("Período:", bm.get('periodo', ''), detail_y)
        detail_y -= line_h
        _draw_right_label("OS:", bm.get('os_number', ''), detail_y)
        
        # === FOOTER BOX ===
        footer_bottom = border_margin + 0.5 * cm
        footer_height = 1.4 * cm
        footer_top = footer_bottom + footer_height
        canvas_obj.setStrokeColor(colors.HexColor('#777777'))
        canvas_obj.setLineWidth(0.5)
        canvas_obj.rect(content_left, footer_bottom, content_width, footer_height)
        
        center_x = page_w / 2
        y = footer_top - 0.45 * cm
        canvas_obj.setFont("Helvetica-Bold", 8)
        canvas_obj.drawCentredString(center_x, y, "TWAS REPAIR SERVIÇOS NAVAIS E INDUSTRIAIS LTDA")
        y -= 0.3 * cm
        canvas_obj.setFont("Helvetica", 7)
        canvas_obj.drawCentredString(center_x, y, "Travessa Frederico Marques, N\u00b0 84, Boa Vista, São Gonçalo, Rio de Janeiro - CEP.: 24.466-180.")
        y -= 0.28 * cm
        canvas_obj.drawCentredString(center_x, y, "twas@twasrepair.com - www.twasrepair.com")
        
        # Page number
        canvas_obj.setFont("Helvetica", 7)
        canvas_obj.drawRightString(page_w - border_margin - 0.5 * cm, border_margin + 0.2 * cm, f"{page_num}")
        
        canvas_obj.restoreState()
    
    def on_first_page_bm(c, d):
        page_counter[0] = 1
        draw_bm_page(c, d, 1)
    
    def on_later_pages_bm(c, d):
        page_counter[0] += 1
        draw_bm_page(c, d, page_counter[0])
    
    doc = SimpleDocTemplate(
        buf, pagesize=(page_w, page_h),
        topMargin=border_margin + 2.8 * cm,
        bottomMargin=border_margin + 2.1 * cm,
        leftMargin=content_left,
        rightMargin=content_right,
    )
    styles = getSampleStyleSheet()
    elements = []

    # ---- CLIENT INFO ----
    client_style = ParagraphStyle('ClientInfo', fontSize=9, leading=12, textColor=colors.black)
    client_info = Table([
        [Paragraph(f"<b>Cliente:</b> {bm.get('client', '')}", client_style),
         Paragraph(f"<b>P.O.:</b> {bm.get('po_number', '')}", client_style),
         Paragraph(f"<b>Proposta:</b> {bm.get('proposta', '')}", client_style)]
    ], colWidths=[content_width * 0.4, content_width * 0.3, content_width * 0.3])
    client_info.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 0.5, border_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDDDDD')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(client_info)
    elements.append(Spacer(1, 6))

    # ---- SERVICE SCOPE ----
    scope_style = ParagraphStyle('ScopeStyle', fontSize=9, fontName='Helvetica-Bold', textColor=colors.black)
    scope_table = Table([
        [Paragraph("<b>ESCOPO DE SERVIÇOS:</b>", scope_style),
         Paragraph(f"<b>{bm.get('service', '')}</b>", scope_style)]
    ], colWidths=[content_width * 0.25, content_width * 0.75])
    scope_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 0.5, border_color),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F5F5F5')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(scope_table)
    elements.append(Spacer(1, 4))

    # ---- MAIN TABLE ----
    th_style = ParagraphStyle('TH', fontSize=8, fontName='Helvetica-Bold', alignment=TA_CENTER, textColor=colors.black)
    td_style = ParagraphStyle('TD', fontSize=8, alignment=TA_CENTER, textColor=colors.black)
    td_right = ParagraphStyle('TDRight', fontSize=8, alignment=TA_RIGHT, textColor=colors.black)
    td_left = ParagraphStyle('TDLeft', fontSize=8, alignment=TA_LEFT, textColor=colors.black)

    col_widths = [
        content_width * 0.10, content_width * 0.10, content_width * 0.07,
        content_width * 0.10, content_width * 0.28, content_width * 0.13,
        content_width * 0.07, content_width * 0.15,
    ]

    header_row = [
        Paragraph("Data Inicial", th_style), Paragraph("Data Final", th_style),
        Paragraph("Linha", th_style), Paragraph("CÓD.", th_style),
        Paragraph("Descrição das Atividades", th_style), Paragraph("Valor und", th_style),
        Paragraph("Qtd", th_style), Paragraph("Valor total", th_style),
    ]

    table_data = [header_row]
    items = bm.get("items", [])

    for idx, item in enumerate(items):
        table_data.append([
            Paragraph(item.get("data_inicial", ""), td_style),
            Paragraph(item.get("data_final", ""), td_style),
            Paragraph(item.get("linha", str(idx + 1)), td_style),
            Paragraph(item.get("cod", bm.get("cod", "")), td_style),
            Paragraph(item.get("function_name", ""), td_left),
            Paragraph(format_currency(item.get("valor_und", 0)), td_right),
            Paragraph(str(item.get("qtd", 0)), td_style),
            Paragraph(format_currency(item.get("valor_total", 0)), td_right),
        ])

    # Logistics items appear after regular items, before Subtotal
    logistics_items = bm.get("logistics_items", []) or []
    _per = [p.strip() for p in (bm.get("periodo") or "").split(" a ")]
    bm_di = _per[0] if _per and _per[0] else ""
    bm_df = _per[1] if len(_per) > 1 and _per[1] else bm_di
    # Fallback: smallest/biggest date across calculated items
    _dis = [it.get("data_inicial", "") for it in items if it.get("data_inicial")]
    _dfs = [it.get("data_final", "") for it in items if it.get("data_final")]
    if not bm_di and _dis:
        bm_di = min(_dis, key=parse_date_sortable)
    if not bm_df and (_dfs or _dis):
        bm_df = max(_dfs or _dis, key=parse_date_sortable)
    for lidx, litem in enumerate(logistics_items):
        desc = litem.get("description", "")
        unit_price = float(litem.get("unit_price", 0) or 0)
        qty = int(litem.get("quantity", 0) or 0)
        total = float(litem.get("total", unit_price * qty) or 0)
        table_data.append([
            Paragraph(litem.get("data_inicial") or bm_di, td_style),
            Paragraph(litem.get("data_final") or bm_df, td_style),
            Paragraph(str(len(items) + lidx + 1), td_style),
            Paragraph(litem.get("cod", ""), td_style),
            Paragraph(desc, td_left),
            Paragraph(format_currency(unit_price), td_right),
            Paragraph(str(qty), td_style),
            Paragraph(format_currency(total), td_right),
        ])

    total_data_rows = len(items) + len(logistics_items)
    empty_rows_needed = max(0, 8 - total_data_rows)
    for _ in range(empty_rows_needed):
        table_data.append([Paragraph("", td_style)] * 7 + [Paragraph("", td_right)])

    bold_right = ParagraphStyle('BoldRight', fontSize=9, fontName='Helvetica-Bold', alignment=TA_RIGHT, textColor=colors.black)
    table_data.append(["", "", "", "", Paragraph("<b>Subtotal</b>", bold_right), "", "", Paragraph(f"<b>{format_currency(bm.get('subtotal', 0))}</b>", bold_right)])
    table_data.append(["", "", "", "", Paragraph("<b>Impostos</b>", bold_right), "", "", Paragraph(format_currency(bm.get("impostos", 0)), td_right)])
    table_data.append(["", "", "", "", Paragraph("<b>Valor Total</b>", bold_right), "", "", Paragraph(f"<b>{format_currency(bm.get('valor_total', 0))}</b>", bold_right)])

    main_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    num_data_rows = total_data_rows + empty_rows_needed
    table_style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E8EAF6')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 0.5, border_color),
        ('INNERGRID', (0, 0), (-1, num_data_rows), 0.5, colors.HexColor('#DDDDDD')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('LINEABOVE', (0, num_data_rows + 1), (-1, num_data_rows + 1), 1, colors.HexColor('#1a237e')),
        ('SPAN', (0, num_data_rows + 1), (4, num_data_rows + 1)),
        ('SPAN', (5, num_data_rows + 1), (6, num_data_rows + 1)),
        ('SPAN', (0, num_data_rows + 2), (4, num_data_rows + 2)),
        ('SPAN', (5, num_data_rows + 2), (6, num_data_rows + 2)),
        ('SPAN', (0, num_data_rows + 3), (4, num_data_rows + 3)),
        ('SPAN', (5, num_data_rows + 3), (6, num_data_rows + 3)),
        ('BACKGROUND', (0, num_data_rows + 3), (-1, num_data_rows + 3), colors.HexColor('#E8EAF6')),
    ]
    for i in range(1, num_data_rows + 1):
        if i % 2 == 0:
            table_style_cmds.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F8F8F8')))
    main_table.setStyle(TableStyle(table_style_cmds))
    elements.append(main_table)

    doc.build(elements, onFirstPage=on_first_page_bm, onLaterPages=on_later_pages_bm)
    buf.seek(0)

    filename = f"BM_{bm.get('os_number', 'N')}_{bm.get('client', '')}.pdf".replace(" ", "_")
    return Response(
        content=buf.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
        }
    )
