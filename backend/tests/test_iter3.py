"""
Iteration 3 backend tests: client logo upload/get/delete + storage, alert rules
settings (default + per-client), alert generation honoring rules, report
embedding of client logo.
"""
import io
import json
import os
import uuid
import zipfile
import zlib
from pathlib import Path

import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else None
if not BASE_URL:
    for line in Path("/app/frontend/.env").read_text().splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
            break

API = f"{BASE_URL}/api"
ADMIN_EMAIL = "admin@temprudence.com"
ADMIN_PASSWORD = "Temprudence2026!"
TECH_EMAIL_BASE = "test_tech_iter3"
TECH_PW = "TechPass123!"
LOGO_PATH = Path("/app/backend/tests/acme_logo.png")


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200
    s.headers.update({"Authorization": f"Bearer {r.json()['token']}"})
    return s


@pytest.fixture(scope="module")
def tech(admin, worker_id):
    tech_email = f"{TECH_EMAIL_BASE}_{worker_id}@temprudence.com"
    for u in admin.get(f"{API}/users").json():
        if u["email"] == tech_email:
            admin.delete(f"{API}/users/{u['id']}")
    admin.post(f"{API}/users", json={"email": tech_email, "name": "Iter3 Tech",
                                     "password": TECH_PW, "role": "technician"})
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": tech_email, "password": TECH_PW})
    assert r.status_code == 200, r.text
    s.headers.update({"Authorization": f"Bearer {r.json()['token']}"})
    s.tech_email = tech_email
    yield s
    for u in admin.get(f"{API}/users").json():
        if u["email"] == tech_email:
            admin.delete(f"{API}/users/{u['id']}")


@pytest.fixture(scope="module")
def logo_bytes():
    return LOGO_PATH.read_bytes()


@pytest.fixture
def tmp_client(admin):
    name = f"TEST_logo_{uuid.uuid4().hex[:6]}"
    cid = admin.post(f"{API}/clients", json={"name": name}).json()["id"]
    yield cid, name
    admin.delete(f"{API}/clients/{cid}")


def _scan(name, serial, apps=None, admin_users=False, firewall=True, scanned="2026-01-10T12:00:00+00:00"):
    return {
        "scanned_at": scanned, "scanner_version": "1.1.0", "is_admin": True, "limited_sections": [],
        "system": {"computer_name": name, "serial": serial, "manufacturer": "TestCo",
                   "model": "TestModel", "current_user": f"{name}\\u1"},
        "os": {"caption": "Microsoft Windows 11 Pro", "version": "10.0.22631",
               "display_version": "23H2", "build": "22631.3737"},
        "hardware": {"cpu": [{"name": "Test CPU", "cores": 4}], "memory_total_gb": 16,
                     "volumes": [{"device": "C:", "size_gb": 500, "free_gb": 300}]},
        "network": {"adapters": [{"name": "Wi-Fi", "status": "Up", "ipv4": ["10.0.0.5"]}],
                    "firewall": [{"profile": "Domain", "enabled": firewall},
                                 {"profile": "Private", "enabled": firewall},
                                 {"profile": "Public", "enabled": firewall}]},
        "software": apps or [{"name": "BaseApp", "version": "1.0"}],
        "users": {"local": [{"name": "u1", "is_admin": admin_users, "enabled": True,
                             "groups": ["Administrators" if admin_users else "Users"]}],
                  "groups": [{"name": "Administrators", "is_admin_group": True,
                              "members": ([{"name": "u1"}] if admin_users else [])}]},
        "security": {"uac_enabled": True,
                     "antivirus": [{"name": "Defender", "enabled": True, "up_to_date": True}],
                     "defender": {"antivirus_enabled": True, "realtime": True},
                     "secure_boot": True, "tpm": {"present": True, "ready": True}},
        "speed": {"download_mbps": 100, "upload_mbps": 50, "latency_ms": 20},
    }


