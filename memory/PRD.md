# Temprudence Technologies — Windows Inventory Console (PRD)

## Original problem statement
Build a Temprudence Technologies branded web app to perform inventories on Windows computers from the browser (logo + branding guide supplied). Scan OS + version, installed applications + versions, computer settings incl. network configuration, network speed/throughput, hardware configuration and users with roles/privileges. Compile data in a database and produce inventory reports in the browser and in MS Word, ODT and PDF.

## Architecture
- FastAPI + MongoDB backend (`server.py`, `analysis.py` flags/diff, `reports.py` docx/odt/pdf via python-docx/odfpy/reportlab, `scanner_ps1.py` PowerShell template)
- React frontend (brand: #004070 / #B03010 / #002040, Aptos→Arial, Consolas mono; logo unaltered at ≥220px)
- JWT auth (cookies + bearer), roles admin/technician, brute-force lockout
- Scanner: PowerShell script with embedded console URL + upload key → POST /api/agent/upload; throughput test vs console

## Implemented (2026-06, Phase 2 features)
- Clients & sites: clients CRUD, upload keys carry client/site (auto-assign), manual reassignment on computer page (overrides key), client filter, per-client fleet reports
- Report branding: admin default sign-off note (Report settings), per-report "Prepared for" + sign-off on cover (browser + DOCX/ODT/PDF)
- Windows .exe scanner: unsigned C# launcher (`backend/scanner_exe/TemprudenceScanner.cs`, prebuilt `backend/assets/TemprudenceScanner.exe`, rebuilt with mono `mcs`); console appends URL/key/schedule config after `##TTCFG##` marker; self-elevates
- Weekly rescans: opt-in scheduled task (Mondays 9 AM, SYSTEM); in-app change alerts (apps added/removed, user/admin changes, new security findings), nav badge, ack/ack-all, dashboard scheduled/overdue counts

## Implemented (2026-06, client logos & alert rules)
- Client logos (admin upload PNG/JPG/WEBP ≤2MB → Emergent Object Storage, normalized PNG) shown next to Temprudence logo on report covers (browser, DOCX, ODT, PDF)
- Alert rules: default set in Settings + per-client override (apps installed/removed, account changes, admin rights, security findings, min severity)

## Implemented (2026-06, client portal)
- Role `client` (scoped to client_id), admin-created per client via Clients card; same sign-in redirects to /portal
- Portal: branded header (Temprudence + client logo), client's computers, per-computer reports + client summary, DOCX/ODT/PDF; staff APIs 403 for clients, cross-client 404

## Implemented (2026-06, portal health summary)
- /api/portal/health: 0-100 score (updates 30, security 35, access 20, storage 15), grade, plain-language category messages, ranked recommendations; per-computer Health column in portal

## Backlog
- P1: code-signing certificate for the .exe; email delivery for alerts
- P2 (Phase 3): network-wide scanning for domains; license/EOL tracking; emailed reports; audit log

## Implemented (2026-06, Phase 1 MVP)
- Login, admin user management (create/role/reset pw/disable/delete)
- Upload keys (create/revoke), PS1 scanner download + one-line command, JSON import for offline PCs
- Scan collects OS/updates/activation, software (64/32-bit/user), hardware, network adapters/Wi-Fi/firewall/proxy, throughput+latency, local users/groups/admins/sessions, UAC/BitLocker/AV/Defender/Secure Boot/TPM
- Dashboard with flags; computers list (search/filters); detail tabs; history + scan comparison
- Per-computer & fleet reports in browser + DOCX/ODT/PDF with cover, logo, confidentiality, "A Division of YFI Enterprises, LLC"
- Demo data seeder: `backend/seed_demo.py` (3 sample PCs currently in DB)

## Backlog
- P1 (Phase 2): packaged .exe scanner (code-signing later); scheduled recurring scans + change alerts; client/site grouping
- P2 (Phase 3): network-wide scanning for domains; license/EOL tracking; emailed reports; audit log
