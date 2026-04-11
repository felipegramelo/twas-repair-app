from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from bson import ObjectId

from database import db
from dependencies import get_current_user
from models import ShareDocumentRequest, UnshareDocumentRequest, UserRole

router = APIRouter()

# ==================== DOCUMENT SHARING (ADMIN ONLY) ====================

@router.post("/admin/share-document")
async def share_document(data: ShareDocumentRequest, user: dict = Depends(get_current_user)):
    if user.get("role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Apenas administradores podem compartilhar documentos")
    collection = db.reports if data.document_type == "report" else db.timesheets
    doc = await collection.find_one({"_id": ObjectId(data.document_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    await collection.update_one(
        {"_id": ObjectId(data.document_id)},
        {"$addToSet": {"shared_with": {"$each": data.supervisor_ids}}}
    )
    return {"success": True, "message": "Documento compartilhado com sucesso"}


@router.post("/admin/unshare-document")
async def unshare_document(data: UnshareDocumentRequest, user: dict = Depends(get_current_user)):
    if user.get("role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Apenas administradores podem remover compartilhamento")
    collection = db.reports if data.document_type == "report" else db.timesheets
    await collection.update_one(
        {"_id": ObjectId(data.document_id)},
        {"$pull": {"shared_with": {"$in": data.supervisor_ids}}}
    )
    return {"success": True, "message": "Compartilhamento removido"}


@router.get("/admin/document-shares/{document_type}/{document_id}")
async def get_document_shares(document_type: str, document_id: str, user: dict = Depends(get_current_user)):
    if user.get("role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Acesso negado")
    collection = db.reports if document_type == "report" else db.timesheets
    doc = await collection.find_one({"_id": ObjectId(document_id)}, {"shared_with": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    return {"shared_with": doc.get("shared_with", [])}


# ==================== PHOTO UPLOAD ====================

