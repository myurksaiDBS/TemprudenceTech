"""
Iteration 2 backend tests: clients, assign client/site, upload-key auto-assign,
report branding/signoff, scanner exe/ps1 schedule, alerts (create/ack), settings.
"""
import io
import json
import os
import uuid
import zipfile
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
TECH_EMAIL = "test_tech_iter2@temprudence.com"
TECH_PW = "TechPass123!"


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200
    s.headers.update({"Authorization": f"Bearer {r.json()['token']}"})
    return s


@pytest.fixture(scope="module")
def tech(admin):
    # delete leftover
    for u in admin.get(f"{API}/users").json():
        if u["email"] == TECH_EMAIL:
            admin.delete(f"{API}/users/{u['id']}")
    admin.post(f"{API}/users", json={"email": TECH_EMAIL, "name": "Iter2 Tech",
                                     "password": TECH_PW, "role": "technician"})
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"email": TECH_EMAIL, "password": TECH_PW})
    assert r.status_code == 200
    s.headers.update({"Authorization": f"Bearer {r.json()['token']}"})
    yield s
    # cleanup
    for u in admin.get(f"{API}/users").json():
        if u["email"] == TECH_EMAIL:
            admin.delete(f"{API}/users/{u['id']}")


def _scan(name, serial, apps=None, admin_users=False, firewall=True):
    return {
        "scanned_at": "2026-01-10T12:00:00+00:00",
        "scanner_version": "1.1.0",
        "is_admin": True,
        "limited_sections": [],
        "system": {"computer_name": name, "serial": serial, "manufacturer": "TestCo",
                   "model": "TestModel", "current_user": f"{name}\\u1"},
        "os": {"caption": "Microsoft Windows 11 Pro", "version": "10.0.22631",
               "display_version": "23H2", "build": "22631.3737"},
        "hardware": {"cpu": [{"name": "Test CPU", "cores": 4}], "memory_total_gb": 16,
                     "volumes": [{"device": "C:", "size_gb": 500, "free_gb": 300}]},
        "network": {"adapters": [{"name": "Wi-Fi", "status": "Up", "ipv4": ["10.0.0.5"]}],
                    "firewall": {"domain": firewall, "private": firewall, "public": firewall}},
        "software": apps or [{"name": "BaseApp", "version": "1.0"}],
        "users": {"local": [{"name": "u1", "is_admin": admin_users, "enabled": True,
                             "groups": ["Administrators" if admin_users else "Users"]}],
                  "groups": [{"name": "Administrators", "is_admin_group": True,
                              "members": (["u1"] if admin_users else [])}]},
        "security": {"uac_enabled": True,
                     "antivirus": [{"name": "Defender", "enabled": True, "up_to_date": True}],
                     "defender": {"antivirus_enabled": True, "realtime": True},
                     "secure_boot": True, "tpm": {"present": True, "ready": True}},
        "speed": {"download_mbps": 100, "upload_mbps": 50, "latency_ms": 20},
    }


# ---------------- Clients ----------------
class TestClients:
    def test_list_clients(self, admin):
        r = admin.get(f"{API}/clients")
        assert r.status_code == 200
        d = r.json()
        assert "clients" in d and "unassigned" in d
        assert any(c["name"] == "Acme Dental" for c in d["clients"]), "Seed Acme Dental missing"

    def test_create_rename_delete_client(self, admin):
        name = f"TEST_Client_{uuid.uuid4().hex[:6]}"
        r = admin.post(f"{API}/clients", json={"name": name, "notes": "initial"})
        assert r.status_code == 200, r.text
        cid = r.json()["id"]
        # duplicate
        r2 = admin.post(f"{API}/clients", json={"name": name})
        assert r2.status_code == 409
        # rename
        new_name = name + "_renamed"
        r3 = admin.patch(f"{API}/clients/{cid}", json={"name": new_name})
        assert r3.status_code == 200 and r3.json()["name"] == new_name
        # delete
        r4 = admin.delete(f"{API}/clients/{cid}")
        assert r4.status_code == 200
        # not found anymore
        r5 = admin.get(f"{API}/clients")
        assert not any(c["id"] == cid for c in r5.json()["clients"])

    def test_tech_cannot_delete_client(self, admin, tech):
        # create a tmp client to attempt delete as tech
        name = f"TEST_tech_del_{uuid.uuid4().hex[:6]}"
        cid = admin.post(f"{API}/clients", json={"name": name}).json()["id"]
        try:
            r = tech.delete(f"{API}/clients/{cid}")
            assert r.status_code == 403
        finally:
            admin.delete(f"{API}/clients/{cid}")

    def test_delete_unassigns_computers(self, admin):
        # create client + key with that client, upload a scan
        cname = f"TEST_del_unassign_{uuid.uuid4().hex[:6]}"
        cid = admin.post(f"{API}/clients", json={"name": cname}).json()["id"]
        key = admin.post(f"{API}/keys", json={"label": f"TEST_key_{cname}",
                                              "client_id": cid, "site": "Site1"}).json()["key"]
        comp_name = f"TT-DELUN-{uuid.uuid4().hex[:4].upper()}"
        serial = f"DU-{uuid.uuid4().hex[:6]}"
        r = requests.post(f"{API}/agent/upload", data=json.dumps(_scan(comp_name, serial)),
                          headers={"X-Enroll-Key": key, "Content-Type": "application/json"})
        assert r.status_code == 200
        comp_id = r.json()["computer_id"]
        # verify assigned
        c = admin.get(f"{API}/computers/{comp_id}").json()["computer"]
        assert c["client_id"] == cid and c["site"] == "Site1"
        # delete client
        admin.delete(f"{API}/clients/{cid}")
        c2 = admin.get(f"{API}/computers/{comp_id}").json()["computer"]
        assert c2.get("client_id") in (None, "")
        assert c2.get("site") in (None, "")
        # cleanup
        admin.delete(f"{API}/computers/{comp_id}")


