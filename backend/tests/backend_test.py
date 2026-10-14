"""
Comprehensive backend tests for the Temprudence Inventory Console.
Covers: auth (admin/technician), users CRUD, keys CRUD, scanner script,
agent upload, speedtest, computers, compare, dashboard, reports (data+export).
"""
import io
import json
import os
import zipfile
from pathlib import Path

import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else None
if not BASE_URL:
    # Read from frontend/.env
    for line in Path("/app/frontend/.env").read_text().splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
            break

API = f"{BASE_URL}/api"
ADMIN_EMAIL = "admin@temprudence.com"
ADMIN_PASSWORD = "Temprudence2026!"


# ---------- Fixtures ----------
@pytest.fixture(scope="session")
def admin_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    data = r.json()
    s.headers.update({"Authorization": f"Bearer {data['token']}"})
    return s


@pytest.fixture(scope="session")
def upload_key(admin_session):
    r = admin_session.get(f"{API}/keys")
    assert r.status_code == 200
    keys = [k for k in r.json() if k.get("active")]
    assert keys, "No active upload key found"
    return keys[0]["key"]


@pytest.fixture(scope="session")
def computer_id(admin_session):
    r = admin_session.get(f"{API}/computers")
    assert r.status_code == 200
    comps = r.json()
    # Prefer TT-RECEPTION-01 (has 2 scans)
    for c in comps:
        if c["name"] == "TT-RECEPTION-01":
            return c["id"]
    assert comps, "No seeded computers"
    return comps[0]["id"]