# ---------------- Client logo ----------------
class TestClientLogo:
    def test_upload_png_and_get(self, admin, tmp_client, logo_bytes):
        cid, _ = tmp_client
        r = admin.post(f"{API}/clients/{cid}/logo",
                       files={"file": ("acme.png", logo_bytes, "image/png")})
        assert r.status_code == 200, r.text
        j = r.json()
        assert j.get("logo_path") and j.get("logo_size")
        g = admin.get(f"{API}/clients/{cid}/logo")
        assert g.status_code == 200 and g.headers["content-type"].startswith("image/png")
        assert g.content[:8] == b"\x89PNG\r\n\x1a\n"

    def test_upload_rejects_oversize(self, admin, tmp_client):
        cid, _ = tmp_client
        big = b"x" * (2 * 1024 * 1024 + 10)
        r = admin.post(f"{API}/clients/{cid}/logo",
                       files={"file": ("big.png", big, "image/png")})
        assert r.status_code == 413

    def test_upload_rejects_non_image(self, admin, tmp_client):
        cid, _ = tmp_client
        r = admin.post(f"{API}/clients/{cid}/logo",
                       files={"file": ("hello.txt", b"not an image", "text/plain")})
        assert r.status_code == 415

    def test_replace_and_delete(self, admin, tmp_client, logo_bytes):
        cid, _ = tmp_client
        admin.post(f"{API}/clients/{cid}/logo", files={"file": ("a.png", logo_bytes, "image/png")})
        # replace
        r2 = admin.post(f"{API}/clients/{cid}/logo", files={"file": ("b.png", logo_bytes, "image/png")})
        assert r2.status_code == 200
        # delete
        r3 = admin.delete(f"{API}/clients/{cid}/logo")
        assert r3.status_code == 200
        g = admin.get(f"{API}/clients/{cid}/logo")
        assert g.status_code == 404

    def test_tech_cannot_upload_or_delete(self, admin, tech, tmp_client, logo_bytes):
        cid, _ = tmp_client
        r = tech.post(f"{API}/clients/{cid}/logo",
                      files={"file": ("x.png", logo_bytes, "image/png")})
        assert r.status_code == 403, r.text
        admin.post(f"{API}/clients/{cid}/logo",
                   files={"file": ("x.png", logo_bytes, "image/png")})
        r2 = tech.delete(f"{API}/clients/{cid}/logo")
        assert r2.status_code == 403, r2.text
        r3 = tech.get(f"{API}/clients/{cid}/logo")
        assert r3.status_code == 200


# ---------------- Alert rules settings ----------------
class TestAlertRulesSettings:
    def test_default_rules_get(self, admin):
        r = admin.get(f"{API}/settings/alerts")
        assert r.status_code == 200
        rules = r.json()["rules"]
        for k in ("software_added", "software_removed", "accounts", "admin_rights", "security", "min_severity"):
            assert k in rules

    def test_default_rules_update(self, admin):
        new_rules = {"software_added": False, "software_removed": True, "accounts": True,
                     "admin_rights": True, "security": True, "min_severity": "medium"}
        r = admin.put(f"{API}/settings/alerts", json=new_rules)
        assert r.status_code == 200
        got = admin.get(f"{API}/settings/alerts").json()["rules"]
        assert got["software_added"] is False and got["min_severity"] == "medium"
        # restore
        admin.put(f"{API}/settings/alerts", json={"software_added": True, "software_removed": True,
                                                   "accounts": True, "admin_rights": True,
                                                   "security": True, "min_severity": "low"})

    def test_tech_cannot_put(self, tech):
        r = tech.put(f"{API}/settings/alerts", json={"software_added": True, "software_removed": True,
                                                      "accounts": True, "admin_rights": True,
                                                      "security": True, "min_severity": "low"})
        assert r.status_code == 403

    def test_client_rules_override(self, admin, tmp_client):
        cid, _ = tmp_client
        rules = {"software_added": False, "software_removed": False, "accounts": True,
                 "admin_rights": True, "security": True, "min_severity": "high"}
        r = admin.put(f"{API}/clients/{cid}/alert-rules", json={"rules": rules})
        assert r.status_code == 200
        got = r.json()
        assert got.get("alert_rules") == rules
        # revert to defaults
        r2 = admin.put(f"{API}/clients/{cid}/alert-rules", json={"rules": None})
        assert r2.status_code == 200
        assert r2.json().get("alert_rules") in (None, {})


