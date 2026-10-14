from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import asyncio
import io
import json
import logging
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

import bcrypt
import jwt
from fastapi import APIRouter, Depends, FastAPI, File, Header, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import PlainTextResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware

from analysis import DEFAULT_ALERT_RULES, change_alerts, compute_flags, diff_scans, status_from_flags, summarize
from reports import RENDERERS, apply_branding, build_computer_report, build_fleet_report
from scanner_ps1 import VERSION, build_exe, build_script
from storage import APP_NAME, get_object, init_storage, put_object
from PIL import Image, UnidentifiedImageError

db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
app = FastAPI(title="Temprudence Inventory Console")
api = APIRouter(prefix="/api")
JWT_ALG = "HS256"
logger = logging.getLogger("temprudence")
logging.basicConfig(level=logging.INFO)

NO_ID = {"_id": 0}
USER_PUBLIC = {"_id": 0, "password_hash": 0}


def now():
    return datetime.now(timezone.utc)


def iso():
    return now().isoformat()


# ---------------- Models ----------------
class LoginIn(BaseModel):
    email: str
    password: str


class UserCreate(BaseModel):
    email: str
    name: str
    password: str = Field(min_length=8)
    role: Literal["admin", "technician"] = "technician"


class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[Literal["admin", "technician"]] = None
    password: Optional[str] = Field(default=None, min_length=8)
    active: Optional[bool] = None


class KeyCreate(BaseModel):
    label: str
    client_id: Optional[str] = None
    site: Optional[str] = None


class ClientIn(BaseModel):
    name: str = Field(min_length=1)
    notes: Optional[str] = None


class AlertRules(BaseModel):
    software_added: bool = True
    software_removed: bool = True
    accounts: bool = True
    admin_rights: bool = True
    security: bool = True
    min_severity: Literal["low", "medium", "high"] = "low"


class ClientAlertRules(BaseModel):
    rules: Optional[AlertRules] = None


class ReportSettings(BaseModel):
    default_signoff: str = ""


class ComputerUpdate(BaseModel):
    owner: Optional[str] = None
    client_id: Optional[str] = None
    site: Optional[str] = None
    notes: Optional[str] = None


# ---------------- Auth helpers ----------------
def hash_password(p):
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def verify_password(p, h):
    return bcrypt.checkpw(p.encode(), h.encode())


def make_token(uid, kind, minutes):
    return jwt.encode({"sub": uid, "type": kind, "exp": now() + timedelta(minutes=minutes)}, os.environ["JWT_SECRET"], algorithm=JWT_ALG)


def set_cookies(resp, uid):
    access = make_token(uid, "access", 60 * 12)
    resp.set_cookie("access_token", access, httponly=True, secure=True, samesite="none", max_age=43200, path="/")
    resp.set_cookie("refresh_token", make_token(uid, "refresh", 60 * 24 * 7), httponly=True, secure=True, samesite="none", max_age=604800, path="/")
    return access


async def current_user(request: Request):
    token = request.cookies.get("access_token")
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
    if not token:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
    if payload.get("type") != "access":
        raise HTTPException(401, "Invalid token type")
    user = await db.users.find_one({"id": payload["sub"]}, USER_PUBLIC)
    if not user or not user.get("active", True):
        raise HTTPException(401, "User not found or disabled")
    return user


async def require_admin(user=Depends(current_user)):
    if user["role"] != "admin":
        raise HTTPException(403, "Administrator role required")
    return user


# ---------------- Auth routes ----------------
@api.post("/auth/login")
async def login(body: LoginIn, request: Request, response: Response):
    email = body.email.strip().lower()
    ident = f"{request.client.host if request.client else 'x'}:{email}"
    att = await db.login_attempts.find_one({"identifier": ident})
    if att and att.get("locked_until") and att["locked_until"] > iso():
        raise HTTPException(429, "Too many failed attempts. Try again in 15 minutes.")
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        count = (att or {}).get("count", 0) + 1
        upd = {"count": count}
        if count >= 5:
            upd = {"count": 0, "locked_until": (now() + timedelta(minutes=15)).isoformat()}
        await db.login_attempts.update_one({"identifier": ident}, {"$set": upd}, upsert=True)
        raise HTTPException(401, "Invalid email or password")
    if not user.get("active", True):
        raise HTTPException(403, "Account disabled")
    await db.login_attempts.delete_one({"identifier": ident})
    await db.users.update_one({"id": user["id"]}, {"$set": {"last_login": iso()}})
    token = set_cookies(response, user["id"])
    user = {k: v for k, v in user.items() if k not in ("_id", "password_hash")}
    return {"user": user, "token": token}


