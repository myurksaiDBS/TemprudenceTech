"""
Iteration 4 backend tests: Client Portal feature
- Create/list/update/delete portal users via POST/PATCH/DELETE /api/users with role=client
- Role transition rules (client<->staff forbidden)
- Portal routes: /api/portal/overview, /portal/computers/{id}/report/data, /portal/fleet/data, exports
- Security: client -> 403 on staff APIs; staff -> 403 on /api/portal/*
- Cross-tenant 404: other client's computer/report, other client's logo
- Disabled portal user cannot login (403)
- Deleting client cascades portal users
"""
import io
import json
import os
import uuid
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
ACME_PORTAL_EMAIL = "portal@acmedental.com"
ACME_PORTAL_PASSWORD = "AcmePortal2026!"


def _login(session, email, password):
    r = session.post(f"{API}/auth/login", json={"email": email, "password": password})
    return r


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = _login(s, ADMIN_EMAIL, ADMIN_PASSWORD)
    assert r.status_code == 200, r.text
    s.headers.update({"Authorization": f"Bearer {r.json()['token']}"})
    return s


@pytest.fixture(scope="module")
def acme_client_id(admin):
    for c in admin.get(f"{API}/clients").json()["clients"]:
        if c["name"].lower() == "acme dental":
            return c["id"]
    pytest.skip("Acme Dental client not found")


@pytest.fixture(scope="module")
def acme_portal_session():
    s = requests.Session()
    r = _login(s, ACME_PORTAL_EMAIL, ACME_PORTAL_PASSWORD)
    assert r.status_code == 200, f"Acme portal login failed: {r.text}"
    s.headers.update({"Authorization": f"Bearer {r.json()['token']}"})
    return s


# ---------------- Portal user CRUD ----------------
class TestPortalUserCRUD:
    def test_create_requires_client_id(self, admin):
        r = admin.post(f"{API}/users", json={
            "email": f"TEST_portal_noclient_{uuid.uuid4().hex[:6]}@example.com",
            "name": "No Client", "password": "Password123!", "role": "client",
        })
        assert r.status_code == 422, r.text

    def test_create_requires_valid_client(self, admin):
        r = admin.post(f"{API}/users", json={
            "email": f"TEST_portal_badclient_{uuid.uuid4().hex[:6]}@example.com",
            "name": "Bad Client", "password": "Password123!", "role": "client",
            "client_id": "nonexistent-id",
        })
        assert r.status_code == 422

    def test_create_list_delete_portal_user(self, admin, acme_client_id):
        email = f"TEST_portal_{uuid.uuid4().hex[:6]}@example.com"
        r = admin.post(f"{API}/users", json={
            "email": email, "name": "TEST Portal", "password": "Password123!",
            "role": "client", "client_id": acme_client_id,
        })
        assert r.status_code == 200, r.text
        u = r.json()
        assert u["role"] == "client" and u["client_id"] == acme_client_id
        assert "_id" not in u and "password_hash" not in u
        try:
            lst = admin.get(f"{API}/users", params={"client_id": acme_client_id}).json()
            assert any(x["email"] == email.lower() for x in lst)
        finally:
            d = admin.delete(f"{API}/users/{u['id']}")
            assert d.status_code == 200

    def test_patch_cannot_change_role_client_to_staff(self, admin, acme_client_id):
        email = f"TEST_portal_{uuid.uuid4().hex[:6]}@example.com"
        u = admin.post(f"{API}/users", json={
            "email": email, "name": "TEST", "password": "Password123!",
            "role": "client", "client_id": acme_client_id,
        }).json()
        try:
            r = admin.patch(f"{API}/users/{u['id']}", json={"role": "technician"})
            assert r.status_code in (400, 422)
        finally:
            admin.delete(f"{API}/users/{u['id']}")

    def test_patch_cannot_change_role_staff_to_client(self, admin):
        email = f"TEST_tech_{uuid.uuid4().hex[:6]}@example.com"
        u = admin.post(f"{API}/users", json={
            "email": email, "name": "TEST Tech", "password": "Password123!", "role": "technician",
        }).json()
        try:
            # Pydantic UserUpdate.role only allows admin/technician - 'client' triggers 422
            r = admin.patch(f"{API}/users/{u['id']}", json={"role": "client"})
            assert r.status_code in (400, 422)
        finally:
            admin.delete(f"{API}/users/{u['id']}")

    def test_disabled_portal_user_cannot_login(self, admin, acme_client_id):
        email = f"TEST_portal_disable_{uuid.uuid4().hex[:6]}@example.com"
        pw = "Password123!"
        u = admin.post(f"{API}/users", json={
            "email": email, "name": "TEST Disable", "password": pw,
            "role": "client", "client_id": acme_client_id,
        }).json()
        try:
            # disable
            r = admin.patch(f"{API}/users/{u['id']}", json={"active": False})
            assert r.status_code == 200
            s = requests.Session()
            lr = _login(s, email, pw)
            assert lr.status_code == 403, lr.text
            # re-enable and login should succeed
            admin.patch(f"{API}/users/{u['id']}", json={"active": True})
            s2 = requests.Session()
            lr2 = _login(s2, email, pw)
            assert lr2.status_code == 200
        finally:
            admin.delete(f"{API}/users/{u['id']}")


