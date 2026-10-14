# Temprudence Technologies — Windows Inventory Console

A Temprudence-branded web console that collects detailed inventories from Windows computers, stores every scan, and lets technicians browse, compare, and export them.
A small scanner runs on each PC (PowerShell script or Windows .exe), sends its results to the console, and the console produces reports in the browser and as Word, ODT, and PDF files.

## Who it's for
- **Admins** at Temprudence Technologies who manage users, enrollment keys, and the whole fleet of client computers.
- **Technicians** who scan computers, review results, and hand inventory reports to clients.

## Core features and experience
- **Sign-in with roles**: email and password. Admins manage technicians and everything else. Technicians can scan, view, and export reports but can't manage users.
- **Scanner download**: a "Scan a computer" page offers a PowerShell script (phase 1) and a Windows .exe (phase 2). Both come with a built-in upload key, so the results go straight to the console and no one has to sign in on the PC itself.
- **What each scan collects**:
  - Operating system: edition, version, build, install date, last boot, activation status, and installed updates.
  - Installed applications: name, version, publisher, and install date (both 64-bit and 32-bit software).
  - Hardware: manufacturer and model, serial number, BIOS, CPU, memory, disks with free space, GPU, and battery where present.
  - Network configuration: adapters, MAC addresses, IP, subnet, gateway, DNS, DHCP, Wi-Fi, firewall profiles, and proxy settings.
  - Network speed: link speed for each adapter, plus a measured download/upload throughput test and latency to the console.
  - Users and privileges: local accounts, enabled/disabled status, last logon, group memberships (Administrators, Users, Remote Desktop Users, and others), and the currently signed-in user.
  - Key settings: time zone, domain or workgroup, BitLocker status, antivirus status, and UAC.
- **Computers list**: every scanned PC with its last scan date, OS, owner, and status. You can search and filter.
- **Computer detail**: tabs for Overview, Software, Hardware, Network, Users & Privileges, and History.
- **History and comparison**: every scan is kept. You can pick any two scans of a PC to see what changed: apps added, removed, or updated, plus hardware, user, and network changes.
- **Reports**:
  - A per-computer report, viewable in the browser and exportable as MS Word (.docx), ODT, and PDF.
  - A fleet summary report covering all or selected computers (OS spread, outdated OS builds, admin-account counts, low disk space, software counts), exportable in the same three formats.
  - Every export carries the Temprudence logo, a cover page, a confidentiality notice, and the line "A Division of YFI Enterprises, LLC".
- **Dashboard**: fleet totals, recent scans, and flagged items such as extra administrators, disabled security, low disk space, and old OS builds.

## User flow
1. An admin signs in and creates technician accounts.
2. A technician opens "Scan a computer" and downloads the PowerShell script.
3. On the Windows PC, the technician runs the script as Administrator, using the one-line command copied from the console. The script runs for about 1–2 minutes, then uploads.
4. The PC appears in the Computers list. The technician opens it and reviews each tab.
5. Later scans of the same PC are added to its History, and any two scans can be compared.
6. The technician exports the per-computer report or the fleet summary as Word, ODT, or PDF.

## UI/UX feel
- Follows the brand guide. Deep Tech Blue (#004070) dominates for navigation and headings. Rust Red (#B03010) is reserved for calls to action and warnings. Midnight Navy (#002040) is used for formal surfaces, with white space throughout.
- Fonts: Aptos for headings and body, with Arial as the fallback, and Consolas for technical data.
- The full logo is used unaltered: on the sign-in page, in report headers, and in the app header at 220px or wider, with the required clear space around it.
- The tone is calm, competent, and security-minded. The layout is clean and data-dense, with clear tables. Status is never shown by color alone; icons and labels go with it.

## Implementation phases
**Phase 1 — MVP (built now)**
- Sign-in with Admin and Technician roles, and user management.
- PowerShell scanner covering every category above, including the throughput test, with automatic upload.
- Computers list, computer detail tabs, scan history, and comparison between two scans.
- Per-computer and fleet summary reports in the browser, plus Word, ODT, and PDF export.
- Dashboard with flagged items.

**Phase 2**
- Packaged Windows .exe scanner, built from the same scan logic. It will be unsigned at first, so Windows SmartScreen will show a warning until a code-signing certificate is added.
- Scheduled recurring scans on each PC, plus alerts for significant changes.
- Client/site grouping, so reports can be organized by customer.

**Phase 3**
- Network-wide scanning from a single machine for domain environments.
- Software license and end-of-life tracking.
- Emailed reports and an audit log of who viewed or exported what.

## Assumptions
- Browsers can't read system details, so all scanning happens through the downloaded scanner. The web app only displays and reports.
- The .exe is in phase 2 because it needs a separate packaging and signing step. Phase 1 delivers the PowerShell scanner, which collects the same data.
- The scanner needs Administrator rights on the PC to read users, privileges, BitLocker, and some settings. Without those rights, it collects what it can and marks those sections as limited.
- Supported systems are Windows 10, Windows 11, and Windows Server 2016 or later.
- Network throughput is measured against the console server, so it reflects the PC's path to the console, not its full internet speed.
- An upload key controls which scanners may send data. Admins can create and revoke keys.
- A PC is identified across scans by its hardware serial number and computer name.
- Scan data is kept indefinitely until an admin deletes a computer.
- The supplied PNG logo is used as-is. No emblem-only variant is created, because the brand guide requires that variant to be formally approved first.
- New accounts are created only by admins. There is no public sign-up.
