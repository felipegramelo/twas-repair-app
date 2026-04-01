from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File, Query, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse, Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from passlib.context import CryptContext
import jwt
import os
import logging
import httpx
import requests
import uuid
from pathlib import Path
from bson import ObjectId
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage, PageBreak, Frame, PageTemplate, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
import io
from PIL import Image as PILImage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
security = HTTPBearer()

# Object Storage
STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
APP_NAME = "twas-repair"
_storage_key = None

def init_storage():
    global _storage_key
    if _storage_key:
        return _storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key

def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data, timeout=120
    )
    resp.raise_for_status()
    return resp.json()

def get_object(path: str):
    key = init_storage()
    resp = requests.get(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key}, timeout=60
    )
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")

# Create the main app
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# ==================== MODELS ====================

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, schema):
        schema.update(type="string")
        return schema


class UserRole(str):
    ADMIN = "admin"
    SUPERVISOR = "supervisor"


class User(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    email: EmailStr
    password_hash: str
    role: str  # "admin" or "supervisor"
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str
    name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    name: str
    bm_access: Optional[bool] = False
    os_archive_access: Optional[bool] = False
    proposta_access: Optional[bool] = False


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class Employee(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}


class EmployeeCreate(BaseModel):
    name: str


class SOEmployee(BaseModel):
    employee_id: str
    function: str  # E, EN, Sup, T, M, TS


class ServiceOrder(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    os_number: str
    client: str
    location: str
    embarcacao: Optional[str] = ""
    service: str
    employees: List[SOEmployee] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}


class ServiceOrderCreate(BaseModel):
    os_number: str
    client: str
    location: str
    embarcacao: Optional[str] = ""
    service: str
    employees: List[SOEmployee] = []
    schedule_type: Optional[str] = "07-19"


class TimesheetEntry(BaseModel):
    date: str  # DD/MM/YYYY
    employee_id: str
    employee_name: str
    employee_function: str
    service_start: str  # HH:MM
    service_end: str  # HH:MM
    travel_start: Optional[str] = ""  # HH:MM
    travel_end: Optional[str] = ""  # HH:MM


class Timesheet(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    os_id: str
    os_number: str
    client: str
    location: str
    service: str
    entries: List[TimesheetEntry]
    observations: Optional[str] = ""
    supervisor_id: str
    supervisor_name: str
    supervisor_function: Optional[str] = "Supervisor"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}


class TimesheetCreate(BaseModel):
    os_id: str
    entries: List[TimesheetEntry]
    observations: Optional[str] = ""
    supervisor_function: Optional[str] = "Supervisor"


# ==================== REPORT MODELS ====================

class ReportCreate(BaseModel):
    report_type: str  # "service" or "daily"
    os_id: str
    periodo_inicio: Optional[str] = ""
    periodo_fim: Optional[str] = ""
    executado_por: Optional[str] = ""


class ReportSectionData(BaseModel):
    key: str
    number: str
    title: str
    content: Optional[str] = ""
    enabled: bool = True
    subsections: Optional[List[dict]] = []


class ReportUpdate(BaseModel):
    periodo_inicio: Optional[str] = None
    periodo_fim: Optional[str] = None
    executado_por: Optional[str] = None
    oc_wo: Optional[str] = None
    sections: Optional[List[dict]] = None
    status: Optional[str] = None
    daily_entries: Optional[List[dict]] = None


class ReportResponse(BaseModel):
    id: str
    report_type: str
    os_id: str
    os_number: str
    client: str
    location: str
    service: str
    supervisor_id: str
    supervisor_name: str
    periodo: str
    executado_por: str
    status: str
    created_at: str
    updated_at: str


# ==================== AUTH FUNCTIONS ====================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        
        user["_id"] = str(user["_id"])
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")


async def get_admin_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if current_user.get("role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# ==================== AUTH ENDPOINTS ====================

@api_router.post("/auth/register", response_model=Token)
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
            proposta_access=user_dict.get("proposta_access", False)
        )
    )


@api_router.post("/auth/login", response_model=Token)
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
            proposta_access=user.get("proposta_access", False)
        )
    )


@api_router.get("/auth/me")
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    return {
        "id": current_user["_id"],
        "email": current_user["email"],
        "role": current_user["role"],
        "name": current_user["name"],
        "bm_access": current_user.get("bm_access", False),
        "os_archive_access": current_user.get("os_archive_access", False),
        "proposta_access": current_user.get("proposta_access", False),
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


@api_router.get("/users/supervisors", response_model=List[UserResponse])
async def get_supervisors(current_user: Dict[str, Any] = Depends(get_admin_user)):
    supervisors = await db.users.find({"role": UserRole.SUPERVISOR}, {"password_hash": 0}).sort("name", 1).to_list(100)
    return [UserResponse(
        id=str(user["_id"]),
        email=user["email"],
        role=user["role"],
        name=user["name"]
    ) for user in supervisors]


@api_router.post("/users/supervisors", response_model=UserResponse)
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


@api_router.put("/users/supervisors/{user_id}", response_model=UserResponse)
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


@api_router.delete("/users/supervisors/{user_id}")
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

@api_router.put("/auth/change-password")
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


# ==================== ADMIN MANAGEMENT ENDPOINTS ====================

@api_router.get("/users/admins", response_model=List[UserResponse])
async def get_admins(current_user: Dict[str, Any] = Depends(get_admin_user)):
    admins = await db.users.find({"role": UserRole.ADMIN}, {"password_hash": 0}).sort("name", 1).to_list(100)
    return [UserResponse(
        id=str(user["_id"]),
        email=user["email"],
        role=user["role"],
        name=user["name"],
        bm_access=user.get("bm_access", False),
        os_archive_access=user.get("os_archive_access", False),
        proposta_access=user.get("proposta_access", False)
    ) for user in admins]


@api_router.post("/users/admins", response_model=UserResponse)
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
    result = await db.users.insert_one(user_dict)
    return UserResponse(
        id=str(result.inserted_id),
        email=user_dict["email"],
        role=user_dict["role"],
        name=user_dict["name"],
        bm_access=False,
        os_archive_access=False,
        proposta_access=False
    )


@api_router.put("/users/admins/{user_id}", response_model=UserResponse)
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
        proposta_access=updated_user.get("proposta_access", False)
    )


@api_router.delete("/users/admins/{user_id}")
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


# ==================== EMPLOYEE ENDPOINTS (Admin only) ====================

@api_router.post("/employees", response_model=Employee)
async def create_employee(employee_data: EmployeeCreate, current_user: Dict[str, Any] = Depends(get_admin_user)):
    employee_dict = employee_data.model_dump()
    employee_dict["created_at"] = datetime.utcnow()
    
    result = await db.employees.insert_one(employee_dict)
    employee_dict["_id"] = str(result.inserted_id)
    
    return Employee(**employee_dict)


@api_router.get("/employees", response_model=List[dict])
async def get_employees(current_user: Dict[str, Any] = Depends(get_current_user)):
    employees = await db.employees.find().sort("name", 1).to_list(500)
    for emp in employees:
        emp["id"] = str(emp.pop("_id"))
    return employees


