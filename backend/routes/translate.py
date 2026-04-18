import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime
import os
import uuid

from database import db
from dependencies import get_current_user
from emergentintegrations.llm.chat import LlmChat, UserMessage

router = APIRouter()

EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")


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


async def call_llm(text: str, target_lang: str) -> str:
    if not text or not text.strip():
        return text
    chat = LlmChat(
        api_key=EMERGENT_KEY,
        session_id=f"translate-{uuid.uuid4().hex[:8]}",
        system_message=f"You are a professional translator. Translate the following text from Portuguese to {target_lang}. Keep the same formatting, bullet points, and line breaks. Only return the translated text, nothing else."
    ).with_model("openai", "gpt-4.1-mini")

    response = await chat.send_message(UserMessage(text=text))
    return response


async def translate_report(doc_id: str, target_lang: str, lang_code: str, current_user: dict):
    report = await db.reports.find_one({"_id": ObjectId(doc_id)})
    if not report:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")

    # Translate sections
    translated_sections = []
    for section in report.get("sections", []):
        translated_content = await call_llm(section.get("content", ""), target_lang)
        translated_title = await call_llm(section.get("title", ""), target_lang)
        new_section = {**section, "content": translated_content, "title": translated_title}
        # Translate subsections
        new_subsections = []
        for sub in section.get("subsections", []):
            t_sub_content = await call_llm(sub.get("content", ""), target_lang)
            t_sub_title = await call_llm(sub.get("title", ""), target_lang)
            new_sub = {**sub, "content": t_sub_content, "title": t_sub_title, "key": sub.get("key", "") + f"_{lang_code}"}
            # Translate nested subsections
            nested = []
            for nsub in sub.get("subsections", []):
                t_nsub_content = await call_llm(nsub.get("content", ""), target_lang)
                t_nsub_title = await call_llm(nsub.get("title", ""), target_lang)
                nested.append({**nsub, "content": t_nsub_content, "title": t_nsub_title, "key": nsub.get("key", "") + f"_{lang_code}"})
            new_sub["subsections"] = nested
            new_subsections.append(new_sub)
        new_section["subsections"] = new_subsections
        new_section["key"] = section.get("key", "") + f"_{lang_code}"
        translated_sections.append(new_section)

    # Translate daily entries
    translated_daily = []
    for entry in report.get("daily_entries", []):
        t_desc = await call_llm(entry.get("description", ""), target_lang)
        translated_daily.append({**entry, "description": t_desc, "id": str(uuid.uuid4().hex[:8])})

    # Create copy
    lang_label = {"en": "EN", "es": "ES"}.get(lang_code, lang_code.upper())
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

    # Translate text fields
    t_servico = await call_llm(proposal.get("servico", ""), target_lang)
    t_observacoes = await call_llm(proposal.get("observacoes", ""), target_lang)
    t_termos = await call_llm(proposal.get("termos_gerais", ""), target_lang)

    # Translate items descriptions
    translated_itens = []
    for item in proposal.get("itens", []):
        t_desc = await call_llm(item.get("descricao", ""), target_lang)
        new_item = {**item, "descricao": t_desc}
        # Translate subsections
        new_subs = []
        for sub in item.get("subsections", []):
            t_sub_desc = await call_llm(sub.get("descricao", ""), target_lang)
            new_subs.append({**sub, "descricao": t_sub_desc})
        new_item["subsections"] = new_subs
        translated_itens.append(new_item)

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

    # Translate observations and entry descriptions
    t_obs = await call_llm(ts.get("observations", ""), target_lang)

    translated_entries = []
    for entry in ts.get("entries", []):
        t_service_desc = await call_llm(entry.get("service_description", ""), target_lang)
        new_entry = {**entry, "service_description": t_service_desc}
        translated_entries.append(new_entry)

    lang_label = {"en": "EN", "es": "ES"}.get(lang_code, lang_code.upper())
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
