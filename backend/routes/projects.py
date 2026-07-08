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
    """Return list of (depth, task) in hierarchical order."""
    by_parent: Dict[Optional[str], List[dict]] = {}
    for t in tasks:
        by_parent.setdefault(t.get("parent_id") or None, []).append(t)
    for lst in by_parent.values():
        lst.sort(key=lambda x: (int(x.get("order") or 0), x.get("name") or ""))

    out: List[tuple] = []
    def walk(parent: Optional[str], depth: int):
        for t in by_parent.get(parent, []):
            out.append((depth, t))
            walk(t["id"], depth + 1)
    walk(None, 0)
    return out


def _fmt_date(iso: Optional[str]) -> str:
    d = _parse_date(iso)
    return d.strftime("%d/%m/%y") if d else "-"


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
    pdf = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=1*cm, rightMargin=1*cm, topMargin=1*cm, bottomMargin=1*cm)
    styles = getSampleStyleSheet()
    h_style = ParagraphStyle("h", parent=styles["Heading1"], alignment=TA_CENTER, fontSize=14)
    sub_style = ParagraphStyle("sub", parent=styles["Normal"], alignment=TA_CENTER, fontSize=9)
    cell_style = ParagraphStyle("c", parent=styles["Normal"], fontSize=8, leading=10)
    cell_bold = ParagraphStyle("cb", parent=cell_style, fontName="Helvetica-Bold")

    elements = []
    elements.append(Paragraph(doc.get("title") or "Projeto", h_style))
    header_line = f"OS: {doc.get('os_number','')} | Embarcação: {doc.get('embarcacao','')} | Cliente: {doc.get('client','')}"
    elements.append(Paragraph(header_line, sub_style))
    elements.append(Paragraph(f"Início: {_fmt_date(doc.get('start_date'))} | Término: {_fmt_date(doc.get('end_date'))}", sub_style))
    elements.append(Spacer(1, 0.4*cm))

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
    total_days = max((proj_end - proj_start).days, 1)

    # Table header
    data = [[
        Paragraph("#", cell_bold),
        Paragraph("Nome da Tarefa", cell_bold),
        Paragraph("Duração", cell_bold),
        Paragraph("Início", cell_bold),
        Paragraph("Término", cell_bold),
        Paragraph("% Concl.", cell_bold),
        Paragraph("Gantt", cell_bold),
    ]]

    gantt_col_width = 10 * cm  # visual bar column width
    ordered = _flatten_tasks(doc.get("tasks", []))
    for i, (depth, t) in enumerate(ordered, start=1):
        indent = "&nbsp;" * (depth * 4)
        name_html = f"{indent}{'<b>' if depth==0 else ''}{t.get('name','')}{'</b>' if depth==0 else ''}"
        dur = f"{t.get('duration_value','')} {t.get('duration_unit','')}".strip()
        s = _parse_date(t.get("start_date"))
        e = _parse_date(t.get("end_date"))
        # Build a mini Gantt using a nested table of cells
        # Split gantt column into total_days cells; fill start..end range gray, and completed portion darker
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
            for j in range(start_idx, end_idx + 1):
                if j < start_idx + progress_len:
                    style_gantt.append(("BACKGROUND", (j,0), (j,0), colors.HexColor("#1e88e5")))
                else:
                    style_gantt.append(("BACKGROUND", (j,0), (j,0), colors.HexColor("#bbdefb")))
        gantt_table = Table([cells], colWidths=[gantt_col_width/total_days]*total_days, rowHeights=[0.55*cm])
        gantt_table.setStyle(TableStyle(style_gantt))

        data.append([
            Paragraph(str(i), cell_style),
            Paragraph(name_html, cell_style),
            Paragraph(dur, cell_style),
            Paragraph(_fmt_date(t.get("start_date")), cell_style),
            Paragraph(_fmt_date(t.get("end_date")), cell_style),
            Paragraph(f"{float(t.get('progress_percent') or 0):.0f}%", cell_style),
            gantt_table,
        ])

    col_widths = [0.9*cm, 6.0*cm, 2.0*cm, 1.8*cm, 1.8*cm, 1.5*cm, gantt_col_width]
    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0d47a1")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (0,0), (0,-1), "CENTER"),
        ("ALIGN", (2,0), (5,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.whitesmoke, colors.white]),
    ]))
    elements.append(tbl)
    pdf.build(elements)
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
