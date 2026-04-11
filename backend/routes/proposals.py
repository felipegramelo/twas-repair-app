from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
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
from PIL import Image as PILImage
import io
import uuid
import jwt
from pathlib import Path

from database import db
from config import SECRET_KEY, ALGORITHM, put_object, get_object
from dependencies import get_current_user, get_admin_user
from models import UserRole

router = APIRouter()

class ProposalSubsectionModel(BaseModel):
    id: str = ""
    titulo: str
    descricao: str = ""

class ProposalItemModel(BaseModel):
    id: str = ""
    titulo: str
    descricao: str = ""
    valor: Optional[float] = 0.0
    images: Optional[List[str]] = []
    subsections: Optional[List[ProposalSubsectionModel]] = []

class ProposalCreate(BaseModel):
    empresa: str
    contato: str
    email: str = ""
    embarcacao: str = ""
    local: str = ""
    equipamento: str = ""
    servico: str = ""
    itens: List[ProposalItemModel] = []
    termos_gerais: str = ""
    observacoes: str = ""

class ProposalUpdate(BaseModel):
    empresa: Optional[str] = None
    contato: Optional[str] = None
    email: Optional[str] = None
    embarcacao: Optional[str] = None
    local: Optional[str] = None
    equipamento: Optional[str] = None
    servico: Optional[str] = None
    itens: Optional[List[ProposalItemModel]] = None
    termos_gerais: Optional[str] = None
    observacoes: Optional[str] = None

async def generate_proposal_number() -> str:
    """Generate auto-numbering: YYMM - Seq (seq is global for the year, resets on new year)."""
    now = datetime.utcnow()
    yy = now.strftime("%y")
    mm = now.strftime("%m")
    year_start = datetime(now.year, 1, 1)
    year_end = datetime(now.year + 1, 1, 1)
    count = await db.propostas.count_documents({
        "created_at": {"$gte": year_start, "$lt": year_end}
    })
    seq = count + 1
    return f"{yy}{mm} - {seq:02d}"

