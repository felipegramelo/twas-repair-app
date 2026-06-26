import logging
from fastapi import APIRouter, HTTPException, Depends, Query, Header, UploadFile, File, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import Response, StreamingResponse
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
from PIL import Image as PILImage
import io
import uuid
import jwt
from pathlib import Path

from database import db
from config import SECRET_KEY, ALGORITHM, put_object, get_object, APP_NAME
from dependencies import get_current_user, get_admin_user
from models import ReportCreate, ReportUpdate, UserRole
from utils import parse_date_sortable

router = APIRouter()

ROOT_DIR = Path(__file__).parent.parent

def get_default_service_sections(client="", service="", location=""):
    intro_text = (
        f"A TWAS Repair foi contratada pela(o) {client} para realizar o (a) {service} "
        f"da embarcação {location}.\n"
        f"A TWAS Repair performou as atividades descritas no relatório abaixo, utilizando-se de mão de obra "
        f"especializada, atendendo os requerimentos da(o) {client}, através do representante/especialista "
        f"do sistema treinado pelo fabricante."
    )
    equip_text = "Azimuth Thruster:\nSerial:\nData:"
    obj_text = f"O serviço teve por objetivo o(a) {service}."
    return [
        {"key": "introduction", "number": "1", "title": "INTRODUÇÃO", "content": intro_text, "enabled": True, "subsections": []},
        {"key": "equipment", "number": "2", "title": "EQUIPAMENTOS", "content": equip_text, "enabled": True, "subsections": []},
        {"key": "objective", "number": "3", "title": "OBJETIVO", "content": obj_text, "enabled": True, "subsections": []},
        {"key": "service_description", "number": "4", "title": "DESCRIÇÃO DOS SERVIÇOS", "content": "", "enabled": True, "subsections": [
            {"key": "disassembly", "number": "4.1", "title": "DESMONTAGEM", "content": "", "enabled": True, "subsections": [
                {"key": "disassembly_photos", "number": "4.1.1", "title": "FOTOS", "content": "", "enabled": True}
            ]},
            {"key": "assembly", "number": "4.2", "title": "MONTAGEM", "content": "", "enabled": True, "subsections": [
                {"key": "assembly_photos", "number": "4.2.1", "title": "FOTOS", "content": "", "enabled": True}
            ]},
        ]},
        {"key": "ndt", "number": "5", "title": "RELATÓRIO DE ENSAIO NÃO DESTRUTIVO", "content": "", "enabled": False, "subsections": [
            {"key": "propeller_shaft", "number": "5.1", "title": "PROPELLER SHAFT", "content": "", "enabled": True},
            {"key": "pinion_shaft", "number": "5.2", "title": "PINION SHAFT", "content": "", "enabled": True},
            {"key": "input_shaft", "number": "5.3", "title": "INPUT SHAFT", "content": "", "enabled": True},
            {"key": "coupling", "number": "5.4", "title": "COUPLING", "content": "", "enabled": True},
            {"key": "swivel_pinion", "number": "5.5", "title": "SWIVEL PINION SHAFT", "content": "", "enabled": True},
            {"key": "propeller", "number": "5.6", "title": "PROPELLER", "content": "", "enabled": True},
            {"key": "reduction_gear", "number": "5.7", "title": "REDUCTION GEAR", "content": "", "enabled": True},
        ]},
        {"key": "pressure_test", "number": "6", "title": "TESTE DE PRESSÃO", "content": "", "enabled": False, "subsections": []},
        {"key": "certificates", "number": "7", "title": "CERTIFICADOS", "content": "", "enabled": False, "subsections": []},
        {"key": "client_eval", "number": "8", "title": "AVALIAÇÃO DO CLIENTE", "content": "", "enabled": False, "subsections": []},
    ]

def get_default_daily_sections(client="", service="", location=""):
    intro_text = (
        f"A TWAS Repair foi contratada pela(o) {client} para realizar o (a) {service} "
        f"da embarcação {location}.\n"
        f"A TWAS Repair performou as atividades descritas no relatório abaixo, utilizando-se de mão de obra "
        f"especializada, atendendo os requerimentos da(o) {client}, através do representante/especialista "
        f"do sistema treinado pelo fabricante."
    )
    equip_text = "Azimuth Thruster:\nSerial:\nData:"
    obj_text = f"O serviço teve por objetivo o(a) {service}."
    return [
        {"key": "introduction", "number": "1", "title": "INTRODUÇÃO", "content": intro_text, "enabled": True, "subsections": []},
        {"key": "equipment", "number": "2", "title": "EQUIPAMENTOS", "content": equip_text, "enabled": True, "subsections": []},
        {"key": "objective", "number": "3", "title": "OBJETIVO", "content": obj_text, "enabled": True, "subsections": []},
        {"key": "service_description", "number": "4", "title": "DESCRIÇÃO DOS SERVIÇOS", "content": "", "enabled": True, "subsections": []},
    ]


@router.post("/reports")
async def create_report(report: ReportCreate, user: dict = Depends(get_current_user)):
    os_data = await db.service_orders.find_one({"_id": ObjectId(report.os_id)})
    if not os_data:
        raise HTTPException(status_code=404, detail="Ordem de Serviço não encontrada")
    
    now = datetime.utcnow()
    default_sections = get_default_service_sections(
        client=os_data["client"], service=os_data["service"], location=os_data["location"]
    ) if report.report_type == "service" else get_default_daily_sections(
        client=os_data["client"], service=os_data["service"], location=os_data["location"]
    )
    report_doc = {
        "report_type": report.report_type,
        "os_id": report.os_id,
        "os_number": os_data["os_number"],
        "client": os_data["client"],
        "location": os_data["location"],
        "embarcacao": os_data.get("embarcacao", ""),
        "service": os_data["service"],
        "supervisor_id": str(user["_id"]),
        "supervisor_name": user["name"],
        "periodo_inicio": report.periodo_inicio or "",
        "periodo_fim": report.periodo_fim or "",
        "executado_por": report.executado_por or user["name"],
        "sections": default_sections,
        "status": "draft",
        "created_at": now,
        "updated_at": now,
    }
    result = await db.reports.insert_one(report_doc)
    return {
        "id": str(result.inserted_id),
        "report_type": report_doc["report_type"],
        "os_number": report_doc["os_number"],
        "client": report_doc["client"],
        "status": "draft",
    }

@router.get("/reports")
async def get_reports(user: dict = Depends(get_current_user)):
    query = {}
    if user.get("role") != UserRole.ADMIN:
        # Supervisor sees own reports + reports shared with them
        user_id = user["_id"]
        query = {"$or": [
            {"supervisor_id": user_id},
            {"shared_with": user_id}
        ]}
    reports = []
    cursor = db.reports.find(query).sort("created_at", -1)
    async for doc in cursor:
        reports.append({
            "id": str(doc["_id"]),
            "report_type": doc.get("report_type", "service"),
            "os_id": doc.get("os_id", ""),
            "os_number": doc.get("os_number", ""),
            "client": doc.get("client", ""),
            "location": doc.get("location", ""),
            "service": doc.get("service", ""),
            "supervisor_id": doc.get("supervisor_id", ""),
            "supervisor_name": doc.get("supervisor_name", ""),
            "periodo_inicio": doc.get("periodo_inicio", doc.get("periodo", "")),
            "periodo_fim": doc.get("periodo_fim", ""),
            "executado_por": doc.get("executado_por", ""),
            "oc_wo": doc.get("oc_wo", ""),
            "sections": doc.get("sections", []),
            "daily_entries": doc.get("daily_entries", []),
            "cover_photo": doc.get("cover_photo", ""),
            "status": doc.get("status", "draft"),
            "shared_with": doc.get("shared_with", []),
            "created_at": doc.get("created_at", "").isoformat() if doc.get("created_at") else "",
            "updated_at": doc.get("updated_at", "").isoformat() if doc.get("updated_at") else "",
        })
    return {"reports": reports}