@api.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/", samesite="none", secure=True)
    response.delete_cookie("refresh_token", path="/", samesite="none", secure=True)
    return {"ok": True}


@api.get("/auth/me")
async def me(user=Depends(current_user)):
    return user


@api.post("/auth/refresh")
async def refresh(request: Request, response: Response):
    tok = request.cookies.get("refresh_token")
    try:
        payload = jwt.decode(tok or "", os.environ["JWT_SECRET"], algorithms=[JWT_ALG])
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid refresh token")
    if payload.get("type") != "refresh":
        raise HTTPException(401, "Invalid token type")
    return {"token": set_cookies(response, payload["sub"])}


# ---------------- Users (admin) ----------------
@api.get("/users")
async def list_users(_=Depends(require_admin)):
    return await db.users.find({}, USER_PUBLIC).sort("created_at", 1).to_list(500)


@api.post("/users")
async def create_user(body: UserCreate, _=Depends(require_admin)):
    email = body.email.strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise HTTPException(422, "Invalid email address")
    if await db.users.find_one({"email": email}):
        raise HTTPException(409, "A user with this email already exists")
    doc = {"id": str(uuid.uuid4()), "email": email, "name": body.name.strip(), "role": body.role,
           "password_hash": hash_password(body.password), "active": True, "created_at": iso()}
    await db.users.insert_one(doc)
    return {k: v for k, v in doc.items() if k not in ("_id", "password_hash")}


@api.patch("/users/{uid}")
async def update_user(uid: str, body: UserUpdate, admin=Depends(require_admin)):
    upd = {k: v for k, v in body.model_dump().items() if v is not None and k != "password"}
    if body.password:
        upd["password_hash"] = hash_password(body.password)
    if uid == admin["id"] and (upd.get("role") == "technician" or upd.get("active") is False):
        raise HTTPException(400, "You cannot demote or disable your own account")
    res = await db.users.update_one({"id": uid}, {"$set": upd})
    if not res.matched_count:
        raise HTTPException(404, "User not found")
    return await db.users.find_one({"id": uid}, USER_PUBLIC)


@api.delete("/users/{uid}")
async def delete_user(uid: str, admin=Depends(require_admin)):
    if uid == admin["id"]:
        raise HTTPException(400, "You cannot delete your own account")
    res = await db.users.delete_one({"id": uid})
    if not res.deleted_count:
        raise HTTPException(404, "User not found")
    return {"ok": True}


# ---------------- Enrollment keys ----------------
def new_key():
    return "tt_" + secrets.token_urlsafe(24)


@api.get("/keys")
async def list_keys(_=Depends(current_user)):
    return await db.enroll_keys.find({}, NO_ID).sort("created_at", -1).to_list(200)


@api.post("/keys")
async def create_key(body: KeyCreate, admin=Depends(require_admin)):
    if body.client_id and not await db.clients.find_one({"id": body.client_id}):
        raise HTTPException(404, "Client not found")
    doc = {"id": str(uuid.uuid4()), "key": new_key(), "label": body.label.strip() or "Upload key", "active": True,
           "client_id": body.client_id or None, "site": (body.site or "").strip() or None,
           "created_at": iso(), "created_by": admin["email"], "use_count": 0, "last_used": None}
    await db.enroll_keys.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api.post("/keys/{kid}/revoke")
async def revoke_key(kid: str, _=Depends(require_admin)):
    res = await db.enroll_keys.update_one({"id": kid}, {"$set": {"active": False, "revoked_at": iso()}})
    if not res.matched_count:
        raise HTTPException(404, "Key not found")
    return {"ok": True}


async def check_key(key: Optional[str]):
    k = await db.enroll_keys.find_one({"key": key or "", "active": True}, NO_ID)
    if not k:
        raise HTTPException(401, "Invalid or revoked upload key")
    return k


def public_base(request: Request):
    proto = request.headers.get("x-forwarded-proto", request.url.scheme).split(",")[0].strip()
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    return f"{proto}://{host}"