@router.post("/proposals")
async def create_proposal(data: ProposalCreate, current_user: Dict[str, Any] = Depends(get_admin_user)):
    if not current_user.get("proposta_access", False):
        raise HTTPException(status_code=403, detail="Acesso negado. Permissão de Propostas não habilitada.")
    numero = await generate_proposal_number()
    now = datetime.utcnow()
    itens = []
    for item in data.itens:
        subs = []
        for sub in (item.subsections or []):
            subs.append({
                "id": sub.id or str(uuid.uuid4()),
                "titulo": sub.titulo,
                "descricao": sub.descricao,
            })
        itens.append({
            "id": item.id or str(uuid.uuid4()),
            "titulo": item.titulo,
            "descricao": item.descricao,
            "valor": item.valor or 0.0,
            "images": item.images or [],
            "subsections": subs,
        })
    doc = {
        "numero_proposta": numero,
        "empresa": data.empresa,
        "contato": data.contato,
        "email": data.email,
        "embarcacao": data.embarcacao,
        "local": data.local,
        "equipamento": data.equipamento,
        "servico": data.servico,
        "itens": itens,
        "termos_gerais": data.termos_gerais,
        "observacoes": data.observacoes,
        "status": "pendente",
        "po_number": "",
        "os_id": "",
        "os_number": "",
        "created_by": current_user["_id"],
        "created_at": now,
        "updated_at": now,
    }
    result = await db.propostas.insert_one(doc)
    return {
        "id": str(result.inserted_id),
        "numero_proposta": numero,
        "empresa": data.empresa,
        "contato": data.contato,
        "email": data.email,
        "embarcacao": data.embarcacao,
        "local": data.local,
        "equipamento": data.equipamento,
        "servico": data.servico,
        "itens": itens,
        "termos_gerais": data.termos_gerais,
        "observacoes": data.observacoes,
        "status": "pendente",
        "po_number": "",
        "os_id": "",
        "os_number": "",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

def serialize_proposal(p):
    """Helper to serialize a proposal document."""
    return {
        "id": str(p["_id"]),
        "numero_proposta": p.get("numero_proposta", ""),
        "empresa": p.get("empresa", ""),
        "contato": p.get("contato", ""),
        "email": p.get("email", ""),
        "embarcacao": p.get("embarcacao", ""),
        "local": p.get("local", ""),
        "equipamento": p.get("equipamento", ""),
        "servico": p.get("servico", ""),
        "itens": p.get("itens", []),
        "termos_gerais": p.get("termos_gerais", ""),
        "observacoes": p.get("observacoes", ""),
        "status": p.get("status", "pendente"),
        "po_number": p.get("po_number", ""),
        "os_id": p.get("os_id", ""),
        "os_number": p.get("os_number", ""),
        "created_at": p.get("created_at", "").isoformat() if p.get("created_at") else "",
        "updated_at": p.get("updated_at", "").isoformat() if p.get("updated_at") else "",
    }

@router.get("/proposals")
async def list_proposals(month: Optional[int] = Query(None), year: Optional[int] = Query(None), current_user: Dict[str, Any] = Depends(get_admin_user)):
    if not current_user.get("proposta_access", False):
        raise HTTPException(status_code=403, detail="Acesso negado")
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
    proposals = await db.propostas.find(query).sort("created_at", -1).to_list(500)
    return [serialize_proposal(p) for p in proposals]

@router.get("/proposals/{proposal_id}")
async def get_proposal(proposal_id: str, current_user: Dict[str, Any] = Depends(get_admin_user)):
    if not current_user.get("proposta_access", False):
        raise HTTPException(status_code=403, detail="Acesso negado")
    p = await db.propostas.find_one({"_id": ObjectId(proposal_id)})
    if not p:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")
    return serialize_proposal(p)

@router.put("/proposals/{proposal_id}")
async def update_proposal(proposal_id: str, data: ProposalUpdate, current_user: Dict[str, Any] = Depends(get_admin_user)):
    if not current_user.get("proposta_access", False):
        raise HTTPException(status_code=403, detail="Acesso negado")
    p = await db.propostas.find_one({"_id": ObjectId(proposal_id)})
    if not p:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")
    update_dict = {"updated_at": datetime.utcnow()}
    if data.empresa is not None:
        update_dict["empresa"] = data.empresa
    if data.contato is not None:
        update_dict["contato"] = data.contato
    if data.email is not None:
        update_dict["email"] = data.email
    if data.embarcacao is not None:
        update_dict["embarcacao"] = data.embarcacao
    if data.local is not None:
        update_dict["local"] = data.local
    if data.equipamento is not None:
        update_dict["equipamento"] = data.equipamento
    if data.servico is not None:
        update_dict["servico"] = data.servico
    if data.observacoes is not None:
        update_dict["observacoes"] = data.observacoes
    if data.termos_gerais is not None:
        update_dict["termos_gerais"] = data.termos_gerais
    if data.itens is not None:
        itens = []
        for item in data.itens:
            subs = []
            for sub in (item.subsections or []):
                subs.append({
                    "id": sub.id or str(uuid.uuid4()),
                    "titulo": sub.titulo,
                    "descricao": sub.descricao,
                })
            itens.append({
                "id": item.id or str(uuid.uuid4()),
                "titulo": item.titulo,
                "descricao": item.descricao,
                "valor": item.valor or 0.0,
                "images": item.images or [],
                "subsections": subs,
            })
        update_dict["itens"] = itens
    await db.propostas.update_one({"_id": ObjectId(proposal_id)}, {"$set": update_dict})
    updated = await db.propostas.find_one({"_id": ObjectId(proposal_id)})
    return serialize_proposal(updated)

@router.delete("/proposals/{proposal_id}")
async def delete_proposal(proposal_id: str, current_user: Dict[str, Any] = Depends(get_admin_user)):
    if not current_user.get("proposta_access", False):
        raise HTTPException(status_code=403, detail="Acesso negado")
    result = await db.propostas.delete_one({"_id": ObjectId(proposal_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")
    return {"message": "Proposta excluída com sucesso"}

# ==================== PROPOSAL PHOTOS ====================

@router.post("/proposals/{proposal_id}/upload-photo")
async def upload_proposal_photo(
    proposal_id: str,
    file: UploadFile = File(...),
    section_index: int = Query(default=0),
    section_key: str = Query(default=""),
    user: dict = Depends(get_current_user)
):
    proposal = await db.propostas.find_one({"_id": ObjectId(proposal_id)})
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")

    ext = file.filename.split(".")[-1].lower() if "." in file.filename else "jpg"
    if ext not in MIME_TYPES:
        raise HTTPException(status_code=400, detail="Formato não suportado. Use jpg, png, gif, webp ou pdf.")

    data = await file.read()
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Arquivo muito grande. Máximo 20MB.")

    uploaded_paths = []

    if ext == "pdf":
        try:
            pages = convert_pdf_to_images(data)
        except Exception as e:
            logging.error(f"PDF conversion error: {e}")
            raise HTTPException(status_code=400, detail="Erro ao converter PDF para imagens")
        for img_data, img_name in pages:
            pil_img = PILImage.open(io.BytesIO(img_data))
            if pil_img.mode != 'RGB':
                pil_img = pil_img.convert('RGB')
            out_buf = io.BytesIO()
            pil_img.save(out_buf, format='JPEG', quality=60)
            compressed = out_buf.getvalue()
            file_id = str(uuid.uuid4())
            storage_path = f"{APP_NAME}/proposals/{proposal_id}/{section_index}/{file_id}.jpeg"
            try:
                result = put_object(storage_path, compressed, "image/jpeg")
            except Exception as e:
                logging.error(f"Upload error: {e}")
                continue
            await db.proposal_photos.insert_one({
                "proposal_id": proposal_id,
                "section_index": section_index,
                "section_key": section_key,
                "storage_path": result["path"],
                "original_filename": f"{file.filename} - {img_name}",
                "content_type": "image/jpeg",
                "is_deleted": False,
                "created_at": datetime.utcnow(),
            })
            uploaded_paths.append(result["path"])
        return {"storage_paths": uploaded_paths, "section_index": section_index, "pages_converted": len(uploaded_paths)}
    else:
        content_type = MIME_TYPES.get(ext, "image/jpeg")
        try:
            pil_img = PILImage.open(io.BytesIO(data))
            if pil_img.mode != 'RGB':
                pil_img = pil_img.convert('RGB')
            max_dim = 2000
            if max(pil_img.size) > max_dim:
                pil_img.thumbnail((max_dim, max_dim), PILImage.LANCZOS)
            out_buf = io.BytesIO()
            pil_img.save(out_buf, format='JPEG', quality=60)
            data = out_buf.getvalue()
            ext = "jpeg"
            content_type = "image/jpeg"
        except Exception:
            pass
        file_id = str(uuid.uuid4())
        storage_path = f"{APP_NAME}/proposals/{proposal_id}/{section_index}/{file_id}.{ext}"
        try:
            result = put_object(storage_path, data, content_type)
        except Exception as e:
            logging.error(f"Upload error: {e}")
            raise HTTPException(status_code=500, detail="Erro no upload")
        await db.proposal_photos.insert_one({
            "proposal_id": proposal_id,
            "section_index": section_index,
            "section_key": section_key,
            "storage_path": result["path"],
            "original_filename": file.filename,
            "content_type": content_type,
            "is_deleted": False,
            "created_at": datetime.utcnow(),
        })
        return {"storage_path": result["path"], "section_index": section_index, "filename": file.filename}

@router.get("/proposals/{proposal_id}/photos")
async def get_proposal_photos(proposal_id: str, user: dict = Depends(get_current_user)):
    photos = await db.proposal_photos.find({"proposal_id": proposal_id, "is_deleted": {"$ne": True}}).sort("created_at", 1).to_list(200)
    return [{
        "id": str(p["_id"]),
        "section_index": p.get("section_index", 0),
        "section_key": p.get("section_key", ""),
        "storage_path": p.get("storage_path", ""),
        "original_filename": p.get("original_filename", ""),
    } for p in photos]

@router.delete("/proposals/{proposal_id}/photos/{photo_id}")
async def delete_proposal_photo(proposal_id: str, photo_id: str, user: dict = Depends(get_current_user)):
    result = await db.proposal_photos.update_one(
        {"_id": ObjectId(photo_id), "proposal_id": proposal_id},
        {"$set": {"is_deleted": True}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Foto não encontrada")
    return {"message": "Foto excluída"}

# ==================== INFORMAR P.O. (Approve proposal & create O.S.) ====================

class InformarPORequest(BaseModel):
    po_number: str

async def generate_os_number_from_proposal(numero_proposta: str) -> str:
    """Generate O.S. number: SEQ - NUMERO_PROPOSTA. SEQ is global yearly sequential."""
    now = datetime.utcnow()
    year_start = datetime(now.year, 1, 1)
    year_end = datetime(now.year + 1, 1, 1)
    count = await db.service_orders.count_documents({
        "created_at": {"$gte": year_start, "$lt": year_end}
    })
    seq = count + 1
    return f"{seq:02d} - {numero_proposta}"

@router.put("/proposals/{proposal_id}/informar-po")
async def informar_po(proposal_id: str, data: InformarPORequest, current_user: Dict[str, Any] = Depends(get_admin_user)):
    if not current_user.get("proposta_access", False):
        raise HTTPException(status_code=403, detail="Acesso negado")
    p = await db.propostas.find_one({"_id": ObjectId(proposal_id)})
    if not p:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")
    if p.get("status") == "aprovada":
        raise HTTPException(status_code=400, detail="Proposta já aprovada")
    if not data.po_number.strip():
        raise HTTPException(status_code=400, detail="Número da P.O. é obrigatório")

    # Generate O.S. number
    os_number = await generate_os_number_from_proposal(p["numero_proposta"])

    # Create service order from proposal data
    now = datetime.utcnow()
    so_dict = {
        "os_number": os_number,
        "client": p.get("empresa", ""),
        "embarcacao": p.get("embarcacao", ""),
        "location": p.get("local", ""),
        "service": p.get("servico", ""),
        "employees": [],
        "schedule_type": "07-19",
        "proposal_id": str(p["_id"]),
        "po_number": data.po_number.strip(),
        "created_at": now,
    }
    so_result = await db.service_orders.insert_one(so_dict)
    so_id = str(so_result.inserted_id)

    # Update proposal status
    await db.propostas.update_one(
        {"_id": ObjectId(proposal_id)},
        {"$set": {
            "status": "aprovada",
            "po_number": data.po_number.strip(),
            "os_id": so_id,
            "os_number": os_number,
            "updated_at": now,
        }}
    )

    updated = await db.propostas.find_one({"_id": ObjectId(proposal_id)})
    return serialize_proposal(updated)

# ==================== PROPOSAL PDF GENERATION ====================

@router.get("/proposals/{proposal_id}/pdf")
async def generate_proposal_pdf(proposal_id: str, tipo: str = Query(default="comercial"), token: Optional[str] = Query(None), credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))):
    """Generate PDF for a proposal. tipo='comercial' includes prices, tipo='tecnica' excludes prices."""
    actual_token = token
    if not actual_token and credentials:
        actual_token = credentials.credentials
    if not actual_token:
        raise HTTPException(status_code=401, detail="Token required")
    try:
        payload = jwt.decode(actual_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user or user.get("role") != UserRole.ADMIN or not user.get("proposta_access", False):
            raise HTTPException(status_code=403, detail="Acesso negado")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

    proposal = await db.propostas.find_one({"_id": ObjectId(proposal_id)})
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")

    is_comercial = tipo != "tecnica"
    pdf_title = "PROPOSTA COMERCIAL" if is_comercial else "PROPOSTA TÉCNICA"

    buf = io.BytesIO()
    page_width, page_height = A4
    border_margin = 1.0 * cm
    content_left = 2.03 * cm
    content_right = 2.03 * cm
    content_width = page_width - content_left - content_right

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
        except Exception:
            pass

    page_counter = [0]

    def draw_proposal_page(canvas_obj, doc_obj, page_num):
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
        canvas_obj.drawCentredString(page_width / 2, header_bottom + 1.6 * cm, pdf_title)
        canvas_obj.setFont("Helvetica", 7)
        canvas_obj.drawCentredString(page_width / 2, header_bottom + 1.15 * cm, f"N\u00ba {proposal.get('numero_proposta', '')}")

        # Right side details
        right_x = content_left + content_width - 0.15 * cm
        detail_y = header_top - 0.45 * cm
        line_h = 0.35 * cm

        def _draw_right_label(label, value, y_pos):
            canvas_obj.setFont("Helvetica", 8)
            val_w = canvas_obj.stringWidth(value, "Helvetica", 8)
            canvas_obj.drawRightString(right_x, y_pos, value)
            canvas_obj.setFont("Helvetica-Bold", 8)
            canvas_obj.drawRightString(right_x - val_w - 3, y_pos, label)

        from datetime import datetime as dt_parse
        date_str = dt_parse.utcnow().strftime("%d/%m/%Y")
        _draw_right_label("Data:", date_str, detail_y)
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

    def on_first_page_prop(c, d):
        page_counter[0] = 1
        draw_proposal_page(c, d, 1)

    def on_later_pages_prop(c, d):
        page_counter[0] += 1
        draw_proposal_page(c, d, page_counter[0])

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=border_margin + 3.1 * cm,
        bottomMargin=border_margin + 2.1 * cm,
        leftMargin=content_left,
        rightMargin=content_right,
    )

    styles = getSampleStyleSheet()
    body_style = ParagraphStyle('PropBody', parent=styles['Normal'], fontSize=9, leading=13, spaceAfter=3, alignment=TA_JUSTIFY, textColor=colors.black)
    label_style = ParagraphStyle('PropLabel', parent=styles['Normal'], fontSize=9, textColor=colors.black, fontName='Helvetica-Bold')
    section_style = ParagraphStyle('PropSec', parent=styles['Heading2'], fontSize=10, textColor=colors.black, spaceBefore=12, spaceAfter=5, fontName='Helvetica-Bold')
    th_style = ParagraphStyle('PropTH', fontSize=8, fontName='Helvetica-Bold', alignment=TA_CENTER, textColor=colors.white)
    td_style = ParagraphStyle('PropTD', fontSize=8, alignment=TA_LEFT, textColor=colors.black, leading=10)
    td_right = ParagraphStyle('PropTDR', fontSize=8, alignment=TA_RIGHT, textColor=colors.black)

    elements = []

    # === CLIENT INFO (plain text, no table) ===
    import html as html_mod
    info_style = ParagraphStyle('InfoLine', parent=styles['Normal'], fontSize=9, leading=13, spaceAfter=1, textColor=colors.black)
    info_fields = [
        ("Empresa", proposal.get("empresa", "")),
        ("A/C", proposal.get("contato", "")),
        ("Email", proposal.get("email", "")),
        ("Embarca\u00e7\u00e3o", proposal.get("embarcacao", "")),
        ("Equipamento", proposal.get("equipamento", "")),
        ("Servi\u00e7o", proposal.get("servico", "")),
    ]
    for lbl, val in info_fields:
        if val:
            elements.append(Paragraph(f"<b>{lbl}:</b> {html_mod.escape(val)}", info_style))
    elements.append(Spacer(1, 0.4 * cm))

    # === INTRO TEXT ===
    servico_val = proposal.get("servico", "")
    embarcacao_val = proposal.get("embarcacao", "")
    intro_text = f"Prezados,<br/>Agradecemos a consulta e temos o prazer de apresentar nossa proposta comercial para o servi\u00e7o de <b>{html_mod.escape(servico_val) if servico_val else '____________________'}</b> a ser realizado na(o) <b>{html_mod.escape(embarcacao_val) if embarcacao_val else '____________________'}</b>."
    intro_style = ParagraphStyle('IntroText', parent=styles['Normal'], fontSize=9, leading=14, spaceAfter=6, textColor=colors.black, alignment=TA_JUSTIFY)
    elements.append(Paragraph(intro_text, intro_style))
    elements.append(Spacer(1, 0.3 * cm))

    # === NUMBERED SECTIONS (Escopo) ===
    itens = proposal.get("itens", [])
    section_num = 1
    total_valor = 0.0

    # Title for scope
    elements.append(Paragraph("ESCOPO DOS SERVI\u00c7OS", section_style))
    elements.append(Spacer(1, 0.2 * cm))

    for idx, item in enumerate(itens):
        titulo = item.get("titulo", "")
        descricao = item.get("descricao", "")
        valor = item.get("valor", 0.0) or 0.0
        total_valor += valor

        # Section heading with number
        if is_comercial and valor > 0:
            heading_text = f"<b>{section_num}. {html_mod.escape(titulo)}</b> &nbsp;&nbsp; <font color='#1a237e'><b>{format_currency(valor)}</b></font>"
        else:
            heading_text = f"<b>{section_num}. {html_mod.escape(titulo)}</b>"

        item_heading_style = ParagraphStyle('ItemHeading', parent=styles['Normal'], fontSize=10, leading=14, spaceAfter=4, textColor=colors.black, fontName='Helvetica-Bold')
        elements.append(Paragraph(heading_text, item_heading_style))

        # Description
        if descricao:
            desc_escaped = html_mod.escape(descricao).replace('\n', '<br/>')
            elements.append(Paragraph(desc_escaped, body_style))

        # Images from item.images (inline URLs) + proposal_photos collection
        from reportlab.platypus import Image as RLImage
        all_images = list(item.get("images", []))

        # Also fetch photos from DB for this section index
        db_photos = await db.proposal_photos.find({
            "proposal_id": str(proposal["_id"]),
            "section_index": idx,
            "is_deleted": {"$ne": True},
        }).to_list(50)
        for dp in db_photos:
            sp = dp.get("storage_path", "")
            if sp:
                try:
                    photo_url = get_object_url(sp)
                    all_images.append(photo_url)
                except Exception:
                    pass

        for img_url in all_images:
            try:
                if img_url.startswith("http"):
                    import urllib.request
                    img_data = io.BytesIO()
                    with urllib.request.urlopen(img_url, timeout=10) as resp:
                        img_data.write(resp.read())
                    img_data.seek(0)
                    pil = PILImage.open(img_data)
                else:
                    img_path = Path(img_url)
                    if img_path.exists():
                        pil = PILImage.open(img_path)
                    else:
                        continue
                iw, ih = pil.size
                max_w = content_width * 0.85
                max_h = 8 * cm
                ratio = min(max_w / iw, max_h / ih)
                draw_w = iw * ratio
                draw_h = ih * ratio
                temp_img = io.BytesIO()
                if pil.mode != 'RGB':
                    pil = pil.convert('RGB')
                pil.save(temp_img, format='JPEG')
                temp_img.seek(0)
                from reportlab.platypus import Image as RLImage
                elements.append(Spacer(1, 0.2 * cm))
                elements.append(RLImage(temp_img, width=draw_w, height=draw_h))
            except Exception:
                pass

        # Subsections
        subsections = item.get("subsections", [])
        for sub_idx, sub in enumerate(subsections):
            sub_titulo = sub.get("titulo", "")
            sub_descricao = sub.get("descricao", "")
            sub_heading = f"<b>{section_num}.{sub_idx + 1} {html_mod.escape(sub_titulo)}</b>"
            sub_heading_style = ParagraphStyle('SubHeading', parent=styles['Normal'], fontSize=9, leading=13, spaceAfter=3, textColor=colors.HexColor('#333333'), fontName='Helvetica-Bold')
            elements.append(Spacer(1, 0.15 * cm))
            elements.append(Paragraph(sub_heading, sub_heading_style))
            if sub_descricao:
                sub_desc_escaped = html_mod.escape(sub_descricao).replace('\n', '<br/>')
                elements.append(Paragraph(sub_desc_escaped, body_style))

            # Subsection photos (section_key = "{idx}.{sub_idx}")
            sub_photos = await db.proposal_photos.find({
                "proposal_id": str(proposal["_id"]),
                "section_key": f"{idx}.{sub_idx}",
                "is_deleted": {"$ne": True},
            }).to_list(50)
            for sp in sub_photos:
                sp_path = sp.get("storage_path", "")
                if sp_path:
                    try:
                        photo_url = get_object_url(sp_path)
                        import urllib.request
                        img_data = io.BytesIO()
                        with urllib.request.urlopen(photo_url, timeout=10) as resp_data:
                            img_data.write(resp_data.read())
                        img_data.seek(0)
                        pil = PILImage.open(img_data)
                        iw, ih = pil.size
                        max_w = content_width * 0.8
                        max_h = 7 * cm
                        ratio = min(max_w / iw, max_h / ih)
                        draw_w = iw * ratio
                        draw_h = ih * ratio
                        temp_img = io.BytesIO()
                        if pil.mode != 'RGB':
                            pil = pil.convert('RGB')
                        pil.save(temp_img, format='JPEG')
                        temp_img.seek(0)
                        elements.append(Spacer(1, 0.15 * cm))
                        elements.append(RLImage(temp_img, width=draw_w, height=draw_h))
                    except Exception:
                        pass

        elements.append(Spacer(1, 0.3 * cm))
        section_num += 1

    # === TOTAL for comercial ===
    if is_comercial and itens:
        elements.append(Spacer(1, 0.2 * cm))
        total_table = Table([
            [Paragraph("<b>VALOR TOTAL</b>", ParagraphStyle('TotalLabel', fontSize=10, fontName='Helvetica-Bold', alignment=TA_RIGHT)),
             Paragraph(f"<b>{format_currency(total_valor)}</b>", ParagraphStyle('TotalVal', fontSize=10, fontName='Helvetica-Bold', alignment=TA_RIGHT))]
        ], colWidths=[content_width * 0.80, content_width * 0.20])
        total_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#1a237e')),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#E8EAF6')),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(total_table)

    # === TERMOS GERAIS ===
    termos = proposal.get("termos_gerais", "")
    if termos:
        elements.append(Spacer(1, 0.5 * cm))
        elements.append(Paragraph(f"<b>{section_num}. TERMOS E CONDI\u00c7\u00d5ES GERAIS</b>", section_style))
        termos_escaped = html_mod.escape(termos).replace('\n', '<br/>')
        termos_style = ParagraphStyle('TermosBody', parent=styles['Normal'], fontSize=8, leading=11, spaceAfter=3, alignment=TA_JUSTIFY, textColor=colors.black)
        elements.append(Paragraph(termos_escaped, termos_style))
        section_num += 1

    # === OBSERVATIONS ===
    obs = proposal.get("observacoes", "")
    if obs:
        elements.append(Spacer(1, 0.5 * cm))
        elements.append(Paragraph(f"<b>{section_num}. OBSERVA\u00c7\u00d5ES</b>", section_style))
        obs_escaped = html_mod.escape(obs).replace('\n', '<br/>')
        elements.append(Paragraph(obs_escaped, body_style))

    # === SIGNATURE BLOCK ===
    elements.append(Spacer(1, 2 * cm))
    sig_line = "_" * 40
    sig_line_style = ParagraphStyle('SigLine', alignment=TA_CENTER, fontSize=10, spaceAfter=2)
    sig_name_style = ParagraphStyle('SigName', alignment=TA_CENTER, fontSize=9, fontName='Helvetica-Bold')
    sig_detail_style = ParagraphStyle('SigDetail', alignment=TA_CENTER, fontSize=8, textColor=colors.gray)

    elements.append(Paragraph(sig_line, sig_line_style))
    elements.append(Paragraph("TWAS REPAIR SERVI\u00c7OS NAVAIS E INDUSTRIAIS LTDA", sig_name_style))
    elements.append(Paragraph("CNPJ: 31.839.501/0001-90", sig_detail_style))

    doc.build(elements, onFirstPage=on_first_page_prop, onLaterPages=on_later_pages_prop)
    buf.seek(0)

    # Post-process with PyMuPDF: add page numbers
    import fitz
    pdf_doc = fitz.open(stream=buf.read(), filetype="pdf")
    total = len(pdf_doc)
    for i in range(total):
        page = pdf_doc[i]
        text = f"{i + 1} de {total}"
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

    tipo_label = "comercial" if is_comercial else "tecnica"
    filename = f"Proposta_{tipo_label}_{proposal.get('numero_proposta', '').replace(' ', '_')}.pdf"
    return Response(
        content=final_buffer.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
        }
    )

