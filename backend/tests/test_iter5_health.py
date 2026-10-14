"""Iteration 5: Portal Health Summary tests."""
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN = {"email": "admin@temprudence.com", "password": "Temprudence2026!"}
CLIENT = {"email": "portal@acmedental.com", "password": "AcmePortal2026!"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login failed {creds['email']}: {r.status_code} {r.text}"
    s.headers.update({"Authorization": f"Bearer {r.json()['token']}"})
    return s


@pytest.fixture(scope="module")
def admin():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def client():
    return _login(CLIENT)


# --- Access control ---
def test_staff_forbidden(admin):
    r = admin.get(f"{BASE_URL}/api/portal/health")
    assert r.status_code == 403, f"expected 403 for staff, got {r.status_code}"


def test_unauth_denied():
    r = requests.get(f"{BASE_URL}/api/portal/health")
    assert r.status_code in (401, 403)


# --- Shape & grading ---
def test_health_shape(client):
    r = client.get(f"{BASE_URL}/api/portal/health")
    assert r.status_code == 200, r.text
    d = r.json()
    assert "overall" in d and "categories" in d and "computers" in d and "recommendations" in d
    o = d["overall"]
    assert 0 <= o["score"] <= 100
    assert o["grade"] in ("Excellent", "Good", "Fair", "Needs attention")
    assert isinstance(o["summary"], str) and len(o["summary"]) > 0
    assert o["computer_count"] == len(d["computers"])
    cat_keys = {c["key"] for c in d["categories"]}
    assert cat_keys == {"updates", "security", "access", "storage"}
    for c in d["categories"]:
        assert 0 <= c["percent"] <= 100
        assert c["status"] in ("good", "fair", "poor")
        assert c["message"]
    for comp in d["computers"]:
        assert 0 <= comp["score"] <= 100
        assert comp["grade"] in ("Excellent", "Good", "Fair", "Needs attention")


def test_client_only_sees_own_computers(admin, client):
    # staff sees all computers
    r = admin.get(f"{BASE_URL}/api/computers")
    assert r.status_code == 200
    all_comps = r.json()
    # client sees only computers assigned to Acme Dental
    r2 = client.get(f"{BASE_URL}/api/portal/health")
    client_names = {c["name"] for c in r2.json()["computers"]}
    # Any computer with no/other client_id should NOT appear
    from_acme_only = {c["name"] for c in all_comps if c.get("client_id")}
    assert client_names.issubset(from_acme_only), f"client sees unassigned/other-client: {client_names - from_acme_only}"
    unassigned = {c["name"] for c in all_comps if not c.get("client_id")}
    assert not (client_names & unassigned), f"client sees unassigned: {client_names & unassigned}"


# --- Math: TT-ENG-WS03 expected 75 Good (firewall off + stale updates) ---
@pytest.mark.asyncio
async def test_ws03_scoring():
    """Compute health for TT-ENG-WS03 directly via analysis to verify math."""
    import sys
    sys.path.insert(0, "/app/backend")
    from analysis import computer_health
    from dotenv import load_dotenv
    load_dotenv("/app/backend/.env")
    from motor.motor_asyncio import AsyncIOMotorClient
    c = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = c[os.environ["DB_NAME"]]
    comp = await db.computers.find_one({"name": "TT-ENG-WS03"}, {"_id": 0})
    assert comp is not None
    scan = await db.scans.find_one({"id": comp["last_scan_id"]}, {"_id": 0})
    assert scan is not None
    h = computer_health(scan["data"])
    print(f"TT-ENG-WS03 health: {h}")
    assert h["score"] == 75, f"expected 75, got {h['score']} cats={h['categories']} tips={h['tips']}"
    assert h["grade"] == "Good"
    assert h["categories"]["security"] == 20  # 35 - 15 firewall_off
    assert h["categories"]["updates"] == 20  # 30 - 10 updates_stale


# --- Multi-computer averaging via temporary reassignment ---
def test_multi_computer_averaging_and_recs(admin, client):
    # find TT-ACCOUNTING-02 and Acme Dental client id
    r = admin.get(f"{BASE_URL}/api/computers")
    comps = r.json()
    acc02 = next((c for c in comps if c["name"] == "TT-ACCOUNTING-02"), None)
    assert acc02 is not None, "TT-ACCOUNTING-02 missing"
    original_client_id = acc02.get("client_id") or ""

    r = admin.get(f"{BASE_URL}/api/clients")
    clients_list = r.json().get("clients", [])
    acme = next((c for c in clients_list if c["name"] == "Acme Dental"), None)
    assert acme is not None, "Acme Dental client missing"

    # Baseline: client health with 1 computer
    r = client.get(f"{BASE_URL}/api/portal/health")
    base = r.json()
    base_count = base["overall"]["computer_count"]

    try:
        # Assign TT-ACCOUNTING-02 to Acme Dental
        r = admin.patch(f"{BASE_URL}/api/computers/{acc02['id']}", json={"client_id": acme["id"]})
        assert r.status_code == 200, r.text

        r = client.get(f"{BASE_URL}/api/portal/health")
        assert r.status_code == 200
        d = r.json()
        assert d["overall"]["computer_count"] == base_count + 1
        names = {c["name"] for c in d["computers"]}
        assert "TT-ACCOUNTING-02" in names

        # recommendations should include at least Win10 EOL, firewall off, AV off, low disk, extra admins
        rec_texts = " | ".join(r["text"] for r in d["recommendations"])
        print("RECS:", rec_texts)
        expected_fragments = ["Upgrade to Windows 11", "firewall", "antivirus", "disk", "administrator"]
        missing = [f for f in expected_fragments if f.lower() not in rec_texts.lower()]
        assert not missing, f"missing rec fragments: {missing} | got: {rec_texts}"

        # averaging sanity: new overall is average of per-computer scores
        n = len(d["computers"])
        avg = round(sum(c["score"] for c in d["computers"]) / n)
        assert d["overall"]["score"] == avg
    finally:
        # Restore to unassigned
        r = admin.patch(f"{BASE_URL}/api/computers/{acc02['id']}", json={"client_id": ""})
        assert r.status_code == 200, f"restore failed: {r.text}"
        # verify
        r = admin.get(f"{BASE_URL}/api/computers")
        after = next((c for c in r.json() if c["name"] == "TT-ACCOUNTING-02"), None)
        assert not after.get("client_id"), f"expected unassigned, got {after.get('client_id')}"


# --- Regression: portal reports still work ---
def test_portal_fleet_data_still_works(client):
    r = client.get(f"{BASE_URL}/api/portal/fleet/data")
    assert r.status_code == 200


def test_portal_overview_still_works(client):
    r = client.get(f"{BASE_URL}/api/portal/overview")
    assert r.status_code == 200
    assert "computers" in r.json()
