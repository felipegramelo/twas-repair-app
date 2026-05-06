import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import Response, StreamingResponse
from typing import List, Optional, Dict, Any
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
from models import TimesheetCreate, UserRole, _validate_timesheet_entries

router = APIRouter()

ROOT_DIR = Path(__file__).parent.parent

@router.post("/timesheets", response_model=dict)
async def create_timesheet(ts_data: TimesheetCreate, current_user: Dict[str, Any] = Depends(get_current_user)):
    if len(ts_data.entries) > 12:
        raise HTTPException(status_code=400, detail="Máximo de 12 entradas por timesheet. Crie um novo timesheet para mais funcionários.")
    _validate_timesheet_entries(ts_data.entries)
    # Get service order details
    so = await db.service_orders.find_one({"_id": ObjectId(ts_data.os_id)})
    if not so:
        raise HTTPException(status_code=404, detail="Service Order not found")
    
    ts_dict = ts_data.model_dump()
    ts_dict["os_number"] = so["os_number"]
    ts_dict["client"] = so["client"]
    ts_dict["embarcacao"] = so.get("embarcacao", "")
    ts_dict["location"] = so["location"]
    ts_dict["service"] = so["service"]
    ts_dict["supervisor_id"] = current_user["_id"]
    ts_dict["supervisor_name"] = current_user["name"]
    ts_dict["created_at"] = datetime.utcnow()
    ts_dict["updated_at"] = datetime.utcnow()
    
    # Auto-incrementing sequence number per OS
    existing_count = await db.timesheets.count_documents({"os_id": ts_data.os_id})
    ts_dict["sequence_number"] = existing_count + 1
    
    result = await db.timesheets.insert_one(ts_dict)
    
    # Reload from database and convert _id to id
    created_ts = await db.timesheets.find_one({"_id": result.inserted_id})
    created_ts["id"] = str(created_ts.pop("_id"))
    created_ts["created_at"] = created_ts["created_at"].isoformat() if isinstance(created_ts["created_at"], datetime) else created_ts["created_at"]
    created_ts["updated_at"] = created_ts["updated_at"].isoformat() if isinstance(created_ts["updated_at"], datetime) else created_ts["updated_at"]
    
    return created_ts


@router.get("/timesheets", response_model=List[dict])
async def get_timesheets(current_user: Dict[str, Any] = Depends(get_current_user)):
    query = {}
    if current_user.get("role") != UserRole.ADMIN:
        user_id = current_user["_id"]
        query = {"$or": [
            {"supervisor_id": user_id},
            {"shared_with": user_id}
        ]}
    
    timesheets = await db.timesheets.find(query).sort("created_at", -1).to_list(500)
    result = []
    
    # Cache SO data for backfilling legacy timesheets
    so_cache: Dict[str, dict] = {}
    
    # For admin: compute sequence_number for timesheets that don't have one
    if current_user.get("role") == UserRole.ADMIN:
        os_groups: Dict[str, list] = {}
        for ts in timesheets:
            os_id = ts.get("os_id", "")
            if os_id not in os_groups:
                os_groups[os_id] = []
            os_groups[os_id].append(ts)
        for os_id in os_groups:
            os_groups[os_id].sort(key=lambda x: x.get("created_at", datetime.min))
            for idx, ts in enumerate(os_groups[os_id]):
                if "sequence_number" not in ts or not ts.get("sequence_number"):
                    ts["sequence_number"] = idx + 1
    
    for ts in timesheets:
        # Backfill missing service/location/observations from SO for legacy timesheets
        if not ts.get("service") or not ts.get("location"):
            os_id = ts.get("os_id", "")
            if os_id and os_id not in so_cache:
                try:
                    so = await db.service_orders.find_one({"_id": ObjectId(os_id)})
                    so_cache[os_id] = so or {}
                except Exception:
                    so_cache[os_id] = {}
            so_data = so_cache.get(os_id, {})
            if not ts.get("service"):
                ts["service"] = so_data.get("service", "")
            if not ts.get("location"):
                ts["location"] = so_data.get("location", "")
        if "observations" not in ts:
            ts["observations"] = ""
        
        ts["id"] = str(ts.pop("_id"))
        result.append(ts)
    return result