# ---------------- Scanner + agent ----------------
@api.get("/scanner/script.ps1")
async def scanner_script(request: Request, k: str, download: int = 0, schedule: int = 0):
    await check_key(k)
    headers = {"Content-Disposition": 'attachment; filename="TemprudenceScanner.ps1"'} if download else {}
    return PlainTextResponse(build_script(public_base(request), k, bool(schedule)), headers=headers)


@api.get("/scanner/exe")
async def scanner_exe(request: Request, k: str, schedule: int = 0):
    await check_key(k)
    name = "TemprudenceScanner_Weekly.exe" if schedule else "TemprudenceScanner.exe"
    return Response(build_exe(public_base(request), k, bool(schedule)), media_type="application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


@api.get("/scanner/info")
async def scanner_info(_=Depends(current_user)):
    return {"version": VERSION, "formats": ["ps1", "exe"], "exe_available": True}


@api.get("/agent/ping")
async def ping():
    return {"pong": True, "time": iso()}


@api.get("/agent/speedtest/download")
async def speed_down(k: str, mb: int = Query(10, ge=1, le=25)):
    await check_key(k)
    return Response(os.urandom(mb * 1024 * 1024), media_type="application/octet-stream")


@api.post("/agent/speedtest/upload")
async def speed_up(request: Request, k: str):
    await check_key(k)
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
    return {"received_bytes": size}


async def default_alert_rules():
    doc = await db.settings.find_one({"id": "alert_rules"}, NO_ID)
    return {**DEFAULT_ALERT_RULES, **((doc or {}).get("rules") or {})}


async def alert_rules_for(client_id):
    c = await db.clients.find_one({"id": client_id}, NO_ID) if client_id else None
    return (c or {}).get("alert_rules") or await default_alert_rules()


async def ingest(data: dict, source: str, key_doc: Optional[dict] = None):
    if not isinstance(data, dict) or not isinstance(data.get("system"), dict):
        raise HTTPException(422, "Not a Temprudence scan file")
    sysd = data["system"]
    name = str(sysd.get("computer_name") or "UNKNOWN").upper()
    serial = str(sysd.get("serial") or "").strip()
    ckey = f"{serial.lower()}|{name.lower()}"
    try:
        flags, summary = compute_flags(data), summarize(data)
    except (TypeError, AttributeError, KeyError, ValueError):
        raise HTTPException(422, "Scan file has an unexpected structure")
    scanned_at = data.get("scanned_at") or iso()
    comp = await db.computers.find_one({"key": ckey}, NO_ID)
    cid = comp["id"] if comp else str(uuid.uuid4())
    sid = str(uuid.uuid4())
    prev = await db.scans.find_one({"id": comp["last_scan_id"]}, NO_ID) if comp else None
    await db.scans.insert_one({"id": sid, "computer_id": cid, "scanned_at": scanned_at, "received_at": iso(), "source": source,
                               "scanner_version": data.get("scanner_version"), "data": data, "flags": flags, "summary": summary})
    upd = {"name": name, "serial": serial, "last_scan_at": scanned_at, "last_scan_id": sid, "summary": summary,
           "flags": flags, "status": status_from_flags(flags), "updated_at": iso()}
    if not comp or not comp.get("owner_manual"):
        upd["owner"] = summary.get("current_user")
    if key_doc and key_doc.get("client_id") and (not comp or not comp.get("client_manual")):
        upd["client_id"], upd["site"] = key_doc["client_id"], key_doc.get("site")
    sched = data.get("schedule") if isinstance(data.get("schedule"), dict) else {}
    upd["scheduled"] = bool(sched.get("enabled"))
    upd["next_scheduled_run"] = sched.get("next_run")
    await db.computers.update_one({"key": ckey}, {"$set": upd, "$inc": {"scan_count": 1},
                                                  "$setOnInsert": {"id": cid, "key": ckey, "first_seen": iso()}}, upsert=True)
    if prev and prev["scanned_at"] < scanned_at:
        client_id = upd.get("client_id", (comp or {}).get("client_id"))
        items, sev = change_alerts(prev["data"], prev.get("flags") or [], data, flags, await alert_rules_for(client_id))
        if items:
            await db.alerts.insert_one({"id": str(uuid.uuid4()), "computer_id": cid, "computer_name": name,
                                        "client_id": upd.get("client_id", (comp or {}).get("client_id")), "scan_id": sid,
                                        "prev_scan_id": prev["id"], "created_at": iso(), "severity": sev, "items": items,
                                        "run_type": sched.get("run_type") or "manual", "acknowledged": False})
    return {"ok": True, "computer_id": cid, "scan_id": sid, "computer_name": name, "flags": len(flags)}


@api.post("/agent/upload")
async def agent_upload(request: Request, x_enroll_key: Optional[str] = Header(None)):
    k = await check_key(x_enroll_key)
    try:
        data = json.loads((await request.body()).decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(422, "Invalid JSON")
    res = await ingest(data, f"scanner ({k['label']})", k)
    await db.enroll_keys.update_one({"id": k["id"]}, {"$set": {"last_used": iso()}, "$inc": {"use_count": 1}})
    return res


@api.post("/scans/import")
async def import_scan(file: UploadFile = File(...), user=Depends(current_user)):
    raw = await file.read()
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError):
        try:
            data = json.loads(raw.decode("utf-16"))
        except (ValueError, UnicodeDecodeError):
            raise HTTPException(422, "File is not valid JSON")
    return await ingest(data, f"import ({user['email']})")


# ---------------- Computers & scans ----------------
COMPUTER_LIST = {"_id": 0, "key": 0}


@api.get("/computers")
async def list_computers(q: str = "", status: str = "", os_name: str = "", client_id: str = "", _=Depends(current_user)):
    flt = {}
    if client_id == "none":
        flt["client_id"] = None
    elif client_id:
        flt["client_id"] = client_id
    if q:
        rx = {"$regex": re.escape(q), "$options": "i"}
        flt["$or"] = [{"name": rx}, {"serial": rx}, {"owner": rx}, {"site": rx}, {"summary.ip": rx}, {"summary.model": rx}]
    if status:
        flt["status"] = status
    if os_name:
        flt["summary.os_caption"] = {"$regex": re.escape(os_name), "$options": "i"}
    return await db.computers.find(flt, COMPUTER_LIST).sort("last_scan_at", -1).to_list(2000)


async def get_computer(cid):
    c = await db.computers.find_one({"id": cid}, COMPUTER_LIST)
    if not c:
        raise HTTPException(404, "Computer not found")
    return c


@api.get("/computers/{cid}")
async def computer_detail(cid: str, scan_id: Optional[str] = None, _=Depends(current_user)):
    c = await get_computer(cid)
    scan = await db.scans.find_one({"id": scan_id or c["last_scan_id"], "computer_id": cid}, NO_ID)
    return {"computer": c, "scan": scan}


@api.patch("/computers/{cid}")
async def update_computer(cid: str, body: ComputerUpdate, _=Depends(current_user)):
    await get_computer(cid)
    upd = {k: v for k, v in body.model_dump().items() if v is not None}
    if "owner" in upd:
        upd["owner_manual"] = True
    if "client_id" in upd:
        if upd["client_id"] and not await db.clients.find_one({"id": upd["client_id"]}):
            raise HTTPException(404, "Client not found")
        upd["client_id"] = upd["client_id"] or None
        upd["client_manual"] = True
        await db.alerts.update_many({"computer_id": cid}, {"$set": {"client_id": upd["client_id"]}})
    if "site" in upd:
        upd["site"] = upd["site"].strip() or None
    await db.computers.update_one({"id": cid}, {"$set": upd})
    return await get_computer(cid)


@api.delete("/computers/{cid}")
async def delete_computer(cid: str, _=Depends(require_admin)):
    await get_computer(cid)
    await db.scans.delete_many({"computer_id": cid})
    await db.alerts.delete_many({"computer_id": cid})
    await db.computers.delete_one({"id": cid})
    return {"ok": True}


@api.get("/computers/{cid}/scans")
async def computer_scans(cid: str, _=Depends(current_user)):
    return await db.scans.find({"computer_id": cid}, {"_id": 0, "data": 0}).sort("scanned_at", -1).to_list(500)


@api.get("/computers/{cid}/compare")
async def compare(cid: str, a: str, b: str, _=Depends(current_user)):
    sa = await db.scans.find_one({"id": a, "computer_id": cid}, NO_ID)
    sb = await db.scans.find_one({"id": b, "computer_id": cid}, NO_ID)
    if not sa or not sb:
        raise HTTPException(404, "Scan not found")
    if sa["scanned_at"] > sb["scanned_at"]:
        sa, sb = sb, sa
    return {"from": {"id": sa["id"], "scanned_at": sa["scanned_at"]}, "to": {"id": sb["id"], "scanned_at": sb["scanned_at"]},
            "diff": diff_scans(sa["data"], sb["data"])}


@api.delete("/scans/{sid}")
async def delete_scan(sid: str, _=Depends(require_admin)):
    s = await db.scans.find_one({"id": sid}, {"_id": 0, "computer_id": 1})
    if not s:
        raise HTTPException(404, "Scan not found")
    c = await get_computer(s["computer_id"])
    if c["last_scan_id"] == sid:
        raise HTTPException(400, "The latest scan cannot be deleted; delete the computer instead")
    await db.scans.delete_one({"id": sid})
    await db.computers.update_one({"id": c["id"]}, {"$inc": {"scan_count": -1}})
    return {"ok": True}


def is_overdue(c):
    return bool(c.get("scheduled")) and (c.get("last_scan_at") or "") < (now() - timedelta(days=8)).isoformat()


# ---------------- Clients ----------------
@api.get("/clients")
async def list_clients(_=Depends(current_user)):
    clients = await db.clients.find({}, NO_ID).sort("name", 1).to_list(1000)
    counts = {r["_id"]: r for r in await db.computers.aggregate([{"$group": {"_id": "$client_id", "n": {"$sum": 1},
                                                                             "critical": {"$sum": {"$cond": [{"$eq": ["$status", "critical"]}, 1, 0]}},
                                                                             "sites": {"$addToSet": "$site"}}}]).to_list(1000)}
    for c in clients:
        r = counts.get(c["id"], {})
        c["computer_count"], c["critical_count"] = r.get("n", 0), r.get("critical", 0)
        c["sites"] = sorted(s for s in r.get("sites", []) if s)
    return {"clients": clients, "unassigned": counts.get(None, {}).get("n", 0)}


@api.post("/clients")
async def create_client(body: ClientIn, user=Depends(current_user)):
    name = body.name.strip()
    if await db.clients.find_one({"name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}}):
        raise HTTPException(409, "A client with this name already exists")
    doc = {"id": str(uuid.uuid4()), "name": name, "notes": body.notes, "created_at": iso(), "created_by": user["email"]}
    await db.clients.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api.patch("/clients/{client_id}")
async def update_client(client_id: str, body: ClientIn, _=Depends(current_user)):
    res = await db.clients.update_one({"id": client_id}, {"$set": {"name": body.name.strip(), "notes": body.notes}})
    if not res.matched_count:
        raise HTTPException(404, "Client not found")
    return await db.clients.find_one({"id": client_id}, NO_ID)


@api.delete("/clients/{client_id}")
async def delete_client(client_id: str, _=Depends(require_admin)):
    res = await db.clients.delete_one({"id": client_id})
    if not res.deleted_count:
        raise HTTPException(404, "Client not found")
    await db.computers.update_many({"client_id": client_id}, {"$set": {"client_id": None, "site": None}})
    await db.enroll_keys.update_many({"client_id": client_id}, {"$set": {"client_id": None}})
    await db.alerts.update_many({"client_id": client_id}, {"$set": {"client_id": None}})
    return {"ok": True}


LOGO_MAX = 2 * 1024 * 1024


@api.post("/clients/{client_id}/logo")
async def upload_client_logo(client_id: str, file: UploadFile = File(...), admin=Depends(require_admin)):
    client = await db.clients.find_one({"id": client_id}, NO_ID)
    if not client:
        raise HTTPException(404, "Client not found")
    raw = await file.read()
    if len(raw) > LOGO_MAX:
        raise HTTPException(413, "Logo must be 2 MB or smaller")
    try:
        im = Image.open(io.BytesIO(raw))
        if im.format not in ("PNG", "JPEG", "WEBP"):
            raise HTTPException(415, "Logo must be a PNG, JPG or WEBP image")
        im = im.convert("RGBA")
        im.thumbnail((800, 800))
        bg = Image.new("RGB", im.size, "white")
        bg.paste(im, mask=im.split()[3])
        buf = io.BytesIO()
        bg.save(buf, "PNG")
    except (UnidentifiedImageError, OSError):
        raise HTTPException(415, "Logo must be a PNG, JPG or WEBP image")
    path = f"{APP_NAME}/client-logos/{client_id}/{uuid.uuid4()}.png"
    try:
        res = await asyncio.to_thread(put_object, path, buf.getvalue(), "image/png")
    except Exception as e:
        logger.error(f"Logo upload failed: {e}")
        raise HTTPException(502, "Logo storage is unavailable. Please try again.")
    if client.get("logo_path"):
        await db.files.update_one({"storage_path": client["logo_path"]}, {"$set": {"is_deleted": True}})
    await db.files.insert_one({"id": str(uuid.uuid4()), "storage_path": res["path"], "original_filename": file.filename,
                               "content_type": "image/png", "size": res.get("size"), "is_deleted": False,
                               "owner": f"client:{client_id}", "created_at": iso(), "created_by": admin["email"]})
    await db.clients.update_one({"id": client_id}, {"$set": {"logo_path": res["path"], "logo_size": list(bg.size)}})
    return await db.clients.find_one({"id": client_id}, NO_ID)


@api.delete("/clients/{client_id}/logo")
async def delete_client_logo(client_id: str, _=Depends(require_admin)):
    client = await db.clients.find_one({"id": client_id}, NO_ID)
    if not client:
        raise HTTPException(404, "Client not found")
    if client.get("logo_path"):
        await db.files.update_one({"storage_path": client["logo_path"]}, {"$set": {"is_deleted": True}})
    await db.clients.update_one({"id": client_id}, {"$unset": {"logo_path": "", "logo_size": ""}})
    return {"ok": True}


async def load_client_logo(client_id):
    c = await db.clients.find_one({"id": client_id}, NO_ID) if client_id else None
    if not c or not c.get("logo_path"):
        return None
    try:
        return await asyncio.to_thread(get_object, c["logo_path"])
    except Exception as e:
        logger.error(f"Logo fetch failed: {e}")
        return None


@api.get("/clients/{client_id}/logo")
async def get_client_logo(client_id: str, _=Depends(current_user)):
    data = await load_client_logo(client_id)
    if not data:
        raise HTTPException(404, "No logo")
    return Response(data, media_type="image/png", headers={"Cache-Control": "private, max-age=300"})


@api.put("/clients/{client_id}/alert-rules")
async def set_client_alert_rules(client_id: str, body: ClientAlertRules, _=Depends(require_admin)):
    rules = body.rules.model_dump() if body.rules else None
    res = await db.clients.update_one({"id": client_id}, {"$set": {"alert_rules": rules}})
    if not res.matched_count:
        raise HTTPException(404, "Client not found")
    return await db.clients.find_one({"id": client_id}, NO_ID)


@api.get("/settings/alerts")
async def get_alert_settings(_=Depends(current_user)):
    return {"rules": await default_alert_rules()}


@api.put("/settings/alerts")
async def put_alert_settings(body: AlertRules, admin=Depends(require_admin)):
    await db.settings.update_one({"id": "alert_rules"}, {"$set": {"rules": body.model_dump(), "updated_by": admin["email"], "updated_at": iso()}}, upsert=True)
    return {"rules": await default_alert_rules()}


# ---------------- Alerts ----------------
@api.get("/alerts")
async def list_alerts(status: str = "open", client_id: str = "", _=Depends(current_user)):
    flt = {"acknowledged": False} if status == "open" else {}
    if client_id:
        flt["client_id"] = client_id
    return await db.alerts.find(flt, NO_ID).sort("created_at", -1).to_list(500)


@api.post("/alerts/{alert_id}/ack")
async def ack_alert(alert_id: str, user=Depends(current_user)):
    res = await db.alerts.update_one({"id": alert_id}, {"$set": {"acknowledged": True, "acknowledged_by": user["email"], "acknowledged_at": iso()}})
    if not res.matched_count:
        raise HTTPException(404, "Alert not found")
    return {"ok": True}


@api.post("/alerts/ack-all")
async def ack_all(user=Depends(current_user)):
    res = await db.alerts.update_many({"acknowledged": False}, {"$set": {"acknowledged": True, "acknowledged_by": user["email"], "acknowledged_at": iso()}})
    return {"ok": True, "count": res.modified_count}


# ---------------- Settings ----------------
@api.get("/settings/report")
async def get_report_settings(_=Depends(current_user)):
    return await db.settings.find_one({"id": "report"}, NO_ID) or {"id": "report", "default_signoff": ""}


@api.put("/settings/report")
async def put_report_settings(body: ReportSettings, admin=Depends(require_admin)):
    await db.settings.update_one({"id": "report"}, {"$set": {"default_signoff": body.default_signoff, "updated_by": admin["email"], "updated_at": iso()}}, upsert=True)
    return await db.settings.find_one({"id": "report"}, NO_ID)


# ---------------- Dashboard ----------------
@api.get("/dashboard")
async def dashboard(_=Depends(current_user)):
    comps = await db.computers.find({}, COMPUTER_LIST).to_list(5000)
    os_dist, flagged = {}, []
    for c in comps:
        sm = c.get("summary") or {}
        k = sm.get("os_caption") or "Unknown"
        os_dist[k] = os_dist.get(k, 0) + 1
        for f in c.get("flags") or []:
            if f["severity"] in ("high", "medium"):
                flagged.append({**f, "computer_id": c["id"], "computer_name": c["name"]})
    order = {"high": 0, "medium": 1, "low": 2}
    flagged.sort(key=lambda f: order.get(f["severity"], 3))
    recent = await db.scans.find({}, {"_id": 0, "id": 1, "computer_id": 1, "scanned_at": 1, "source": 1, "summary": 1, "flags": 1}
                                 ).sort("received_at", -1).to_list(8)
    codes = {}
    for f in flagged:
        codes[f["code"]] = codes.get(f["code"], 0) + 1
    return {
        "totals": {"computers": len(comps), "scans": await db.scans.count_documents({}),
                   "critical": sum(1 for c in comps if c.get("status") == "critical"),
                   "warning": sum(1 for c in comps if c.get("status") == "warning"),
                   "healthy": sum(1 for c in comps if c.get("status") == "ok"),
                   "applications": sum((c.get("summary") or {}).get("software_count") or 0 for c in comps)},
        "open_alerts": await db.alerts.count_documents({"acknowledged": False}),
        "overdue": sum(1 for c in comps if is_overdue(c)),
        "scheduled": sum(1 for c in comps if c.get("scheduled")),
        "flag_counts": {"extra_admins": codes.get("extra_admins", 0),
                        "security": sum(codes.get(x, 0) for x in ("uac_off", "firewall_off", "av_off", "av_outdated", "bitlocker_off")),
                        "low_disk": codes.get("low_disk", 0), "old_os": codes.get("os_eol", 0) + codes.get("os_outdated", 0)},
        "os_distribution": [{"name": k, "count": v} for k, v in sorted(os_dist.items(), key=lambda x: -x[1])],
        "recent_scans": [{**r, "flag_count": len(r.pop("flags", []) or [])} for r in recent],
        "flagged": flagged[:25],
    }


# ---------------- Reports ----------------
async def file_response(rep, fmt, basename):
    if fmt not in RENDERERS:
        raise HTTPException(400, "Format must be docx, odt or pdf")
    fn, mime = RENDERERS[fmt]
    rep["client_logo"] = await load_client_logo(rep.get("client_logo_id"))
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", basename)
    return Response(fn(rep), media_type=mime, headers={"Content-Disposition": f'attachment; filename="{safe}.{fmt}"',
                                                       "Access-Control-Expose-Headers": "Content-Disposition"})


async def default_signoff(signoff):
    if signoff is not None:
        return signoff
    return ((await db.settings.find_one({"id": "report"}, NO_ID)) or {}).get("default_signoff") or None


async def client_name_for(client_id):
    c = await db.clients.find_one({"id": client_id}, NO_ID) if client_id else None
    return c["name"] if c else None


async def computer_report(cid, scan_id, user, client_name, signoff):
    c = await get_computer(cid)
    scan = await db.scans.find_one({"id": scan_id or c["last_scan_id"], "computer_id": cid}, NO_ID)
    if not scan:
        raise HTTPException(404, "Scan not found")
    by = f"{user['name']} ({user['email']})"
    client_doc = await db.clients.find_one({"id": c.get("client_id")}, NO_ID) if c.get("client_id") else None
    if client_name is None:
        client_name = await client_name_for(c.get("client_id"))
        if client_name and c.get("site"):
            client_name = f"{client_name} - {c['site']}"
    rep = apply_branding(build_computer_report(c, scan, by), client_name, await default_signoff(signoff), by)
    if client_doc and client_doc.get("logo_path"):
        rep["client_logo_id"] = client_doc["id"]
    return rep, c, scan


@api.get("/reports/computer/{cid}/data")
async def computer_report_data(cid: str, scan_id: Optional[str] = None, client_name: Optional[str] = None,
                               signoff: Optional[str] = None, user=Depends(current_user)):
    return (await computer_report(cid, scan_id, user, client_name, signoff))[0]


@api.get("/reports/computer/{cid}/export")
async def computer_report_export(cid: str, format: str, scan_id: Optional[str] = None, client_name: Optional[str] = None,
                                 signoff: Optional[str] = None, user=Depends(current_user)):
    rep, c, scan = await computer_report(cid, scan_id, user, client_name, signoff)
    return await file_response(rep, format, f"Temprudence_Inventory_{c['name']}_{scan['scanned_at'][:10]}")


async def fleet_report(ids, user, client_id="", client_name=None, signoff=None):
    flt = {"id": {"$in": [i for i in ids.split(",") if i]}} if ids else {}
    if client_id:
        flt["client_id"] = None if client_id == "none" else client_id
    comps = await db.computers.find(flt, COMPUTER_LIST).sort("name", 1).to_list(5000)
    scans = {}
    for c in comps:
        s = await db.scans.find_one({"id": c["last_scan_id"]}, NO_ID)
        if s:
            scans[c["id"]] = s
    by = f"{user['name']} ({user['email']})"
    rep = build_fleet_report(comps, scans, by)
    if client_name is None and client_id and client_id != "none":
        client_name = await client_name_for(client_id)
    if client_name:
        rep["subtitle"] = f"{client_name} - {rep['subtitle']}"
    client_doc = await db.clients.find_one({"id": client_id}, NO_ID) if client_id and client_id != "none" else None
    if client_doc and client_doc.get("logo_path"):
        rep["client_logo_id"] = client_doc["id"]
    return apply_branding(rep, client_name, await default_signoff(signoff), by)


@api.get("/reports/fleet/data")
async def fleet_data(ids: str = "", client_id: str = "", client_name: Optional[str] = None, signoff: Optional[str] = None,
                     user=Depends(current_user)):
    return await fleet_report(ids, user, client_id, client_name, signoff)


@api.get("/reports/fleet/export")
async def fleet_export(format: str, ids: str = "", client_id: str = "", client_name: Optional[str] = None,
                       signoff: Optional[str] = None, user=Depends(current_user)):
    rep = await fleet_report(ids, user, client_id, client_name, signoff)
    if client_name is None and client_id and client_id != "none":
        client_name = await client_name_for(client_id)
    tag = re.sub(r"[^A-Za-z0-9]+", "_", client_name or "") or "Fleet"
    return await file_response(rep, format, f"Temprudence_{tag}_Summary_{now().strftime('%Y-%m-%d')}")


# ---------------- Startup ----------------
@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.login_attempts.create_index("identifier")
    await db.computers.create_index("key", unique=True)
    await db.computers.create_index("id", unique=True)
    await db.scans.create_index([("computer_id", 1), ("scanned_at", -1)])
    await db.enroll_keys.create_index("key", unique=True)
    await db.clients.create_index("id", unique=True)
    await db.alerts.create_index([("acknowledged", 1), ("created_at", -1)])
    try:
        await asyncio.to_thread(init_storage)
    except Exception as e:
        logger.error(f"Storage init failed: {e}")
    email, pw = os.environ["ADMIN_EMAIL"].lower(), os.environ["ADMIN_PASSWORD"]
    ex = await db.users.find_one({"email": email})
    if not ex:
        await db.users.insert_one({"id": str(uuid.uuid4()), "email": email, "name": "Temprudence Admin", "role": "admin",
                                   "password_hash": hash_password(pw), "active": True, "created_at": iso()})
    elif not verify_password(pw, ex["password_hash"]):
        await db.users.update_one({"email": email}, {"$set": {"password_hash": hash_password(pw)}})
    if not await db.enroll_keys.count_documents({}):
        await db.enroll_keys.insert_one({"id": str(uuid.uuid4()), "key": new_key(), "label": "Default upload key", "active": True,
                                         "created_at": iso(), "created_by": email, "use_count": 0, "last_used": None})


app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=[o.strip() for o in os.environ["FRONTEND_URL"].split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)
