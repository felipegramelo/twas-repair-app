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

from database import db
from config import SECRET_KEY, ALGORITHM, get_object
from dependencies import get_current_user, get_admin_user

router = APIRouter()

from dependencies import get_bm_admin_user

# ==================== CLIENT PRICE TABLE ENDPOINTS ====================

class ClientPriceEntry(BaseModel):
    function_code: str
    function_name: str
    day_rate: float
    night_rate: float

class ClientPriceTableCreate(BaseModel):
    client_name: str
    prices: List[ClientPriceEntry]

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


@router.post("/bm/calculate/{os_id}")
async def calculate_bm(os_id: str, body: BMCalculateRequest, current_user: Dict[str, Any] = Depends(get_bm_admin_user)):
    so = await db.service_orders.find_one({"_id": ObjectId(os_id)})
    if not so:
        raise HTTPException(status_code=404, detail="O.S. não encontrada")

    schedule_type = so.get("schedule_type", "07-19")
    if schedule_type == "06-18":
        day_start, day_end = 6, 18
    else:
        day_start, day_end = 7, 19

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

    # Count unique employee+date per function per shift
    function_days = {}
    all_dates = []

    for ts in timesheets:
        for entry in ts.get("entries", []):
            func = entry.get("employee_function", "T")
            date = entry.get("date", "")
            start_str = entry.get("service_start", "")
            if not start_str or not date:
                continue
            # Apply date filter
            if date_filter_start or date_filter_end:
                date_sortable = parse_date_sortable(date)
                if date_filter_start and date_sortable < date_filter_start:
                    continue
                if date_filter_end and date_sortable > date_filter_end:
                    continue
            all_dates.append(date)
            try:
                start_hour = int(start_str.split(":")[0])
            except:
                continue
            is_day = day_start <= start_hour < day_end
            shift = "day" if is_day else "night"
            key = f"{func}_{shift}"
            if key not in function_days:
                function_days[key] = set()
            emp_date = f"{entry.get('employee_id', '')}_{date}"
            function_days[key].add(emp_date)

    # Sort dates
    sorted_dates = sorted(set(all_dates), key=parse_date_sortable)
    # Use user-provided dates or auto-detect from data
    data_inicial = body.data_inicio if body.data_inicio else (sorted_dates[0] if sorted_dates else "")
    data_final = body.data_fim if body.data_fim else (sorted_dates[-1] if sorted_dates else "")

    # Get client prices
    client_name = so.get("client", "")
    price_table = await db.client_prices.find_one({"client_name": client_name})

    items = []
    for key in sorted(function_days.keys()):
        dates_set = function_days[key]
        func_code, shift = key.rsplit("_", 1)
        func_name = FUNCTION_NAMES.get(func_code, func_code)
        qtd = len(dates_set)
        rate = 0.0
        if price_table:
            for p in price_table.get("prices", []):
                if p["function_code"] == func_code:
                    day_rate = p.get("day_rate", 0)
                    if shift == "day":
                        rate = day_rate
                    else:
                        rate = round(day_rate * 1.2, 2)  # Noturno = diurno + 20%
                    break
        display_name = func_name if shift == "day" else f"{func_name} (NOTURNO)"
        items.append({
            "function_code": func_code,
            "function_name": display_name,
            "shift": shift,
            "data_inicial": data_inicial,
            "data_final": data_final,
            "valor_und": rate,
            "qtd": qtd,
            "valor_total": round(rate * qtd, 2),
        })

    subtotal = sum(item["valor_total"] for item in items)
    return {
        "os_id": os_id,
        "os_number": so.get("os_number", ""),
        "client": client_name,
        "location": so.get("location", ""),
        "service": so.get("service", ""),
        "schedule_type": schedule_type,
        "data_inicial": data_inicial,
        "data_final": data_final,
        "items": items,
        "subtotal": round(subtotal, 2),
        "has_price_table": price_table is not None,
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
    items: List[dict]
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

    empty_rows_needed = max(0, 8 - len(items))
    for _ in range(empty_rows_needed):
        table_data.append([Paragraph("", td_style)] * 7 + [Paragraph("", td_right)])

    bold_right = ParagraphStyle('BoldRight', fontSize=9, fontName='Helvetica-Bold', alignment=TA_RIGHT, textColor=colors.black)
    table_data.append(["", "", "", "", Paragraph("<b>Subtotal</b>", bold_right), "", "", Paragraph(f"<b>{format_currency(bm.get('subtotal', 0))}</b>", bold_right)])
    table_data.append(["", "", "", "", Paragraph("<b>Impostos</b>", bold_right), "", "", Paragraph(format_currency(bm.get("impostos", 0)), td_right)])
    table_data.append(["", "", "", "", Paragraph("<b>Valor Total</b>", bold_right), "", "", Paragraph(f"<b>{format_currency(bm.get('valor_total', 0))}</b>", bold_right)])

    main_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    num_data_rows = len(items) + empty_rows_needed
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



