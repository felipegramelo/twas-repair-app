from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime
from fastapi import HTTPException

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
    dashboard_access: Optional[bool] = False


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
    service_start: Optional[str] = ""  # HH:MM (empty when only travel hours)
    service_end: Optional[str] = ""  # HH:MM (empty when only travel hours)
    travel_start: Optional[str] = ""  # HH:MM
    travel_end: Optional[str] = ""  # HH:MM


def _time_to_minutes(t: str) -> int:
    """Convert HH:MM to minutes since midnight."""
    try:
        parts = t.strip().split(':')
        return int(parts[0]) * 60 + int(parts[1])
    except (ValueError, IndexError):
        return -1


def _travel_overlaps_service(service_start: str, service_end: str, travel_start: str, travel_end: str) -> bool:
    """Check if travel time overlaps with service time."""
    ss = _time_to_minutes(service_start)
    se = _time_to_minutes(service_end)
    ts = _time_to_minutes(travel_start)
    te = _time_to_minutes(travel_end)
    if ss < 0 or se < 0 or ts < 0 or te < 0:
        return False
    return ts < se and ss < te


def _validate_timesheet_entries(entries):
    """Validate travel vs service conflict for all entries.

    A day must have either service hours OR travel hours (or both).
    If service hours are present, they must not overlap with travel.
    """
    for i, entry in enumerate(entries):
        travel_s = entry.travel_start if hasattr(entry, 'travel_start') else entry.get("travel_start", "")
        travel_e = entry.travel_end if hasattr(entry, 'travel_end') else entry.get("travel_end", "")
        serv_s = entry.service_start if hasattr(entry, 'service_start') else entry.get("service_start", "")
        serv_e = entry.service_end if hasattr(entry, 'service_end') else entry.get("service_end", "")
        emp_name = entry.employee_name if hasattr(entry, 'employee_name') else entry.get("employee_name", "")

        has_service = serv_s and serv_e and serv_s not in ("", "-", "0") and serv_e not in ("", "-", "0")
        has_travel = travel_s and travel_e and travel_s not in ("", "-", "0") and travel_e not in ("", "-", "0")

        if not has_service and not has_travel:
            raise HTTPException(
                status_code=400,
                detail=f"{emp_name}: informe ao menos hora de serviço OU hora de viagem."
            )

        if has_service and has_travel:
            if _travel_overlaps_service(serv_s, serv_e, travel_s, travel_e):
                raise HTTPException(
                    status_code=400,
                    detail=f"Conflito de horário para {emp_name}: "
                           f"A viagem ({travel_s}-{travel_e}) não pode coincidir com o serviço ({serv_s}-{serv_e}). "
                           f"A viagem deve ser antes ou depois do horário de serviço."
                )


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
    representante_twas: Optional[str] = None
    representante_cliente: Optional[str] = None
    sections: Optional[List[dict]] = None
    status: Optional[str] = None
    daily_entries: Optional[List[dict]] = None


class ShareDocumentRequest(BaseModel):
    document_id: str
    document_type: str  # "report" or "timesheet"
    supervisor_ids: List[str]


class UnshareDocumentRequest(BaseModel):
    document_id: str
    document_type: str
    supervisor_ids: List[str]


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

