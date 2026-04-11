import os
import logging
import httpx
import requests
from passlib.context import CryptContext
from fastapi.security import HTTPBearer
from datetime import datetime, timedelta
import jwt

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
    resp = requests.post(
        f"{STORAGE_URL}/key",
        headers={"x-emergent-key": EMERGENT_KEY},
        json={"app_name": APP_NAME}
    )
    resp.raise_for_status()
    _storage_key = resp.json().get("storage_key")


def put_object(path: str, data: bytes, content_type: str) -> dict:
    global _storage_key
    if not _storage_key:
        init_storage()
    resp = requests.post(
        f"{STORAGE_URL}/put",
        headers={"x-storage-key": _storage_key},
        files={"file": (path, data, content_type)},
        data={"path": path},
    )
    resp.raise_for_status()
    return resp.json()


def get_object(path: str):
    global _storage_key
    if not _storage_key:
        init_storage()
    resp = requests.get(
        f"{STORAGE_URL}/get",
        headers={"x-storage-key": _storage_key},
        params={"path": path},
    )
    if resp.status_code == 200:
        return resp.content, resp.headers.get("content-type", "application/octet-stream")
    return None, None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
