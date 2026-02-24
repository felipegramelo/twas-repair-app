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
    
    # Create PDF with A4 page size
    buffer = io.BytesIO()
    
    # A4 dimensions: 21cm x 29.7cm
    page_width, page_height = A4
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4, 
        rightMargin=2*cm, 
        leftMargin=2*cm, 
        topMargin=2*cm, 
        bottomMargin=2*cm
    )
    
    # Available width for content (A4 width - margins)
    content_width = page_width - 4*cm  # 17cm
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=colors.black,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        spaceAfter=6
    )
    
    small_header_style = ParagraphStyle(
        'SmallHeaderStyle',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.black,
        alignment=TA_RIGHT,
        fontName='Helvetica'
    )
    
    # Logo and header
    logo_path = ROOT_DIR / "../logo.bmp"
    logo_cell = ""
    if logo_path.exists():
        try:
            pil_img = PILImage.open(logo_path)
            if pil_img.mode != 'RGB':
                pil_img = pil_img.convert('RGB')
            temp_logo = io.BytesIO()
            pil_img.save(temp_logo, format='JPEG')
            temp_logo.seek(0)
            logo_cell = RLImage(temp_logo, width=4.5*cm, height=2.2*cm)
        except Exception as e:
            logging.error(f"Error loading logo: {e}")
            logo_cell = ""
    
    # Current date and revision
    from datetime import datetime as dt
    current_date = dt.now().strftime("%d/%m/%Y")
    date_rev_text = f"{current_date}<br/>Rev.: 2"
    
    # Header table - ALIGNED to content_width
    header_data = [
        [
            logo_cell,
            Paragraph("RELATÓRIO DE HORAS<br/>TIME SHEET", header_style),
            Paragraph(date_rev_text, small_header_style)
        ]
    ]
    
    header_table = Table(header_data, colWidths=[5*cm, 7*cm, 5*cm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
    ]))
    
    elements.append(header_table)
    elements.append(Spacer(1, 0.5*cm))
    
    # Service Order Info - 2x2 grid - ALIGNED to content_width
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
    
    info_table = Table(info_data, colWidths=[8.5*cm, 8.5*cm])
    info_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0.3*cm),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0.3*cm),
        ('TOPPADDING', (0, 0), (-1, -1), 0.2*cm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0.2*cm),
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 0.4*cm))
    
    # Main timesheet table - ALIGNED to content_width
    # Column widths adjusted for A4 (total = 17cm)
    col_widths = [2*cm, 2*cm, 2*cm, 2*cm, 4.5*cm, 2*cm, 2.5*cm]
    
    # Entries per page calculation (15 entries fit comfortably in A4)
    entries_per_page = 15
    total_entries = len(ts["entries"])
    total_pages = (total_entries + entries_per_page - 1) // entries_per_page if total_entries > 0 else 1
    
    # Process entries in chunks (pages)
    for page_num in range(total_pages):
        # If not first page, add page break
        if page_num > 0:
            elements.append(PageBreak())
            # Add header again on new page
            elements.append(header_table)
            elements.append(Spacer(1, 0.5*cm))
            elements.append(info_table)
            elements.append(Spacer(1, 0.4*cm))
        
        # Table header
        table_data = [
            [
                Paragraph("<b>Data<br/>Date</b>", ParagraphStyle('centered', parent=styles['Normal'], alignment=TA_CENTER, fontSize=8)),
                Paragraph("<b>Em Serviço<br/>In Service<br/>Início<br/>Start</b>", ParagraphStyle('centered', parent=styles['Normal'], alignment=TA_CENTER, fontSize=7)),
                Paragraph("<b>Em Serviço<br/>In Service<br/>Final<br/>Final</b>", ParagraphStyle('centered', parent=styles['Normal'], alignment=TA_CENTER, fontSize=7)),
                Paragraph("<b>Função<br/>Function</b>", ParagraphStyle('centered', parent=styles['Normal'], alignment=TA_CENTER, fontSize=8)),
                Paragraph("<b>Nome<br/>Name</b>", ParagraphStyle('centered', parent=styles['Normal'], alignment=TA_CENTER, fontSize=8)),
                Paragraph("<b>Em Viagem<br/>In Travel<br/>Início<br/>Start</b>", ParagraphStyle('centered', parent=styles['Normal'], alignment=TA_CENTER, fontSize=7)),
                Paragraph("<b>Em Viagem<br/>In Travel<br/>Final<br/>Final</b>", ParagraphStyle('centered', parent=styles['Normal'], alignment=TA_CENTER, fontSize=7)),
            ]
        ]
        
        # Add entries for this page
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
        
        # Add empty rows to fill page (minimum 15 rows per page)
        current_rows = len(table_data) - 1  # Exclude header
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
        elements.append(Spacer(1, 0.3*cm))
        
        # Only add legend, approval, observations, and footer on last page
        if page_num == total_pages - 1:
            # Legend - ALIGNED to content_width
            legend_style = ParagraphStyle('legend', parent=styles['Normal'], fontSize=7, alignment=TA_LEFT)
            legend_text = "<b>Legenda / Caption:</b> "
            legend_text += "Engenheiro (E) / Engineer (E) | "
            legend_text += "Encarregado (EN) / Foreman (EN) | "
            legend_text += "Supervisor (Sup) / Supervisor (Sup) | "
            legend_text += "Técnico (T) / Technician (T) | "
            legend_text += "Mecânico (M) / Mechanic (M) | "
            legend_text += "Téc. Seg. (TS) / Safety Tech (ST)"
            legend = Paragraph(legend_text, legend_style)
            elements.append(legend)
            elements.append(Spacer(1, 0.3*cm))
            
            # Client Approval section - ALIGNED to content_width
            approval_data = [
                [Paragraph("<b>Aprovação do Cliente / Client Approval</b>", styles['Normal'])],
                [""],
                [Paragraph("<b>Nome / Name</b>", styles['Normal'])],
                [""],
                [Paragraph("<b>Função / Function</b>", styles['Normal'])],
                [""],
                [Paragraph("<b>Carimbo / Stamp</b>", styles['Normal'])],
            ]
            
            approval_table = Table(approval_data, colWidths=[17*cm], rowHeights=[0.6*cm, 0.6*cm, 0.5*cm, 0.6*cm, 0.5*cm, 0.6*cm, 0.5*cm])
            approval_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0.3*cm),
                ('TOPPADDING', (0, 0), (-1, -1), 0.15*cm),
            ]))
            
            elements.append(approval_table)
            elements.append(Spacer(1, 0.3*cm))
            
            # Observations section - ALIGNED to content_width
            obs_data = [
                [Paragraph("<b>Observações / Remarks:</b>", styles['Normal'])],
                [Paragraph(ts.get("observations", ""), styles['Normal']) if ts.get("observations") else ""]
            ]
            
            obs_table = Table(obs_data, colWidths=[17*cm], rowHeights=[0.5*cm, 1.2*cm])
            obs_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0.3*cm),
                ('TOPPADDING', (0, 0), (-1, -1), 0.15*cm),
            ]))
            
            elements.append(obs_table)
            elements.append(Spacer(1, 0.5*cm))
            
            # Footer with company info - ALIGNED center
            footer_style = ParagraphStyle('footer', parent=styles['Normal'], fontSize=7, alignment=TA_CENTER)
            footer_text = "<b>TWAS REPAIR SERVIÇOS NAVAIS E INDUSTRIAIS LTDA - CNPJ: 31.839.501/0001-90</b><br/>"
            footer_text += "Travessa Frederico Marques, N° 84, Boa Vista, São Gonçalo, Rio de Janeiro - CEP.: 24466-180.<br/>"
            footer_text += "www.twasrepair.com<br/>"
            footer_text += f"Página {page_num + 1} de {total_pages}"
            footer = Paragraph(footer_text, footer_style)
            elements.append(footer)
    
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
