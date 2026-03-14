from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
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
from pathlib import Path
from bson import ObjectId
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage, PageBreak, Frame, PageTemplate
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
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
    service: str
    employees: List[SOEmployee] = []


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
    except jwt.JWTError:
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
            name=user_dict["name"]
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
            name=user["name"]
        )
    )


@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    return UserResponse(
        id=current_user["_id"],
        email=current_user["email"],
        role=current_user["role"],
        name=current_user["name"]
    )


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
        name=user["name"]
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
    result = await db.users.insert_one(user_dict)
    return UserResponse(
        id=str(result.inserted_id),
        email=user_dict["email"],
        role=user_dict["role"],
        name=user_dict["name"]
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
        name=updated_user["name"]
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
async def get_service_orders(current_user: Dict[str, Any] = Depends(get_current_user)):
    service_orders = await db.service_orders.find().sort("os_number", 1).to_list(500)
    for so in service_orders:
        so["id"] = str(so.pop("_id"))
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
    
    # Border margins (distance from page edge)
    border_margin = 0.7*cm
    
    # Content margins (inside the border)
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
        obs_data = [[Paragraph(obs_content, ParagraphStyle(f'obs_{page_num}', parent=styles['Normal'], fontSize=9, leading=12))]]
        
        obs_table = Table(obs_data, colWidths=[content_width], rowHeights=[2.5*cm])
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

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