# ---------- Auth ----------
class TestAuth:
    def test_login_success(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert r.status_code == 200
        data = r.json()
        assert "token" in data and "user" in data
        assert data["user"]["email"] == ADMIN_EMAIL
        assert data["user"]["role"] == "admin"
        # bcrypt hash not exposed
        assert "password_hash" not in data["user"]

    def test_login_bad_password(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong-pw-xyz"})
        assert r.status_code == 401

    def test_me_requires_auth(self):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code == 401

    def test_me_with_token(self, admin_session):
        r = admin_session.get(f"{API}/auth/me")
        assert r.status_code == 200
        assert r.json()["email"] == ADMIN_EMAIL

    def test_logout(self, admin_session):
        r = admin_session.post(f"{API}/auth/logout")
        assert r.status_code == 200


# ---------- Users ----------
class TestUsers:
    created_id = None
    tech_email = "test_tech_backend@temprudence.com"
    tech_pw = "TechPass123!"

    def test_list_users_admin(self, admin_session):
        r = admin_session.get(f"{API}/users")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_tech(self, admin_session):
        # cleanup any leftover
        for u in admin_session.get(f"{API}/users").json():
            if u["email"] == TestUsers.tech_email:
                admin_session.delete(f"{API}/users/{u['id']}")
        r = admin_session.post(f"{API}/users", json={
            "email": TestUsers.tech_email, "name": "Test Tech",
            "password": TestUsers.tech_pw, "role": "technician"
        })
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["role"] == "technician"
        TestUsers.created_id = d["id"]

    def test_tech_cannot_list_users(self):
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json={"email": TestUsers.tech_email, "password": TestUsers.tech_pw})
        assert r.status_code == 200
        tok = r.json()["token"]
        r = s.get(f"{API}/users", headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code == 403

    def test_tech_cannot_create_key(self):
        s = requests.Session()
        tok = s.post(f"{API}/auth/login", json={"email": TestUsers.tech_email, "password": TestUsers.tech_pw}).json()["token"]
        r = s.post(f"{API}/keys", json={"label": "nope"}, headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
        assert r.status_code == 403

    def test_update_tech_role(self, admin_session):
        r = admin_session.patch(f"{API}/users/{TestUsers.created_id}", json={"name": "Updated Tech"})
        assert r.status_code == 200
        assert r.json()["name"] == "Updated Tech"

    def test_disable_tech(self, admin_session):
        r = admin_session.patch(f"{API}/users/{TestUsers.created_id}", json={"active": False})
        assert r.status_code == 200
        # disabled user cannot login
        r2 = requests.post(f"{API}/auth/login", json={"email": TestUsers.tech_email, "password": TestUsers.tech_pw})
        assert r2.status_code == 403

    def test_delete_tech(self, admin_session):
        r = admin_session.delete(f"{API}/users/{TestUsers.created_id}")
        assert r.status_code == 200

    def test_admin_cannot_demote_self(self, admin_session):
        me = admin_session.get(f"{API}/auth/me").json()
        r = admin_session.patch(f"{API}/users/{me['id']}", json={"role": "technician"})
        assert r.status_code == 400


# ---------- Keys ----------
class TestKeys:
    key_id = None

    def test_create_key(self, admin_session):
        r = admin_session.post(f"{API}/keys", json={"label": "TEST_pytest_key"})
        assert r.status_code == 200
        d = r.json()
        assert d["active"] and d["key"].startswith("tt_")
        TestKeys.key_id = d["id"]
        TestKeys.key_val = d["key"]

    def test_scanner_script_valid(self):
        r = requests.get(f"{API}/scanner/script.ps1", params={"k": TestKeys.key_val})
        assert r.status_code == 200
        assert "param" in r.text.lower() or "powershell" in r.text.lower() or "$" in r.text
        assert TestKeys.key_val in r.text  # embedded key

    def test_scanner_script_invalid_key(self):
        r = requests.get(f"{API}/scanner/script.ps1", params={"k": "bad_key_xxx"})
        assert r.status_code == 401

    def test_revoke_key(self, admin_session):
        r = admin_session.post(f"{API}/keys/{TestKeys.key_id}/revoke")
        assert r.status_code == 200
        # revoked key rejected
        r2 = requests.get(f"{API}/scanner/script.ps1", params={"k": TestKeys.key_val})
        assert r2.status_code == 401


# ---------- Agent / Upload ----------
class TestAgent:
    def _sample_scan(self, name="TT-PYTEST-01", serial="PYTEST-SERIAL"):
        return {
            "scanned_at": "2026-01-10T12:00:00+00:00",
            "scanner_version": "1.0.0",
            "is_admin": True,
            "limited_sections": [],
            "system": {"computer_name": name, "serial": serial, "manufacturer": "TestCo",
                       "model": "TestModel", "current_user": f"{name}\\pytest"},
            "os": {"caption": "Microsoft Windows 11 Pro", "version": "10.0.22631",
                   "display_version": "23H2", "build": "22631.3737"},
            "hardware": {"cpu": [{"name": "Test CPU", "cores": 4}], "memory_total_gb": 16,
                         "volumes": [{"device": "C:", "size_gb": 500, "free_gb": 300}]},
            "network": {"adapters": [{"name": "Wi-Fi", "status": "Up", "ipv4": ["10.0.0.5"]}]},
            "software": [{"name": "TestApp", "version": "1.0"}],
            "users": {"local": [{"name": "pytest", "is_admin": False, "enabled": True, "groups": ["Users"]}],
                      "groups": [{"name": "Administrators", "is_admin_group": True, "members": []}]},
            "security": {"uac_enabled": True, "antivirus": [{"name": "Defender", "enabled": True, "up_to_date": True}],
                         "defender": {"antivirus_enabled": True, "realtime": True}, "secure_boot": True,
                         "tpm": {"present": True, "ready": True}},
            "speed": {"download_mbps": 100, "upload_mbps": 50, "latency_ms": 20},
        }

    def test_upload_invalid_key(self):
        r = requests.post(f"{API}/agent/upload", json=self._sample_scan(), headers={"X-Enroll-Key": "bad"})
        assert r.status_code == 401

    def test_upload_creates_computer(self, upload_key):
        payload = self._sample_scan()
        r = requests.post(f"{API}/agent/upload", data=json.dumps(payload),
                          headers={"X-Enroll-Key": upload_key, "Content-Type": "application/json"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["ok"] and d["computer_name"] == "TT-PYTEST-01"
        TestAgent.cid = d["computer_id"]

    def test_upload_same_serial_same_computer(self, upload_key):
        payload = self._sample_scan()
        payload["scanned_at"] = "2026-01-11T12:00:00+00:00"
        payload["software"].append({"name": "NewApp", "version": "2.0"})
        r = requests.post(f"{API}/agent/upload", data=json.dumps(payload),
                          headers={"X-Enroll-Key": upload_key, "Content-Type": "application/json"})
        assert r.status_code == 200
        assert r.json()["computer_id"] == TestAgent.cid

    def test_ping(self):
        r = requests.get(f"{API}/agent/ping")
        assert r.status_code == 200
        assert r.json()["pong"] is True

    def test_speedtest_download(self, upload_key):
        r = requests.get(f"{API}/agent/speedtest/download", params={"k": upload_key, "mb": 1})
        assert r.status_code == 200
        assert len(r.content) == 1024 * 1024

    def test_speedtest_upload(self, upload_key):
        payload = os.urandom(512 * 1024)
        r = requests.post(f"{API}/agent/speedtest/upload", params={"k": upload_key}, data=payload)
        assert r.status_code == 200
        assert r.json()["received_bytes"] == len(payload)


# ---------- Computers ----------
class TestComputers:
    def test_list_computers(self, admin_session):
        r = admin_session.get(f"{API}/computers")
        assert r.status_code == 200
        comps = r.json()
        names = {c["name"] for c in comps}
        assert "TT-RECEPTION-01" in names
        assert "TT-ACCOUNTING-02" in names

    def test_search(self, admin_session):
        r = admin_session.get(f"{API}/computers", params={"q": "RECEPTION"})
        assert r.status_code == 200
        assert all("RECEPTION" in c["name"] for c in r.json())

    def test_filter_status(self, admin_session):
        r = admin_session.get(f"{API}/computers", params={"status": "critical"})
        assert r.status_code == 200
        for c in r.json():
            assert c["status"] == "critical"

    def test_computer_detail(self, admin_session, computer_id):
        r = admin_session.get(f"{API}/computers/{computer_id}")
        assert r.status_code == 200
        d = r.json()
        assert d["computer"]["id"] == computer_id
        assert d["scan"] is not None
        assert "_id" not in d["computer"]

    def test_scans_list(self, admin_session, computer_id):
        r = admin_session.get(f"{API}/computers/{computer_id}/scans")
        assert r.status_code == 200
        scans = r.json()
        assert len(scans) >= 2  # TT-RECEPTION-01 has 2 scans

    def test_compare(self, admin_session, computer_id):
        scans = admin_session.get(f"{API}/computers/{computer_id}/scans").json()
        assert len(scans) >= 2
        a, b = scans[0]["id"], scans[1]["id"]
        r = admin_session.get(f"{API}/computers/{computer_id}/compare", params={"a": a, "b": b})
        assert r.status_code == 200
        d = r.json()
        assert "diff" in d and "from" in d and "to" in d

    def test_update_owner(self, admin_session, computer_id):
        r = admin_session.patch(f"{API}/computers/{computer_id}", json={"owner": "TEST_pytest_owner"})
        assert r.status_code == 200
        assert r.json()["owner"] == "TEST_pytest_owner"


# ---------- Dashboard ----------
class TestDashboard:
    def test_dashboard(self, admin_session):
        r = admin_session.get(f"{API}/dashboard")
        assert r.status_code == 200
        d = r.json()
        for key in ("totals", "flag_counts", "os_distribution", "recent_scans", "flagged"):
            assert key in d
        assert d["totals"]["computers"] >= 3
        assert d["totals"]["scans"] >= 4


# ---------- Reports ----------
class TestReports:
    def test_computer_report_data(self, admin_session, computer_id):
        r = admin_session.get(f"{API}/reports/computer/{computer_id}/data")
        assert r.status_code == 200
        assert "sections" in r.json() or isinstance(r.json(), dict)

    @pytest.mark.parametrize("fmt,sig", [("docx", b"PK"), ("odt", b"PK"), ("pdf", b"%PDF")])
    def test_computer_report_export(self, admin_session, computer_id, fmt, sig):
        r = admin_session.get(f"{API}/reports/computer/{computer_id}/export", params={"format": fmt})
        assert r.status_code == 200, r.text[:200]
        assert r.content[:len(sig)] == sig, f"{fmt} bad signature"
        if fmt in ("docx", "odt"):
            z = zipfile.ZipFile(io.BytesIO(r.content))
            names = z.namelist()
            if fmt == "docx":
                assert any("document.xml" in n for n in names)
            else:
                assert "mimetype" in names
                assert z.read("mimetype").startswith(b"application/vnd.oasis.opendocument")

    def test_fleet_data(self, admin_session):
        r = admin_session.get(f"{API}/reports/fleet/data")
        assert r.status_code == 200

    @pytest.mark.parametrize("fmt,sig", [("docx", b"PK"), ("odt", b"PK"), ("pdf", b"%PDF")])
    def test_fleet_export(self, admin_session, fmt, sig):
        r = admin_session.get(f"{API}/reports/fleet/export", params={"format": fmt})
        assert r.status_code == 200
        assert r.content[:len(sig)] == sig


# ---------- Scan import ----------
class TestImport:
    def test_import_scan_file(self, admin_session):
        payload = {
            "scanned_at": "2026-01-12T00:00:00+00:00",
            "scanner_version": "1.0.0",
            "is_admin": True, "limited_sections": [],
            "system": {"computer_name": "TT-IMPORT-PYTEST", "serial": "IMPORT-SER",
                       "current_user": "TT-IMPORT-PYTEST\\x"},
            "os": {"caption": "Windows 11 Pro", "version": "10.0.22631", "build": "22631"},
            "hardware": {"cpu": [{"name": "x", "cores": 4}], "memory_total_gb": 8,
                         "volumes": [{"device": "C:", "size_gb": 100, "free_gb": 50}]},
            "network": {"adapters": []},
            "software": [],
            "users": {"local": [], "groups": []},
            "security": {},
        }
        s = requests.Session()
        tok = admin_session.headers["Authorization"]
        r = s.post(f"{API}/scans/import", headers={"Authorization": tok},
                   files={"file": ("scan.json", json.dumps(payload).encode(), "application/json")})
        assert r.status_code == 200, r.text
        assert r.json()["computer_name"] == "TT-IMPORT-PYTEST"