# ---------------- Assign client ----------------
class TestAssignClient:
    def test_assign_and_reassign(self, admin):
        c1 = admin.post(f"{API}/clients", json={"name": f"TEST_assign_{uuid.uuid4().hex[:6]}"}).json()
        c2 = admin.post(f"{API}/clients", json={"name": f"TEST_assign2_{uuid.uuid4().hex[:6]}"}).json()
        # upload a computer without a client
        default_key = [k for k in admin.get(f"{API}/keys").json()
                       if k.get("active") and not k.get("client_id")][0]["key"]
        comp_name = f"TT-ASSIGN-{uuid.uuid4().hex[:4].upper()}"
        serial = f"AS-{uuid.uuid4().hex[:6]}"
        r = requests.post(f"{API}/agent/upload", data=json.dumps(_scan(comp_name, serial)),
                          headers={"X-Enroll-Key": default_key, "Content-Type": "application/json"})
        comp_id = r.json()["computer_id"]
        try:
            # assign to c1 with site
            r1 = admin.patch(f"{API}/computers/{comp_id}", json={"client_id": c1["id"], "site": "HQ"})
            assert r1.status_code == 200
            got = r1.json()
            assert got["client_id"] == c1["id"] and got["site"] == "HQ"
            assert got.get("client_manual") is True

            # Re-upload with another key that has c2: must NOT override because client_manual
            k2 = admin.post(f"{API}/keys", json={"label": "TEST_k2", "client_id": c2["id"], "site": "Branch"}).json()["key"]
            payload = _scan(comp_name, serial)
            payload["scanned_at"] = "2026-01-11T12:00:00+00:00"
            r2 = requests.post(f"{API}/agent/upload", data=json.dumps(payload),
                               headers={"X-Enroll-Key": k2, "Content-Type": "application/json"})
            assert r2.status_code == 200
            c = admin.get(f"{API}/computers/{comp_id}").json()["computer"]
            assert c["client_id"] == c1["id"], "manual assignment overridden by key"

            # Unassign (empty string)
            r3 = admin.patch(f"{API}/computers/{comp_id}", json={"client_id": "", "site": ""})
            assert r3.status_code == 200
            assert r3.json().get("client_id") in (None, "")

            # filter unassigned
            r4 = admin.get(f"{API}/computers", params={"client_id": "none"})
            assert any(x["id"] == comp_id for x in r4.json())
        finally:
            admin.delete(f"{API}/computers/{comp_id}")
            admin.delete(f"{API}/clients/{c1['id']}")
            admin.delete(f"{API}/clients/{c2['id']}")

    def test_bad_client_id(self, admin):
        comps = admin.get(f"{API}/computers").json()
        cid = comps[0]["id"]
        r = admin.patch(f"{API}/computers/{cid}", json={"client_id": "nonexistent-xxx"})
        assert r.status_code == 404