@api_router.get("/employees/{employee_id}", response_model=dict)
async def get_employee(employee_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    employee = await db.employees.find_one({"_id": ObjectId(employee_id)})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    employee["id"] = str(employee.pop("_id"))
    return employee


@api_router.put("/employees/{employee_id}", response_model=Employee)
async def update_employee(employee_id: str, employee_data: EmployeeCreate, current_user: Dict[str, Any] = Depends(get_admin_user)):
    employee_dict = employee_data.model_dump()
    
    result = await db.employees.update_one(
        {"_id": ObjectId(employee_id)},
        {"$set": employee_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    updated_employee = await db.employees.find_one({"_id": ObjectId(employee_id)})
    updated_employee["_id"] = str(updated_employee["_id"])
    return Employee(**updated_employee)


@api_router.delete("/employees/{employee_id}")
async def delete_employee(employee_id: str, current_user: Dict[str, Any] = Depends(get_admin_user)):
    result = await db.employees.delete_one({"_id": ObjectId(employee_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Employee not found")
    return {"message": "Employee deleted successfully"}


# ==================== SERVICE ORDER ENDPOINTS (Admin only) ====================

@api_router.post("/service-orders", response_model=ServiceOrder)
async def create_service_order(so_data: ServiceOrderCreate, current_user: Dict[str, Any] = Depends(get_admin_user)):
    so_dict = so_data.model_dump()
    so_dict["created_at"] = datetime.utcnow()
    
    result = await db.service_orders.insert_one(so_dict)
    so_dict["_id"] = str(result.inserted_id)
    
    return ServiceOrder(**so_dict)


@api_router.get("/service-orders", response_model=List[dict])
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


@api_router.get("/service-orders/{so_id}", response_model=dict)
async def get_service_order(so_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    so = await db.service_orders.find_one({"_id": ObjectId(so_id)})
    if not so:
        raise HTTPException(status_code=404, detail="Service Order not found")
    so["id"] = str(so.pop("_id"))
    return so


@api_router.put("/service-orders/{so_id}", response_model=ServiceOrder)
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


@api_router.delete("/service-orders/{so_id}")
async def delete_service_order(so_id: str, current_user: Dict[str, Any] = Depends(get_admin_user)):
    result = await db.service_orders.delete_one({"_id": ObjectId(so_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Service Order not found")
    return {"message": "Service Order deleted successfully"}



# ==================== OS ARCHIVE ENDPOINT ====================

@api_router.get("/admin/os-archive")
async def get_os_archive(current_user: Dict[str, Any] = Depends(get_admin_user)):
    """Get all service orders with their related documents (timesheets + reports)"""
    service_orders = await db.service_orders.find().sort("os_number", 1).to_list(500)
    
    result = []
    for so in service_orders:
        so_id = str(so["_id"])
        
        # Get timesheets for this OS (only finalized ones for admin archive)
        timesheets = await db.timesheets.find({"os_id": so_id, "status": "finalized"}).sort("created_at", -1).to_list(100)
        ts_list = []
        for ts in timesheets:
            ts["id"] = str(ts.pop("_id"))
            ts.pop("_id", None)
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



# ==================== BM ACCESS CONTROL ====================

async def get_bm_admin_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if current_user.get("role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    if not current_user.get("bm_access", False):
        raise HTTPException(status_code=403, detail="Acesso ao Boletim de Medição não autorizado")
    return current_user

# ==================== CLIENT PRICE TABLE ENDPOINTS ====================

class ClientPriceEntry(BaseModel):
    function_code: str
    function_name: str
    day_rate: float
    night_rate: float

class ClientPriceTableCreate(BaseModel):
    client_name: str
    prices: List[ClientPriceEntry]

@api_router.get("/client-prices")
async def get_client_prices(current_user: Dict[str, Any] = Depends(get_bm_admin_user)):
    tables = await db.client_prices.find().sort("client_name", 1).to_list(100)
    for t in tables:
        t["id"] = str(t.pop("_id"))
        t.pop("_id", None)
    return tables

@api_router.post("/client-prices")
async def create_client_price(data: ClientPriceTableCreate, current_user: Dict[str, Any] = Depends(get_bm_admin_user)):
    doc = data.model_dump()
    doc["created_at"] = datetime.utcnow()
    result = await db.client_prices.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    doc.pop("_id", None)
    doc["created_at"] = doc["created_at"].isoformat()
    return doc

@api_router.put("/client-prices/{price_id}")
async def update_client_price(price_id: str, data: ClientPriceTableCreate, current_user: Dict[str, Any] = Depends(get_bm_admin_user)):
    result = await db.client_prices.update_one(
        {"_id": ObjectId(price_id)},
        {"$set": data.model_dump()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Tabela não encontrada")
    return {"message": "Atualizado com sucesso"}

@api_router.delete("/client-prices/{price_id}")
async def delete_client_price(price_id: str, current_user: Dict[str, Any] = Depends(get_bm_admin_user)):
    result = await db.client_prices.delete_one({"_id": ObjectId(price_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Tabela não encontrada")
    return {"message": "Excluído com sucesso"}

# ==================== BM CALCULATION ====================

FUNCTION_NAMES = {
    "E": "ENGENHEIRO",
    "EN": "ENCARREGADO",
    "Sup": "SUPERVISOR",
    "T": "TÉCNICO",
    "M": "MECÂNICO",
    "TS": "TÉCNICO DE SEGURANÇA",
}

def parse_date_sortable(d: str) -> str:
    try:
        parts = d.split("/")
        if len(parts) == 3:
            return f"{parts[2]}-{parts[1]}-{parts[0]}"
    except:
        pass
    return d

@api_router.get("/bm/timesheets/{os_id}")
async def list_timesheets_for_bm(os_id: str, current_user: Dict[str, Any] = Depends(get_bm_admin_user)):
    """List available timesheets for a specific OS so user can select which to include in BM."""
    so = await db.service_orders.find_one({"_id": ObjectId(os_id)})
    if not so:
        raise HTTPException(status_code=404, detail="O.S. não encontrada")
    timesheets = await db.timesheets.find({"os_id": os_id}).to_list(500)
    result = []
    for ts in timesheets:
        entries = ts.get("entries", [])
        dates = sorted(set(e.get("date", "") for e in entries if e.get("date")), key=parse_date_sortable)
        employees = sorted(set(e.get("employee_name", "") for e in entries if e.get("employee_name")))
        result.append({
            "id": str(ts["_id"]),
            "os_number": ts.get("os_number", ""),
            "supervisor_name": ts.get("supervisor_name", ""),
            "entries_count": len(entries),
            "dates": dates,
            "date_range": f"{dates[0]} - {dates[-1]}" if dates else "",
            "employees": employees,
            "created_at": str(ts.get("created_at", "")),
        })
    return result


class BMCalculateRequest(BaseModel):
    timesheet_ids: List[str] = []
    data_inicio: str = ""
    data_fim: str = ""


@api_router.post("/bm/calculate/{os_id}")
async def calculate_bm(os_id: str, body: BMCalculateRequest, current_user: Dict[str, Any] = Depends(get_bm_admin_user)):
    so = await db.service_orders.find_one({"_id": ObjectId(os_id)})
    if not so:
        raise HTTPException(status_code=404, detail="O.S. não encontrada")

    schedule_type = so.get("schedule_type", "07-19")
    if schedule_type == "06-18":
        day_start, day_end = 6, 18
    else:
        day_start, day_end = 7, 19

    # Fetch only selected timesheets or all if none specified
    if body.timesheet_ids:
        ts_object_ids = [ObjectId(tid) for tid in body.timesheet_ids]
        timesheets = await db.timesheets.find({"_id": {"$in": ts_object_ids}, "os_id": os_id}).to_list(500)
    else:
        timesheets = await db.timesheets.find({"os_id": os_id}).to_list(500)

    # Parse date filters if provided
    date_filter_start = None
    date_filter_end = None
    if body.data_inicio:
        date_filter_start = parse_date_sortable(body.data_inicio)
    if body.data_fim:
        date_filter_end = parse_date_sortable(body.data_fim)

    # Count unique employee+date per function per shift
    function_days = {}
    all_dates = []

    for ts in timesheets:
        for entry in ts.get("entries", []):
            func = entry.get("employee_function", "T")
            date = entry.get("date", "")
            start_str = entry.get("service_start", "")
            if not start_str or not date:
                continue
            # Apply date filter
            if date_filter_start or date_filter_end:
                date_sortable = parse_date_sortable(date)
                if date_filter_start and date_sortable < date_filter_start:
                    continue
                if date_filter_end and date_sortable > date_filter_end:
                    continue
            all_dates.append(date)
            try:
                start_hour = int(start_str.split(":")[0])
            except:
                continue
            is_day = day_start <= start_hour < day_end
            shift = "day" if is_day else "night"
            key = f"{func}_{shift}"
            if key not in function_days:
                function_days[key] = set()
            emp_date = f"{entry.get('employee_id', '')}_{date}"
            function_days[key].add(emp_date)

    # Sort dates
    sorted_dates = sorted(set(all_dates), key=parse_date_sortable)
    # Use user-provided dates or auto-detect from data
    data_inicial = body.data_inicio if body.data_inicio else (sorted_dates[0] if sorted_dates else "")
    data_final = body.data_fim if body.data_fim else (sorted_dates[-1] if sorted_dates else "")

    # Get client prices
    client_name = so.get("client", "")
    price_table = await db.client_prices.find_one({"client_name": client_name})

    items = []
    for key in sorted(function_days.keys()):
        dates_set = function_days[key]
        func_code, shift = key.rsplit("_", 1)
        func_name = FUNCTION_NAMES.get(func_code, func_code)
        qtd = len(dates_set)
        rate = 0.0
        if price_table:
            for p in price_table.get("prices", []):
                if p["function_code"] == func_code:
                    day_rate = p.get("day_rate", 0)
                    if shift == "day":
                        rate = day_rate
                    else:
                        rate = round(day_rate * 1.2, 2)  # Noturno = diurno + 20%
                    break
        display_name = func_name if shift == "day" else f"{func_name} (NOTURNO)"
        items.append({
            "function_code": func_code,
            "function_name": display_name,
            "shift": shift,
            "data_inicial": data_inicial,
            "data_final": data_final,
            "valor_und": rate,
            "qtd": qtd,
            "valor_total": round(rate * qtd, 2),
        })

    subtotal = sum(item["valor_total"] for item in items)
    return {
        "os_id": os_id,
        "os_number": so.get("os_number", ""),
        "client": client_name,
        "location": so.get("location", ""),
        "service": so.get("service", ""),
        "schedule_type": schedule_type,
        "data_inicial": data_inicial,
        "data_final": data_final,
        "items": items,
        "subtotal": round(subtotal, 2),
        "has_price_table": price_table is not None,
    }

# ==================== BM CRUD ====================

class BMCreate(BaseModel):
    os_id: str
    periodo: str = ""
    data: str = ""
    rev: str = "0"
    po_number: str = ""
    proposta: str = ""
    cod: str = ""
    items: List[dict]
    subtotal: float
    impostos: float = 0.0
    valor_total: float

@api_router.post("/bm")
async def create_bm(data: BMCreate, current_user: Dict[str, Any] = Depends(get_bm_admin_user)):
    so = await db.service_orders.find_one({"_id": ObjectId(data.os_id)})
    if not so:
        raise HTTPException(status_code=404, detail="O.S. não encontrada")
    doc = data.model_dump()
    doc["os_number"] = so.get("os_number", "")
    doc["client"] = so.get("client", "")
    doc["location"] = so.get("location", "")
    doc["service"] = so.get("service", "")
    doc["created_by"] = current_user["_id"]
    doc["created_at"] = datetime.utcnow()
    doc["updated_at"] = datetime.utcnow()
    result = await db.boletins_medicao.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    doc.pop("_id", None)
    doc["created_at"] = doc["created_at"].isoformat()
    doc["updated_at"] = doc["updated_at"].isoformat()
    return doc

@api_router.get("/bm")
async def list_bm(current_user: Dict[str, Any] = Depends(get_bm_admin_user)):
    bms = await db.boletins_medicao.find().sort("created_at", -1).to_list(500)
    for bm in bms:
        bm["id"] = str(bm.pop("_id"))
        bm.pop("_id", None)
        for field in ["created_at", "updated_at"]:
            val = bm.get(field, "")
            bm[field] = val.isoformat() if hasattr(val, "isoformat") else str(val)
    return bms

@api_router.get("/bm/{bm_id}")
async def get_bm_detail(bm_id: str, current_user: Dict[str, Any] = Depends(get_bm_admin_user)):
    bm = await db.boletins_medicao.find_one({"_id": ObjectId(bm_id)})
    if not bm:
        raise HTTPException(status_code=404, detail="BM não encontrado")
    bm["id"] = str(bm.pop("_id"))
    bm.pop("_id", None)
    for field in ["created_at", "updated_at"]:
        val = bm.get(field, "")
        bm[field] = val.isoformat() if hasattr(val, "isoformat") else str(val)
    return bm

@api_router.delete("/bm/{bm_id}")
async def delete_bm(bm_id: str, current_user: Dict[str, Any] = Depends(get_bm_admin_user)):
    result = await db.boletins_medicao.delete_one({"_id": ObjectId(bm_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="BM não encontrado")
    return {"message": "BM excluído com sucesso"}


@api_router.put("/bm/{bm_id}")
async def update_bm(bm_id: str, data: BMCreate, current_user: Dict[str, Any] = Depends(get_bm_admin_user)):
    existing = await db.boletins_medicao.find_one({"_id": ObjectId(bm_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="BM não encontrado")
    so = await db.service_orders.find_one({"_id": ObjectId(data.os_id)})
    if not so:
        raise HTTPException(status_code=404, detail="O.S. não encontrada")
    update_doc = data.model_dump()
    update_doc["os_number"] = so.get("os_number", "")
    update_doc["client"] = so.get("client", "")
    update_doc["location"] = so.get("location", "")
    update_doc["service"] = so.get("service", "")
    update_doc["updated_at"] = datetime.utcnow()
    await db.boletins_medicao.update_one({"_id": ObjectId(bm_id)}, {"$set": update_doc})
    update_doc["id"] = bm_id
    update_doc["updated_at"] = update_doc["updated_at"].isoformat()
    return update_doc
    return {"message": "BM excluído com sucesso"}

# ==================== BM ACCESS MANAGEMENT ====================

@api_router.put("/users/admins/{user_id}/bm-access")
async def toggle_bm_access(user_id: str, current_user: Dict[str, Any] = Depends(get_admin_user)):
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user or user.get("role") != UserRole.ADMIN:
        raise HTTPException(status_code=404, detail="Administrador não encontrado")
    new_access = not user.get("bm_access", False)
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"bm_access": new_access}})
    return {"bm_access": new_access}

@api_router.put("/users/admins/{user_id}/os-archive-access")
async def toggle_os_archive_access(user_id: str, current_user: Dict[str, Any] = Depends(get_admin_user)):
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user or user.get("role") != UserRole.ADMIN:
        raise HTTPException(status_code=404, detail="Administrador não encontrado")
    new_access = not user.get("os_archive_access", False)
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"os_archive_access": new_access}})
    return {"os_archive_access": new_access}

@api_router.put("/users/admins/{user_id}/proposta-access")
async def toggle_proposta_access(user_id: str, current_user: Dict[str, Any] = Depends(get_admin_user)):
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user or user.get("role") != UserRole.ADMIN:
        raise HTTPException(status_code=404, detail="Administrador não encontrado")
    new_access = not user.get("proposta_access", False)
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"proposta_access": new_access}})
    return {"proposta_access": new_access}

# ==================== BM PDF GENERATION ====================

def format_currency(value: float) -> str:
    formatted = f"{value:,.2f}"
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"

@api_router.get("/bm/{bm_id}/pdf")
async def generate_bm_pdf(bm_id: str, token: Optional[str] = Query(None), credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))):
    # Auth via token query param or header
    actual_token = token
    if not actual_token and credentials:
        actual_token = credentials.credentials
    if not actual_token:
        raise HTTPException(status_code=401, detail="Token required")
    try:
        payload = jwt.decode(actual_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user or user.get("role") != UserRole.ADMIN or not user.get("bm_access", False):
            raise HTTPException(status_code=403, detail="Acesso negado")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

    bm = await db.boletins_medicao.find_one({"_id": ObjectId(bm_id)})
    if not bm:
        raise HTTPException(status_code=404, detail="BM não encontrado")

    buf = io.BytesIO()
    page_w, page_h = A4[1], A4[0]  # Landscape
    border_margin = 1.0 * cm
    border_color = colors.HexColor('#AAAAAA')
    
    content_left = border_margin + 0.3 * cm
    content_right = border_margin + 0.3 * cm
    content_width = page_w - content_left - content_right
    
    page_counter = [0]
    
    def draw_bm_page(canvas_obj, doc_obj, page_num):
        canvas_obj.saveState()
        
        # === PAGE BORDER ===
        canvas_obj.setStrokeColor(border_color)
        canvas_obj.setLineWidth(1)
        canvas_obj.rect(border_margin, border_margin, page_w - 2 * border_margin, page_h - 2 * border_margin)
        
        # === HEADER BOX ===
        header_top = page_h - border_margin - 0.5 * cm
        header_height = 2.0 * cm
        header_bottom = header_top - header_height
        canvas_obj.setStrokeColor(colors.HexColor('#777777'))
        canvas_obj.setLineWidth(0.5)
        canvas_obj.rect(content_left, header_bottom, content_width, header_height)
        
        # Logo
        logo_path = ROOT_DIR / "../logo.bmp"
        if logo_path.exists():
            try:
                from reportlab.lib.utils import ImageReader
                pil_img = PILImage.open(logo_path)
                temp_logo = io.BytesIO()
                pil_img.save(temp_logo, format='JPEG')
                temp_logo.seek(0)
                logo_w = 4.0 * cm
                logo_h = 1.4 * cm
                canvas_obj.drawImage(ImageReader(temp_logo), content_left + 0.3 * cm, header_bottom + (header_height - logo_h) / 2, width=logo_w, height=logo_h, preserveAspectRatio=True, mask='auto')
            except Exception:
                pass
        
        # Vertical line after logo
        sep_x = content_left + 4.6 * cm
        canvas_obj.line(sep_x, header_bottom, sep_x, header_top)
        
        # Title "BOLETIM DE MEDIÇÃO" - centered between logo separator and right side info
        right_info_width = 3.5 * cm
        title_area_start = sep_x
        title_area_end = content_left + content_width - right_info_width
        title_x = title_area_start + (title_area_end - title_area_start) / 2
        canvas_obj.setFont("Helvetica-Bold", 11)
        canvas_obj.drawCentredString(title_x, header_top - 0.6 * cm, "BOLETIM DE MEDIÇÃO")
        canvas_obj.setFont("Helvetica", 7)
        canvas_obj.drawCentredString(title_x, header_top - 0.95 * cm, "Anexo 02_formulário - Boletim de Medição")
        
        # Right side details
        detail_x = page_w - content_right - 0.3 * cm
        line_h = 0.32 * cm
        detail_y = header_top - 0.4 * cm
        
        def _draw_right_label(label, value, y):
            canvas_obj.setFont("Helvetica-Bold", 7)
            canvas_obj.drawRightString(detail_x, y, f"{label} {value}")
        
        _draw_right_label("Data:", bm.get('data', ''), detail_y)
        detail_y -= line_h
        _draw_right_label("Rev.:", bm.get('rev', '0'), detail_y)
        detail_y -= line_h
        _draw_right_label("Período:", bm.get('periodo', ''), detail_y)
        detail_y -= line_h
        _draw_right_label("OS:", bm.get('os_number', ''), detail_y)
        
        # === FOOTER BOX ===
        footer_bottom = border_margin + 0.5 * cm
        footer_height = 1.4 * cm
        footer_top = footer_bottom + footer_height
        canvas_obj.setStrokeColor(colors.HexColor('#777777'))
        canvas_obj.setLineWidth(0.5)
        canvas_obj.rect(content_left, footer_bottom, content_width, footer_height)
        
        center_x = page_w / 2
        y = footer_top - 0.45 * cm
        canvas_obj.setFont("Helvetica-Bold", 8)
        canvas_obj.drawCentredString(center_x, y, "TWAS REPAIR SERVIÇOS NAVAIS E INDUSTRIAIS LTDA")
        y -= 0.3 * cm
        canvas_obj.setFont("Helvetica", 7)
        canvas_obj.drawCentredString(center_x, y, "Travessa Frederico Marques, N\u00b0 84, Boa Vista, São Gonçalo, Rio de Janeiro - CEP.: 24.466-180.")
        y -= 0.28 * cm
        canvas_obj.drawCentredString(center_x, y, "twas@twasrepair.com - www.twasrepair.com")
        
        # Page number
        canvas_obj.setFont("Helvetica", 7)
        canvas_obj.drawRightString(page_w - border_margin - 0.5 * cm, border_margin + 0.2 * cm, f"{page_num}")
        
        canvas_obj.restoreState()
    
    def on_first_page_bm(c, d):
        page_counter[0] = 1
        draw_bm_page(c, d, 1)
    
    def on_later_pages_bm(c, d):
        page_counter[0] += 1
        draw_bm_page(c, d, page_counter[0])
    
    doc = SimpleDocTemplate(
        buf, pagesize=(page_w, page_h),
        topMargin=border_margin + 2.8 * cm,
        bottomMargin=border_margin + 2.1 * cm,
        leftMargin=content_left,
        rightMargin=content_right,
    )
    styles = getSampleStyleSheet()
    elements = []

    # ---- CLIENT INFO ----
    client_style = ParagraphStyle('ClientInfo', fontSize=9, leading=12, textColor=colors.black)
    client_info = Table([
        [Paragraph(f"<b>Cliente:</b> {bm.get('client', '')}", client_style),
         Paragraph(f"<b>P.O.:</b> {bm.get('po_number', '')}", client_style),
         Paragraph(f"<b>Proposta:</b> {bm.get('proposta', '')}", client_style)]
    ], colWidths=[content_width * 0.4, content_width * 0.3, content_width * 0.3])
    client_info.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 0.5, border_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDDDDD')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(client_info)
    elements.append(Spacer(1, 6))

    # ---- SERVICE SCOPE ----
    scope_style = ParagraphStyle('ScopeStyle', fontSize=9, fontName='Helvetica-Bold', textColor=colors.black)
    scope_table = Table([
        [Paragraph("<b>ESCOPO DE SERVIÇOS:</b>", scope_style),
         Paragraph(f"<b>{bm.get('service', '')}</b>", scope_style)]
    ], colWidths=[content_width * 0.25, content_width * 0.75])
    scope_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 0.5, border_color),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F5F5F5')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(scope_table)
    elements.append(Spacer(1, 4))

    # ---- MAIN TABLE ----
    th_style = ParagraphStyle('TH', fontSize=8, fontName='Helvetica-Bold', alignment=TA_CENTER, textColor=colors.black)
    td_style = ParagraphStyle('TD', fontSize=8, alignment=TA_CENTER, textColor=colors.black)
    td_right = ParagraphStyle('TDRight', fontSize=8, alignment=TA_RIGHT, textColor=colors.black)
    td_left = ParagraphStyle('TDLeft', fontSize=8, alignment=TA_LEFT, textColor=colors.black)

    col_widths = [
        content_width * 0.10, content_width * 0.10, content_width * 0.07,
        content_width * 0.10, content_width * 0.28, content_width * 0.13,
        content_width * 0.07, content_width * 0.15,
    ]

    header_row = [
        Paragraph("Data Inicial", th_style), Paragraph("Data Final", th_style),
        Paragraph("Linha", th_style), Paragraph("CÓD.", th_style),
        Paragraph("Descrição das Atividades", th_style), Paragraph("Valor und", th_style),
        Paragraph("Qtd", th_style), Paragraph("Valor total", th_style),
    ]

    table_data = [header_row]
    items = bm.get("items", [])

    for idx, item in enumerate(items):
        table_data.append([
            Paragraph(item.get("data_inicial", ""), td_style),
            Paragraph(item.get("data_final", ""), td_style),
            Paragraph(item.get("linha", str(idx + 1)), td_style),
            Paragraph(item.get("cod", bm.get("cod", "")), td_style),
            Paragraph(item.get("function_name", ""), td_left),
            Paragraph(format_currency(item.get("valor_und", 0)), td_right),
            Paragraph(str(item.get("qtd", 0)), td_style),
            Paragraph(format_currency(item.get("valor_total", 0)), td_right),
        ])

    empty_rows_needed = max(0, 8 - len(items))
    for _ in range(empty_rows_needed):
        table_data.append([Paragraph("", td_style)] * 7 + [Paragraph("", td_right)])

    bold_right = ParagraphStyle('BoldRight', fontSize=9, fontName='Helvetica-Bold', alignment=TA_RIGHT, textColor=colors.black)
    table_data.append(["", "", "", "", Paragraph("<b>Subtotal</b>", bold_right), "", "", Paragraph(f"<b>{format_currency(bm.get('subtotal', 0))}</b>", bold_right)])
    table_data.append(["", "", "", "", Paragraph("<b>Impostos</b>", bold_right), "", "", Paragraph(format_currency(bm.get("impostos", 0)), td_right)])
    table_data.append(["", "", "", "", Paragraph("<b>Valor Total</b>", bold_right), "", "", Paragraph(f"<b>{format_currency(bm.get('valor_total', 0))}</b>", bold_right)])

    main_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    num_data_rows = len(items) + empty_rows_needed
    table_style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E8EAF6')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 0.5, border_color),
        ('INNERGRID', (0, 0), (-1, num_data_rows), 0.5, colors.HexColor('#DDDDDD')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('LINEABOVE', (0, num_data_rows + 1), (-1, num_data_rows + 1), 1, colors.HexColor('#1a237e')),
        ('SPAN', (0, num_data_rows + 1), (4, num_data_rows + 1)),
        ('SPAN', (5, num_data_rows + 1), (6, num_data_rows + 1)),
        ('SPAN', (0, num_data_rows + 2), (4, num_data_rows + 2)),
        ('SPAN', (5, num_data_rows + 2), (6, num_data_rows + 2)),
        ('SPAN', (0, num_data_rows + 3), (4, num_data_rows + 3)),
        ('SPAN', (5, num_data_rows + 3), (6, num_data_rows + 3)),
        ('BACKGROUND', (0, num_data_rows + 3), (-1, num_data_rows + 3), colors.HexColor('#E8EAF6')),
    ]
    for i in range(1, num_data_rows + 1):
        if i % 2 == 0:
            table_style_cmds.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F8F8F8')))
    main_table.setStyle(TableStyle(table_style_cmds))
    elements.append(main_table)

    doc.build(elements, onFirstPage=on_first_page_bm, onLaterPages=on_later_pages_bm)
    buf.seek(0)

    filename = f"BM_{bm.get('os_number', 'N')}_{bm.get('client', '')}.pdf".replace(" ", "_")
    return Response(
        content=buf.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
        }
    )



# ==================== TIMESHEET ENDPOINTS ====================

@api_router.post("/timesheets", response_model=dict)
async def create_timesheet(ts_data: TimesheetCreate, current_user: Dict[str, Any] = Depends(get_current_user)):
    if len(ts_data.entries) > 12:
        raise HTTPException(status_code=400, detail="Máximo de 12 entradas por timesheet. Crie um novo timesheet para mais funcionários.")
    # Get service order details
    so = await db.service_orders.find_one({"_id": ObjectId(ts_data.os_id)})
    if not so:
        raise HTTPException(status_code=404, detail="Service Order not found")
    
    ts_dict = ts_data.model_dump()
    ts_dict["os_number"] = so["os_number"]
    ts_dict["client"] = so["client"]
    ts_dict["location"] = so["location"]
    ts_dict["service"] = so["service"]
    ts_dict["supervisor_id"] = current_user["_id"]
    ts_dict["supervisor_name"] = current_user["name"]
    ts_dict["created_at"] = datetime.utcnow()
    ts_dict["updated_at"] = datetime.utcnow()
    
    result = await db.timesheets.insert_one(ts_dict)
    
    # Reload from database and convert _id to id
    created_ts = await db.timesheets.find_one({"_id": result.inserted_id})
    created_ts["id"] = str(created_ts.pop("_id"))
    created_ts["created_at"] = created_ts["created_at"].isoformat() if isinstance(created_ts["created_at"], datetime) else created_ts["created_at"]
    created_ts["updated_at"] = created_ts["updated_at"].isoformat() if isinstance(created_ts["updated_at"], datetime) else created_ts["updated_at"]
    
    return created_ts


@api_router.get("/timesheets", response_model=List[dict])
async def get_timesheets(current_user: Dict[str, Any] = Depends(get_current_user)):
    query = {}
    if current_user.get("role") != UserRole.ADMIN:
        query["supervisor_id"] = current_user["_id"]
    
    timesheets = await db.timesheets.find(query).sort("created_at", -1).to_list(500)
    result = []
    for ts in timesheets:
        ts["id"] = str(ts.pop("_id"))  # Rename _id to id
        result.append(ts)
    return result


@api_router.get("/timesheets/{ts_id}")
async def get_timesheet(ts_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    ts = await db.timesheets.find_one({"_id": ObjectId(ts_id)})
    if not ts:
        raise HTTPException(status_code=404, detail="Timesheet not found")
    
    # Check permissions
    if current_user.get("role") != UserRole.ADMIN and ts["supervisor_id"] != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    ts["id"] = str(ts.pop("_id"))  # Rename _id to id
    return ts


@api_router.put("/timesheets/{ts_id}")
async def update_timesheet(ts_id: str, ts_data: TimesheetCreate, current_user: Dict[str, Any] = Depends(get_current_user)):
    existing = await db.timesheets.find_one({"_id": ObjectId(ts_id)})
    if existing and existing.get("status") == "finalized":
        raise HTTPException(status_code=403, detail="Timesheet finalizada. Não é possível editar.")
    if len(ts_data.entries) > 12:
        raise HTTPException(status_code=400, detail="Máximo de 12 entradas por timesheet. Crie um novo timesheet para mais funcionários.")
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


@api_router.delete("/timesheets/{ts_id}")
async def delete_timesheet(ts_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    ts = await db.timesheets.find_one({"_id": ObjectId(ts_id)})
    if not ts:
        raise HTTPException(status_code=404, detail="Timesheet not found")
    
    # Check permissions
    if current_user.get("role") != UserRole.ADMIN and ts["supervisor_id"] != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await db.timesheets.delete_one({"_id": ObjectId(ts_id)})
    return {"message": "Timesheet deleted successfully"}


@api_router.put("/timesheets/{ts_id}/finalize")
async def finalize_timesheet(ts_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    ts = await db.timesheets.find_one({"_id": ObjectId(ts_id)})
    if not ts:
        raise HTTPException(status_code=404, detail="Timesheet não encontrada")
    if current_user.get("role") != UserRole.ADMIN and ts["supervisor_id"] != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    await db.timesheets.update_one({"_id": ObjectId(ts_id)}, {"$set": {"status": "finalized", "updated_at": datetime.utcnow()}})
    return {"success": True}


@api_router.put("/reports/{report_id}/finalize")
async def finalize_report(report_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    report = await db.reports.find_one({"_id": ObjectId(report_id)})
    if not report:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")
    if current_user.get("role") != UserRole.ADMIN and report["supervisor_id"] != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    await db.reports.update_one({"_id": ObjectId(report_id)}, {"$set": {"status": "finalized", "updated_at": datetime.utcnow()}})
    return {"success": True}


@api_router.put("/reports/{report_id}/revert")
async def revert_report(report_id: str, current_user: Dict[str, Any] = Depends(get_admin_user)):
    report = await db.reports.find_one({"_id": ObjectId(report_id)})
    if not report:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")
    await db.reports.update_one({"_id": ObjectId(report_id)}, {"$set": {"status": "draft", "updated_at": datetime.utcnow()}})
    return {"success": True}


@api_router.put("/timesheets/{ts_id}/revert")
async def revert_timesheet(ts_id: str, current_user: Dict[str, Any] = Depends(get_admin_user)):
    ts = await db.timesheets.find_one({"_id": ObjectId(ts_id)})
    if not ts:
        raise HTTPException(status_code=404, detail="Timesheet não encontrada")
    await db.timesheets.update_one({"_id": ObjectId(ts_id)}, {"$set": {"status": "draft", "updated_at": datetime.utcnow()}})
    return {"success": True}


@api_router.post("/timesheets/{ts_id}/duplicate")
async def duplicate_timesheet(ts_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    original = await db.timesheets.find_one({"_id": ObjectId(ts_id)})
    if not original:
        raise HTTPException(status_code=404, detail="Timesheet não encontrada")
    new_ts = {
        "os_id": original["os_id"],
        "os_number": original.get("os_number", ""),
        "client": original.get("client", ""),
        "supervisor_id": current_user["_id"],
        "supervisor_name": current_user.get("name", ""),
        "entries": original.get("entries", []),
        "status": "draft",
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

@api_router.get("/timesheets/{ts_id}/pdf")
async def generate_timesheet_pdf(ts_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    ts = await db.timesheets.find_one({"_id": ObjectId(ts_id)})
    if not ts:
        raise HTTPException(status_code=404, detail="Timesheet not found")
    
    # Check permissions
    if current_user.get("role") != UserRole.ADMIN and ts["supervisor_id"] != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
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
        canvas_obj.drawRightString(right_x, detail_y, f"Cliente: {ts['client']}")
        detail_y -= 0.35*cm
        canvas_obj.drawRightString(right_x, detail_y, f"Embarcação: {ts['location']}")
        detail_y -= 0.35*cm
        canvas_obj.drawRightString(right_x, detail_y, f"OS: {ts['os_number']}")
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
            Paragraph(ts["service"], styles['Normal']),
            Paragraph(ts["os_number"], styles['Normal'])
        ],
        [
            Paragraph("<b>Cliente / Client:</b>", styles['Normal']),
            Paragraph("<b>Local / Location:</b>", styles['Normal'])
        ],
        [
            Paragraph(ts["client"], styles['Normal']),
            Paragraph(ts["location"], styles['Normal'])
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
            table_data.append([
                entry["date"],
                entry["service_start"],
                entry["service_end"],
                entry["employee_function"],
                entry["employee_name"],
                entry.get("travel_start", ""),
                entry.get("travel_end", "")
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
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=timesheet_{ts['os_number']}.pdf",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    )


# ==================== REPORT ENDPOINTS ====================

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


@api_router.post("/reports")
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

@api_router.get("/reports")
async def get_reports(user: dict = Depends(get_current_user)):
    reports = []
    cursor = db.reports.find().sort("created_at", -1)
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
            "created_at": doc.get("created_at", "").isoformat() if doc.get("created_at") else "",
            "updated_at": doc.get("updated_at", "").isoformat() if doc.get("updated_at") else "",
        })
    return {"reports": reports}

@api_router.get("/reports/{report_id}")
async def get_report_by_id(report_id: str, user: dict = Depends(get_current_user)):
    doc = await db.reports.find_one({"_id": ObjectId(report_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")
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
        "created_at": doc.get("created_at", "").isoformat() if doc.get("created_at") else "",
        "updated_at": doc.get("updated_at", "").isoformat() if doc.get("updated_at") else "",
    }

@api_router.put("/reports/{report_id}")
async def update_report(report_id: str, update: ReportUpdate, user: dict = Depends(get_current_user)):
    doc = await db.reports.find_one({"_id": ObjectId(report_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")
    if doc.get("status") == "finalized" and user.get("role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Relatório finalizado. Não é possível editar.")
    
    update_data = {}
    for field in ["periodo_inicio", "periodo_fim", "executado_por", "oc_wo", "sections", "status", "daily_entries"]:
        value = getattr(update, field, None)
        if value is not None:
            update_data[field] = value
    
    update_data["updated_at"] = datetime.utcnow()
    await db.reports.update_one({"_id": ObjectId(report_id)}, {"$set": update_data})
    return {"success": True}

@api_router.delete("/reports/{report_id}")
async def delete_report(report_id: str, user: dict = Depends(get_current_user)):
    result = await db.reports.delete_one({"_id": ObjectId(report_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")
    return {"success": True}


# ==================== DUPLICATE REPORT ====================

class DuplicateReportRequest(BaseModel):
    os_id: Optional[str] = None
    periodo_inicio: Optional[str] = None
    periodo_fim: Optional[str] = None
    executado_por: Optional[str] = None

@api_router.post("/reports/{report_id}/duplicate")
async def duplicate_report(report_id: str, dup: DuplicateReportRequest, user: dict = Depends(get_current_user)):
    original = await db.reports.find_one({"_id": ObjectId(report_id)})
    if not original:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")

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

@api_router.post("/reports/{report_id}/upload-photo")
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


@api_router.get("/photos/{path:path}")
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


@api_router.get("/reports/{report_id}/photos")
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


@api_router.put("/reports/{report_id}/photos/{photo_id}/caption")
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


@api_router.delete("/reports/{report_id}/photos/{photo_id}")
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

@api_router.get("/reports/{report_id}/pdf")
async def generate_report_pdf(report_id: str, request: Request, token: str = Query(default=None), day_ids: str = Query(default=None)):
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
    report_title = "RELATÓRIO TÉCNICO" if is_service else "RELATÓRIO DIÁRIO"
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
        _draw_right_label("Rig/Vessel:", report.get('location', ''), detail_y)
        detail_y -= line_h
        _draw_right_label("Equipamento:", report.get('service', ''), detail_y)
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
    elements.append(Spacer(1, 0.5*cm))
    
    # Cover photo (larger, centered)
    cover_photos = report_photos.get("cover", [])
    if cover_photos:
        photo = cover_photos[0]
        img = load_photo_image(photo["storage_path"], content_width, 12*cm)
        if img:
            # Center the image
            img.hAlign = 'CENTER'
            elements.append(img)
    
    # Vessel/Embarcacao name below photo
    embarcacao_cover_name = report.get("embarcacao", "").upper()
    vessel_cover_style = ParagraphStyle('VesselCover', parent=styles['Normal'], fontSize=12, fontName='Helvetica-Bold', alignment=TA_CENTER, textColor=colors.black, spaceBefore=12, spaceAfter=16)
    elements.append(Paragraph(embarcacao_cover_name, vessel_cover_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # Info table
    info_data = [
        [Paragraph("<b>CLIENTE:</b>", label_style), Paragraph(report.get("client", ""), value_style)],
        [Paragraph("<b>EMBARCA\u00c7\u00c3O:</b>", label_style), Paragraph(report.get("embarcacao", ""), value_style)],
        [Paragraph("<b>LOCAL:</b>", label_style), Paragraph(report.get("location", ""), value_style)],
        [Paragraph("<b>ORDEM DE SERVIÇO:</b>", label_style), Paragraph(report.get("os_number", ""), value_style)],
        [Paragraph("<b>SERVIÇO:</b>", label_style), Paragraph(report.get("service", ""), value_style)],
        [Paragraph("<b>EXECUTADO POR:</b>", label_style), Paragraph(report.get("executado_por", report.get("supervisor_name", "")), value_style)],
        [Paragraph("<b>PERÍODO:</b>", label_style), Paragraph(periodo_str, value_style)],
    ]
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
    sumario_title_style = ParagraphStyle('SumarioTitle', parent=styles['Normal'], fontSize=14, fontName='Helvetica-Bold', alignment=TA_CENTER, textColor=colors.black, spaceBefore=12, spaceAfter=24)
    elements.append(Paragraph("SUMÁRIO", sumario_title_style))
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
                _render_photos(sub_key, elements_list, header_elements=sub_header)
            
            for subsub in sub.get("subsections", []):
                if subsub.get("enabled", True):
                    ss_key = subsub.get("key", "")
                    ss_photos = report_photos.get(ss_key, [])
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
                        _render_photos(ss_key, elements_list, header_elements=ss_header)
    
    # Image-only sections: render full-page images (one per page)
    FULL_PAGE_KEYS = {'ndt', 'pressure_test', 'certificate', 'propeller_shaft', 'pinion_shaft', 'input_shaft', 'coupling', 'swivel_pinion', 'propeller', 'reduction_gear'}
    
    # Photo rendering helper: 2 per row, uniform size, aligned with content width
    photo_col_w = content_width / 2
    photo_img_w = photo_col_w - 0.3*cm
    photo_img_h = 6*cm
    
    def _render_photos(section_key, elements_list, force_full_page=False, header_elements=None):
        """Render photos for a section. header_elements: list of flowables to keep together with first photo row."""
        sec_photos = report_photos.get(section_key, [])
        if not sec_photos:
            # No photos - just add headers if provided
            if header_elements:
                for h in header_elements:
                    elements_list.append(h)
            return
        
        # Full page: NDT subsections, pressure_test, certificate, custom sections
        is_full_page = force_full_page or section_key in FULL_PAGE_KEYS or section_key.startswith('sub_') or section_key.startswith('subsub_') or section_key.startswith('custom_')
        
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
        elements.append(Paragraph(f"<b>NAVIO/VESSEL:</b> {report.get('location', '')}", aval_field_style))
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
    
    return StreamingResponse(
        final_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=relatorio_{report.get('os_number', 'report')}.pdf",
            "Cache-Control": "no-cache, no-store, must-revalidate",
        }
    )


# ==================== PROPOSTA COMERCIAL (PROPOSALS) ====================

class ProposalItemModel(BaseModel):
    id: str = ""
    titulo: str
    descricao: str = ""
    valor: Optional[float] = 0.0

class ProposalCreate(BaseModel):
    empresa: str
    contato: str
    email: str = ""
    embarcacao: str = ""
    equipamento: str = ""
    itens: List[ProposalItemModel] = []
    observacoes: str = ""

class ProposalUpdate(BaseModel):
    empresa: Optional[str] = None
    contato: Optional[str] = None
    email: Optional[str] = None
    embarcacao: Optional[str] = None
    equipamento: Optional[str] = None
    itens: Optional[List[ProposalItemModel]] = None
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

@api_router.post("/proposals")
async def create_proposal(data: ProposalCreate, current_user: Dict[str, Any] = Depends(get_admin_user)):
    if not current_user.get("proposta_access", False):
        raise HTTPException(status_code=403, detail="Acesso negado. Permissão de Propostas não habilitada.")
    numero = await generate_proposal_number()
    now = datetime.utcnow()
    itens = []
    for item in data.itens:
        itens.append({
            "id": item.id or str(uuid.uuid4()),
            "titulo": item.titulo,
            "descricao": item.descricao,
            "valor": item.valor or 0.0,
        })
    doc = {
        "numero_proposta": numero,
        "empresa": data.empresa,
        "contato": data.contato,
        "email": data.email,
        "embarcacao": data.embarcacao,
        "equipamento": data.equipamento,
        "itens": itens,
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
        "equipamento": data.equipamento,
        "itens": itens,
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
        "equipamento": p.get("equipamento", ""),
        "itens": p.get("itens", []),
        "observacoes": p.get("observacoes", ""),
        "status": p.get("status", "pendente"),
        "po_number": p.get("po_number", ""),
        "os_id": p.get("os_id", ""),
        "os_number": p.get("os_number", ""),
        "created_at": p.get("created_at", "").isoformat() if p.get("created_at") else "",
        "updated_at": p.get("updated_at", "").isoformat() if p.get("updated_at") else "",
    }

@api_router.get("/proposals")
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

@api_router.get("/proposals/{proposal_id}")
async def get_proposal(proposal_id: str, current_user: Dict[str, Any] = Depends(get_admin_user)):
    if not current_user.get("proposta_access", False):
        raise HTTPException(status_code=403, detail="Acesso negado")
    p = await db.propostas.find_one({"_id": ObjectId(proposal_id)})
    if not p:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")
    return serialize_proposal(p)

@api_router.put("/proposals/{proposal_id}")
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
    if data.equipamento is not None:
        update_dict["equipamento"] = data.equipamento
    if data.observacoes is not None:
        update_dict["observacoes"] = data.observacoes
    if data.itens is not None:
        itens = []
        for item in data.itens:
            itens.append({
                "id": item.id or str(uuid.uuid4()),
                "titulo": item.titulo,
                "descricao": item.descricao,
                "valor": item.valor or 0.0,
            })
        update_dict["itens"] = itens
    await db.propostas.update_one({"_id": ObjectId(proposal_id)}, {"$set": update_dict})
    updated = await db.propostas.find_one({"_id": ObjectId(proposal_id)})
    return serialize_proposal(updated)

@api_router.delete("/proposals/{proposal_id}")
async def delete_proposal(proposal_id: str, current_user: Dict[str, Any] = Depends(get_admin_user)):
    if not current_user.get("proposta_access", False):
        raise HTTPException(status_code=403, detail="Acesso negado")
    result = await db.propostas.delete_one({"_id": ObjectId(proposal_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")
    return {"message": "Proposta excluída com sucesso"}

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

@api_router.put("/proposals/{proposal_id}/informar-po")
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
        "location": "",
        "service": p.get("equipamento", ""),
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

@api_router.get("/proposals/{proposal_id}/pdf")
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

    # === CLIENT INFO TABLE ===
    info_data = [
        [Paragraph("<b>Empresa:</b>", label_style), Paragraph(proposal.get("empresa", ""), body_style)],
        [Paragraph("<b>A/C:</b>", label_style), Paragraph(proposal.get("contato", ""), body_style)],
        [Paragraph("<b>Email:</b>", label_style), Paragraph(proposal.get("email", ""), body_style)],
        [Paragraph("<b>Embarca\u00e7\u00e3o:</b>", label_style), Paragraph(proposal.get("embarcacao", ""), body_style)],
        [Paragraph("<b>Equipamento:</b>", label_style), Paragraph(proposal.get("equipamento", ""), body_style)],
    ]
    info_table = Table(info_data, colWidths=[content_width * 0.2, content_width * 0.8])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#777777')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDDDDD')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F5F5F5')),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.5 * cm))

    # === ITEMS TABLE ===
    itens = proposal.get("itens", [])
    if is_comercial:
        header_row = [
            Paragraph("Item", th_style),
            Paragraph("Descri\u00e7\u00e3o", th_style),
            Paragraph("Valor (R$)", th_style),
        ]
        col_widths = [content_width * 0.08, content_width * 0.72, content_width * 0.20]
    else:
        header_row = [
            Paragraph("Item", th_style),
            Paragraph("Descri\u00e7\u00e3o", th_style),
        ]
        col_widths = [content_width * 0.08, content_width * 0.92]

    table_data = [header_row]
    total_valor = 0.0
    for idx, item in enumerate(itens):
        desc_text = f"<b>{item.get('titulo', '')}</b>"
        if item.get('descricao'):
            desc_text += f"<br/>{item['descricao']}"
        if is_comercial:
            valor = item.get("valor", 0.0) or 0.0
            total_valor += valor
            table_data.append([
                Paragraph(str(idx + 1), ParagraphStyle('ItemNum', fontSize=8, alignment=TA_CENTER)),
                Paragraph(desc_text, td_style),
                Paragraph(format_currency(valor), td_right),
            ])
        else:
            table_data.append([
                Paragraph(str(idx + 1), ParagraphStyle('ItemNum', fontSize=8, alignment=TA_CENTER)),
                Paragraph(desc_text, td_style),
            ])

    items_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#777777')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDDDDD')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F8F8F8')))
    items_table.setStyle(TableStyle(style_cmds))
    elements.append(Paragraph("Escopo dos Servi\u00e7os", section_style))
    elements.append(items_table)

    # Total row for comercial
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

    # === OBSERVATIONS ===
    obs = proposal.get("observacoes", "")
    if obs:
        elements.append(Spacer(1, 0.5 * cm))
        elements.append(Paragraph("Observa\u00e7\u00f5es", section_style))
        import html as html_mod
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


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    try:
        init_storage()
        logging.info("Object storage initialized")
    except Exception as e:
        logging.error(f"Storage init failed (will retry on first upload): {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
