"""Project routes — hierarchical task planning (like a mini MS Project).

Access control:
- Admin: full CRUD on projects and tasks.
- Supervisor: can list projects; can update ONLY task progress_percent.

Data model (single document per project):
  db.projects = {
    _id, os_number, title, embarcacao, client, location,
    start_date, end_date, lock_end_date, description,
    created_by, created_at, updated_at,
    tasks: [ { id, parent_id, name, duration_value, duration_unit,
                start_date, end_date, progress_percent, order, notes } ]
  }
"""
import io
import uuid
import asyncio
import logging
import os
import re
import json as jsonlib
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Query, Request, UploadFile, File
from fastapi.responses import StreamingResponse
from bson import ObjectId
from pydantic import BaseModel
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import jwt

from database import db
from config import SECRET_KEY, ALGORITHM
from dependencies import get_current_user, get_admin_user
from models import (
    ProjectCreate, ProjectUpdate, ProjectTaskCreate, ProjectTaskUpdate,
    ProjectProgressUpdate, UserRole,
)
from services.onedrive import send_pdf_to_onedrive

ROOT_DIR = Path(__file__).parent.parent

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------- helpers ----------------
def _now() -> str:
    return datetime.utcnow().isoformat()


def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.split("T")[0]).date()
    except Exception:
        return None


def _task_new(task_in: dict) -> dict:
    """Build a task dict with a UUID id."""
    return {
        "id": str(uuid.uuid4()),
        "parent_id": task_in.get("parent_id") or None,
        "name": task_in.get("name") or "",
        "duration_value": float(task_in.get("duration_value") or 0),
        "duration_unit": task_in.get("duration_unit") or "dias",
        "start_date": task_in.get("start_date") or None,
        "end_date": task_in.get("end_date") or None,
        "progress_percent": max(0.0, min(100.0, float(task_in.get("progress_percent") or 0))),
        "order": int(task_in.get("order") or 0),
        "notes": task_in.get("notes") or "",
    }


