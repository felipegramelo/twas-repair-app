import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime
import os
import json
import re
import uuid

from database import db
from dependencies import get_current_user

router = APIRouter()



class TranslateRequest(BaseModel):
    document_id: str
    document_type: str  # "report", "timesheet", "proposal"
    target_language: str  # "en" or "es"


@router.post("/translate")
async def translate_document(data: TranslateRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    lang_map = {"en": "English", "es": "Spanish"}
    target_lang = lang_map.get(data.target_language)
    if not target_lang:
        raise HTTPException(status_code=400, detail="Idioma não suportado. Use 'en' ou 'es'.")

    if data.document_type == "report":
        return await translate_report(data.document_id, target_lang, data.target_language, current_user)
    elif data.document_type == "proposal":
        return await translate_proposal(data.document_id, target_lang, data.target_language, current_user)
    elif data.document_type == "timesheet":
        return await translate_timesheet(data.document_id, target_lang, data.target_language, current_user)
    else:
        raise HTTPException(status_code=400, detail="Tipo de documento não suportado.")


TRANSLATE_SYSTEM = (
    "You are a professional translator. You receive a JSON array of strings in Portuguese. "
    "Translate EACH string to {lang}. Return ONLY a JSON array with the same length and order. "
    "Preserve formatting: bullet points (•), line breaks (\\n) and **bold** markers. Do not add explanations."
)


async def translate_texts(texts: list, target_lang: str) -> list:
    """Translate many strings in few LLM calls (free Gemini tier allows ~5 req/min)."""
    from services.llm import generate_text
    result = list(texts)
    idx = [i for i, t in enumerate(texts) if isinstance(t, str) and t.strip()]
    batch_size = 40
    for b in range(0, len(idx), batch_size):
        chunk = idx[b:b + batch_size]
        payload = json.dumps([texts[i] for i in chunk], ensure_ascii=False)
        out = await generate_text(TRANSLATE_SYSTEM.format(lang=target_lang), payload, session_id=f"translate-{uuid.uuid4().hex[:8]}")
        m = re.search(r"\[[\s\S]*\]", out)
        parsed = json.loads(m.group(0)) if m else None
        if not isinstance(parsed, list) or len(parsed) != len(chunk):
            raise HTTPException(status_code=502, detail="A IA não retornou a tradução no formato esperado. Tente novamente.")
        for i, t in zip(chunk, parsed):
            result[i] = t if isinstance(t, str) else texts[i]
    return result


class _Batch:
    """Collect (container, field) pairs, translate all at once, then write back."""

    def __init__(self, target_lang: str):
        self.target_lang = target_lang
        self.refs = []

    def add(self, container: dict, field: str):
        self.refs.append((container, field))

    async def run(self):
        texts = [c.get(f, "") or "" for c, f in self.refs]
        translated = await translate_texts(texts, self.target_lang)
        for (c, f), t in zip(self.refs, translated):
            c[f] = t


async def translate_report(doc_id: str, target_lang: str, lang_code: str, current_user: dict):
    report = await db.reports.find_one({"_id": ObjectId(doc_id)})
    if not report:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")

    batch = _Batch(target_lang)
    translated_sections = []
    for section in report.get("sections", []):
        new_section = {**section, "key": section.get("key", "") + f"_{lang_code}"}
        batch.add(new_section, "content"); batch.add(new_section, "title")
        new_subsections = []
        for sub in section.get("subsections", []):
            new_sub = {**sub, "key": sub.get("key", "") + f"_{lang_code}"}
            batch.add(new_sub, "content"); batch.add(new_sub, "title")
            nested = []
            for nsub in sub.get("subsections", []):
                new_nsub = {**nsub, "key": nsub.get("key", "") + f"_{lang_code}"}
                batch.add(new_nsub, "content"); batch.add(new_nsub, "title")
                nested.append(new_nsub)
            new_sub["subsections"] = nested
            new_subsections.append(new_sub)
        new_section["subsections"] = new_subsections
        translated_sections.append(new_section)

    translated_daily = []
    for entry in report.get("daily_entries", []):
        new_entry = {**entry, "id": str(uuid.uuid4().hex[:8])}
        batch.add(new_entry, "description")
        translated_daily.append(new_entry)

    await batch.run()

    copy_doc = {
        "os_id": report.get("os_id", ""),
        "os_number": report.get("os_number", ""),
        "report_type": report.get("report_type", ""),
        "supervisor_id": current_user["_id"],
        "supervisor_name": current_user.get("name", ""),
        "sections": translated_sections,
        "daily_entries": translated_daily,
        "status": "draft",
        "shared_with": [],
        "translated_from": str(report["_id"]),
        "language": lang_code,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    result = await db.reports.insert_one(copy_doc)
    return {"id": str(result.inserted_id), "message": f"Relatório traduzido para {target_lang} com sucesso!"}


async def translate_proposal(doc_id: str, target_lang: str, lang_code: str, current_user: dict):
    proposal = await db.propostas.find_one({"_id": ObjectId(doc_id)})
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")

    batch = _Batch(target_lang)
    fields = {"servico": proposal.get("servico", ""), "observacoes": proposal.get("observacoes", ""), "termos_gerais": proposal.get("termos_gerais", "")}
    for f in fields:
        batch.add(fields, f)
    translated_itens = []
    for item in proposal.get("itens", []):
        new_item = {**item}
        batch.add(new_item, "descricao")
        new_subs = []
        for sub in item.get("subsections", []):
            new_sub = {**sub}
            batch.add(new_sub, "descricao")
            new_subs.append(new_sub)
        new_item["subsections"] = new_subs
        translated_itens.append(new_item)
    await batch.run()
    t_servico, t_observacoes, t_termos = fields["servico"], fields["observacoes"], fields["termos_gerais"]

    lang_label = {"en": "EN", "es": "ES"}.get(lang_code, lang_code.upper())
    
    # Get next proposal number
    count = await db.propostas.count_documents({})
    numero = f"P-{count + 1:04d}-{lang_label}"

    copy_doc = {
        "numero_proposta": numero,
        "empresa": proposal.get("empresa", ""),
        "contato": proposal.get("contato", ""),
        "email": proposal.get("email", ""),
        "embarcacao": proposal.get("embarcacao", ""),
        "local": proposal.get("local", ""),
        "equipamento": proposal.get("equipamento", ""),
        "servico": t_servico,
        "itens": translated_itens,
        "termos_gerais": t_termos,
        "observacoes": t_observacoes,
        # Preserve optional price/logistics tables (values stay the same — they are numbers)
        "show_price_table": proposal.get("show_price_table", False),
        "price_table_layout": proposal.get("price_table_layout", "rates"),
        "price_table_rows": proposal.get("price_table_rows", []),
        "show_logistics_table": proposal.get("show_logistics_table", False),
        "logistics_rows": proposal.get("logistics_rows", []),
        "status": "pendente",
        "po_number": "",
        "os_id": "",
        "os_number": "",
        "translated_from": str(proposal["_id"]),
        "language": lang_code,
        "created_by": current_user["_id"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    result = await db.propostas.insert_one(copy_doc)
    return {"id": str(result.inserted_id), "message": f"Proposta traduzida para {target_lang} com sucesso!"}


async def translate_timesheet(doc_id: str, target_lang: str, lang_code: str, current_user: dict):
    ts = await db.timesheets.find_one({"_id": ObjectId(doc_id)})
    if not ts:
        raise HTTPException(status_code=404, detail="Timesheet não encontrada")

    batch = _Batch(target_lang)
    obs_holder = {"observations": ts.get("observations", "")}
    batch.add(obs_holder, "observations")
    translated_entries = []
    for entry in ts.get("entries", []):
        new_entry = {**entry}
        batch.add(new_entry, "service_description")
        translated_entries.append(new_entry)
    await batch.run()
    t_obs = obs_holder["observations"]

    copy_doc = {
        "os_id": ts.get("os_id", ""),
        "os_number": ts.get("os_number", ""),
        "client": ts.get("client", ""),
        "location": ts.get("location", ""),
        "service": ts.get("service", ""),
        "supervisor_id": current_user["_id"],
        "supervisor_name": current_user.get("name", ""),
        "entries": translated_entries,
        "observations": t_obs,
        "status": "draft",
        "translated_from": str(ts["_id"]),
        "language": lang_code,
        "sequence_number": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    result = await db.timesheets.insert_one(copy_doc)
    return {"id": str(result.inserted_id), "message": f"Timesheet traduzida para {target_lang} com sucesso!"}
