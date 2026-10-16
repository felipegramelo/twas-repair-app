import os
import logging
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
    if _storage_key:
        return _storage_key
    if not EMERGENT_KEY:
        raise RuntimeError("EMERGENT_LLM_KEY não configurada no servidor")
    resp = requests.post(
        f"{STORAGE_URL}/init",
        json={"emergent_key": EMERGENT_KEY},
        timeout=30
    )
    if not resp.ok:
        raise RuntimeError(f"storage init failed: HTTP {resp.status_code} {resp.text[:200]}")
    _storage_key = resp.json().get("storage_key")
    if not _storage_key:
        raise RuntimeError("storage init sem storage_key na resposta")
    return _storage_key


def _reset_storage_key():
    global _storage_key
    _storage_key = None


_objects_coll = None


def _objects():
    global _objects_coll
    if _objects_coll is None:
        from pymongo import MongoClient
        from bson import Binary  # noqa: F401
        coll = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]["stored_objects"]
        coll.create_index("path", unique=True)
        _objects_coll = coll
    return _objects_coll


def _put_object_mongo(path: str, data: bytes, content_type: str) -> dict:
    from bson import Binary
    _objects().replace_one(
        {"path": path},
        {"path": path, "data": Binary(data), "content_type": content_type, "size": len(data), "created_at": datetime.utcnow()},
        upsert=True,
    )
    return {"path": path, "size": len(data), "backend": "mongo"}


def _put_object_emergent(path: str, data: bytes, content_type: str) -> dict:
    for attempt in range(2):
        key = init_storage()
        resp = requests.put(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key, "Content-Type": content_type},
            data=data,
            timeout=120
        )
        if resp.status_code in (401, 403) and attempt == 0:
            _reset_storage_key()
            continue
        if not resp.ok:
            raise RuntimeError(f"storage put failed: HTTP {resp.status_code} {resp.text[:200]}")
        return resp.json()


def put_object(path: str, data: bytes, content_type: str) -> dict:
    try:
        return _put_object_emergent(path, data, content_type)
    except Exception as e:
        logging.warning(f"Emergent storage indisponível ({str(e)[:120]}); salvando no MongoDB")
        return _put_object_mongo(path, data, content_type)


def get_object(path: str):
    try:
        doc = _objects().find_one({"path": path})
        if doc:
            return bytes(doc["data"]), doc.get("content_type", "application/octet-stream")
    except Exception as e:
        logging.warning(f"Mongo object lookup failed: {e}")
    try:
        key = init_storage()
        resp = requests.get(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key},
            timeout=60
        )
        if resp.status_code == 200:
            return resp.content, resp.headers.get("Content-Type", "application/octet-stream")
    except Exception as e:
        logging.warning(f"Emergent storage get failed: {e}")
    return None, None



def storage_health() -> dict:
    info = {"emergent_key_configured": bool(EMERGENT_KEY), "emergent_ok": False, "mongo_ok": False, "active_backend": None, "error": None}
    try:
        _reset_storage_key()
        init_storage()
        _put_object_emergent(f"{APP_NAME}/_health/probe.txt", b"ok", "text/plain")
        info["emergent_ok"] = True
    except Exception as e:
        info["error"] = str(e)[:300]
    try:
        _put_object_mongo(f"{APP_NAME}/_health/probe.txt", b"ok", "text/plain")
        info["mongo_ok"] = True
    except Exception as e:
        info["error"] = (info["error"] or "") + f" | mongo: {str(e)[:200]}"
    info["active_backend"] = "emergent" if info["emergent_ok"] else ("mongo" if info["mongo_ok"] else None)
    return info


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