# ---------------- Alert generation honoring rules ----------------
class TestAlertGeneration:
    def _default_key(self, admin):
        return [k for k in admin.get(f"{API}/keys").json()
                if k.get("active") and not k.get("client_id")][0]["key"]

    def _upload_two(self, key, mod=None):
        name = f"TT-R3-{uuid.uuid4().hex[:4].upper()}"
        serial = f"R3-{uuid.uuid4().hex[:6]}"
        p1 = _scan(name, serial, apps=[{"name": "AppA", "version": "1.0"}])
        r1 = requests.post(f"{API}/agent/upload", data=json.dumps(p1),
                           headers={"X-Enroll-Key": key, "Content-Type": "application/json"})
        assert r1.status_code == 200
        cid = r1.json()["computer_id"]
        p2 = _scan(name, serial, apps=[{"name": "AppA", "version": "1.0"}, {"name": "AppB", "version": "2.0"}],
                   admin_users=True, scanned="2026-01-15T12:00:00+00:00")
        if mod:
            mod(p2)
        r2 = requests.post(f"{API}/agent/upload", data=json.dumps(p2),
                           headers={"X-Enroll-Key": key, "Content-Type": "application/json"})
        assert r2.status_code == 200
        return cid, name

    def test_default_rules_create_alert(self, admin):
        # ensure defaults = all on, low
        admin.put(f"{API}/settings/alerts", json={"software_added": True, "software_removed": True,
                                                   "accounts": True, "admin_rights": True,
                                                   "security": True, "min_severity": "low"})
        key = self._default_key(admin)
        cid, _ = self._upload_two(key)
        try:
            alerts = [a for a in admin.get(f"{API}/alerts").json() if a["computer_id"] == cid]
            assert alerts, "expected alert with default rules"
            a = alerts[0]
            kinds = {i["rule"] for i in a["items"]}
            # should contain software_added and admin_rights
            assert "software_added" in kinds
            assert "admin_rights" in kinds
        finally:
            admin.delete(f"{API}/computers/{cid}")

    def test_disabling_software_added_suppresses(self, admin):
        admin.put(f"{API}/settings/alerts", json={"software_added": False, "software_removed": True,
                                                   "accounts": True, "admin_rights": True,
                                                   "security": True, "min_severity": "low"})
        try:
            key = self._default_key(admin)
            cid, _ = self._upload_two(key)
            try:
                alerts = [a for a in admin.get(f"{API}/alerts").json() if a["computer_id"] == cid]
                assert alerts
                rules_in = {i["rule"] for i in alerts[0]["items"]}
                assert "software_added" not in rules_in, "software_added should be suppressed"
            finally:
                admin.delete(f"{API}/computers/{cid}")
        finally:
            admin.put(f"{API}/settings/alerts", json={"software_added": True, "software_removed": True,
                                                       "accounts": True, "admin_rights": True,
                                                       "security": True, "min_severity": "low"})

    def test_min_severity_high_only(self, admin):
        admin.put(f"{API}/settings/alerts", json={"software_added": True, "software_removed": True,
                                                   "accounts": True, "admin_rights": True,
                                                   "security": True, "min_severity": "high"})
        try:
            key = self._default_key(admin)
            cid, _ = self._upload_two(key)
            try:
                alerts = [a for a in admin.get(f"{API}/alerts").json() if a["computer_id"] == cid]
                assert alerts, "admin rights granted (high) should still raise an alert"
                for i in alerts[0]["items"]:
                    assert i["severity"] == "high"
            finally:
                admin.delete(f"{API}/computers/{cid}")
        finally:
            admin.put(f"{API}/settings/alerts", json={"software_added": True, "software_removed": True,
                                                       "accounts": True, "admin_rights": True,
                                                       "security": True, "min_severity": "low"})

    def test_all_rules_off_no_alert(self, admin):
        admin.put(f"{API}/settings/alerts", json={"software_added": False, "software_removed": False,
                                                   "accounts": False, "admin_rights": False,
                                                   "security": False, "min_severity": "low"})
        try:
            key = self._default_key(admin)
            cid, _ = self._upload_two(key)
            try:
                alerts = [a for a in admin.get(f"{API}/alerts").json() if a["computer_id"] == cid]
                assert not alerts, "no alert should be created when all rules are off"
            finally:
                admin.delete(f"{API}/computers/{cid}")
        finally:
            admin.put(f"{API}/settings/alerts", json={"software_added": True, "software_removed": True,
                                                       "accounts": True, "admin_rights": True,
                                                       "security": True, "min_severity": "low"})

    def test_client_rules_override_defaults(self, admin):
        # Setup client w/ custom rules min_severity=high, and a dedicated key for it
        cname = f"TEST_rules_{uuid.uuid4().hex[:6]}"
        cid_client = admin.post(f"{API}/clients", json={"name": cname}).json()["id"]
        admin.put(f"{API}/clients/{cid_client}/alert-rules",
                  json={"rules": {"software_added": True, "software_removed": True, "accounts": True,
                                  "admin_rights": True, "security": True, "min_severity": "high"}})
        key = admin.post(f"{API}/keys", json={"label": f"TEST_rules_k_{cname}", "client_id": cid_client}).json()["key"]
        try:
            name = f"TT-RC-{uuid.uuid4().hex[:4].upper()}"
            serial = f"RC-{uuid.uuid4().hex[:6]}"
            p1 = _scan(name, serial, apps=[{"name": "AppA", "version": "1.0"}])
            requests.post(f"{API}/agent/upload", data=json.dumps(p1),
                          headers={"X-Enroll-Key": key, "Content-Type": "application/json"})
            # 2nd: add App only (medium) -> should be filtered out since min_severity=high
            p2 = _scan(name, serial,
                       apps=[{"name": "AppA", "version": "1.0"}, {"name": "AppB", "version": "2.0"}],
                       scanned="2026-01-16T12:00:00+00:00")
            r2 = requests.post(f"{API}/agent/upload", data=json.dumps(p2),
                               headers={"X-Enroll-Key": key, "Content-Type": "application/json"})
            comp_id = r2.json()["computer_id"]
            try:
                alerts = [a for a in admin.get(f"{API}/alerts").json() if a["computer_id"] == comp_id]
                assert not alerts, "medium 'app installed' should be filtered by high min_severity client override"
            finally:
                admin.delete(f"{API}/computers/{comp_id}")
        finally:
            admin.delete(f"{API}/clients/{cid_client}")