@router.get("/timesheets/{ts_id}")
async def get_timesheet(ts_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    ts = await db.timesheets.find_one({"_id": ObjectId(ts_id)})
    if not ts:
        raise HTTPException(status_code=404, detail="Timesheet not found")
    
    # Check permissions: owner, admin, or shared
    if current_user.get("role") != UserRole.ADMIN and ts["supervisor_id"] != current_user["_id"] and current_user["_id"] not in ts.get("shared_with", []):
        raise HTTPException(status_code=403, detail="Access denied")
    
    ts["id"] = str(ts.pop("_id"))  # Rename _id to id
    return ts


@router.put("/timesheets/{ts_id}")
async def update_timesheet(ts_id: str, ts_data: TimesheetCreate, current_user: Dict[str, Any] = Depends(get_current_user)):
    existing = await db.timesheets.find_one({"_id": ObjectId(ts_id)})
    if existing and existing.get("status") == "finalized":
        raise HTTPException(status_code=403, detail="Timesheet finalizada. Não é possível editar.")
    if len(ts_data.entries) > 12:
        raise HTTPException(status_code=400, detail="Máximo de 12 entradas por timesheet. Crie um novo timesheet para mais funcionários.")
    _validate_timesheet_entries(ts_data.entries)
    ts = await db.timesheets.find_one({"_id": ObjectId(ts_id)})
    if not ts:
        raise HTTPException(status_code=404, detail="Timesheet not found")
    
    # Check permissions
    if current_user.get("role") != UserRole.ADMIN and ts["supervisor_id"] != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get service order details
    so = await db.service_orders.find_one({"_id": ObjectId(ts_data.os_id)})
    if not so:
        raise HTTPException(status_code=404, detail="Service Order not found")
    
    update_dict = ts_data.model_dump()
    update_dict["os_number"] = so["os_number"]
    update_dict["client"] = so["client"]
    update_dict["location"] = so["location"]
    update_dict["service"] = so["service"]
    update_dict["updated_at"] = datetime.utcnow()
    
    await db.timesheets.update_one(
        {"_id": ObjectId(ts_id)},
        {"$set": update_dict}
    )
    
    updated_ts = await db.timesheets.find_one({"_id": ObjectId(ts_id)})
    updated_ts["id"] = str(updated_ts.pop("_id"))  # Return id instead of _id
    return updated_ts


@router.delete("/timesheets/{ts_id}")
async def delete_timesheet(ts_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    ts = await db.timesheets.find_one({"_id": ObjectId(ts_id)})
    if not ts:
        raise HTTPException(status_code=404, detail="Timesheet not found")
    
    # Check permissions
    if current_user.get("role") != UserRole.ADMIN and ts["supervisor_id"] != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await db.timesheets.delete_one({"_id": ObjectId(ts_id)})
    return {"message": "Timesheet deleted successfully"}


@router.put("/timesheets/{ts_id}/finalize")
async def finalize_timesheet(ts_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    ts = await db.timesheets.find_one({"_id": ObjectId(ts_id)})
    if not ts:
        raise HTTPException(status_code=404, detail="Timesheet não encontrada")
    if current_user.get("role") != UserRole.ADMIN and ts["supervisor_id"] != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    await db.timesheets.update_one({"_id": ObjectId(ts_id)}, {"$set": {"status": "finalized", "updated_at": datetime.utcnow()}})
    return {"success": True}


@router.put("/reports/{report_id}/finalize")
async def finalize_report(report_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    report = await db.reports.find_one({"_id": ObjectId(report_id)})
    if not report:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")
    if current_user.get("role") != UserRole.ADMIN and report["supervisor_id"] != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    await db.reports.update_one({"_id": ObjectId(report_id)}, {"$set": {"status": "finalized", "updated_at": datetime.utcnow()}})
    return {"success": True}


@router.put("/reports/{report_id}/revert")
async def revert_report(report_id: str, current_user: Dict[str, Any] = Depends(get_admin_user)):
    report = await db.reports.find_one({"_id": ObjectId(report_id)})
    if not report:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")
    await db.reports.update_one({"_id": ObjectId(report_id)}, {"$set": {"status": "draft", "updated_at": datetime.utcnow()}})
    return {"success": True}


@router.put("/timesheets/{ts_id}/revert")
async def revert_timesheet(ts_id: str, current_user: Dict[str, Any] = Depends(get_admin_user)):
    ts = await db.timesheets.find_one({"_id": ObjectId(ts_id)})
    if not ts:
        raise HTTPException(status_code=404, detail="Timesheet não encontrada")
    await db.timesheets.update_one({"_id": ObjectId(ts_id)}, {"$set": {"status": "draft", "updated_at": datetime.utcnow()}})
    return {"success": True}


@router.post("/timesheets/{ts_id}/duplicate")
async def duplicate_timesheet(ts_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    original = await db.timesheets.find_one({"_id": ObjectId(ts_id)})
    if not original:
        raise HTTPException(status_code=404, detail="Timesheet não encontrada")
    # Auto-incrementing sequence number per OS
    os_id = original["os_id"]
    existing_count = await db.timesheets.count_documents({"os_id": os_id})
    new_ts = {
        "os_id": os_id,
        "os_number": original.get("os_number", ""),
        "client": original.get("client", ""),
        "supervisor_id": current_user["_id"],
        "supervisor_name": current_user.get("name", ""),
        "entries": original.get("entries", []),
        "status": "draft",
        "sequence_number": existing_count + 1,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    result = await db.timesheets.insert_one(new_ts)
    new_ts["id"] = str(result.inserted_id)
    del new_ts["_id"]
    new_ts["created_at"] = new_ts["created_at"].isoformat()
    new_ts["updated_at"] = new_ts["updated_at"].isoformat()
    return new_ts


# ==================== PDF GENERATION ====================

@router.get("/timesheets/{ts_id}/pdf")
async def generate_timesheet_pdf(ts_id: str, token: Optional[str] = Query(None), credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))):
    # Accept token via query string (?token=...) OR Authorization: Bearer header (for mobile & web)
    auth_token = token
    if not auth_token and credentials:
        auth_token = credentials.credentials
    if not auth_token:
        raise HTTPException(status_code=401, detail="Token não fornecido")
    try:
        payload = jwt.decode(auth_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token inválido")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

    current_user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not current_user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    # Normalize _id to string (matches other routes that use get_current_user)
    current_user["_id"] = str(current_user["_id"])

    ts = await db.timesheets.find_one({"_id": ObjectId(ts_id)})
    if not ts:
        raise HTTPException(status_code=404, detail="Timesheet not found")

    # Check permissions (same rule as GET: admin, owner, or shared)
    if (
        current_user.get("role") != UserRole.ADMIN
        and ts["supervisor_id"] != current_user["_id"]
        and current_user["_id"] not in ts.get("shared_with", [])
    ):
        raise HTTPException(status_code=403, detail="Access denied")

    # Fallback: timesheets created before embarcacao was tracked - load from OS
    if not ts.get("embarcacao"):
        try:
            so_doc = await db.service_orders.find_one({"_id": ObjectId(ts.get("os_id"))})
            if so_doc:
                ts["embarcacao"] = so_doc.get("embarcacao", "")
        except Exception:
            pass
    
    # Create PDF with A4 page size
    buffer = io.BytesIO()
    page_width, page_height = A4
    
    # Border margins (distance from page edge) - TIMESHEET uses original values
    border_margin = 0.7*cm
    
    # Content margins (inside the border) - aligned with header/footer
    content_left = border_margin + 0.5*cm
    content_right = border_margin + 0.5*cm
    content_top = border_margin + 2.5*cm  # Space for header drawn on canvas
    content_bottom = border_margin + 1.8*cm  # Space for footer drawn on canvas
    
    content_width = page_width - content_left - content_right
    
    # Preload logo
    logo_path = ROOT_DIR / "../logo.bmp"
    logo_image = None
    if logo_path.exists():
        try:
            pil_img = PILImage.open(logo_path)
            if pil_img.mode != 'RGB':
                pil_img = pil_img.convert('RGB')
            temp_logo = io.BytesIO()
            pil_img.save(temp_logo, format='JPEG')
            temp_logo.seek(0)
            logo_image = temp_logo
        except Exception as e:
            logging.error(f"Error loading logo: {e}")
    
    from datetime import datetime as dt
    current_date = dt.now().strftime("%d/%m/%Y")
    
    # Calculate total pages
    entries_per_page = 12
    total_entries = len(ts["entries"])
    total_pages = (total_entries + entries_per_page - 1) // entries_per_page if total_entries > 0 else 1
    
    def draw_page_template(canvas_obj, doc_obj, page_num):
        canvas_obj.saveState()
        
        # === PAGE BORDER ===
        canvas_obj.setStrokeColor(colors.black)
        canvas_obj.setLineWidth(0.5)
        canvas_obj.rect(
            border_margin, border_margin,
            page_width - 2*border_margin,
            page_height - 2*border_margin
        )
        
        # === HEADER BOX (inside border, top area) ===
        header_top = page_height - border_margin - 0.4*cm
        header_height = 1.8*cm
        header_bottom = header_top - header_height
        
        # Draw header box
        canvas_obj.setLineWidth(0.5)
        canvas_obj.rect(content_left, header_bottom, page_width - content_left - content_right, header_height)
        
        # Logo (left side)
        if logo_image:
            logo_image.seek(0)
            from reportlab.lib.utils import ImageReader
            img_reader = ImageReader(logo_image)
            canvas_obj.drawImage(img_reader, content_left + 0.2*cm, header_bottom + 0.1*cm, width=3.8*cm, height=1.6*cm, preserveAspectRatio=True)
        
        # Title (center)
        canvas_obj.setFont("Helvetica-Bold", 12)
        canvas_obj.drawCentredString(page_width/2, header_bottom + 1.0*cm, "RELATÓRIO DE HORAS")
        canvas_obj.setFont("Helvetica-Bold", 10)
        canvas_obj.drawCentredString(page_width/2, header_bottom + 0.35*cm, "TIME SHEET")
        
        # Right side - Client/OS details
        right_x = page_width - content_right - 0.2*cm
        detail_y = header_top - 0.35*cm
        canvas_obj.setFont("Helvetica-Bold", 6.5)
        canvas_obj.drawRightString(right_x, detail_y, f"Cliente: {ts.get('client', '')}")
        detail_y -= 0.35*cm
        canvas_obj.drawRightString(right_x, detail_y, f"Embarcação: {ts.get('location', '')}")
        detail_y -= 0.35*cm
        canvas_obj.drawRightString(right_x, detail_y, f"OS: {ts.get('os_number', '')}")
        detail_y -= 0.35*cm
        canvas_obj.setFont("Helvetica", 6.5)
        canvas_obj.drawRightString(right_x, detail_y, f"{current_date}  |  Rev.: 0")
        
        # === FOOTER BOX (inside border, bottom area) ===
        footer_bottom = border_margin + 0.4*cm
        footer_height = 1.4*cm
        footer_top = footer_bottom + footer_height
        
        # Draw footer box
        canvas_obj.setLineWidth(0.5)
        canvas_obj.rect(content_left, footer_bottom, page_width - content_left - content_right, footer_height)
        
        # Company info centered in footer box
        center_x = page_width / 2
        y = footer_top - 0.25*cm
        canvas_obj.setFont("Helvetica-Bold", 5.5)
        canvas_obj.drawCentredString(center_x, y, "TWAS REPAIR SERVIÇOS NAVAIS E INDUSTRIAIS LTDA - CNPJ: 31.839.501/0001-90")
        y -= 0.25*cm
        canvas_obj.setFont("Helvetica", 5.5)
        canvas_obj.drawCentredString(center_x, y, "Travessa Frederico Marques, N° 84, Boa Vista, São Gonçalo, Rio de Janeiro - CEP.: 24.466-180")
        y -= 0.22*cm
        canvas_obj.drawCentredString(center_x, y, "twas@twasrepair.com  |  www.twasrepair.com")
        y -= 0.25*cm
        canvas_obj.setFont("Helvetica-BoldOblique", 6)
        canvas_obj.drawCentredString(center_x, y, "TOGETHER WE ARE STRONGER")
        y -= 0.2*cm
        canvas_obj.setFont("Helvetica", 5.5)
        canvas_obj.drawCentredString(center_x, y, f"Página {page_num} de {total_pages}")
        
        canvas_obj.restoreState()
    
    # Page counter for callbacks
    page_counter = [0]
    
    def on_first_page(canvas_obj, doc_obj):
        page_counter[0] = 1
        draw_page_template(canvas_obj, doc_obj, 1)
    
    def on_later_pages(canvas_obj, doc_obj):
        page_counter[0] += 1
        draw_page_template(canvas_obj, doc_obj, page_counter[0])
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=content_right,
        leftMargin=content_left,
        topMargin=content_top,
        bottomMargin=content_bottom
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Service Order Info table
    info_data = [
        [
            Paragraph("<b>Serviços / Jobs:</b>", styles['Normal']),
            Paragraph("<b>OS / PO (TWAS):</b>", styles['Normal'])
        ],
        [
            Paragraph(ts.get("service", ""), styles['Normal']),
            Paragraph(ts.get("os_number", ""), styles['Normal'])
        ],
        [
            Paragraph("<b>Cliente / Client:</b>", styles['Normal']),
            Paragraph("<b>Local / Location:</b>", styles['Normal'])
        ],
        [
            Paragraph(
                f"{ts.get('client', '')}{(' / ' + ts.get('embarcacao', '')) if ts.get('embarcacao') else ''}",
                styles['Normal']
            ),
            Paragraph(ts.get("location", ""), styles['Normal'])
        ]
    ]
    
    half_width = content_width / 2
    info_table = Table(info_data, colWidths=[half_width, half_width])
    info_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0.2*cm),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0.2*cm),
        ('TOPPADDING', (0, 0), (-1, -1), 0.1*cm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0.2*cm),
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 0.2*cm))
    
    # Column widths for entries table
    col_widths_raw = [2.2, 2.2, 2.2, 2.0, 5.0, 2.2, 2.2]
    total_raw = sum(col_widths_raw)
    col_widths = [(w / total_raw) * content_width for w in col_widths_raw]
    
    for page_num in range(total_pages):
        if page_num > 0:
            elements.append(PageBreak())
            elements.append(info_table)
            elements.append(Spacer(1, 0.15*cm))
        
        # Table header
        table_data = [
            [
                Paragraph("<b>Data<br/>Date</b>", ParagraphStyle('centered', parent=styles['Normal'], alignment=TA_CENTER, fontSize=8)),
                Paragraph("<b>Em Serviço<br/>In Service<br/>Início<br/>Start</b>", ParagraphStyle('centered2', parent=styles['Normal'], alignment=TA_CENTER, fontSize=7)),
                Paragraph("<b>Em Serviço<br/>In Service<br/>Final<br/>Final</b>", ParagraphStyle('centered3', parent=styles['Normal'], alignment=TA_CENTER, fontSize=7)),
                Paragraph("<b>Função<br/>Function</b>", ParagraphStyle('centered4', parent=styles['Normal'], alignment=TA_CENTER, fontSize=8)),
                Paragraph("<b>Nome<br/>Name</b>", ParagraphStyle('centered5', parent=styles['Normal'], alignment=TA_CENTER, fontSize=8)),
                Paragraph("<b>Em Viagem<br/>In Travel<br/>Início<br/>Start</b>", ParagraphStyle('centered6', parent=styles['Normal'], alignment=TA_CENTER, fontSize=7)),
                Paragraph("<b>Em Viagem<br/>In Travel<br/>Final<br/>Final</b>", ParagraphStyle('centered7', parent=styles['Normal'], alignment=TA_CENTER, fontSize=7)),
            ]
        ]
        
        start_idx = page_num * entries_per_page
        end_idx = min(start_idx + entries_per_page, total_entries)
        
        for i in range(start_idx, end_idx):
            entry = ts["entries"][i]
            svc_start = entry.get("service_start") or "-"
            svc_end = entry.get("service_end") or "-"
            travel_start = entry.get("travel_start") or "-"
            travel_end = entry.get("travel_end") or "-"
            table_data.append([
                entry["date"],
                svc_start,
                svc_end,
                entry["employee_function"],
                entry["employee_name"],
                travel_start,
                travel_end,
            ])
        
        current_rows = len(table_data) - 1
        while current_rows < entries_per_page:
            table_data.append(["", "", "", "", "", "", ""])
            current_rows += 1
        
        entries_table = Table(table_data, colWidths=col_widths)
        entries_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 0.15*cm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0.15*cm),
        ]))
        
        elements.append(entries_table)
        elements.append(Spacer(1, 0.1*cm))
        
        # Legend
        legend_title = Paragraph("<b>Legenda / Caption</b>", ParagraphStyle(f'legend_title_{page_num}', parent=styles['Normal'], fontSize=8))
        elements.append(legend_title)
        elements.append(Spacer(1, 0.05*cm))
        
        legend_cell_style = ParagraphStyle(f'legend_cell_{page_num}', parent=styles['Normal'], fontSize=6, alignment=TA_CENTER, leading=8)
        legend_col_w = content_width / 6
        legend_data = [[
            Paragraph("Engenheiro (E)<br/>Engineer (E)", legend_cell_style),
            Paragraph("Encarregado (EN)<br/>Foreman (EN)", legend_cell_style),
            Paragraph("Supervisor (Sup)<br/>Supervisor (Sup)", legend_cell_style),
            Paragraph("Técnico (T)<br/>Technician (T)", legend_cell_style),
            Paragraph("Mecânico (M)<br/>Mechanic (M)", legend_cell_style),
            Paragraph("Téc. Seg. (TS)<br/>Safety Tech (ST)", legend_cell_style),
        ]]
        
        legend_table = Table(legend_data, colWidths=[legend_col_w]*6, rowHeights=[0.7*cm])
        legend_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0.1*cm),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0.1*cm),
            ('TOPPADDING', (0, 0), (-1, -1), 0.05*cm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0.05*cm),
        ]))
        
        elements.append(legend_table)
        elements.append(Spacer(1, 0.1*cm))
        
        # Client Approval
        approval_title = Paragraph("<b>Aprovação do Cliente / Client Approval</b>", ParagraphStyle(f'approval_title_{page_num}', parent=styles['Normal'], fontSize=9))
        elements.append(approval_title)
        elements.append(Spacer(1, 0.1*cm))
        
        third_width = content_width / 3
        approval_data = [
            [
                Paragraph("<b>Nome / Name</b>", ParagraphStyle(f'appr_h_{page_num}', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER)),
                Paragraph("<b>Função / Function</b>", ParagraphStyle(f'appr_h2_{page_num}', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER)),
                Paragraph("<b>Carimbo / Stamp</b>", ParagraphStyle(f'appr_h3_{page_num}', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER))
            ],
            ["", "", ""]
        ]
        
        approval_table = Table(approval_data, colWidths=[third_width]*3, rowHeights=[0.5*cm, 0.9*cm])
        approval_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0.2*cm),
            ('TOPPADDING', (0, 0), (-1, -1), 0.15*cm),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ]))
        
        elements.append(approval_table)
        elements.append(Spacer(1, 0.1*cm))
        
        # Observations
        obs_title = Paragraph("<b>Observações / Remarks:</b>", ParagraphStyle(f'obs_title_{page_num}', parent=styles['Normal'], fontSize=9))
        elements.append(obs_title)
        elements.append(Spacer(1, 0.05*cm))
        
        obs_content = (ts.get("observations", "") or "") if page_num == 0 else ""
        obs_content = obs_content.replace('\n', '<br/>')
        obs_data = [[Paragraph(obs_content, ParagraphStyle(f'obs_{page_num}', parent=styles['Normal'], fontSize=9, leading=12))]]
        
        obs_table = Table(obs_data, colWidths=[content_width], rowHeights=[4.0*cm])
        obs_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0.3*cm),
            ('TOPPADDING', (0, 0), (-1, -1), 0.15*cm),
        ]))
        
        elements.append(obs_table)
        elements.append(Spacer(1, 0.1*cm))
        
        # TWAS Approval with signature
        sig_name_style = ParagraphStyle(f'sig_nm_{page_num}', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER)
        twas_data = [
            [
                Paragraph("<b>Data / Date</b>", ParagraphStyle(f'twas_h_{page_num}', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER)),
                Paragraph("<b>Nome / Name</b>", ParagraphStyle(f'twas_h2_{page_num}', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER)),
                Paragraph("<b>Função / Function</b>", ParagraphStyle(f'twas_h3_{page_num}', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER))
            ],
            [
                Paragraph(current_date, ParagraphStyle(f'twas_c_{page_num}', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER)),
                Paragraph(f"<br/>______________________<br/><font size=8>{ts['supervisor_name']}</font>", sig_name_style),
                Paragraph(ts.get("supervisor_function", "Supervisor"), ParagraphStyle(f'twas_c3_{page_num}', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER))
            ]
        ]
        
        twas_table = Table(twas_data, colWidths=[third_width]*3, rowHeights=[0.5*cm, 1.2*cm])
        twas_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            ('VALIGN', (0, 1), (0, 1), 'MIDDLE'),
            ('VALIGN', (1, 1), (1, 1), 'BOTTOM'),
            ('VALIGN', (2, 1), (2, 1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0.2*cm),
            ('TOPPADDING', (0, 0), (-1, -1), 0.1*cm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0.1*cm),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ]))
        
        elements.append(twas_table)
    
    # Build PDF with page template callbacks
    doc.build(elements, onFirstPage=on_first_page, onLaterPages=on_later_pages)
    buffer.seek(0)

    import re
    def _safe(s: str) -> str:
        return re.sub(r'[<>:"/\\|?*]', '', str(s or '')).strip()
    filename = f"{_safe(ts.get('os_number', ''))} - {_safe(ts.get('client', ''))} - TM - {_safe(ts.get('service', ''))}.pdf".strip(" -")

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    )


