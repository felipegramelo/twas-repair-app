from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPAuthorizationCredentials
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr
from bson import ObjectId
from datetime import datetime

from database import db
from config import verify_password, get_password_hash, create_access_token, SECRET_KEY, ALGORITHM
from dependencies import get_current_user, get_admin_user
from models import UserCreate, UserLogin, UserResponse, Token, UserRole

router = APIRouter()

@router.post("/auth/register", response_model=Token)
async def register(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user_dict = user_data.model_dump()
    user_dict["password_hash"] = get_password_hash(user_dict.pop("password"))
    user_dict["created_at"] = datetime.utcnow()
    
    result = await db.users.insert_one(user_dict)
    user_dict["_id"] = str(result.inserted_id)
    
    # Create token
    access_token = create_access_token(data={"sub": user_dict["_id"]})
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user_dict["_id"],
            email=user_dict["email"],
            role=user_dict["role"],
            name=user_dict["name"],
            bm_access=user_dict.get("bm_access", False),
            os_archive_access=user_dict.get("os_archive_access", False),
            proposta_access=user_dict.get("proposta_access", False),
            dashboard_access=user_dict.get("dashboard_access", False)
        )
    )


@router.post("/auth/login", response_model=Token)
async def login(user_data: UserLogin):
    user = await db.users.find_one({"email": user_data.email})
    if not user or not verify_password(user_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    user_id = str(user["_id"])
    access_token = create_access_token(data={"sub": user_id})
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user_id,
            email=user["email"],
            role=user["role"],
            name=user["name"],
            bm_access=user.get("bm_access", False),
            os_archive_access=user.get("os_archive_access", False),
            proposta_access=user.get("proposta_access", False),
            dashboard_access=user.get("dashboard_access", False)
        )
    )


@router.get("/auth/me")
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    return {
        "id": current_user["_id"],
        "email": current_user["email"],
        "role": current_user["role"],
        "name": current_user["name"],
        "bm_access": current_user.get("bm_access", False),
        "os_archive_access": current_user.get("os_archive_access", False),
        "proposta_access": current_user.get("proposta_access", False),
        "dashboard_access": current_user.get("dashboard_access", False),
    }


# ==================== USER MANAGEMENT ENDPOINTS (Admin only) ====================

class SupervisorCreate(BaseModel):
    email: EmailStr
    name: str
    password: str


class SupervisorUpdate(BaseModel):
    email: EmailStr
    name: str
    password: Optional[str] = None


@router.get("/users/supervisors", response_model=List[UserResponse])
async def get_supervisors(current_user: Dict[str, Any] = Depends(get_admin_user)):
    supervisors = await db.users.find({"role": UserRole.SUPERVISOR}, {"password_hash": 0}).sort("name", 1).to_list(100)
    return [UserResponse(
        id=str(user["_id"]),
        email=user["email"],
        role=user["role"],
        name=user["name"]
    ) for user in supervisors]


@router.post("/users/supervisors", response_model=UserResponse)
async def create_supervisor(supervisor_data: SupervisorCreate, current_user: Dict[str, Any] = Depends(get_admin_user)):
    # Check if user exists
    existing_user = await db.users.find_one({"email": supervisor_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    
    # Create supervisor
    user_dict = supervisor_data.model_dump()
    user_dict["password_hash"] = get_password_hash(user_dict.pop("password"))
    user_dict["role"] = UserRole.SUPERVISOR
    user_dict["created_at"] = datetime.utcnow()
    
    result = await db.users.insert_one(user_dict)
    user_dict["_id"] = str(result.inserted_id)
    
    return UserResponse(
        id=user_dict["_id"],
        email=user_dict["email"],
        role=user_dict["role"],
        name=user_dict["name"]
    )


@router.put("/users/supervisors/{user_id}", response_model=UserResponse)
async def update_supervisor(user_id: str, supervisor_data: SupervisorUpdate, current_user: Dict[str, Any] = Depends(get_admin_user)):
    # Check if user exists
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="Supervisor não encontrado")
    
    if user["role"] != UserRole.SUPERVISOR:
        raise HTTPException(status_code=400, detail="Usuário não é um supervisor")
    
    # Check if email is already taken by another user
    existing_user = await db.users.find_one({"email": supervisor_data.email, "_id": {"$ne": ObjectId(user_id)}})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email já cadastrado para outro usuário")
    
    # Update user
    update_dict = {
        "email": supervisor_data.email,
        "name": supervisor_data.name
    }
    
    if supervisor_data.password:
        update_dict["password_hash"] = get_password_hash(supervisor_data.password)
    
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_dict}
    )
    
    updated_user = await db.users.find_one({"_id": ObjectId(user_id)})
    
    return UserResponse(
        id=str(updated_user["_id"]),
        email=updated_user["email"],
        role=updated_user["role"],
        name=updated_user["name"]
    )


