"""Posts sample Windows scans to the local API (demo/testing data). Usage: python seed_demo.py"""
import copy
import json
import os
import random
import urllib.request
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
KEY = db.enroll_keys.find_one({"active": True})["key"]

APPS = [("Google Chrome", "125.0.6422.142", "Google LLC"), ("Microsoft Edge", "125.0.2535.92", "Microsoft Corporation"),
        ("Microsoft 365 Apps for business - en-us", "16.0.17628.20144", "Microsoft Corporation"), ("7-Zip 23.01 (x64)", "23.01", "Igor Pavlov"),
        ("Adobe Acrobat Reader (64-bit)", "24.002.20759", "Adobe"), ("Zoom Workplace", "6.0.11", "Zoom Video Communications, Inc."),
        ("Microsoft Teams", "24124.2311.2911.3341", "Microsoft Corporation"), ("Notepad++ (64-bit x64)", "8.6.7", "Notepad++ Team"),
        ("VLC media player", "3.0.20", "VideoLAN"), ("Mozilla Firefox (x64 en-US)", "126.0.1", "Mozilla"),
        ("Microsoft Visual C++ 2015-2022 Redistributable (x64)", "14.38.33135.0", "Microsoft Corporation"),
        ("Dell SupportAssist", "4.0.3.53766", "Dell Inc."), ("Git", "2.45.1", "The Git Development Community"),
        ("Python 3.12.3 (64-bit)", "3.12.3150.0", "Python Software Foundation"), ("Visual Studio Code", "1.90.0", "Microsoft Corporation"),
        ("QuickBooks Desktop Pro 2023", "33.0.4005.3305", "Intuit Inc."), ("TeamViewer", "15.54.3", "TeamViewer")]


def scan(name, serial, cap, ver, build, maker, model, users, admins, free_c, sw_n, fw_ok=True, av_ok=True, days_ago=0, extra_apps=()):
    apps = [{"name": n, "version": v, "publisher": p, "install_date": "2024-03-1" + str(i % 9), "arch": "64-bit" if i % 3 else "32-bit", "size_mb": 120.5}
            for i, (n, v, p) in enumerate(APPS[:sw_n])] + list(extra_apps)
    loc = []
    for u in ["Administrator", "Guest", "DefaultAccount", "WDAGUtilityAccount"] + users:
        builtin = u in ("Administrator", "Guest", "DefaultAccount", "WDAGUtilityAccount")
        adm = u in admins or u == "Administrator"
        groups = (["Administrators"] if adm else []) + ([] if builtin else ["Users"]) + (["Remote Desktop Users"] if u == users[0] else [])
        loc.append({"name": u, "full_name": u.title(), "enabled": not builtin, "description": "Built-in account" if builtin else "",
                    "last_logon": (datetime.now(timezone.utc) - timedelta(days=random.randint(0, 20))).isoformat() if not builtin else None,
                    "password_last_set": "2024-01-10T15:00:00Z", "password_required": True, "password_expires": None,
                    "sid": f"S-1-5-21-1000-{random.randint(1000, 9999)}", "groups": groups, "is_admin": adm})
    groups = [{"name": "Administrators", "sid": "S-1-5-32-544", "description": "Administrators have complete and unrestricted access",
               "is_admin_group": True, "members": [{"name": f"{name}\\{u['name']}", "type": "User", "source": "Local"} for u in loc if u["is_admin"]]},
              {"name": "Users", "sid": "S-1-5-32-545", "description": "Users are prevented from making system-wide changes", "is_admin_group": False,
               "members": [{"name": f"{name}\\{u['name']}", "type": "User", "source": "Local"} for u in loc if "Users" in u["groups"]]},
              {"name": "Remote Desktop Users", "sid": "S-1-5-32-555", "description": "Granted the right to logon remotely", "is_admin_group": False,
               "members": [{"name": f"{name}\\{users[0]}", "type": "User", "source": "Local"}]}]
    t = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return {
        "scanner_version": "1.0.0", "scanned_at": t.isoformat(), "is_admin": True, "limited_sections": [],
        "system": {"computer_name": name, "dns_hostname": name, "domain": "WORKGROUP", "part_of_domain": False, "workgroup": "WORKGROUP",
                   "domain_role": 0, "manufacturer": maker, "model": model, "system_type": "x64-based PC", "serial": serial,
                   "bios_vendor": maker, "bios_version": "1.18.0", "bios_date": "2023-11-02T00:00:00Z",
                   "timezone": "(UTC-05:00) Eastern Time (US & Canada)", "timezone_id": "Eastern Standard Time",
                   "current_user": f"{name}\\{users[0]}", "scan_user": f"{name}\\{users[0]}"},
        "os": {"caption": cap, "version": f"10.0.{build.split('.')[0]}", "display_version": ver, "build": build, "edition_id": "Professional",
               "architecture": "64-bit", "install_date": "2023-06-14T13:22:00Z", "last_boot": (t - timedelta(hours=30)).isoformat(),
               "registered_owner": users[0], "organization": "", "language": "en-US", "activation_status": "Licensed",
               "hotfixes": [{"id": f"KB50{37000 + i * 13}", "description": "Security Update", "installed_on": f"2024-0{1 + i % 6}-12T00:00:00Z"} for i in range(6)]},
        "hardware": {"cpu": [{"name": "Intel(R) Core(TM) i7-1265U", "manufacturer": "GenuineIntel", "cores": 10, "logical": 12, "max_clock_mhz": 1800, "socket": "U3E1"}],
                     "memory_total_gb": 15.7, "memory_modules": [{"capacity_gb": 8, "speed_mhz": 3200, "manufacturer": "Samsung", "part_number": "M471A1K43DB1-CWE", "slot": f"DIMM {i}"} for i in (0, 1)],
                     "volumes": [{"device": "C:", "label": "OS", "filesystem": "NTFS", "size_gb": 475.8, "free_gb": free_c}],
                     "physical_disks": [{"model": "SAMSUNG MZVL2512HCJQ-00BL7", "interface": "SCSI", "media_type": "SSD", "size_gb": 476.9, "serial": "S64KNX0T1234", "partitions": 4}],
                     "gpu": [{"name": "Intel(R) Iris(R) Xe Graphics", "driver_version": "31.0.101.4502", "vram_mb": 128, "resolution": "1920x1080"}],
                     "battery": [{"name": "DELL M033W33", "charge_pct": 87, "status": "On AC power"}]},
        "software": apps,
        "network": {"adapters": [{"name": "Wi-Fi", "description": "Intel(R) Wi-Fi 6E AX211 160MHz", "mac": "A4-6B-B6-12-34-" + serial[-2:], "status": "Up",
                                  "link_speed": "866.7 Mbps", "link_speed_bps": 866700000, "media_type": "Native 802.11", "physical": True,
                                  "ipv4": ["192.168.1." + str(20 + len(name))], "ipv6": ["fe80::1c2d:3e4f:5a6b:7c8d"], "subnet": ["255.255.255.0"],
                                  "gateway": ["192.168.1.1"], "dns": ["192.168.1.1", "1.1.1.1"], "dhcp": True, "dhcp_server": "192.168.1.1", "dns_suffix": "home"},
                                 {"name": "Ethernet", "description": "Realtek USB GbE Family Controller", "mac": "00-E0-4C-68-01-" + serial[-2:], "status": "Disconnected",
                                  "link_speed": "0 bps", "link_speed_bps": 0, "media_type": "802.3", "physical": True, "ipv4": [], "ipv6": [], "subnet": [],
                                  "gateway": [], "dns": [], "dhcp": True, "dhcp_server": None, "dns_suffix": None}],
                    "wifi": {"ssid": "Temprudence-Office", "bssid": "3c:84:6a:aa:bb:cc", "state": "connected", "signal": "92%", "authentication": "WPA2-Personal",
                             "cipher": "CCMP", "radio_type": "802.11ax", "channel": "44", "receive_rate_mbps": "866.7", "transmit_rate_mbps": "866.7"},
                    "firewall": [{"profile": p, "enabled": fw_ok or p != "Public", "inbound": "Block", "outbound": "Allow"} for p in ("Domain", "Private", "Public")],
                    "proxy": {"enabled": False, "server": None, "bypass": None, "auto_config_url": None, "winhttp": "Current WinHTTP proxy settings: Direct access (no proxy server)."}},
        "speed": {"target": "https://console", "latency_ms": round(random.uniform(18, 60), 1), "latency_min_ms": 15.2,
                  "download_mbps": round(random.uniform(80, 400), 2), "upload_mbps": round(random.uniform(20, 90), 2), "download_mb": 10, "upload_mb": 5, "error": None},
        "users": {"local": loc, "groups": groups, "admin_group": "Administrators", "sessions": [f">{users[0].lower()}  console  1  Active  none  {t.strftime('%m/%d/%Y %H:%M')}"],
                  "current_user": f"{name}\\{users[0]}"},
        "security": {"uac_enabled": True, "bitlocker": [{"mount": "C:", "protection": "On" if av_ok else "Off", "status": "FullyEncrypted" if av_ok else "FullyDecrypted",
                                                          "encryption_pct": 100 if av_ok else 0, "method": "XtsAes128"}],
                     "antivirus": [{"name": "Windows Defender", "enabled": av_ok, "up_to_date": True, "state_hex": "061100" if av_ok else "060100"}],
                     "defender": {"antivirus_enabled": av_ok, "realtime": av_ok, "signature_age_days": 0, "signature_version": "1.413.123.0", "last_quick_scan": t.isoformat()},
                     "secure_boot": True, "tpm": {"present": True, "ready": True}},
    }


