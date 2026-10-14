from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

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

from analysis import compute_flags, diff_scans, status_from_flags, summarize
from reports import RENDERERS, build_computer_report, build_fleet_report
from scanner_ps1 import VERSION, build_script

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


class ComputerUpdate(BaseModel):
    owner: Optional[str] = None
    client: Optional[str] = None
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
    doc = {"id": str(uuid.uuid4()), "key": new_key(), "label": body.label.strip() or "Upload key", "active": True,
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
async def scanner_script(request: Request, k: str, download: int = 0):
    await check_key(k)
    headers = {"Content-Disposition": 'attachment; filename="TemprudenceScanner.ps1"'} if download else {}
    return PlainTextResponse(build_script(public_base(request), k), headers=headers)


@api.get("/scanner/info")
async def scanner_info(_=Depends(current_user)):
    return {"version": VERSION, "formats": ["ps1"], "exe_available": False}


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


async def ingest(data: dict, source: str):
    if not isinstance(data, dict) or not isinstance(data.get("system"), dict):
        raise HTTPException(422, "Not a Temprudence scan file")
    sysd = data["system"]
    name = str(sysd.get("computer_name") or "UNKNOWN").upper()
    serial = str(sysd.get("serial") or "").strip()
    ckey = f"{serial.lower()}|{name.lower()}"
    flags, summary = compute_flags(data), summarize(data)
    scanned_at = data.get("scanned_at") or iso()
    comp = await db.computers.find_one({"key": ckey}, NO_ID)
    cid = comp["id"] if comp else str(uuid.uuid4())
    sid = str(uuid.uuid4())
    await db.scans.insert_one({"id": sid, "computer_id": cid, "scanned_at": scanned_at, "received_at": iso(), "source": source,
                               "scanner_version": data.get("scanner_version"), "data": data, "flags": flags, "summary": summary})
    upd = {"name": name, "serial": serial, "last_scan_at": scanned_at, "last_scan_id": sid, "summary": summary,
           "flags": flags, "status": status_from_flags(flags), "updated_at": iso()}
    if not comp or not comp.get("owner_manual"):
        upd["owner"] = summary.get("current_user")
    await db.computers.update_one({"key": ckey}, {"$set": upd, "$inc": {"scan_count": 1},
                                                  "$setOnInsert": {"id": cid, "key": ckey, "first_seen": iso()}}, upsert=True)
    return {"ok": True, "computer_id": cid, "scan_id": sid, "computer_name": name, "flags": len(flags)}


@api.post("/agent/upload")
async def agent_upload(request: Request, x_enroll_key: Optional[str] = Header(None)):
    k = await check_key(x_enroll_key)
    try:
        data = json.loads((await request.body()).decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(422, "Invalid JSON")
    res = await ingest(data, f"scanner ({k['label']})")
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
async def list_computers(q: str = "", status: str = "", os_name: str = "", _=Depends(current_user)):
    flt = {}
    if q:
        rx = {"$regex": re.escape(q), "$options": "i"}
        flt["$or"] = [{"name": rx}, {"serial": rx}, {"owner": rx}, {"client": rx}, {"summary.ip": rx}, {"summary.model": rx}]
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
    await db.computers.update_one({"id": cid}, {"$set": upd})
    return await get_computer(cid)


@api.delete("/computers/{cid}")
async def delete_computer(cid: str, _=Depends(require_admin)):
    await get_computer(cid)
    await db.scans.delete_many({"computer_id": cid})
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
        "flag_counts": {"extra_admins": codes.get("extra_admins", 0),
                        "security": sum(codes.get(x, 0) for x in ("uac_off", "firewall_off", "av_off", "av_outdated", "bitlocker_off")),
                        "low_disk": codes.get("low_disk", 0), "old_os": codes.get("os_eol", 0) + codes.get("os_outdated", 0)},
        "os_distribution": [{"name": k, "count": v} for k, v in sorted(os_dist.items(), key=lambda x: -x[1])],
        "recent_scans": [{**r, "flag_count": len(r.pop("flags", []) or [])} for r in recent],
        "flagged": flagged[:25],
    }


# ---------------- Reports ----------------
def file_response(rep, fmt, basename):
    if fmt not in RENDERERS:
        raise HTTPException(400, "Format must be docx, odt or pdf")
    fn, mime = RENDERERS[fmt]
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", basename)
    return Response(fn(rep), media_type=mime, headers={"Content-Disposition": f'attachment; filename="{safe}.{fmt}"',
                                                       "Access-Control-Expose-Headers": "Content-Disposition"})


async def computer_report(cid, scan_id, user):
    c = await get_computer(cid)
    scan = await db.scans.find_one({"id": scan_id or c["last_scan_id"], "computer_id": cid}, NO_ID)
    if not scan:
        raise HTTPException(404, "Scan not found")
    return build_computer_report(c, scan, f"{user['name']} ({user['email']})"), c, scan


@api.get("/reports/computer/{cid}/data")
async def computer_report_data(cid: str, scan_id: Optional[str] = None, user=Depends(current_user)):
    return (await computer_report(cid, scan_id, user))[0]


@api.get("/reports/computer/{cid}/export")
async def computer_report_export(cid: str, format: str, scan_id: Optional[str] = None, user=Depends(current_user)):
    rep, c, scan = await computer_report(cid, scan_id, user)
    return file_response(rep, format, f"Temprudence_Inventory_{c['name']}_{scan['scanned_at'][:10]}")


async def fleet_report(ids, user):
    flt = {"id": {"$in": [i for i in ids.split(",") if i]}} if ids else {}
    comps = await db.computers.find(flt, COMPUTER_LIST).sort("name", 1).to_list(5000)
    scans = {}
    for c in comps:
        s = await db.scans.find_one({"id": c["last_scan_id"]}, NO_ID)
        if s:
            scans[c["id"]] = s
    return build_fleet_report(comps, scans, f"{user['name']} ({user['email']})")


@api.get("/reports/fleet/data")
async def fleet_data(ids: str = "", user=Depends(current_user)):
    return await fleet_report(ids, user)


@api.get("/reports/fleet/export")
async def fleet_export(format: str, ids: str = "", user=Depends(current_user)):
    return file_response(await fleet_report(ids, user), format, f"Temprudence_Fleet_Summary_{now().strftime('%Y-%m-%d')}")


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
