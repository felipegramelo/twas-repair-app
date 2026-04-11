from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from bson import ObjectId
from datetime import datetime

from database import db
from dependencies import get_current_user, get_admin_user
from models import Employee, EmployeeCreate

router = APIRouter()

@router.post("/employees", response_model=Employee)
async def create_employee(employee_data: EmployeeCreate, current_user: Dict[str, Any] = Depends(get_admin_user)):
    employee_dict = employee_data.model_dump()
    employee_dict["created_at"] = datetime.utcnow()
    
    result = await db.employees.insert_one(employee_dict)
    employee_dict["_id"] = str(result.inserted_id)
    
    return Employee(**employee_dict)


@router.get("/employees", response_model=List[dict])
async def get_employees(current_user: Dict[str, Any] = Depends(get_current_user)):
    employees = await db.employees.find().sort("name", 1).to_list(500)
    for emp in employees:
        emp["id"] = str(emp.pop("_id"))
    return employees


@router.get("/employees/{employee_id}", response_model=dict)
async def get_employee(employee_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    employee = await db.employees.find_one({"_id": ObjectId(employee_id)})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    employee["id"] = str(employee.pop("_id"))
    return employee


@router.put("/employees/{employee_id}", response_model=Employee)
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


@router.delete("/employees/{employee_id}")
async def delete_employee(employee_id: str, current_user: Dict[str, Any] = Depends(get_admin_user)):
    result = await db.employees.delete_one({"_id": ObjectId(employee_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Employee not found")
    return {"message": "Employee deleted successfully"}