# ---------------- Report with client logo ----------------
class TestReportWithLogo:
    def test_computer_report_data_includes_logo_id(self, admin, logo_bytes):
        # Find Acme Dental and ensure it has a logo + an assigned computer
        clients = admin.get(f"{API}/clients").json()["clients"]
        acme = next((c for c in clients if c["name"] == "Acme Dental"), None)
        assert acme, "Acme Dental seed required"
        if not acme.get("logo_path"):
            admin.post(f"{API}/clients/{acme['id']}/logo",
                       files={"file": ("acme.png", logo_bytes, "image/png")})
        comps = admin.get(f"{API}/computers", params={"client_id": acme["id"]}).json()
        assert comps, "need at least one Acme Dental computer"
        cid = comps[0]["id"]
        r = admin.get(f"{API}/reports/computer/{cid}/data")
        assert r.status_code == 200
        assert r.json().get("client_logo_id") == acme["id"]

    def test_docx_contains_two_images(self, admin, logo_bytes):
        clients = admin.get(f"{API}/clients").json()["clients"]
        acme = next((c for c in clients if c["name"] == "Acme Dental"), None)
        if not acme.get("logo_path"):
            admin.post(f"{API}/clients/{acme['id']}/logo",
                       files={"file": ("acme.png", logo_bytes, "image/png")})
        comps = admin.get(f"{API}/computers", params={"client_id": acme["id"]}).json()
        cid = comps[0]["id"]
        r = admin.get(f"{API}/reports/computer/{cid}/export", params={"format": "docx"})
        assert r.status_code == 200 and r.content[:2] == b"PK"
        z = zipfile.ZipFile(io.BytesIO(r.content))
        media = [n for n in z.namelist() if n.startswith("word/media/")]
        assert len(media) >= 2, f"expected >=2 images in docx, got {media}"

    def test_odt_contains_two_images(self, admin):
        clients = admin.get(f"{API}/clients").json()["clients"]
        acme = next((c for c in clients if c["name"] == "Acme Dental"), None)
        comps = admin.get(f"{API}/computers", params={"client_id": acme["id"]}).json()
        cid = comps[0]["id"]
        r = admin.get(f"{API}/reports/computer/{cid}/export", params={"format": "odt"})
        assert r.status_code == 200 and r.content[:2] == b"PK"
        z = zipfile.ZipFile(io.BytesIO(r.content))
        pics = [n for n in z.namelist() if n.startswith("Pictures/")]
        assert len(pics) >= 2, f"expected >=2 images in odt, got {pics}"

    def test_pdf_valid(self, admin):
        clients = admin.get(f"{API}/clients").json()["clients"]
        acme = next((c for c in clients if c["name"] == "Acme Dental"), None)
        comps = admin.get(f"{API}/computers", params={"client_id": acme["id"]}).json()
        cid = comps[0]["id"]
        r = admin.get(f"{API}/reports/computer/{cid}/export", params={"format": "pdf"})
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"

    def test_fleet_with_client_logo_id(self, admin):
        clients = admin.get(f"{API}/clients").json()["clients"]
        acme = next((c for c in clients if c["name"] == "Acme Dental"), None)
        r = admin.get(f"{API}/reports/fleet/data", params={"client_id": acme["id"]})
        assert r.status_code == 200
        assert r.json().get("client_logo_id") == acme["id"]

    def test_report_without_client_logo(self, admin):
        # Find a computer with no client (unassigned)
        comps = admin.get(f"{API}/computers", params={"client_id": "none"}).json()
        if not comps:
            pytest.skip("no unassigned computer")
        cid = comps[0]["id"]
        r = admin.get(f"{API}/reports/computer/{cid}/data")
        assert r.status_code == 200
        assert not r.json().get("client_logo_id")
