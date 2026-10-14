# Temprudence Technologies — Windows Inventory Console (PRD)

## Original problem statement
Build a Temprudence Technologies branded web app to perform inventories on Windows computers from the browser (logo + branding guide supplied). Scan OS + version, installed applications + versions, computer settings incl. network configuration, network speed/throughput, hardware configuration and users with roles/privileges. Compile data in a database and produce inventory reports in the browser and in MS Word, ODT and PDF.

## Architecture
- FastAPI + MongoDB backend (`server.py`, `analysis.py` flags/diff, `reports.py` docx/odt/pdf via python-docx/odfpy/reportlab, `scanner_ps1.py` PowerShell template)
- React frontend (brand: #004070 / #B03010 / #002040, Aptos→Arial, Consolas mono; logo unaltered at ≥220px)
- JWT auth (cookies + bearer), roles admin/technician, brute-force lockout
- Scanner: PowerShell script with embedded console URL + upload key → POST /api/agent/upload; throughput test vs console

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