# ---------------- Client cascade delete ----------------
class TestClientCascadeDeletesPortalUsers:
    def test_delete_client_removes_its_portal_users(self, admin):
        cname = f"TEST Client {uuid.uuid4().hex[:6]}"
        c = admin.post(f"{API}/clients", json={"name": cname}).json()
        email = f"TEST_cascade_{uuid.uuid4().hex[:6]}@example.com"
        u = admin.post(f"{API}/users", json={
            "email": email, "name": "Cascade", "password": "Password123!",
            "role": "client", "client_id": c["id"],
        }).json()
        d = admin.delete(f"{API}/clients/{c['id']}")
        assert d.status_code == 200
        # user should be gone -> login invalid
        s = requests.Session()
        lr = _login(s, email, "Password123!")
        assert lr.status_code == 401
        # also not in /users list
        lst = admin.get(f"{API}/users").json()
        assert not any(x["id"] == u["id"] for x in lst)


# ---------------- Portal endpoints functionality ----------------
class TestPortalEndpoints:
    def test_portal_overview(self, acme_portal_session, acme_client_id):
        r = acme_portal_session.get(f"{API}/portal/overview")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["client"]["id"] == acme_client_id
        assert data["client"]["name"].lower() == "acme dental"
        # Expected demo computer per prompt
        names = [c["name"] for c in data["computers"]]
        assert "TT-ENG-WS03" in names
        # All computers should be Acme Dental's (no client_id field exposed, so trust server filter)
        assert len(data["computers"]) >= 1

    def test_portal_computer_report_data(self, acme_portal_session):
        r = acme_portal_session.get(f"{API}/portal/overview")
        cid = r.json()["computers"][0]["id"]
        rp = acme_portal_session.get(f"{API}/portal/computers/{cid}/report/data")
        assert rp.status_code == 200, rp.text
        rep = rp.json()
        assert rep.get("prepared_by") == "Temprudence Technologies (client portal copy)" or \
               "client portal copy" in json.dumps(rep).lower()

    def test_portal_fleet_data(self, acme_portal_session):
        r = acme_portal_session.get(f"{API}/portal/fleet/data")
        assert r.status_code == 200
        rep = r.json()
        assert "subtitle" in rep
        assert "acme" in rep["subtitle"].lower()

    @pytest.mark.parametrize("fmt,mime_frag", [
        ("docx", "wordprocessingml"),
        ("odt", "opendocument"),
        ("pdf", "pdf"),
    ])
    def test_portal_computer_export(self, acme_portal_session, fmt, mime_frag):
        cid = acme_portal_session.get(f"{API}/portal/overview").json()["computers"][0]["id"]
        r = acme_portal_session.get(f"{API}/portal/computers/{cid}/report/export", params={"format": fmt})
        assert r.status_code == 200
        assert mime_frag in r.headers.get("content-type", "").lower()
        cd = r.headers.get("content-disposition", "")
        assert fmt in cd.lower()

    @pytest.mark.parametrize("fmt", ["docx", "odt", "pdf"])
    def test_portal_fleet_export(self, acme_portal_session, fmt):
        r = acme_portal_session.get(f"{API}/portal/fleet/export", params={"format": fmt})
        assert r.status_code == 200
        assert fmt in r.headers.get("content-disposition", "").lower()

    def test_portal_own_logo(self, acme_portal_session, acme_client_id):
        r = acme_portal_session.get(f"{API}/clients/{acme_client_id}/logo")
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("image/")