def post(d):
    req = urllib.request.Request("http://localhost:8001/api/agent/upload", data=json.dumps(d).encode(),
                                 headers={"Content-Type": "application/json", "X-Enroll-Key": KEY}, method="POST")
    print(json.loads(urllib.request.urlopen(req).read()))


old = scan("TT-RECEPTION-01", "7XK2Q93", "Microsoft Windows 11 Pro", "23H2", "22631.3593", "Dell Inc.", "Latitude 5430", ["jsmith"], [], 212.4, 12, days_ago=30)
new = copy.deepcopy(old)
new.update(scan("TT-RECEPTION-01", "7XK2Q93", "Microsoft Windows 11 Pro", "23H2", "22631.3737", "Dell Inc.", "Latitude 5430", ["jsmith", "temp.contractor"],
                ["temp.contractor"], 168.9, 14, extra_apps=[{"name": "AnyDesk", "version": "8.0.10", "publisher": "AnyDesk Software GmbH", "install_date": "2024-06-02", "arch": "32-bit", "size_mb": 6.1}]))
new["software"][0]["version"] = "126.0.6478.62"
for d in (old, new):
    post(d)
post(scan("TT-ACCOUNTING-02", "5CG1234XYZ", "Microsoft Windows 10 Pro", "22H2", "19045.4529", "HP", "EliteBook 840 G8", ["mdavis", "bookkeeper"],
          ["mdavis", "bookkeeper"], 21.3, 16, fw_ok=False, av_ok=False, days_ago=2))
post(scan("TT-ENG-WS03", "PF3ABCDE", "Microsoft Windows 11 Enterprise", "24H2", "26100.1150", "Lenovo", "ThinkPad T14 Gen 4", ["rgarcia"], [], 302.0, 17, days_ago=1))
