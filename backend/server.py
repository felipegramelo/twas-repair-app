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
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
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
    function: str  # E, SE, T, M, W, TK
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}


class EmployeeCreate(BaseModel):
    name: str
    function: str


class ServiceOrder(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    os_number: str
    client: str
    location: str
    service: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}


class ServiceOrderCreate(BaseModel):
    os_number: str
    client: str
    location: str
    service: str


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
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}


class TimesheetCreate(BaseModel):
    os_id: str
    entries: List[TimesheetEntry]
    observations: Optional[str] = ""


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
    supervisors = await db.users.find({"role": UserRole.SUPERVISOR}).sort("name", 1).to_list(1000)
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
    employees = await db.employees.find().sort("name", 1).to_list(1000)
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
    service_orders = await db.service_orders.find().sort("os_number", 1).to_list(1000)
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
    
    timesheets = await db.timesheets.find(query).sort("created_at", -1).to_list(1000)
    result = []
    for ts in timesheets:
        ts["id"] = str(ts.pop("_id"))  # Rename _id to id
        result.append(ts)
    return result


@api_router.get("/timesheets/{ts_id}", response_model=Timesheet)
async def get_timesheet(ts_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    ts = await db.timesheets.find_one({"_id": ObjectId(ts_id)})
    if not ts:
        raise HTTPException(status_code=404, detail="Timesheet not found")
    
    # Check permissions
    if current_user.get("role") != UserRole.ADMIN and ts["supervisor_id"] != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    ts["id"] = str(ts.pop("_id"))  # Rename _id to id
    return Timesheet(**ts)


@api_router.put("/timesheets/{ts_id}", response_model=Timesheet)
async def update_timesheet(ts_id: str, ts_data: TimesheetCreate, current_user: Dict[str, Any] = Depends(get_current_user)):
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
    return Timesheet(**updated_ts)


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
    
    # Create PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1a237e'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    # Add logo if exists
    logo_path = ROOT_DIR / "../logo.bmp"
    if logo_path.exists():
        try:
            # Convert BMP to RGB if needed
            pil_img = PILImage.open(logo_path)
            if pil_img.mode != 'RGB':
                pil_img = pil_img.convert('RGB')
            
            # Save as temporary JPEG
            temp_logo = io.BytesIO()
            pil_img.save(temp_logo, format='JPEG')
            temp_logo.seek(0)
            
            logo = RLImage(temp_logo, width=2*inch, height=1*inch)
            elements.append(logo)
            elements.append(Spacer(1, 12))
        except Exception as e:
            logging.error(f"Error loading logo: {e}")
    
    # Title
    title = Paragraph("RELATÓRIO DE HORAS (TIME SHEET)", title_style)
    elements.append(title)
    elements.append(Spacer(1, 12))
    
    # Service Order Info
    info_data = [
        ["Serviços / Jobs:", ts["service"]],
        ["Cliente / Client:", ts["client"]],
        ["OS / PO (TWAS):", ts["os_number"]],
        ["Local / Location:", ts["location"]]
    ]
    
    info_table = Table(info_data, colWidths=[2*inch, 5*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e3f2fd')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 20))
    
    # Timesheet entries table
    table_data = [
        ["Data/\nDate", "Em Serviço / In Service\nInício", "Em Serviço / In Service\nFinal", 
         "Função/\nFunction", "Nome/\nName", "Em Viagem / In Travel\nInício", "Em Viagem / In Travel\nFinal"]
    ]
    
    for entry in ts["entries"]:
        table_data.append([
            entry["date"],
            entry["service_start"],
            entry["service_end"],
            entry["employee_function"],
            entry["employee_name"],
            entry.get("travel_start", ""),
            entry.get("travel_end", "")
        ])
    
    # Add empty rows to fill page
    while len(table_data) < 12:
        table_data.append(["", "", "", "", "", "", ""])
    
    entries_table = Table(table_data, colWidths=[0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 1.5*inch, 0.8*inch, 0.8*inch])
    entries_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
    ]))
    
    elements.append(entries_table)
    elements.append(Spacer(1, 20))
    
    # Legend
    legend_text = "Legenda: Engenheiro (E) / Engineer | Especialista (SE) / Specialist | Técnico (T) / Technician | Mecânico (M) / Mechanic | Soldador (W) / Welder | Almoxarife (TK) / Tool Keeper"
    legend = Paragraph(legend_text, styles['Normal'])
    elements.append(legend)
    elements.append(Spacer(1, 20))
    
    # Observations
    if ts.get("observations"):
        obs_title = Paragraph("<b>Observações / Remarks:</b>", styles['Normal'])
        elements.append(obs_title)
        obs_text = Paragraph(ts["observations"], styles['Normal'])
        elements.append(obs_text)
        elements.append(Spacer(1, 20))
    
    # Approval section
    approval_data = [
        ["Aprovação do Cliente / Client Approval"],
        ["Nome / Name: _______________________________"],
        ["Função / Function: _______________________________"],
        ["Carimbo / Stamp:"]
    ]
    
    approval_table = Table(approval_data, colWidths=[7*inch])
    approval_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e3f2fd')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
    ]))
    
    elements.append(approval_table)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=timesheet_{ts['os_number']}.pdf"}
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