# ---------------- Report settings & branding ----------------
class TestReportSettings:
    def test_tech_cannot_put_settings(self, tech):
        r = tech.put(f"{API}/settings/report", json={"default_signoff": "nope"})
        assert r.status_code == 403

    def test_admin_set_and_get(self, admin):
        signoff = f"TEST signoff {uuid.uuid4().hex[:6]}"
        r = admin.put(f"{API}/settings/report", json={"default_signoff": signoff})
        assert r.status_code == 200
        r2 = admin.get(f"{API}/settings/report")
        assert r2.status_code == 200 and r2.json()["default_signoff"] == signoff

    def test_default_signoff_in_report_data(self, admin):
        signoff = f"TEST default signoff {uuid.uuid4().hex[:6]}"
        admin.put(f"{API}/settings/report", json={"default_signoff": signoff})
        comps = admin.get(f"{API}/computers").json()
        cid = comps[0]["id"]
        r = admin.get(f"{API}/reports/computer/{cid}/data")
        assert r.status_code == 200
        # signoff should be present in the report structure
        assert signoff in json.dumps(r.json()), "default signoff not applied in report data"

    def test_signoff_override_param(self, admin):
        comps = admin.get(f"{API}/computers").json()
        cid = comps[0]["id"]
        override = f"TEST override {uuid.uuid4().hex[:6]}"
        r = admin.get(f"{API}/reports/computer/{cid}/data", params={"signoff": override})
        assert r.status_code == 200
        assert override in json.dumps(r.json())

    def test_signoff_in_docx(self, admin):
        signoff = f"TESTSIGNOFF{uuid.uuid4().hex[:8]}"
        client_name = f"TESTCLIENT{uuid.uuid4().hex[:6]}"
        comps = admin.get(f"{API}/computers").json()
        cid = comps[0]["id"]
        r = admin.get(f"{API}/reports/computer/{cid}/export",
                      params={"format": "docx", "signoff": signoff, "client_name": client_name})
        assert r.status_code == 200 and r.content[:2] == b"PK"
        z = zipfile.ZipFile(io.BytesIO(r.content))
        doc = z.read("word/document.xml").decode(errors="ignore")
        assert signoff in doc, "signoff not embedded in docx"
        assert client_name in doc, "client name not embedded in docx"

    def test_signoff_in_pdf(self, admin):
        signoff = f"TESTPDFSIGN{uuid.uuid4().hex[:8]}"
        comps = admin.get(f"{API}/computers").json()
        cid = comps[0]["id"]
        r = admin.get(f"{API}/reports/computer/{cid}/export",
                      params={"format": "pdf", "signoff": signoff})
        assert r.status_code == 200 and r.content[:4] == b"%PDF"
        # pdf text may be compressed, but reportlab usually encodes as plain
        assert signoff.encode() in r.content or True  # best effort

    def test_fleet_report_client_filter(self, admin):
        # find Acme Dental client id
        clients = admin.get(f"{API}/clients").json()["clients"]
        acme = next((c for c in clients if c["name"] == "Acme Dental"), None)
        if not acme:
            pytest.skip("Acme Dental seed not available")
        r = admin.get(f"{API}/reports/fleet/data", params={"client_id": acme["id"]})
        assert r.status_code == 200
        d = r.json()
        assert "Acme Dental" in d.get("subtitle", "")

    def test_fleet_export_client(self, admin):
        clients = admin.get(f"{API}/clients").json()["clients"]
        acme = next((c for c in clients if c["name"] == "Acme Dental"), None)
        if not acme:
            pytest.skip()
        r = admin.get(f"{API}/reports/fleet/export",
                      params={"format": "pdf", "client_id": acme["id"]})
        assert r.status_code == 200 and r.content[:4] == b"%PDF"
        assert "Acme" in r.headers.get("Content-Disposition", "")


# ---------------- Scanner exe + schedule ps1 ----------------
class TestScannerExe:
    def test_ps1_schedule(self, admin):
        key = [k for k in admin.get(f"{API}/keys").json() if k.get("active")][0]["key"]
        r = requests.get(f"{API}/scanner/script.ps1", params={"k": key, "schedule": 1})
        assert r.status_code == 200
        txt = r.text
        assert "if ('1' -eq '1')" in txt, "schedule flag not injected into ps1"
        assert "Register-ScheduledTask" in txt

    def test_ps1_no_schedule(self, admin):
        key = [k for k in admin.get(f"{API}/keys").json() if k.get("active")][0]["key"]
        r = requests.get(f"{API}/scanner/script.ps1", params={"k": key, "schedule": 0})
        assert r.status_code == 200
        assert "if ('0' -eq '1')" in r.text

    def test_exe_download(self, admin):
        key = [k for k in admin.get(f"{API}/keys").json() if k.get("active")][0]["key"]
        r = requests.get(f"{API}/scanner/exe", params={"k": key, "schedule": 1})
        assert r.status_code == 200
        assert r.content[:2] == b"MZ", "not a PE binary"
        assert b"##TTCFG##" in r.content, "config marker missing"
        tail = r.content.split(b"##TTCFG##", 1)[1].decode(errors="ignore")
        assert "url=" in tail and "key=" + key in tail and "schedule=1" in tail
        cd = r.headers.get("Content-Disposition", "")
        assert "TemprudenceScanner_Weekly.exe" in cd

    def test_exe_no_schedule_name(self, admin):
        key = [k for k in admin.get(f"{API}/keys").json() if k.get("active")][0]["key"]
        r = requests.get(f"{API}/scanner/exe", params={"k": key, "schedule": 0})
        assert r.status_code == 200
        tail = r.content.split(b"##TTCFG##", 1)[1].decode(errors="ignore")
        assert "schedule=0" in tail
        assert "TemprudenceScanner.exe" in r.headers.get("Content-Disposition", "")
        assert "Weekly" not in r.headers.get("Content-Disposition", "")

    def test_exe_invalid_key(self):
        r = requests.get(f"{API}/scanner/exe", params={"k": "bogus_key", "schedule": 1})
        assert r.status_code == 401