def _clean_project(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    doc.setdefault("tasks", [])
    doc.setdefault("shared_with", [])
    return doc


def _is_admin(user: dict) -> bool:
    return (user.get("role") or "").lower() == "admin"


def _uid(user: dict) -> str:
    return str(user.get("_id") or user.get("id") or "")


def _can_edit(project: dict, user: dict) -> bool:
    """Admin can always; supervisor only if listed in shared_with."""
    if _is_admin(user):
        return True
    return _uid(user) in (project.get("shared_with") or [])


def _recalc_end_date(project: dict) -> Optional[str]:
    """Return the max task end_date. Used only if lock_end_date=False."""
    dates = [_parse_date(t.get("end_date")) for t in project.get("tasks", [])]
    dates = [d for d in dates if d]
    if not dates:
        return None
    return max(dates).isoformat()


# ---------------- routes ----------------
@router.post("/projects")
async def create_project(payload: ProjectCreate, current_user: Dict[str, Any] = Depends(get_admin_user)):
    tasks = [_task_new(t.model_dump()) for t in payload.tasks]
    doc = payload.model_dump(exclude={"tasks"})
    doc.update({
        "tasks": tasks,
        "created_by": str(current_user.get("_id") or current_user.get("id") or ""),
        "created_at": _now(),
        "updated_at": _now(),
    })
    if not doc.get("lock_end_date"):
        auto_end = _recalc_end_date(doc)
        if auto_end:
            doc["end_date"] = auto_end
    result = await db.projects.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _clean_project(doc)


@router.get("/projects")
async def list_projects(
    os_number: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    query = {}
    if os_number:
        query["os_number"] = os_number
    # Supervisor sees only projects assigned to them
    if not _is_admin(current_user):
        query["shared_with"] = _uid(current_user)
    projects = await db.projects.find(query).sort("created_at", -1).to_list(500)
    return [_clean_project(p) for p in projects]


@router.get("/projects/{project_id}")
async def get_project(project_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    if not ObjectId.is_valid(project_id):
        raise HTTPException(400, "Invalid project id")
    doc = await db.projects.find_one({"_id": ObjectId(project_id)})
    if not doc:
        raise HTTPException(404, "Project not found")
    if not _can_edit(doc, current_user) and not _is_admin(current_user):
        raise HTTPException(403, "Não autorizado a acessar este projeto")
    return _clean_project(doc)


@router.put("/projects/{project_id}")
async def update_project(project_id: str, payload: ProjectUpdate, current_user: Dict[str, Any] = Depends(get_current_user)):
    if not ObjectId.is_valid(project_id):
        raise HTTPException(400, "Invalid project id")
    doc = await db.projects.find_one({"_id": ObjectId(project_id)})
    if not doc:
        raise HTTPException(404, "Project not found")
    if not _can_edit(doc, current_user):
        raise HTTPException(403, "Não autorizado a editar este projeto")
    updates = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    # Only admin may change shared_with
    if "shared_with" in updates and not _is_admin(current_user):
        updates.pop("shared_with")
    if not updates:
        raise HTTPException(400, "No fields to update")
    updates["updated_at"] = _now()
    await db.projects.update_one({"_id": ObjectId(project_id)}, {"$set": updates})
    doc = await db.projects.find_one({"_id": ObjectId(project_id)})
    return _clean_project(doc)


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str, current_user: Dict[str, Any] = Depends(get_admin_user)):
    if not ObjectId.is_valid(project_id):
        raise HTTPException(400, "Invalid project id")
    await db.projects.delete_one({"_id": ObjectId(project_id)})
    return {"ok": True}


class ShareRequest(BaseModel):
    supervisor_ids: List[str]


@router.post("/projects/{project_id}/share")
async def share_project(
    project_id: str,
    payload: ShareRequest,
    current_user: Dict[str, Any] = Depends(get_admin_user),
):
    """Admin sets which supervisors can edit this project."""
    if not ObjectId.is_valid(project_id):
        raise HTTPException(400, "Invalid project id")
    doc = await db.projects.find_one({"_id": ObjectId(project_id)})
    if not doc:
        raise HTTPException(404, "Project not found")
    ids = list({str(x) for x in payload.supervisor_ids if x})
    await db.projects.update_one(
        {"_id": ObjectId(project_id)},
        {"$set": {"shared_with": ids, "updated_at": _now()}},
    )
    doc = await db.projects.find_one({"_id": ObjectId(project_id)})
    return _clean_project(doc)


@router.get("/projects/_/supervisors")
async def list_supervisors(current_user: Dict[str, Any] = Depends(get_admin_user)):
    """List all supervisor users (for admin to pick when creating/sharing a project)."""
    users = await db.users.find({"role": "supervisor"}).sort("name", 1).to_list(500)
    return [
        {"id": str(u["_id"]), "name": u.get("name") or u.get("email"), "email": u.get("email", "")}
        for u in users
    ]


@router.post("/projects/{project_id}/import-pdf")
async def import_pdf(
    project_id: str,
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Kick off async import from a project PDF. Returns immediately.
    Frontend should poll GET /api/projects/{id} — while import runs,
    the project has import_status='processing'. When done, tasks appear
    and import_status='done' (or 'error').
    """
    if not ObjectId.is_valid(project_id):
        raise HTTPException(400, "Invalid project id")
    doc = await db.projects.find_one({"_id": ObjectId(project_id)})
    if not doc:
        raise HTTPException(404, "Project not found")
    if not _can_edit(doc, current_user):
        raise HTTPException(403, "Não autorizado a editar este projeto")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(400, "Empty file")

    # Extract PDF text synchronously (fast)
    try:
        import fitz
        pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages_text = [p.get_text("text") for p in pdf]
        pdf.close()
        raw_text = "\n\n".join(pages_text)[:12000]
    except Exception as e:
        raise HTTPException(400, f"Falha ao ler PDF: {e}")
    if not raw_text.strip():
        raise HTTPException(400, "PDF sem texto extraível (talvez seja imagem escaneada)")

    # Mark project as processing
    await db.projects.update_one(
        {"_id": ObjectId(project_id)},
        {"$set": {"import_status": "processing", "import_error": None, "updated_at": _now()}},
    )
    # Fire background task and return immediately
    asyncio.create_task(_do_import(project_id, raw_text))
    return {"ok": True, "status": "processing", "message": "Importação iniciada. Aguarde alguns segundos e recarregue."}


async def _do_import(project_id: str, raw_text: str):
    """Background: call Gemini, parse JSON, append tasks to project."""
    try:
        api_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
        if not api_key:
            raise RuntimeError("EMERGENT_LLM_KEY não configurada")

        system_prompt = (
            "Você é um extrator de cronogramas. Retorne APENAS um JSON válido, sem prosa nem code fences.\n"
            "Formato: {\"tasks\":[{\"name\":str,\"parent_index\":int|null,\"duration_value\":float,\"duration_unit\":\"dias\"|\"hrs\",\"start_date\":\"YYYY-MM-DD\"|null,\"end_date\":\"YYYY-MM-DD\"|null,\"progress_percent\":0-100}]}\n"
            "parent_index é o índice base 0 da tarefa pai NO MESMO array. null quando é fase raiz.\n"
            "Deduza hierarquia por indentação, numeração ou títulos em maiúsculas.\n"
            "Converta duração '7,75 days' → duration_value=7.75, duration_unit='dias'. 'hours' → 'hrs'."
        )

        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(
            api_key=api_key,
            session_id=f"import-{project_id}",
            system_message=system_prompt,
        ).with_model("gemini", "gemini-3-flash-preview")

        response = await chat.send_message(UserMessage(text=f"Texto extraído do PDF:\n\n{raw_text}"))
        llm_out = (response if isinstance(response, str) else str(response)).strip()

        m = re.search(r"\{[\s\S]*\}", llm_out)
        if not m:
            raise RuntimeError("IA não retornou JSON")
        parsed = jsonlib.loads(m.group(0))
        raw_tasks = parsed.get("tasks") or []
        if not isinstance(raw_tasks, list) or not raw_tasks:
            raise RuntimeError("Nenhuma tarefa extraída")

        id_by_index: Dict[int, str] = {}
        new_tasks: List[dict] = []
        for i, t in enumerate(raw_tasks):
            try:
                new_id = str(uuid.uuid4())
                id_by_index[i] = new_id
                pi = t.get("parent_index")
                parent_id = id_by_index.get(pi) if isinstance(pi, int) and pi < i else None
                unit = (t.get("duration_unit") or "dias").strip().lower()
                if unit in ("hours", "hour", "hr", "h"):
                    unit = "hrs"
                if unit in ("days", "day", "d"):
                    unit = "dias"
                new_tasks.append({
                    "id": new_id,
                    "parent_id": parent_id,
                    "name": (t.get("name") or "").strip()[:200],
                    "duration_value": float(t.get("duration_value") or 0),
                    "duration_unit": unit,
                    "start_date": t.get("start_date") or None,
                    "end_date": t.get("end_date") or None,
                    "progress_percent": max(0.0, min(100.0, float(t.get("progress_percent") or 0))),
                    "order": i,
                    "notes": "",
                })
            except Exception:
                continue
        if not new_tasks:
            raise RuntimeError("Nenhuma tarefa válida após parse")

        # Append to project (re-load to avoid overwriting concurrent changes)
        doc = await db.projects.find_one({"_id": ObjectId(project_id)})
        if not doc:
            return
        existing = doc.get("tasks") or []
        max_order = max([int(t.get("order") or 0) for t in existing], default=-1)
        for k, nt in enumerate(new_tasks):
            nt["order"] = max_order + 1 + k
        existing.extend(new_tasks)
        upd = {"tasks": existing, "import_status": "done", "import_error": None, "updated_at": _now()}
        if not doc.get("lock_end_date"):
            merged = {**doc, "tasks": existing}
            auto_end = _recalc_end_date(merged)
            if auto_end:
                upd["end_date"] = auto_end
        await db.projects.update_one({"_id": ObjectId(project_id)}, {"$set": upd})
        logger.info(f"Import PDF done for project {project_id}: {len(new_tasks)} tasks")
    except Exception as e:
        logger.exception(f"Import PDF failed: {e}")
        await db.projects.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": {"import_status": "error", "import_error": str(e)[:300], "updated_at": _now()}},
        )


# ---------------- task subroutes ----------------
@router.post("/projects/{project_id}/tasks")
async def add_task(project_id: str, task: ProjectTaskCreate, current_user: Dict[str, Any] = Depends(get_current_user)):
    if not ObjectId.is_valid(project_id):
        raise HTTPException(400, "Invalid project id")
    doc = await db.projects.find_one({"_id": ObjectId(project_id)})
    if not doc:
        raise HTTPException(404, "Project not found")
    if not _can_edit(doc, current_user):
        raise HTTPException(403, "Não autorizado a editar este projeto")
    new_task = _task_new(task.model_dump())
    doc.setdefault("tasks", []).append(new_task)
    if not doc.get("lock_end_date"):
        auto_end = _recalc_end_date(doc)
        if auto_end:
            doc["end_date"] = auto_end
    doc["updated_at"] = _now()
    await db.projects.replace_one({"_id": ObjectId(project_id)}, doc)
    return {"ok": True, "task": new_task}


@router.put("/projects/{project_id}/tasks/{task_id}")
async def update_task(
    project_id: str, task_id: str, payload: ProjectTaskUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not ObjectId.is_valid(project_id):
        raise HTTPException(400, "Invalid project id")
    doc = await db.projects.find_one({"_id": ObjectId(project_id)})
    if not doc:
        raise HTTPException(404, "Project not found")
    if not _can_edit(doc, current_user):
        raise HTTPException(403, "Não autorizado a editar este projeto")
    updates = payload.model_dump(exclude_none=True)
    found = False
    for t in doc.get("tasks", []):
        if t.get("id") == task_id:
            for k, v in updates.items():
                if k == "progress_percent":
                    v = max(0.0, min(100.0, float(v)))
                t[k] = v
            found = True
            break
    if not found:
        raise HTTPException(404, "Task not found")
    if not doc.get("lock_end_date"):
        auto_end = _recalc_end_date(doc)
        if auto_end:
            doc["end_date"] = auto_end
    doc["updated_at"] = _now()
    await db.projects.replace_one({"_id": ObjectId(project_id)}, doc)
    return _clean_project(doc)


@router.patch("/projects/{project_id}/tasks/{task_id}/progress")
async def update_task_progress(
    project_id: str, task_id: str, payload: ProjectProgressUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Update ONLY the progress % of a task. Admin OR authorized supervisor."""
    if not ObjectId.is_valid(project_id):
        raise HTTPException(400, "Invalid project id")
    doc = await db.projects.find_one({"_id": ObjectId(project_id)})
    if not doc:
        raise HTTPException(404, "Project not found")
    if not _can_edit(doc, current_user):
        raise HTTPException(403, "Não autorizado a editar este projeto")
    found = False
    for t in doc.get("tasks", []):
        if t.get("id") == task_id:
            t["progress_percent"] = max(0.0, min(100.0, float(payload.progress_percent)))
            found = True
            break
    if not found:
        raise HTTPException(404, "Task not found")
    doc["updated_at"] = _now()
    await db.projects.replace_one({"_id": ObjectId(project_id)}, doc)
    return _clean_project(doc)


@router.delete("/projects/{project_id}/tasks/{task_id}")
async def delete_task(project_id: str, task_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    if not ObjectId.is_valid(project_id):
        raise HTTPException(400, "Invalid project id")
    doc = await db.projects.find_one({"_id": ObjectId(project_id)})
    if not doc:
        raise HTTPException(404, "Project not found")
    if not _can_edit(doc, current_user):
        raise HTTPException(403, "Não autorizado a editar este projeto")
    # remove task and its descendants
    tasks = doc.get("tasks", [])
    to_del = {task_id}
    changed = True
    while changed:
        changed = False
        for t in tasks:
            if t.get("parent_id") in to_del and t["id"] not in to_del:
                to_del.add(t["id"])
                changed = True
    doc["tasks"] = [t for t in tasks if t["id"] not in to_del]
    if not doc.get("lock_end_date"):
        auto_end = _recalc_end_date(doc)
        if auto_end:
            doc["end_date"] = auto_end
    doc["updated_at"] = _now()
    await db.projects.replace_one({"_id": ObjectId(project_id)}, doc)
    return {"ok": True, "deleted_ids": list(to_del)}


# ---------------- PDF ----------------
def _flatten_tasks(tasks: List[dict]) -> List[tuple]:
    """Return list of (depth, task, has_children) in hierarchical order."""
    by_parent: Dict[Optional[str], List[dict]] = {}
    for t in tasks:
        by_parent.setdefault(t.get("parent_id") or None, []).append(t)
    for lst in by_parent.values():
        lst.sort(key=lambda x: (int(x.get("order") or 0), x.get("name") or ""))

    out: List[tuple] = []
    def walk(parent: Optional[str], depth: int):
        for t in by_parent.get(parent, []):
            has_children = bool(by_parent.get(t["id"]))
            out.append((depth, t, has_children))
            walk(t["id"], depth + 1)
    walk(None, 0)
    return out


_WEEKDAY_PT = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]


def _fmt_date(iso: Optional[str]) -> str:
    d = _parse_date(iso)
    return d.strftime("%d/%m/%y") if d else "-"


def _fmt_date_full(iso: Optional[str]) -> str:
    """Format like 'Qua 14/01/26' (day-of-week + date), matching MS Project style."""
    d = _parse_date(iso)
    if not d:
        return "-"
    return f"{_WEEKDAY_PT[d.weekday()]} {d.strftime('%d/%m/%y')}"


@router.get("/projects/{project_id}/pdf")
async def project_pdf(
    project_id: str,
    request: Request,
    token: Optional[str] = Query(None),
    download: str = Query(default=None),
):
    # Accept auth from query (?token=) or Authorization: Bearer header
    auth_token = token
    if not auth_token:
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            auth_token = auth_header[7:]
    if not auth_token:
        raise HTTPException(401, "Token não fornecido")
    try:
        payload = jwt.decode(auth_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(401, "Token inválido")
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(401, "Usuário não encontrado")
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expirado")
    except jwt.PyJWTError:
        raise HTTPException(401, "Token inválido")

    if not ObjectId.is_valid(project_id):
        raise HTTPException(400, "Invalid project id")
    doc = await db.projects.find_one({"_id": ObjectId(project_id)})
    if not doc:
        raise HTTPException(404, "Project not found")

    buffer = io.BytesIO()
    page_w, page_h = landscape(A4)

    # === Margins (smaller than defaults) ===
    border_margin = 0.4*cm          # page border distance to page edge
    content_left = 0.7*cm            # actual usable left margin
    content_right = 0.7*cm
    header_h = 1.8*cm                 # header box height
    footer_h = 1.1*cm                 # footer box height
    top_margin = border_margin + header_h + 0.15*cm
    bottom_margin = border_margin + footer_h + 0.15*cm
    content_width = page_w - content_left - content_right

    # === Preload TWAS logo ===
    logo_path = ROOT_DIR / "../logo.bmp"
    logo_image = None
    if logo_path.exists():
        try:
            from PIL import Image as PILImage
            pil_img = PILImage.open(logo_path)
            if pil_img.mode != 'RGB':
                pil_img = pil_img.convert('RGB')
            temp_logo = io.BytesIO()
            pil_img.save(temp_logo, format='JPEG')
            temp_logo.seek(0)
            logo_image = temp_logo
        except Exception as e:
            logging.error(f"Project PDF: error loading logo: {e}")

    pdf = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=content_left,
        rightMargin=content_right,
        topMargin=top_margin,
        bottomMargin=bottom_margin,
    )

    # === On-page decoration (border + header + footer) ===
    def _draw_page(canvas_obj, _doc_obj):
        canvas_obj.saveState()

        # Page border
        canvas_obj.setStrokeColor(colors.HexColor('#777777'))
        canvas_obj.setLineWidth(0.5)
        canvas_obj.rect(border_margin, border_margin, page_w - 2*border_margin, page_h - 2*border_margin)

        # ---------- HEADER BOX ----------
        header_top = page_h - border_margin - 0.15*cm
        header_bottom = header_top - header_h
        canvas_obj.setStrokeColor(colors.HexColor('#777777'))
        canvas_obj.setLineWidth(0.5)
        canvas_obj.rect(content_left, header_bottom, content_width, header_h)

        # Logo (left)
        if logo_image:
            logo_image.seek(0)
            from reportlab.lib.utils import ImageReader
            img_reader = ImageReader(logo_image)
            logo_h = 1.5*cm
            logo_y = header_bottom + (header_h - logo_h) / 2
            canvas_obj.drawImage(
                img_reader,
                content_left + 0.15*cm, logo_y,
                width=3.5*cm, height=logo_h,
                preserveAspectRatio=True, mask='auto',
            )

        # Center: title + form id
        canvas_obj.setFont("Helvetica-Bold", 13)
        canvas_obj.drawCentredString(page_w/2, header_bottom + 1.05*cm, "CRONOGRAMA DE PROJETO")
        canvas_obj.setFont("Helvetica-Bold", 10)
        proj_title = (doc.get('title') or 'Projeto')[:80]
        canvas_obj.drawCentredString(page_w/2, header_bottom + 0.5*cm, proj_title)

        # Right: Cliente / Rig / OS / Rev
        right_x = content_left + content_width - 0.15*cm
        detail_y = header_top - 0.32*cm
        line_h = 0.34*cm

        def _draw_right_label(label, value, y_pos):
            canvas_obj.setFont("Helvetica", 8)
            val_w = canvas_obj.stringWidth(value, "Helvetica", 8)
            canvas_obj.drawRightString(right_x, y_pos, value)
            canvas_obj.setFont("Helvetica-Bold", 8)
            canvas_obj.drawRightString(right_x - val_w - 3, y_pos, label)

        _draw_right_label("Cliente:", str(doc.get('client', '') or '-'), detail_y)
        detail_y -= line_h
        _draw_right_label("Rig/Vessel:", str(doc.get('embarcacao', '') or '-'), detail_y)
        detail_y -= line_h
        _draw_right_label("OS:", str(doc.get('os_number', '') or '-'), detail_y)
        detail_y -= line_h
        _draw_right_label("Rev:", "0", detail_y)

        # ---------- FOOTER BOX ----------
        footer_bottom = border_margin + 0.15*cm
        footer_top = footer_bottom + footer_h
        canvas_obj.rect(content_left, footer_bottom, content_width, footer_h)

        center_x = page_w / 2
        y = footer_top - 0.35*cm
        canvas_obj.setFont("Helvetica-Bold", 8)
        canvas_obj.drawCentredString(center_x, y, "TWAS REPAIR SERVIÇOS NAVAIS E INDUSTRIAIS LTDA")
        y -= 0.28*cm
        canvas_obj.setFont("Helvetica", 7.5)
        canvas_obj.drawCentredString(center_x, y, "Travessa Frederico Marques, N° 84, Boa Vista, São Gonçalo, Rio de Janeiro - CEP.: 24.466-180.")
        y -= 0.25*cm
        canvas_obj.drawCentredString(center_x, y, "twas@twasrepair.com  -  www.twasrepair.com")

        # Page number (bottom-right, inside footer)
        canvas_obj.setFont("Helvetica", 7)
        canvas_obj.drawRightString(right_x, footer_bottom + 0.1*cm, f"Pag. {canvas_obj.getPageNumber()}")

        canvas_obj.restoreState()

    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle("c", parent=styles["Normal"], fontSize=8, leading=10)
    cell_bold = ParagraphStyle("cb", parent=cell_style, fontName="Helvetica-Bold")
    phase_style = ParagraphStyle("ph", parent=styles["Normal"], fontSize=9, leading=11, fontName="Helvetica-Bold")
    tick_style = ParagraphStyle("tk", parent=styles["Normal"], fontSize=6, leading=7, alignment=TA_CENTER, fontName="Helvetica-Bold")

    elements = []
    # Small summary line (dates) since title/OS/Client are now in the standard header
    date_summary = ParagraphStyle("ds", parent=styles["Normal"], alignment=TA_CENTER, fontSize=9, fontName="Helvetica-Bold")
    elements.append(Paragraph(
        f"Início: {_fmt_date_full(doc.get('start_date'))}   |   Término: {_fmt_date_full(doc.get('end_date'))}",
        date_summary,
    ))
    elements.append(Spacer(1, 0.2*cm))

    # Determine timeline extent for Gantt bars
    all_dates = []
    for t in doc.get("tasks", []):
        s = _parse_date(t.get("start_date"))
        e = _parse_date(t.get("end_date"))
        if s:
            all_dates.append(s)
        if e:
            all_dates.append(e)
    proj_start = _parse_date(doc.get("start_date")) or (min(all_dates) if all_dates else date.today())
    proj_end = _parse_date(doc.get("end_date")) or (max(all_dates) if all_dates else proj_start)
    total_days = max((proj_end - proj_start).days + 1, 1)

    gantt_col_width = 9.4 * cm  # narrower to give more room to the Name column

    # Build a timeline header (date ticks) matching the Gantt column
    # Show ~9 tick labels evenly spaced across the timeline (like the model: 08 11 14 17 20 23 26 29 01)
    tick_count = min(9, total_days) if total_days > 1 else 1
    tick_cells = []
    for i in range(tick_count):
        # position i-th tick at day index = round(i * (total_days-1) / (tick_count-1))
        if tick_count == 1:
            day_offset = 0
        else:
            day_offset = round(i * (total_days - 1) / (tick_count - 1))
        d = proj_start + timedelta(days=day_offset)
        tick_cells.append(Paragraph(d.strftime("%d/%m"), tick_style))
    header_gantt = Table([tick_cells], colWidths=[gantt_col_width/tick_count]*tick_count, rowHeights=[0.5*cm])
    header_gantt.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#0d47a1")),
        ("TEXTCOLOR", (0,0), (-1,-1), colors.white),
        ("BOX", (0,0), (-1,-1), 0.25, colors.grey),
        ("INNERGRID", (0,0), (-1,-1), 0.25, colors.HexColor("#3a6fbf")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
    ]))

    # Table header: last column is the timeline ticks row
    data = [[
        Paragraph("#", cell_bold),
        Paragraph("Nome da Tarefa", cell_bold),
        Paragraph("Duração", cell_bold),
        Paragraph("Início", cell_bold),
        Paragraph("Término", cell_bold),
        Paragraph("% Concl.", cell_bold),
        header_gantt,
    ]]

    ordered = _flatten_tasks(doc.get("tasks", []))
    phase_row_indices: List[int] = []  # rows to highlight with light-gray background
    for i, (depth, t, has_children) in enumerate(ordered, start=1):
        # Phase headers: any task that has children — rendered bold + slightly larger.
        is_phase = has_children
        indent = "&nbsp;" * (depth * 3)
        name_text = t.get("name") or ""
        if is_phase:
            name_para = Paragraph(f"{indent}<b>{name_text}</b>", phase_style)
            phase_row_indices.append(i)  # position in `data` (header is row 0)
        else:
            name_para = Paragraph(f"{indent}{name_text}", cell_style)

        dur = f"{t.get('duration_value','')} {t.get('duration_unit','')}".strip()
        s = _parse_date(t.get("start_date"))
        e = _parse_date(t.get("end_date"))
        # Build a mini Gantt using a nested table of cells
        cells = [""] * total_days
        style_gantt = [
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("LEFTPADDING", (0,0), (-1,-1), 0),
            ("RIGHTPADDING", (0,0), (-1,-1), 0),
            ("TOPPADDING", (0,0), (-1,-1), 0),
            ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ]
        if s and e and e >= s:
            start_idx = max(0, (s - proj_start).days)
            end_idx = min(total_days - 1, (e - proj_start).days)
            bar_len = end_idx - start_idx + 1
            progress_len = max(0, min(bar_len, int(round(bar_len * float(t.get("progress_percent") or 0) / 100.0))))
            # Phase bars: dark filled black-like bar (matches MS Project phase). Leaf bars: blue.
            done_color = colors.HexColor("#111111") if is_phase else colors.HexColor("#1e88e5")
            todo_color = colors.HexColor("#555555") if is_phase else colors.HexColor("#bbdefb")
            for j in range(start_idx, end_idx + 1):
                fill = done_color if j < start_idx + progress_len else todo_color
                style_gantt.append(("BACKGROUND", (j,0), (j,0), fill))
        bar_row_height = 0.4*cm if is_phase else 0.55*cm
        gantt_table = Table([cells], colWidths=[gantt_col_width/total_days]*total_days, rowHeights=[bar_row_height])
        gantt_table.setStyle(TableStyle(style_gantt))

        num_para = Paragraph(f"<b>{i}</b>", cell_bold) if is_phase else Paragraph(str(i), cell_style)
        dur_para = Paragraph(f"<b>{dur}</b>", cell_bold) if is_phase else Paragraph(dur, cell_style)
        s_para = Paragraph(f"<b>{_fmt_date_full(t.get('start_date'))}</b>", cell_bold) if is_phase else Paragraph(_fmt_date_full(t.get('start_date')), cell_style)
        e_para = Paragraph(f"<b>{_fmt_date_full(t.get('end_date'))}</b>", cell_bold) if is_phase else Paragraph(_fmt_date_full(t.get('end_date')), cell_style)
        pct_txt = f"{float(t.get('progress_percent') or 0):.0f}%"
        pct_para = Paragraph(f"<b>{pct_txt}</b>", cell_bold) if is_phase else Paragraph(pct_txt, cell_style)

        data.append([num_para, name_para, dur_para, s_para, e_para, pct_para, gantt_table])

    col_widths = [0.8*cm, 9.2*cm, 2.2*cm, 2.6*cm, 2.6*cm, 1.5*cm, gantt_col_width]
    table_style = [
        ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0d47a1")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (0,0), (0,-1), "CENTER"),
        ("ALIGN", (2,0), (5,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.whitesmoke, colors.white]),
        # Zero padding for the header gantt cell so its inner table fills it
        ("LEFTPADDING", (6,0), (6,0), 0),
        ("RIGHTPADDING", (6,0), (6,0), 0),
        ("TOPPADDING", (6,0), (6,0), 0),
        ("BOTTOMPADDING", (6,0), (6,0), 0),
        # Zero padding on all Gantt bar cells so bars fill the row
        ("LEFTPADDING", (6,1), (6,-1), 0),
        ("RIGHTPADDING", (6,1), (6,-1), 0),
        ("TOPPADDING", (6,1), (6,-1), 1),
        ("BOTTOMPADDING", (6,1), (6,-1), 1),
    ]
    # Phase row background — subtle light-gray to visually group hierarchy
    for r in phase_row_indices:
        table_style.append(("BACKGROUND", (0,r), (5,r), colors.HexColor("#e3e8ee")))

    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle(table_style))
    elements.append(tbl)
    pdf.build(elements, onFirstPage=_draw_page, onLaterPages=_draw_page)
    buffer.seek(0)

    def _safe(s: str) -> str:
        return re.sub(r'[<>:"/\\|?*]', '', str(s or '')).strip()
    filename = f"{_safe(doc.get('os_number',''))} - {_safe(doc.get('title',''))} - PROJETO.pdf".strip(" -")
    # RFC 6266: fallback ASCII name + UTF-8 encoded name for Unicode chars (em-dash etc.)
    from urllib.parse import quote
    ascii_filename = filename.encode('ascii', 'ignore').decode('ascii') or "project.pdf"
    utf8_filename = quote(filename, safe='')

    if download:
        pdf_bytes = buffer.getvalue()
        buffer.seek(0)
        os_num = (str(doc.get("os_number") or "").strip() or "SEM-OS")
        asyncio.create_task(send_pdf_to_onedrive(
            pdf_bytes=pdf_bytes,
            filename=filename,
            os_number=os_num,
            kind="project",
        ))

    disposition = "attachment" if download else "inline"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"{disposition}; filename=\"{ascii_filename}\"; filename*=UTF-8''{utf8_filename}",
            "Cache-Control": "no-cache, no-store, must-revalidate",
        }
    )