@router.get("/reports/{report_id}")
async def get_report_by_id(report_id: str, user: dict = Depends(get_current_user)):
    doc = await db.reports.find_one({"_id": ObjectId(report_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")
    # Permission check: admin or owner or shared
    if user.get("role") != UserRole.ADMIN:
        if doc.get("supervisor_id") != user["_id"] and user["_id"] not in doc.get("shared_with", []):
            raise HTTPException(status_code=403, detail="Acesso negado a este relatório")
    return {
        "id": str(doc["_id"]),
        "report_type": doc.get("report_type", "service"),
        "os_id": doc.get("os_id", ""),
        "os_number": doc.get("os_number", ""),
        "client": doc.get("client", ""),
        "location": doc.get("location", ""),
        "service": doc.get("service", ""),
        "supervisor_id": doc.get("supervisor_id", ""),
        "supervisor_name": doc.get("supervisor_name", ""),
        "periodo_inicio": doc.get("periodo_inicio", doc.get("periodo", "")),
        "periodo_fim": doc.get("periodo_fim", ""),
        "executado_por": doc.get("executado_por", ""),
        "sections": doc.get("sections", []),
        "daily_entries": doc.get("daily_entries", []),
        "cover_photo": doc.get("cover_photo", ""),
        "status": doc.get("status", "draft"),
        "shared_with": doc.get("shared_with", []),
        "created_at": doc.get("created_at", "").isoformat() if doc.get("created_at") else "",
        "updated_at": doc.get("updated_at", "").isoformat() if doc.get("updated_at") else "",
    }

@router.put("/reports/{report_id}")
async def update_report(report_id: str, update: ReportUpdate, user: dict = Depends(get_current_user)):
    doc = await db.reports.find_one({"_id": ObjectId(report_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")
    if doc.get("status") == "finalized" and user.get("role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Relatório finalizado. Não é possível editar.")
    # Only owner or admin can edit
    if user.get("role") != UserRole.ADMIN and doc.get("supervisor_id") != user["_id"]:
        raise HTTPException(status_code=403, detail="Apenas o autor pode editar este relatório")
    
    update_data = {}
    for field in ["periodo_inicio", "periodo_fim", "executado_por", "oc_wo", "representante_twas", "representante_cliente", "sections", "status", "daily_entries"]:
        value = getattr(update, field, None)
        if value is not None:
            update_data[field] = value
    
    update_data["updated_at"] = datetime.utcnow()
    await db.reports.update_one({"_id": ObjectId(report_id)}, {"$set": update_data})
    return {"success": True}

@router.delete("/reports/{report_id}")
async def delete_report(report_id: str, user: dict = Depends(get_current_user)):
    doc = await db.reports.find_one({"_id": ObjectId(report_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")
    # Only owner or admin can delete
    if user.get("role") != UserRole.ADMIN and doc.get("supervisor_id") != user["_id"]:
        raise HTTPException(status_code=403, detail="Apenas o autor pode excluir este relatório")
    await db.reports.delete_one({"_id": ObjectId(report_id)})
    return {"success": True}


# ==================== DUPLICATE REPORT ====================

class DuplicateReportRequest(BaseModel):
    os_id: Optional[str] = None
    periodo_inicio: Optional[str] = None
    periodo_fim: Optional[str] = None
    executado_por: Optional[str] = None

@router.post("/reports/{report_id}/duplicate")
async def duplicate_report(report_id: str, dup: DuplicateReportRequest, user: dict = Depends(get_current_user)):
    original = await db.reports.find_one({"_id": ObjectId(report_id)})
    if not original:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")
    # Permission check: owner, admin, or shared
    if user.get("role") != UserRole.ADMIN:
        if original.get("supervisor_id") != user["_id"] and user["_id"] not in original.get("shared_with", []):
            raise HTTPException(status_code=403, detail="Acesso negado")

    # If a new OS is provided, fetch its data
    if dup.os_id and dup.os_id != original.get("os_id"):
        os_data = await db.service_orders.find_one({"_id": ObjectId(dup.os_id)})
        if not os_data:
            raise HTTPException(status_code=404, detail="Ordem de Serviço não encontrada")
        os_number = os_data["os_number"]
        client = os_data["client"]
        location = os_data["location"]
        service = os_data["service"]
        os_id = dup.os_id
    else:
        os_id = original["os_id"]
        os_number = original["os_number"]
        client = original["client"]
        location = original["location"]
        service = original["service"]

    # Deep copy sections, clearing photos
    import copy
    sections = copy.deepcopy(original.get("sections", []))

    now = datetime.utcnow()
    new_report = {
        "report_type": original["report_type"],
        "os_id": os_id,
        "os_number": os_number,
        "client": client,
        "location": location,
        "service": service,
        "supervisor_id": str(user["_id"]),
        "supervisor_name": user["name"],
        "periodo_inicio": dup.periodo_inicio or original.get("periodo_inicio", ""),
        "periodo_fim": dup.periodo_fim or original.get("periodo_fim", ""),
        "executado_por": dup.executado_por or original.get("executado_por", ""),
        "cover_photo": "",
        "sections": sections,
        "shared_with": [],
        "status": "draft",
        "created_at": now,
        "updated_at": now,
    }
    result = await db.reports.insert_one(new_report)
    return {
        "id": str(result.inserted_id),
        "report_type": new_report["report_type"],
        "os_number": new_report["os_number"],
        "client": new_report["client"],
        "status": "draft",
    }


# ==================== PHOTO UPLOAD ====================

MIME_TYPES = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "gif": "image/gif", "webp": "image/webp", "pdf": "application/pdf",
}

def convert_pdf_to_images(pdf_data: bytes) -> list:
    """Convert PDF pages to JPEG images, returns list of (bytes, filename)."""
    import fitz
    images = []
    doc = fitz.open(stream=pdf_data, filetype="pdf")
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=150)
        img_data = pix.tobytes("jpeg")
        images.append((img_data, f"page_{i+1}.jpeg"))
    doc.close()
    return images

@router.post("/reports/{report_id}/upload-photo")
async def upload_report_photo(
    report_id: str,
    file: UploadFile = File(...),
    section_key: str = Query(default="cover"),
    user: dict = Depends(get_current_user)
):
    report = await db.reports.find_one({"_id": ObjectId(report_id)})
    if not report:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")

    ext = file.filename.split(".")[-1].lower() if "." in file.filename else "jpg"
    if ext not in MIME_TYPES:
        raise HTTPException(status_code=400, detail="Formato não suportado. Use jpg, png, gif, webp ou pdf.")

    data = await file.read()

    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Arquivo muito grande. Máximo 20MB.")

    uploaded_paths = []

    if ext == "pdf":
        # Convert PDF pages to images
        try:
            pages = convert_pdf_to_images(data)
        except Exception as e:
            logging.error(f"PDF conversion error: {e}")
            raise HTTPException(status_code=400, detail="Erro ao converter PDF para imagens")
        
        for img_data, img_name in pages:
            # Compress the image
            pil_img = PILImage.open(io.BytesIO(img_data))
            if pil_img.mode != 'RGB':
                pil_img = pil_img.convert('RGB')
            out_buf = io.BytesIO()
            pil_img.save(out_buf, format='JPEG', quality=60)
            compressed = out_buf.getvalue()
            
            file_id = str(uuid.uuid4())
            storage_path = f"{APP_NAME}/reports/{report_id}/{section_key}/{file_id}.jpeg"
            try:
                result = put_object(storage_path, compressed, "image/jpeg")
            except Exception as e:
                logging.error(f"Upload error: {e}")
                continue
            
            await db.report_photos.insert_one({
                "report_id": report_id,
                "section_key": section_key,
                "storage_path": result["path"],
                "original_filename": f"{file.filename} - {img_name}",
                "content_type": "image/jpeg",
                "size": result.get("size", len(compressed)),
                "is_deleted": False,
                "created_at": datetime.utcnow(),
            })
            uploaded_paths.append(result["path"])
        
        return {
            "storage_paths": uploaded_paths,
            "section_key": section_key,
            "filename": file.filename,
            "pages_converted": len(uploaded_paths),
        }
    else:
        # Regular image upload - compress it
        content_type = MIME_TYPES.get(ext, "image/jpeg")
        try:
            pil_img = PILImage.open(io.BytesIO(data))
            if pil_img.mode != 'RGB':
                pil_img = pil_img.convert('RGB')
            # Resize if very large
            max_dim = 2000
            if max(pil_img.size) > max_dim:
                pil_img.thumbnail((max_dim, max_dim), PILImage.LANCZOS)
            out_buf = io.BytesIO()
            pil_img.save(out_buf, format='JPEG', quality=60)
            data = out_buf.getvalue()
            ext = "jpeg"
            content_type = "image/jpeg"
        except Exception:
            pass  # If compression fails, use original data

        file_id = str(uuid.uuid4())
        storage_path = f"{APP_NAME}/reports/{report_id}/{section_key}/{file_id}.{ext}"

        try:
            result = put_object(storage_path, data, content_type)
        except Exception as e:
            logging.error(f"Upload error: {e}")
            raise HTTPException(status_code=500, detail="Erro ao fazer upload da imagem")

        await db.report_photos.insert_one({
            "report_id": report_id,
            "section_key": section_key,
            "storage_path": result["path"],
            "original_filename": file.filename,
            "content_type": content_type,
            "size": result.get("size", len(data)),
            "is_deleted": False,
            "created_at": datetime.utcnow(),
        })

        if section_key == "cover":
            await db.reports.update_one(
                {"_id": ObjectId(report_id)},
                {"$set": {"cover_photo": result["path"]}}
            )

        return {
            "storage_path": result["path"],
            "section_key": section_key,
            "filename": file.filename,
        }


@router.get("/photos/{path:path}")
async def get_photo(path: str, auth: str = Query(None), authorization: str = Header(None)):
    # Auth via query param or header
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
    elif auth:
        token = auth
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        data, content_type = get_object(path)
        return Response(content=data, media_type=content_type)
    except Exception as e:
        logging.error(f"Photo download error: {e}")
        raise HTTPException(status_code=404, detail="Foto não encontrada")


@router.get("/reports/{report_id}/photos")
async def get_report_photos(report_id: str, user: dict = Depends(get_current_user)):
    photos = []
    cursor = db.report_photos.find({"report_id": report_id, "is_deleted": False})
    async for doc in cursor:
        photos.append({
            "id": str(doc["_id"]),
            "section_key": doc["section_key"],
            "storage_path": doc["storage_path"],
            "original_filename": doc["original_filename"],
            "content_type": doc.get("content_type", "image/jpeg"),
            "caption": doc.get("caption", ""),
        })
    return {"photos": photos}


@router.put("/reports/{report_id}/photos/{photo_id}/caption")
async def update_photo_caption(report_id: str, photo_id: str, request: Request, user: dict = Depends(get_current_user)):
    body = await request.json()
    caption = body.get("caption", "")
    result = await db.report_photos.update_one(
        {"_id": ObjectId(photo_id), "report_id": report_id, "is_deleted": False},
        {"$set": {"caption": caption}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Foto não encontrada")
    return {"success": True, "caption": caption}


@router.delete("/reports/{report_id}/photos/{photo_id}")
async def delete_report_photo(report_id: str, photo_id: str, user: dict = Depends(get_current_user)):
    result = await db.report_photos.update_one(
        {"_id": ObjectId(photo_id), "report_id": report_id},
        {"$set": {"is_deleted": True}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Foto não encontrada")
    # If it was a cover photo, clear it
    photo = await db.report_photos.find_one({"_id": ObjectId(photo_id)})
    if photo and photo.get("section_key") == "cover":
        await db.reports.update_one(
            {"_id": ObjectId(report_id)},
            {"$set": {"cover_photo": ""}}
        )
    return {"success": True}

@router.get("/reports/{report_id}/pdf")
async def generate_report_pdf(report_id: str, request: Request, token: str = Query(default=None), day_ids: str = Query(default=None), download: str = Query(default=None)):
    # Accept auth from query param OR Authorization header (for mobile browser direct URL access)
    auth_token = token
    if not auth_token:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            auth_token = auth_header[7:]
    if not auth_token:
        raise HTTPException(status_code=401, detail="Token não fornecido")
    try:
        payload = jwt.decode(auth_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token inválido")
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=401, detail="Usuário não encontrado")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

    report = await db.reports.find_one({"_id": ObjectId(report_id)})
    if not report:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")
    
    buffer = io.BytesIO()
    page_width, page_height = A4
    border_margin = 1.0*cm  # Page border at 1cm from edge
    # Header/footer/content boxes ~1cm inside the page border = ~2cm from page edge
    content_left = 2.03*cm
    content_right = 2.03*cm
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
    
    is_service = report.get("report_type") == "service"
    report_lang = report.get("language", "pt")
    if report_lang == "en":
        report_title = "TECHNICAL REPORT" if is_service else "DAILY REPORT"
    elif report_lang == "es":
        report_title = "INFORME T\u00c9CNICO" if is_service else "INFORME DIARIO"
    else:
        report_title = "RELAT\u00d3RIO T\u00c9CNICO" if is_service else "RELAT\u00d3RIO DI\u00c1RIO"
    periodo_inicio = report.get("periodo_inicio", "")
    periodo_fim = report.get("periodo_fim", "")
    periodo_str = f"{periodo_inicio} a {periodo_fim}" if periodo_inicio and periodo_fim else periodo_inicio or periodo_fim or ""
    
    from datetime import datetime as dt
    current_date = dt.now().strftime("%d/%m/%Y")
    
    page_counter = [0]
    total_pages = [0]
    
    def draw_report_page(canvas_obj, doc_obj, page_num):
        canvas_obj.saveState()
        
        # === PAGE BORDER ===
        canvas_obj.setStrokeColor(colors.HexColor('#777777'))
        canvas_obj.setLineWidth(0.5)
        canvas_obj.rect(border_margin, border_margin, page_width - 2*border_margin, page_height - 2*border_margin)
        
        # === WATERMARK LOGO (all pages except cover) ===
        if page_num > 1 and logo_image:
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
        
        # === HEADER BOX (mais perto da borda: 0.4cm) ===
        header_top = page_height - border_margin - 0.4*cm
        header_height = 2.1*cm
        header_bottom = header_top - header_height
        canvas_obj.setStrokeColor(colors.HexColor('#777777'))
        canvas_obj.setLineWidth(0.5)
        canvas_obj.rect(content_left, header_bottom, content_width, header_height)
        
        # Logo (alinhada à esquerda, não ultrapassa linha Rev:0)
        if logo_image:
            logo_image.seek(0)
            from reportlab.lib.utils import ImageReader
            img_reader = ImageReader(logo_image)
            # Logo top aligns with first text line, bottom at Rev line
            logo_h = 1.7*cm
            logo_y = header_top - 0.25*cm - logo_h
            canvas_obj.drawImage(img_reader, content_left + 0.1*cm, logo_y, width=3.5*cm, height=logo_h, preserveAspectRatio=True)
        
        # Center title
        canvas_obj.setFont("Helvetica-Bold", 13)
        canvas_obj.drawCentredString(page_width/2, header_bottom + 1.6*cm, report_title)
        canvas_obj.setFont("Helvetica", 7)
        canvas_obj.drawCentredString(page_width/2, header_bottom + 1.15*cm, "20-FR-01-03 (1)")
        
        # Right side: labels and values right-aligned
        right_x = content_left + content_width - 0.15*cm
        detail_y = header_top - 0.3*cm
        line_h = 0.35*cm
        
        def _draw_right_label(label, value, y_pos):
            canvas_obj.setFont("Helvetica", 8)
            val_w = canvas_obj.stringWidth(value, "Helvetica", 8)
            canvas_obj.drawRightString(right_x, y_pos, value)
            canvas_obj.setFont("Helvetica-Bold", 8)
            canvas_obj.drawRightString(right_x - val_w - 3, y_pos, label)
        
        _draw_right_label("Cliente:", report.get('client', ''), detail_y)
        detail_y -= line_h
        _draw_right_label("Rig/Vessel:", report.get('embarcacao', '') or report.get('location', ''), detail_y)
        detail_y -= line_h
        _draw_right_label("OS:", report.get('os_number', ''), detail_y)
        detail_y -= line_h
        _draw_right_label("Rev:", "0", detail_y)
        
        # === FOOTER BOX (mais perto da borda: 0.5cm) ===
        footer_bottom = border_margin + 0.5*cm
        footer_height = 1.4*cm
        footer_top = footer_bottom + footer_height
        canvas_obj.setStrokeColor(colors.HexColor('#777777'))
        canvas_obj.setLineWidth(0.5)
        canvas_obj.rect(content_left, footer_bottom, content_width, footer_height)
        
        center_x = page_width / 2
        y = footer_top - 0.45*cm
        canvas_obj.setFont("Helvetica-Bold", 8)
        canvas_obj.drawCentredString(center_x, y, "TWAS REPAIR SERVIÇOS NAVAIS E INDUSTRIAIS LTDA")
        y -= 0.3*cm
        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.drawCentredString(center_x, y, "Travessa Frederico Marques, N\u00b0 84, Boa Vista, S\u00e3o Gon\u00e7alo, Rio de Janeiro - CEP.: 24.466-180.")
        y -= 0.28*cm
        canvas_obj.drawCentredString(center_x, y, "twas@twasrepair.com - www.twasrepair.com")
        
        canvas_obj.restoreState()
    
    def on_first_page(c, d):
        page_counter[0] = 1
        draw_report_page(c, d, 1)
    
    def on_later_pages(c, d):
        page_counter[0] += 1
        draw_report_page(c, d, page_counter[0])
    
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=border_margin + 3.1*cm,
        bottomMargin=border_margin + 2.1*cm,
        leftMargin=content_left,
        rightMargin=content_right,
    )
    
    # Calculate safe max image heights based on actual frame dimensions
    frame_available_height = page_height - (border_margin + 3.1*cm) - (border_margin + 2.1*cm) - 12  # 12pt frame padding
    max_full_photo_height = frame_available_height - 0.1*cm   # standalone images - fill page to bottom
    max_first_photo_height = frame_available_height - 1.5*cm    # images with title above (reduced gap)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('RTitle', parent=styles['Heading1'], fontSize=16, textColor=colors.black, alignment=TA_CENTER, spaceAfter=8, fontName='Helvetica-Bold')
    section_style = ParagraphStyle('RSec', parent=styles['Heading2'], fontSize=10, textColor=colors.black, spaceBefore=12, spaceAfter=5, fontName='Helvetica-Bold')
    subsec_style = ParagraphStyle('RSubSec', parent=styles['Heading3'], fontSize=9, textColor=colors.black, spaceBefore=8, spaceAfter=3, fontName='Helvetica-Bold')
    body_style = ParagraphStyle('RBody', parent=styles['Normal'], fontSize=9, leading=13, spaceAfter=3, alignment=TA_JUSTIFY, textColor=colors.black)
    
    def format_content(text):
        """Convert plain text with line breaks and bullet markers to HTML for reportlab."""
        if not text:
            return ""
        import html as html_mod
        text = html_mod.escape(text)
        text = text.replace('\n', '<br/>')
        return text
    label_style = ParagraphStyle('RLabel', parent=styles['Normal'], fontSize=9, textColor=colors.black, fontName='Helvetica-Bold')
    value_style = ParagraphStyle('RValue', parent=styles['Normal'], fontSize=10, fontName='Helvetica', textColor=colors.black)
    
    elements = []
    
    # ===== Fetch photos for this report =====
    report_photos = {}
    cursor = db.report_photos.find({"report_id": report_id, "is_deleted": False})
    async for photo_doc in cursor:
        sk = photo_doc.get("section_key", "")
        if sk not in report_photos:
            report_photos[sk] = []
        report_photos[sk].append(photo_doc)

    # Helper to load a photo from storage into a reportlab Image
    def load_photo_image(storage_path, max_width, max_height):
        try:
            data, ct = get_object(storage_path)
            img_buf = io.BytesIO(data)
            pil = PILImage.open(img_buf)
            if pil.mode != 'RGB':
                pil = pil.convert('RGB')
            # Resize large images to reduce PDF file size (max 1400px on longest side)
            w, h = pil.size
            max_px = 1100
            if max(w, h) > max_px:
                scale = max_px / max(w, h)
                pil = pil.resize((int(w * scale), int(h * scale)), PILImage.LANCZOS)
                w, h = pil.size
            # Calculate proportional size for ReportLab
            ratio = min(max_width / w, max_height / h)
            new_w = w * ratio
            new_h = h * ratio
            out = io.BytesIO()
            pil.save(out, format='JPEG', quality=28)
            out.seek(0)
            return RLImage(out, width=new_w, height=new_h)
        except Exception as e:
            logging.error(f"Failed to load photo {storage_path}: {e}")
            return None

    caption_style = ParagraphStyle('PhotoCaption', parent=styles['Normal'], fontSize=7, alignment=TA_CENTER, textColor=colors.black, spaceAfter=3, leading=9)

    # ===== COVER PAGE =====
    service_name = report.get("service", "").upper()
    vessel_name = report.get("location", "").upper()
    
    elements.append(Spacer(1, 0.5*cm))
    # Service name above photo
    service_cover_style = ParagraphStyle('ServiceCover', parent=styles['Normal'], fontSize=14, fontName='Helvetica-Bold', alignment=TA_CENTER, textColor=colors.black, spaceAfter=12)
    elements.append(Paragraph(service_name, service_cover_style))
    elements.append(Spacer(1, 0.3*cm))
    
    # Cover photo (centered) - reduced height so the info table (incl. TWAS/Client reps) fits on the same page
    cover_photos = report_photos.get("cover", [])
    if cover_photos:
        photo = cover_photos[0]
        img = load_photo_image(photo["storage_path"], content_width, 9*cm)
        if img:
            # Center the image
            img.hAlign = 'CENTER'
            elements.append(img)
    
    # Vessel/Embarcacao name below photo
    embarcacao_cover_name = report.get("embarcacao", "").upper()
    vessel_cover_style = ParagraphStyle('VesselCover', parent=styles['Normal'], fontSize=12, fontName='Helvetica-Bold', alignment=TA_CENTER, textColor=colors.black, spaceBefore=8, spaceAfter=10)
    elements.append(Paragraph(embarcacao_cover_name, vessel_cover_style))
    elements.append(Spacer(1, 0.2*cm))
    
    # Info table - translate labels based on report language
    report_lang = report.get("language", "pt")
    if report_lang == "en":
        lbl_cliente = "CLIENT:"
        lbl_embarcacao = "VESSEL:"
        lbl_local = "LOCATION:"
        lbl_os = "SERVICE ORDER:"
        lbl_servico = "SERVICE:"
        lbl_executado = "PERFORMED BY:"
        lbl_periodo = "PERIOD:"
        lbl_rep_twas = "TWAS REPRESENTATIVE:"
        lbl_rep_cliente = "CLIENT REPRESENTATIVE:"
    elif report_lang == "es":
        lbl_cliente = "CLIENTE:"
        lbl_embarcacao = "EMBARCACI\u00d3N:"
        lbl_local = "UBICACI\u00d3N:"
        lbl_os = "ORDEN DE SERVICIO:"
        lbl_servico = "SERVICIO:"
        lbl_executado = "EJECUTADO POR:"
        lbl_periodo = "PER\u00cdODO:"
        lbl_rep_twas = "REPRESENTANTE TWAS:"
        lbl_rep_cliente = "REPRESENTANTE DEL CLIENTE:"
    else:
        lbl_cliente = "CLIENTE:"
        lbl_embarcacao = "EMBARCA\u00c7\u00c3O:"
        lbl_local = "LOCAL:"
        lbl_os = "ORDEM DE SERVI\u00c7O:"
        lbl_servico = "SERVI\u00c7O:"
        lbl_executado = "EXECUTADO POR:"
        lbl_periodo = "PER\u00cdODO:"
        lbl_rep_twas = "REPRESENTANTE TWAS:"
        lbl_rep_cliente = "REPRESENTANTE DO CLIENTE:"

    info_data = [
        [Paragraph(f"<b>{lbl_cliente}</b>", label_style), Paragraph(report.get("client", ""), value_style)],
        [Paragraph(f"<b>{lbl_embarcacao}</b>", label_style), Paragraph(report.get("embarcacao", ""), value_style)],
        [Paragraph(f"<b>{lbl_local}</b>", label_style), Paragraph(report.get("location", ""), value_style)],
        [Paragraph(f"<b>{lbl_os}</b>", label_style), Paragraph(report.get("os_number", ""), value_style)],
        [Paragraph(f"<b>{lbl_servico}</b>", label_style), Paragraph(report.get("service", ""), value_style)],
        [Paragraph(f"<b>{lbl_executado}</b>", label_style), Paragraph(report.get("executado_por", report.get("supervisor_name", "")), value_style)],
        [Paragraph(f"<b>{lbl_periodo}</b>", label_style), Paragraph(periodo_str, value_style)],
    ]
    # Optional rows: only include when value is present (so capa stays clean if not filled)
    rep_twas_value = (report.get("representante_twas") or "").strip()
    if rep_twas_value:
        info_data.append([Paragraph(f"<b>{lbl_rep_twas}</b>", label_style), Paragraph(rep_twas_value, value_style)])
    rep_cliente_value = (report.get("representante_cliente") or "").strip()
    if rep_cliente_value:
        info_data.append([Paragraph(f"<b>{lbl_rep_cliente}</b>", label_style), Paragraph(rep_cliente_value, value_style)])
    info_table = Table(info_data, colWidths=[5*cm, content_width - 5*cm])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#777777')),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#cccccc')),
    ]))
    elements.append(info_table)
    
    # ===== SUMÁRIO PAGE =====
    elements.append(PageBreak())
    sumario_label = "TABLE OF CONTENTS" if report_lang == "en" else "TABLA DE CONTENIDO" if report_lang == "es" else "SUM\u00c1RIO"
    sumario_title_style = ParagraphStyle('SumarioTitle', parent=styles['Normal'], fontSize=14, fontName='Helvetica-Bold', alignment=TA_CENTER, textColor=colors.black, spaceBefore=12, spaceAfter=24)
    elements.append(Paragraph(sumario_label, sumario_title_style))
    elements.append(Spacer(1, 0.5*cm))
    
    sections = report.get("sections", [])
    
    # Renumber all enabled sections dynamically
    main_idx = 0
    for sec in sections:
        if not sec.get("enabled", True):
            continue
        main_idx += 1
        sec["number"] = str(main_idx)
        sub_idx = 0
        for sub in sec.get("subsections", []):
            if not sub.get("enabled", True):
                continue
            sub_idx += 1
            sub["number"] = f"{main_idx}.{sub_idx}"
            ss_idx = 0
            for ss in sub.get("subsections", []):
                if not ss.get("enabled", True):
                    continue
                ss_idx += 1
                ss["number"] = f"{main_idx}.{sub_idx}.{ss_idx}"
    
    toc_style_main = ParagraphStyle('TOCMain', parent=styles['Normal'], fontSize=10, fontName='Helvetica', textColor=colors.black, spaceBefore=3, spaceAfter=3)
    toc_style_sub = ParagraphStyle('TOCSub', parent=styles['Normal'], fontSize=9, fontName='Helvetica', textColor=colors.black, spaceBefore=2, spaceAfter=2, leftIndent=15)
    toc_style_subsub = ParagraphStyle('TOCSubSub', parent=styles['Normal'], fontSize=9, fontName='Helvetica', textColor=colors.black, spaceBefore=2, spaceAfter=2, leftIndent=30)
    
    def build_toc_entries(sec_list):
        entries = []
        for sec in sec_list:
            if sec.get("enabled", True):
                entries.append({"number": sec["number"], "title": sec["title"], "level": 0, "key": sec.get("key","")})
                for sub in sec.get("subsections", []):
                    if sub.get("enabled", True):
                        entries.append({"number": sub["number"], "title": sub["title"], "level": 1, "key": sub.get("key","")})
                        for subsub in sub.get("subsections", []):
                            if subsub.get("enabled", True):
                                entries.append({"number": subsub["number"], "title": subsub["title"], "level": 2, "key": subsub.get("key","")})
        return entries
    
    toc_entries = build_toc_entries(sections)
    
    # For daily reports: add daily entries as subsections of service_description in TOC
    daily_entries = report.get("daily_entries", [])
    is_daily = report.get("report_type") == "daily"
    
    # Filter daily entries by day_ids if provided
    if is_daily and day_ids:
        allowed_ids = set(day_ids.split(","))
        daily_entries = [e for e in daily_entries if e.get("id") in allowed_ids]
    
    # For daily reports, auto-calculate periodo_fim from last daily entry date
    if is_daily and daily_entries:
        sorted_entry_dates = sorted(
            [e.get("date", "") for e in daily_entries if e.get("date")],
            key=parse_date_sortable
        )
        if sorted_entry_dates:
            periodo_fim = sorted_entry_dates[-1]
    
    if is_daily and daily_entries:
        # Find the service_description section number
        svc_num = "4"
        for sec in sections:
            if sec.get("key") == "service_description" and sec.get("enabled", True):
                svc_num = sec["number"]
                break
        for idx, entry in enumerate(daily_entries):
            entry_num = f"{svc_num}.{idx + 1}"
            entry_date = entry.get("date", "")
            toc_entries.append({"number": entry_num, "title": f"DIA {entry_date}", "level": 1, "key": f"daily_{entry.get('id','')}"})
    
    # Add AVALIAÇÃO DO CLIENTE as the last TOC entry (only for service reports)
    enabled_main_count = sum(1 for s in sections if s.get("enabled", True))
    aval_sec_num = str(enabled_main_count + 1)
    aval_title = "AVALIAÇÃO DE SATISFAÇÃO DO CLIENTE"
    if is_service:
        toc_entries.append({"number": aval_sec_num, "title": aval_title, "level": 0, "key": "_avaliacao_"})
    
    # Build TOC: single row per entry with dot leaders filling entire line
    from reportlab.pdfbase.pdfmetrics import stringWidth
    toc_data = []
    for entry in toc_entries:
        num_part = f"{entry['number']}."
        title_part = f" {entry['title']}"
        label = f"{num_part}{title_part} "
        # Calculate dots needed based on actual font widths
        if entry['level'] == 0:
            font_name = 'Helvetica'
            font_size = 10
            indent = 0
        elif entry['level'] == 1:
            font_name = 'Helvetica'
            font_size = 9
            indent = 15
        else:
            font_name = 'Helvetica'
            font_size = 9
            indent = 30
        # Bold number part width
        num_width = stringWidth(num_part, 'Helvetica-Bold', font_size)
        # Normal title part width
        title_width = stringWidth(title_part + ' ', font_name, font_size)
        available_for_dots = content_width - indent - num_width - title_width - 25  # 25pt reserved for page number
        dot_width = stringWidth('.', font_name, font_size)
        num_dots = max(3, int(available_for_dots / dot_width))
        dots = '.' * num_dots
        # Bold only on the number, title and dots in normal weight
        line_text = f"<b>{num_part}</b>{title_part} {dots}"
        if entry['level'] == 0:
            toc_data.append([Paragraph(line_text, toc_style_main)])
        elif entry['level'] == 1:
            toc_data.append([Paragraph(line_text, toc_style_sub)])
        else:
            toc_data.append([Paragraph(line_text, toc_style_subsub)])
    
    if toc_data:
        toc_table = Table(toc_data, colWidths=[content_width])
        toc_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(toc_table)
    
    # ===== CONTENT PAGES =====
    elements.append(PageBreak())
    
    def render_section(sec, elements_list):
        if not sec.get("enabled", True):
            return
        level = len(sec["number"].split("."))
        style = section_style if level == 1 else subsec_style
        sec_key = sec.get("key", "")
        sec_photos = report_photos.get(sec_key, [])
        is_fp = sec_key in FULL_PAGE_KEYS or sec_key.startswith('sub_') or sec_key.startswith('subsub_') or sec_key.startswith('custom_')
        
        # Check if any subsection has photos (to decide KeepTogether with section title)
        subs = [s for s in sec.get("subsections", []) if s.get("enabled", True)]
        first_sub_with_photos = None
        for sub in subs:
            sub_key = sub.get("key", "")
            if report_photos.get(sub_key, []):
                first_sub_with_photos = sub
                break
        
        if is_fp and sec_photos:
            first_group = [Paragraph(f"{sec['number']}. {sec['title']}", style)]
            content = sec.get("content", "")
            if content:
                first_group.append(Paragraph(format_content(content), body_style))
            first_img = load_photo_image(sec_photos[0]["storage_path"], content_width, max_first_photo_height)
            if first_img:
                first_group.append(first_img)
            elements_list.append(KeepTogether(first_group))
            for idx_p, p in enumerate(sec_photos[1:]):
                if idx_p > 0 or first_img:
                    elements_list.append(PageBreak())
                img = load_photo_image(p["storage_path"], content_width, max_full_photo_height)
                if img:
                    elements_list.append(img)
        elif first_sub_with_photos and not sec_photos:
            # Don't add section title separately - it will be included in the first sub's KeepTogether
            pass
        else:
            elements_list.append(Paragraph(f"{sec['number']}. {sec['title']}", style))
            content = sec.get("content", "")
            if content:
                elements_list.append(Paragraph(format_content(content), body_style))
            _render_photos(sec_key, elements_list)
        
        section_title_included = False
        for sub in subs:
            sub_key = sub.get("key", "")
            sub_photos = report_photos.get(sub_key, [])
            # Respect explicit photo_layout when set; otherwise fall back to legacy auto-rule
            sub_layout = sub.get("photo_layout")
            if sub_layout == "grid":
                sub_is_fp = False
            elif sub_layout == "full_page":
                sub_is_fp = True
            else:
                sub_is_fp = sub_key in FULL_PAGE_KEYS or sub_key.startswith('sub_') or sub_key.startswith('subsub_') or sub_key.startswith('custom_')
            
            if sub_is_fp and sub_photos:
                first_group = []
                # Include parent section title in first subsection's KeepTogether
                if not section_title_included and first_sub_with_photos == sub and not sec_photos:
                    first_group.append(Paragraph(f"{sec['number']}. {sec['title']}", style))
                    content = sec.get("content", "")
                    if content:
                        first_group.append(Paragraph(format_content(content), body_style))
                    section_title_included = True
                first_group.append(Paragraph(f"{sub['number']}. {sub['title']}", subsec_style))
                sub_content = sub.get("content", "")
                if sub_content:
                    first_group.append(Paragraph(format_content(sub_content), body_style))
                first_img = load_photo_image(sub_photos[0]["storage_path"], content_width, max_first_photo_height)
                if first_img:
                    first_group.append(first_img)
                elements_list.append(KeepTogether(first_group))
                for idx_p, p in enumerate(sub_photos[1:]):
                    if idx_p > 0 or first_img:
                        elements_list.append(PageBreak())
                    img = load_photo_image(p["storage_path"], content_width, max_full_photo_height)
                    if img:
                        elements_list.append(img)
            else:
                sub_header = [Paragraph(f"{sub['number']}. {sub['title']}", subsec_style)]
                sub_content = sub.get("content", "")
                if sub_content:
                    sub_header.append(Paragraph(format_content(sub_content), body_style))
                _render_photos(sub_key, elements_list, force_grid=(sub_layout == "grid"), header_elements=sub_header)
            
            for subsub in sub.get("subsections", []):
                if subsub.get("enabled", True):
                    ss_key = subsub.get("key", "")
                    ss_photos = report_photos.get(ss_key, [])
                    ss_layout = subsub.get("photo_layout")
                    if ss_layout == "grid":
                        ss_is_fp = False
                    elif ss_layout == "full_page":
                        ss_is_fp = True
                    else:
                        ss_is_fp = ss_key in FULL_PAGE_KEYS or ss_key.startswith('sub_') or ss_key.startswith('subsub_') or ss_key.startswith('custom_')
                    
                    if ss_is_fp and ss_photos:
                        first_group = [Paragraph(f"{subsub['number']}. {subsub['title']}", subsec_style)]
                        ss_content = subsub.get("content", "")
                        if ss_content:
                            first_group.append(Paragraph(format_content(ss_content), body_style))
                        first_img = load_photo_image(ss_photos[0]["storage_path"], content_width, max_first_photo_height)
                        if first_img:
                            first_group.append(first_img)
                        elements_list.append(KeepTogether(first_group))
                        for idx_p, p in enumerate(ss_photos[1:]):
                            if idx_p > 0 or first_img:
                                elements_list.append(PageBreak())
                            img = load_photo_image(p["storage_path"], content_width, max_full_photo_height)
                            if img:
                                elements_list.append(img)
                    else:
                        ss_header = [Paragraph(f"{subsub['number']}. {subsub['title']}", subsec_style)]
                        ss_content = subsub.get("content", "")
                        if ss_content:
                            ss_header.append(Paragraph(format_content(ss_content), body_style))
                        _render_photos(ss_key, elements_list, force_grid=(ss_layout == "grid"), header_elements=ss_header)
    
    # Image-only sections: render full-page images (one per page)
    FULL_PAGE_KEYS = {'ndt', 'pressure_test', 'certificate', 'propeller_shaft', 'pinion_shaft', 'input_shaft', 'coupling', 'swivel_pinion', 'propeller', 'reduction_gear'}
    
    # Photo rendering helper: 2 per row, uniform size, aligned with content width
    photo_col_w = content_width / 2
    photo_img_w = photo_col_w - 0.3*cm
    photo_img_h = 6*cm
    
    def _render_photos(section_key, elements_list, force_full_page=False, force_grid=False, header_elements=None):
        """Render photos for a section. header_elements: list of flowables to keep together with first photo row."""
        sec_photos = report_photos.get(section_key, [])
        if not sec_photos:
            # No photos - just add headers if provided
            if header_elements:
                for h in header_elements:
                    elements_list.append(h)
            return
        
        # Full page: NDT subsections, pressure_test, certificate, custom sections
        if force_grid:
            is_full_page = False
        elif force_full_page:
            is_full_page = True
        else:
            is_full_page = section_key in FULL_PAGE_KEYS or section_key.startswith('sub_') or section_key.startswith('subsub_') or section_key.startswith('custom_')
        
        if is_full_page:
            if header_elements:
                for h in header_elements:
                    elements_list.append(h)
            for idx_p, p in enumerate(sec_photos):
                img = load_photo_image(p["storage_path"], content_width, max_full_photo_height)
                if img:
                    elements_list.append(img)
                    if idx_p < len(sec_photos) - 1:
                        elements_list.append(PageBreak())
        else:
            rows = []
            for i in range(0, len(sec_photos), 2):
                row_imgs = []
                row_caps = []
                for j in range(2):
                    if i + j < len(sec_photos):
                        p = sec_photos[i + j]
                        img = load_photo_image(p["storage_path"], photo_img_w, photo_img_h)
                        row_imgs.append(img if img else Paragraph("", body_style))
                        row_caps.append(Paragraph(p.get("caption", "") or p.get("original_filename", ""), caption_style))
                    else:
                        row_imgs.append(Paragraph("", body_style))
                        row_caps.append(Paragraph("", caption_style))
                rows.append(row_imgs)
                rows.append(row_caps)
            if rows:
                photo_table = Table(rows, colWidths=[photo_col_w, photo_col_w])
                photo_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ]))
                spacer = Spacer(1, 0.3*cm)
                if header_elements:
                    # Build first photo row table separately
                    first_row_data = rows[:2]  # first image row + caption row
                    first_photo_table = Table(first_row_data, colWidths=[photo_col_w, photo_col_w])
                    first_photo_table.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('TOPPADDING', (0, 0), (-1, -1), 4),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ]))
                    keep_group = list(header_elements) + [spacer, first_photo_table]
                    elements_list.append(KeepTogether(keep_group))
                    # Add remaining rows normally
                    if len(rows) > 2:
                        remaining_rows = rows[2:]
                        remaining_table = Table(remaining_rows, colWidths=[photo_col_w, photo_col_w])
                        remaining_table.setStyle(TableStyle([
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('TOPPADDING', (0, 0), (-1, -1), 4),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                        ]))
                        elements_list.append(remaining_table)
                else:
                    elements_list.append(spacer)
                    elements_list.append(photo_table)
    
    for sec in sections:
        render_section(sec, elements)
    
    # ===== DAILY ENTRIES as subsections of service_description =====
    if is_daily and daily_entries:
        svc_num = "4"
        for sec in sections:
            if sec.get("key") == "service_description" and sec.get("enabled", True):
                svc_num = sec["number"]
                break
        for idx, entry in enumerate(daily_entries):
            entry_num = f"{svc_num}.{idx + 1}"
            entry_date = entry.get("date", "")
            entry_desc = entry.get("description", "")
            entry_id = entry.get("id", "")
            photo_key = f"daily_{entry_id}"
            
            elements.append(Paragraph(f"{entry_num}. DIA {entry_date}", subsec_style))
            if entry_desc:
                elements.append(Paragraph(format_content(entry_desc), body_style))
            # Render photos for this daily entry
            _render_photos(photo_key, elements)
    
    # ==================== AVALIAÇÃO DE SATISFAÇÃO DO CLIENTE (only for service reports) ====================
    if is_service:
        elements.append(PageBreak())
        elements.append(Paragraph(f"{aval_sec_num}. {aval_title}", section_style))
        elements.append(Spacer(1, 0.3*cm))
        
        # Dynamic fields from report — aligned with body text
        oc_wo_val = report.get("oc_wo", "")
        aval_field_style = ParagraphStyle('AvalField', parent=styles['Normal'], fontSize=9, leading=14, textColor=colors.black, spaceAfter=2)
        
        # Use Paragraphs instead of a table so they align exactly with the intro text below
        elements.append(Paragraph(f"<b>CLIENTE:</b> {report.get('client', '')}", aval_field_style))
        elements.append(Paragraph(f"<b>NAVIO/VESSEL:</b> {report.get('embarcacao', '') or report.get('location', '')}", aval_field_style))
        elements.append(Paragraph(f"<b>SERVIÇO / SERVICE:</b> {report.get('service', '')}", aval_field_style))
        elements.append(Paragraph(f"<b>PERÍODO / PERIOD:</b> {periodo_inicio} a {periodo_fim}", aval_field_style))
        if oc_wo_val:
            elements.append(Paragraph(f"<b>OC/WO:</b> {oc_wo_val}", aval_field_style))
        elements.append(Spacer(1, 0.5*cm))
        
        # Bilingual intro text (BEFORE table, as per reference)
        aval_intro = (
            "Prezado cliente,<br/>"
            "Buscando meios para melhorar nossa qualidade, solicitamos a gentileza de preencher o questionário "
            "abaixo, marque com um X a opção que melhor representa o desempenho de nossa equipe.<br/><br/>"
            "<i>Dear client,<br/>"
            "Seeking for means to improve our quality, please kindly fill in the questionnaire, mark with a \"X\" that "
            "represent our team performance.</i>"
        )
        elements.append(Paragraph(aval_intro, ParagraphStyle('AvalIntro', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.black, spaceAfter=8)))
        
        # Rating scale legend (each item on its own line, BEFORE table)
        legend_style = ParagraphStyle('AvalLegend', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.black, spaceAfter=1)
        legend_items = [
            "<b>A</b> = Muito bom / <i>Excellent</i>",
            "<b>B</b> = Acima da expectativa / <i>Above Expectations</i>",
            "<b>C</b> = Expectativas alcançadas / <i>Expectations achieved</i>",
            "<b>D</b> = Regular / <i>Fair</i>",
            "<b>E</b> = Não satisfatório / <i>Unsatisfatory</i>",
            "<b>F</b> = N/A",
        ]
        for item in legend_items:
            elements.append(Paragraph(item, legend_style))
        elements.append(Spacer(1, 0.3*cm))
        
        # Evaluation table
        eval_items = [
            ("1", "Comunicação entre o cliente e a TWAS repair", "Communication between the customer and TWAS repair"),
            ("2", "Atendimento aos requisitos técnicos e contratuais do cliente", "Attendance to customer's technical and contractual requirements"),
            ("3", "Qualidade do Serviço executado", "Quality of work executed."),
            ("4", "Atendimento aos requisitos de saúde, segurança e meio ambiente.", "Met the requirement of health, safety and environment \"HSE\"."),
            ("5", "Pontualidade no atendimento às necessidades do cliente.", "Punctuality in meeting customer needs."),
            ("6", "Qualidade e conteúdo dos relatórios técnicos pós-serviço.", "Quality and content of report after completion service."),
        ]
        
        eval_cell_style = ParagraphStyle('EvalCell', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.black)
        eval_header_style = ParagraphStyle('EvalHdr', parent=styles['Normal'], fontSize=8, leading=10, fontName='Helvetica-Bold', alignment=TA_CENTER, textColor=colors.black)
        
        eval_header = [
            Paragraph("<b>N°</b>", eval_header_style),
            Paragraph("<b>ITEM AVALIADO / EVALUETED ITEM</b>", eval_header_style),
            Paragraph("<b>A</b>", eval_header_style),
            Paragraph("<b>B</b>", eval_header_style),
            Paragraph("<b>C</b>", eval_header_style),
            Paragraph("<b>D</b>", eval_header_style),
            Paragraph("<b>E</b>", eval_header_style),
            Paragraph("<b>F</b>", eval_header_style),
        ]
        eval_data = [eval_header]
        for num, pt_text, en_text in eval_items:
            eval_data.append([
                Paragraph(num, ParagraphStyle('EvalN', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER)),
                Paragraph(f"{pt_text}<br/><i>{en_text}</i>", eval_cell_style),
                "", "", "", "", "", ""
            ])
        
        col_w = 0.7*cm
        eval_table = Table(eval_data, colWidths=[0.8*cm, content_width - 0.8*cm - 6*col_w] + [col_w]*6)
        eval_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#777777')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EEEEEE')),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(eval_table)
        elements.append(Spacer(1, 0.3*cm))
        
        # ==================== PAGE 2: Comments + Date + Signatures ====================
        elements.append(PageBreak())
        
        elements.append(Paragraph("<b>Comentários adicionais / sugestões para melhoria de nossa qualidade:</b>", ParagraphStyle('AvalComm', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.black, spaceAfter=2)))
        elements.append(Paragraph("<b><i>Additional comments / suggestion to improve our quality:</i></b>", ParagraphStyle('AvalCommEn', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.black, spaceAfter=8)))
        
        # Ruled lines for handwritten comments (full width aligned with header/footer)
        line_str = "_" * 90
        line_style = ParagraphStyle('RuledLine', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#999999'), spaceAfter=10)
        for _ in range(8):
            elements.append(Paragraph(line_str, line_style))
        
        # Date (use periodo_fim as the date)
        date_str = ""
        if periodo_fim:
            try:
                from datetime import datetime as dt_parse
                for fmt in ["%Y-%m-%d", "%d/%m/%Y"]:
                    try:
                        d = dt_parse.strptime(periodo_fim, fmt)
                        months_pt = ['janeiro','fevereiro','março','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro']
                        date_str = f"{d.day:02d} de {months_pt[d.month-1]} de {d.year}."
                        break
                    except ValueError:
                        continue
                if not date_str:
                    date_str = periodo_fim
            except:
                date_str = periodo_fim
        if date_str:
            elements.append(Paragraph(date_str, ParagraphStyle('AvalDate', parent=styles['Normal'], fontSize=9, textColor=colors.black, spaceAfter=8)))
        
        elements.append(Spacer(1, 3*cm))
        
        # Signature block
        sig_line = "_" * 40
        sig_line_style = ParagraphStyle('SigLine', alignment=TA_CENTER, fontSize=10, spaceAfter=2)
        sig_name_style = ParagraphStyle('SigName', alignment=TA_CENTER, fontSize=9, fontName='Helvetica-Bold')
        sig_detail_style = ParagraphStyle('SigDetail', alignment=TA_CENTER, fontSize=8, textColor=colors.gray)
        
        supervisor_name = report.get("supervisor_name", "")
        client_name = report.get("client", "")
        
        # Client signature area
        elements.append(Paragraph(sig_line, sig_line_style))
        elements.append(Paragraph("Nome, assinatura e carimbo do representante do cliente.", ParagraphStyle('SigLabel', parent=styles['Normal'], fontSize=9, textColor=colors.black, spaceAfter=1, alignment=TA_CENTER)))
        elements.append(Paragraph(f"<i>Name, signature and stamp of the client representative.</i>", ParagraphStyle('SigLabelEn', parent=styles['Normal'], fontSize=8, textColor=colors.gray, spaceAfter=1, alignment=TA_CENTER)))
        elements.append(Paragraph(f"<b>{client_name}</b>", sig_name_style))
        elements.append(Spacer(1, 2*cm))
        
        # Supervisor / TWAS signature area (centered)
        elements.append(Paragraph(sig_line, sig_line_style))
        elements.append(Paragraph(f"<b>{supervisor_name}</b>", sig_name_style))
        elements.append(Paragraph("TWAS REPAIR SERVIÇOS NAVAIS E INDUSTRIAIS LTDA", sig_detail_style))
        elements.append(Paragraph("CNPJ: 31.839.501/0001-90", sig_detail_style))
    
    doc.build(elements, onFirstPage=on_first_page, onLaterPages=on_later_pages)
    buffer.seek(0)
    
    # Post-process with PyMuPDF: page numbers (right-aligned in footer) + TOC page numbers
    import fitz
    pdf_doc = fitz.open(stream=buffer.read(), filetype="pdf")
    total = len(pdf_doc)
    total_numbered = total - 1  # Cover page not counted
    
    # Find section page numbers by searching for section number prefix on content pages
    section_pages = {}
    for i in range(2, total):  # Skip cover (0) and summary (1)
        page = pdf_doc[i]
        text = page.get_text()
        for entry in toc_entries:
            search_key = f"{entry['number']}. {entry['title']}"
            if search_key not in section_pages:
                # Search by the section number at start of line
                search_prefix = f"{entry['number']}."
                for line in text.split('\n'):
                    stripped = line.strip()
                    if stripped.startswith(search_prefix) and entry['title'][:10] in stripped:
                        section_pages[search_key] = i
                        break
    
    # Update SUMÁRIO page with page numbers at the end of dot leaders
    sumario_page = pdf_doc[1]
    sumario_text = sumario_page.get_text('dict')
    
    # Build a list of all TOC lines with their y-positions for precise matching
    toc_lines = []
    for block in sumario_text['blocks']:
        if 'lines' not in block:
            continue
        for line in block['lines']:
            line_text = ''.join(s['text'] for s in line['spans'])
            if '...' in line_text:
                toc_lines.append({
                    'text': line_text,
                    'y': line['spans'][-1]['origin'][1],
                    'size': line['spans'][-1]['size'],
                    'used': False
                })
    
    for entry in toc_entries:
        search_key = f"{entry['number']}. {entry['title']}"
        page_num = section_pages.get(search_key, "")
        if not page_num:
            continue
        display_num = str(page_num)
        check_prefix = entry['number'] + '.'
        
        for toc_line in toc_lines:
            if toc_line['used']:
                continue
            stripped = toc_line['text'].strip()
            # Exact match: line must start with the entry number followed by non-digit
            if stripped.startswith(check_prefix):
                after = stripped[len(check_prefix):]
                # Skip if next char is a digit (e.g., "4." matching "4.1.")
                if after and after[0].isdigit():
                    continue
                # Found exact match - place page number at right edge
                right_x_pts = content_left + content_width - 0.3*cm
                num_w = len(display_num) * (toc_line['size'] * 0.55)
                sumario_page.insert_text(
                    fitz.Point(right_x_pts - num_w, toc_line['y']),
                    display_num,
                    fontsize=toc_line['size'],
                    fontname="helv",
                    color=(0, 0, 0),
                )
                toc_line['used'] = True
                break
    
    # Add page numbers to footer (right-aligned), skip cover page
    # Reference: x=507, y=772, sz=8, format "X de Y"
    for i in range(1, total):
        page = pdf_doc[i]
        page_num = i  # Cover not counted
        text = f"{page_num} de {total_numbered}"
        page.insert_text(
            fitz.Point(507, 772),
            text,
            fontsize=8,
            fontname="helv",
            color=(0, 0, 0),
        )
    
    final_buffer = io.BytesIO()
    pdf_doc.save(final_buffer)
    pdf_doc.close()
    final_buffer.seek(0)

    import re
    def _safe(s: str) -> str:
        return re.sub(r'[<>:"/\\|?*]', '', str(s or '')).strip()
    report_kind = "RT" if report.get("report_type") == "service" else "RD"
    filename = f"{_safe(report.get('os_number', ''))} - {_safe(report.get('client', ''))} - {report_kind} - {_safe(report.get('service', ''))}.pdf".strip(" -")

    disposition = "attachment" if download else "inline"
    return StreamingResponse(
        final_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'{disposition}; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
        }
    )


