from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import Response
from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from PIL import Image as PILImage
from pathlib import Path
import io
import logging
import jwt

from database import db
from config import SECRET_KEY, ALGORITHM, get_object
from dependencies import get_current_user, get_admin_user
from models import ServiceOrder, ServiceOrderCreate

router = APIRouter()
ROOT_DIR = Path(__file__).parent.parent

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



# ==================== OS PDF GENERATION ====================

@router.get("/service-orders/{so_id}/pdf")
async def generate_os_pdf(so_id: str, token: Optional[str] = Query(None), credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))):
    """Generate PDF for a Service Order with the same visual style as service reports."""
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

    so = await db.service_orders.find_one({"_id": ObjectId(so_id)})
    if not so:
        raise HTTPException(status_code=404, detail="Ordem de Serviço não encontrada")

    # Fetch proposal data if linked
    proposal = None
    if so.get("proposal_id"):
        try:
            proposal = await db.propostas.find_one({"_id": ObjectId(so["proposal_id"])})
        except Exception:
            pass

    buffer = io.BytesIO()
    page_width, page_height = A4
    border_margin = 1.0 * cm
    content_left = 2.03 * cm
    content_right = 2.03 * cm
    content_width = page_width - content_left - content_right

    # Load logo
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

    os_number = so.get("os_number", "")
    client = so.get("client", "")
    embarcacao = so.get("embarcacao", "")
    location = so.get("location", "")
    service = so.get("service", "")
    po_number = so.get("po_number", "")
    contato = proposal.get("contato", "") if proposal else ""
    email = proposal.get("email", "") if proposal else ""
    current_date = datetime.utcnow().strftime("%d/%m/%Y")

    def draw_os_page(canvas_obj, doc_obj):
        canvas_obj.saveState()

        # === PAGE BORDER ===
        canvas_obj.setStrokeColor(colors.HexColor('#777777'))
        canvas_obj.setLineWidth(0.5)
        canvas_obj.rect(border_margin, border_margin, page_width - 2 * border_margin, page_height - 2 * border_margin)

        # === WATERMARK ===
        if logo_image:
            logo_image.seek(0)
            from reportlab.lib.utils import ImageReader
            img_reader = ImageReader(logo_image)
            canvas_obj.saveState()
            canvas_obj.setFillAlpha(0.06)
            wm_w = content_width * 1.15
            wm_h = wm_w * 0.35
            wm_x = content_left + (content_width - wm_w) / 2
            wm_y = (page_height - wm_h) / 2
            canvas_obj.drawImage(img_reader, wm_x, wm_y, width=wm_w, height=wm_h, preserveAspectRatio=True, mask='auto')
            canvas_obj.restoreState()

        # === HEADER BOX ===
        header_top = page_height - border_margin - 0.4 * cm
        header_height = 2.1 * cm
        header_bottom = header_top - header_height
        canvas_obj.setStrokeColor(colors.HexColor('#777777'))
        canvas_obj.setLineWidth(0.5)
        canvas_obj.rect(content_left, header_bottom, content_width, header_height)

        # Logo
        if logo_image:
            logo_image.seek(0)
            from reportlab.lib.utils import ImageReader
            img_reader = ImageReader(logo_image)
            logo_h = 1.7 * cm
            logo_y = header_top - 0.25 * cm - logo_h
            canvas_obj.drawImage(img_reader, content_left + 0.1 * cm, logo_y, width=3.5 * cm, height=logo_h, preserveAspectRatio=True)

        # Center title
        canvas_obj.setFont("Helvetica-Bold", 13)
        canvas_obj.drawCentredString(page_width / 2, header_bottom + 1.6 * cm, "ORDEM DE SERVI\u00c7O")
        canvas_obj.setFont("Helvetica", 7)
        canvas_obj.drawCentredString(page_width / 2, header_bottom + 1.15 * cm, "10-FR-01-06 (1)")

        # Right side
        right_x = content_left + content_width - 0.15 * cm
        detail_y = header_top - 0.3 * cm
        line_h = 0.35 * cm

        def _draw_right_label(label, value, y_pos):
            canvas_obj.setFont("Helvetica", 8)
            val_w = canvas_obj.stringWidth(value, "Helvetica", 8)
            canvas_obj.drawRightString(right_x, y_pos, value)
            canvas_obj.setFont("Helvetica-Bold", 8)
            canvas_obj.drawRightString(right_x - val_w - 3, y_pos, label)

        _draw_right_label("Cliente:", client, detail_y)
        detail_y -= line_h
        _draw_right_label("Rig/Vessel:", embarcacao or location, detail_y)
        detail_y -= line_h
        _draw_right_label("Servi\u00e7o:", service, detail_y)
        detail_y -= line_h
        _draw_right_label("OS:", os_number, detail_y)
        detail_y -= line_h
        _draw_right_label("Rev:", "0", detail_y)

        # === FOOTER BOX ===
        footer_bottom = border_margin + 0.5 * cm
        footer_height = 1.4 * cm
        footer_top = footer_bottom + footer_height
        canvas_obj.setStrokeColor(colors.HexColor('#777777'))
        canvas_obj.setLineWidth(0.5)
        canvas_obj.rect(content_left, footer_bottom, content_width, footer_height)

        center_x = page_width / 2
        y = footer_top - 0.45 * cm
        canvas_obj.setFont("Helvetica-Bold", 8)
        canvas_obj.drawCentredString(center_x, y, "TWAS REPAIR SERVI\u00c7OS NAVAIS E INDUSTRIAIS LTDA")
        y -= 0.3 * cm
        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.drawCentredString(center_x, y, "Travessa Frederico Marques, N\u00b0 84, Boa Vista, S\u00e3o Gon\u00e7alo, Rio de Janeiro - CEP.: 24.466-180.")
        y -= 0.28 * cm
        canvas_obj.drawCentredString(center_x, y, "twas@twasrepair.com - www.twasrepair.com")

        canvas_obj.restoreState()

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=border_margin + 3.1 * cm,
        bottomMargin=border_margin + 2.1 * cm,
        leftMargin=content_left,
        rightMargin=content_right,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('OsTitle', parent=styles['Heading1'], fontSize=14, textColor=colors.black, alignment=TA_CENTER, spaceAfter=20, fontName='Helvetica-Bold')
    label_style = ParagraphStyle('OsLabel', parent=styles['Normal'], fontSize=10, fontName='Helvetica-Bold', textColor=colors.black, spaceAfter=2)
    value_style = ParagraphStyle('OsValue', parent=styles['Normal'], fontSize=10, fontName='Helvetica', textColor=colors.black, spaceAfter=10)

    elements = []
    elements.append(Spacer(1, 0.5 * cm))

    # Info table
    info_data = [
        ["Ordem de Servi\u00e7o:", os_number],
        ["P.O. N\u00famero:", po_number],
        ["Cliente:", client],
        ["Embarca\u00e7\u00e3o / Plataforma:", embarcacao],
        ["Local:", location],
        ["Servi\u00e7o:", service],
        ["Contato:", contato],
        ["Email:", email],
        ["Data:", current_date],
    ]

    table = Table(info_data, colWidths=[content_width * 0.35, content_width * 0.65])
    table.setStyle(TableStyle([
        ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 10),
        ('FONT', (1, 0), (1, -1), 'Helvetica', 10),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#dddddd')),
        ('LINEBELOW', (0, -1), (-1, -1), 1, colors.HexColor('#000000')),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f5f5f5')),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(table)

    doc.build(elements, onFirstPage=draw_os_page, onLaterPages=draw_os_page)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=OS_{os_number}.pdf"}
    )


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