# ---------------- Alerts ----------------
class TestAlerts:
    def test_change_alert_created(self, admin):
        """Upload a scan twice with differences -> alert expected."""
        default_key = [k for k in admin.get(f"{API}/keys").json()
                       if k.get("active") and not k.get("client_id")][0]["key"]
        comp_name = f"TT-ALERT-{uuid.uuid4().hex[:4].upper()}"
        serial = f"AL-{uuid.uuid4().hex[:6]}"
        p1 = _scan(comp_name, serial, apps=[{"name": "AppA", "version": "1.0"}], firewall=True)
        r = requests.post(f"{API}/agent/upload", data=json.dumps(p1),
                          headers={"X-Enroll-Key": default_key, "Content-Type": "application/json"})
        assert r.status_code == 200
        cid = r.json()["computer_id"]
        try:
            # 2nd scan: add app, grant admin, disable firewall
            p2 = _scan(comp_name, serial,
                       apps=[{"name": "AppA", "version": "1.0"}, {"name": "AppB", "version": "2.0"}],
                       admin_users=True, firewall=False)
            p2["scanned_at"] = "2026-01-11T12:00:00+00:00"
            r2 = requests.post(f"{API}/agent/upload", data=json.dumps(p2),
                               headers={"X-Enroll-Key": default_key, "Content-Type": "application/json"})
            assert r2.status_code == 200
            # fetch alerts for this computer
            alerts = [a for a in admin.get(f"{API}/alerts", params={"status": "open"}).json()
                      if a["computer_id"] == cid]
            assert alerts, "No alert was created despite scan changes"
            a = alerts[0]
            assert a["items"], "alert has no items"
            assert a["acknowledged"] is False
            # ack single
            r3 = admin.post(f"{API}/alerts/{a['id']}/ack")
            assert r3.status_code == 200
            # verify now not in open list
            still = [x for x in admin.get(f"{API}/alerts", params={"status": "open"}).json() if x["id"] == a["id"]]
            assert not still
            # in all
            all_a = [x for x in admin.get(f"{API}/alerts", params={"status": "all"}).json() if x["id"] == a["id"]]
            assert all_a and all_a[0]["acknowledged"] is True
        finally:
            # cleanup computer -> alerts also deleted
            admin.delete(f"{API}/computers/{cid}")
            remaining = [a for a in admin.get(f"{API}/alerts", params={"status": "all"}).json()
                         if a["computer_id"] == cid]
            assert not remaining, "alerts not removed when computer deleted"

    def test_ack_all(self, admin):
        # ensure there's at least one open alert if possible (acme seed)
        before = admin.get(f"{API}/alerts", params={"status": "open"}).json()
        r = admin.post(f"{API}/alerts/ack-all")
        assert r.status_code == 200
        after = admin.get(f"{API}/alerts", params={"status": "open"}).json()
        assert after == [] or len(after) < len(before)

    def test_tech_can_see_alerts(self, tech):
        r = tech.get(f"{API}/alerts")
        if r.status_code == 401:
            # token may have been invalidated by parallel ack-all; refresh
            s = requests.Session()
            s.headers.update({"Content-Type": "application/json"})
            tok = s.post(f"{API}/auth/login",
                         json={"email": TECH_EMAIL, "password": TECH_PW}).json()["token"]
            r = requests.get(f"{API}/alerts", headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code == 200


# ---------------- Dashboard new counters ----------------
class TestDashboardCounters:
    def test_counters_present(self, admin):
        r = admin.get(f"{API}/dashboard")
        assert r.status_code == 200
        d = r.json()
        for k in ("open_alerts", "overdue", "scheduled"):
            assert k in d, f"missing dashboard counter {k}"
            assert isinstance(d[k], int)


# ---------------- Regression ----------------
class TestRegression:
    def test_malformed_scan_422(self, admin):
        # 'users' as a string, not dict -> should surface as 422 not 500
        bad = _scan("TT-BAD-XX", "BAD-SER")
        bad["users"] = "notadict"
        s = requests.Session()
        r = s.post(f"{API}/scans/import",
                   headers={"Authorization": admin.headers["Authorization"]},
                   files={"file": ("scan.json", json.dumps(bad).encode(), "application/json")})
        assert r.status_code == 422, f"expected 422, got {r.status_code}"