@router.delete("/users/supervisors/{user_id}")
async def delete_supervisor(user_id: str, current_user: Dict[str, Any] = Depends(get_admin_user)):
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="Supervisor não encontrado")
    
    if user["role"] != UserRole.SUPERVISOR:
        raise HTTPException(status_code=400, detail="Usuário não é um supervisor")
    
    # Check if supervisor has timesheets
    timesheets_count = await db.timesheets.count_documents({"supervisor_id": user_id})
    if timesheets_count > 0:
        raise HTTPException(status_code=400, detail=f"Não é possível excluir. Supervisor possui {timesheets_count} timesheet(s) cadastrado(s)")
    
    await db.users.delete_one({"_id": ObjectId(user_id)})
    return {"message": "Supervisor excluído com sucesso"}


# ==================== CHANGE PASSWORD ENDPOINT ====================

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

@router.put("/auth/change-password")
async def change_password(data: ChangePasswordRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    if not verify_password(data.current_password, current_user["password_hash"]):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="A nova senha deve ter no mínimo 6 caracteres")
    await db.users.update_one(
        {"_id": ObjectId(current_user["_id"])},
        {"$set": {"password_hash": get_password_hash(data.new_password)}}
    )
    return {"message": "Senha alterada com sucesso"}


class AdminResetPasswordRequest(BaseModel):
    new_password: str


@router.put("/admin/reset-password/{user_id}")
async def admin_reset_password(user_id: str, data: AdminResetPasswordRequest, current_user: Dict[str, Any] = Depends(get_admin_user)):
    """Admin resets any user's password without knowing the current one."""
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="A nova senha deve ter no mínimo 6 caracteres")
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"password_hash": get_password_hash(data.new_password)}}
    )
    return {"message": "Senha redefinida com sucesso"}


# ==================== ADMIN MANAGEMENT ENDPOINTS ====================

@router.get("/users/admins", response_model=List[UserResponse])
async def get_admins(current_user: Dict[str, Any] = Depends(get_admin_user)):
    admins = await db.users.find({"role": UserRole.ADMIN}, {"password_hash": 0}).sort("name", 1).to_list(100)
    return [UserResponse(
        id=str(user["_id"]),
        email=user["email"],
        role=user["role"],
        name=user["name"],
        bm_access=user.get("bm_access", False),
        os_archive_access=user.get("os_archive_access", False),
        proposta_access=user.get("proposta_access", False),
        dashboard_access=user.get("dashboard_access", False)
    ) for user in admins]


@router.post("/users/admins", response_model=UserResponse)
async def create_admin(admin_data: SupervisorCreate, current_user: Dict[str, Any] = Depends(get_admin_user)):
    existing_user = await db.users.find_one({"email": admin_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    user_dict = admin_data.model_dump()
    user_dict["password_hash"] = get_password_hash(user_dict.pop("password"))
    user_dict["role"] = UserRole.ADMIN
    user_dict["created_at"] = datetime.utcnow()
    user_dict["bm_access"] = False
    user_dict["os_archive_access"] = False
    user_dict["proposta_access"] = False
    user_dict["dashboard_access"] = False
    result = await db.users.insert_one(user_dict)
    return UserResponse(
        id=str(result.inserted_id),
        email=user_dict["email"],
        role=user_dict["role"],
        name=user_dict["name"],
        bm_access=False,
        os_archive_access=False,
        proposta_access=False,
        dashboard_access=False
    )


@router.put("/users/admins/{user_id}", response_model=UserResponse)
async def update_admin(user_id: str, admin_data: SupervisorUpdate, current_user: Dict[str, Any] = Depends(get_admin_user)):
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="Administrador não encontrado")
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=400, detail="Usuário não é um administrador")
    existing_user = await db.users.find_one({"email": admin_data.email, "_id": {"$ne": ObjectId(user_id)}})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email já cadastrado para outro usuário")
    update_dict = {"email": admin_data.email, "name": admin_data.name}
    if admin_data.password:
        update_dict["password_hash"] = get_password_hash(admin_data.password)
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": update_dict})
    updated_user = await db.users.find_one({"_id": ObjectId(user_id)})
    return UserResponse(
        id=str(updated_user["_id"]),
        email=updated_user["email"],
        role=updated_user["role"],
        name=updated_user["name"],
        bm_access=updated_user.get("bm_access", False),
        os_archive_access=updated_user.get("os_archive_access", False),
        proposta_access=updated_user.get("proposta_access", False),
        dashboard_access=updated_user.get("dashboard_access", False)
    )


@router.delete("/users/admins/{user_id}")
async def delete_admin(user_id: str, current_user: Dict[str, Any] = Depends(get_admin_user)):
    if user_id == current_user["_id"]:
        raise HTTPException(status_code=400, detail="Você não pode excluir sua própria conta")
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="Administrador não encontrado")
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=400, detail="Usuário não é um administrador")
    await db.users.delete_one({"_id": ObjectId(user_id)})
    return {"message": "Administrador excluído com sucesso"}