# ---------------- Security: client -> 403 on staff APIs ----------------
STAFF_GETS = [
    "/computers", "/dashboard", "/alerts", "/keys", "/clients", "/users",
    "/settings/alerts", "/settings/report", "/scanner/info",
]


class TestClientForbiddenOnStaffAPIs:
    @pytest.mark.parametrize("path", STAFF_GETS)
    def test_get_forbidden(self, acme_portal_session, path):
        r = acme_portal_session.get(f"{API}{path}")
        assert r.status_code == 403, f"{path} returned {r.status_code}"

    def test_computer_detail_forbidden(self, acme_portal_session, admin):
        # Pick any computer that belongs to Acme (still should be 403 via staff endpoint)
        c = admin.get(f"{API}/computers").json()[0]
        r = acme_portal_session.get(f"{API}/computers/{c['id']}")
        assert r.status_code == 403

    def test_reports_computer_forbidden(self, acme_portal_session, admin):
        c = admin.get(f"{API}/computers").json()[0]
        r = acme_portal_session.get(f"{API}/reports/computer/{c['id']}/data")
        assert r.status_code == 403

    def test_reports_fleet_forbidden(self, acme_portal_session):
        r = acme_portal_session.get(f"{API}/reports/fleet/data")
        assert r.status_code == 403

    def test_scans_import_forbidden(self, acme_portal_session):
        r = acme_portal_session.post(f"{API}/scans/import",
                                     files={"file": ("x.json", b"{}", "application/json")})
        assert r.status_code == 403


# ---------------- Cross-tenant isolation ----------------
class TestCrossTenantIsolation:
    def test_other_clients_computer_404(self, acme_portal_session, admin):
        # Create a different client with a computer via scan import
        cname = f"TEST Other {uuid.uuid4().hex[:6]}"
        other = admin.post(f"{API}/clients", json={"name": cname}).json()
        key = admin.post(f"{API}/keys", json={"label": "iter4-other", "client_id": other["id"]}).json()
        scan = {
            "scanned_at": "2026-01-05T12:00:00+00:00",
            "scanner_version": "test",
            "system": {"computer_name": f"OTHER-{uuid.uuid4().hex[:4].upper()}", "serial": uuid.uuid4().hex[:10]},
        }
        sess = requests.Session()
        sess.post(f"{API}/agent/upload", data=json.dumps(scan).encode(),
                  headers={"X-Enroll-Key": key["key"], "Content-Type": "application/json"})
        # Get the computer id as admin
        other_comp = [c for c in admin.get(f"{API}/computers").json() if c.get("client_id") == other["id"]][0]
        try:
            r = acme_portal_session.get(f"{API}/portal/computers/{other_comp['id']}/report/data")
            assert r.status_code == 404
            r2 = acme_portal_session.get(f"{API}/portal/computers/{other_comp['id']}/report/export",
                                         params={"format": "docx"})
            assert r2.status_code == 404
            # Other client's logo (no logo on new client, but endpoint should 404 for client role)
            r3 = acme_portal_session.get(f"{API}/clients/{other['id']}/logo")
            assert r3.status_code == 404
        finally:
            admin.delete(f"{API}/computers/{other_comp['id']}")
            admin.delete(f"{API}/clients/{other['id']}")


# ---------------- Staff forbidden on /portal/* ----------------
PORTAL_GETS = ["/portal/overview", "/portal/fleet/data"]


class TestStaffForbiddenOnPortal:
    @pytest.mark.parametrize("path", PORTAL_GETS)
    def test_admin_403(self, admin, path):
        r = admin.get(f"{API}{path}")
        assert r.status_code == 403

    def test_admin_portal_report_data_403(self, admin):
        # Pick an Acme computer
        comps = admin.get(f"{API}/computers").json()
        cid = next((c["id"] for c in comps if c.get("name") == "TT-ENG-WS03"), comps[0]["id"])
        r = admin.get(f"{API}/portal/computers/{cid}/report/data")
        assert r.status_code == 403


# ---------------- Users page client-portal label check ----------------
class TestUsersListIncludesClientRole:
    def test_client_users_have_client_id(self, admin):
        users = admin.get(f"{API}/users").json()
        clients = [u for u in users if u.get("role") == "client"]
        assert len(clients) >= 1
        for u in clients:
            assert u.get("client_id")
