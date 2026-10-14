import re


def _f(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def _l(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def admin_accounts(d):
    users = _l((d.get("users") or {}).get("local"))
    return [u for u in users if u.get("is_admin") and u.get("enabled")]


def admin_group_members(d):
    for g in _l((d.get("users") or {}).get("groups")):
        if g.get("is_admin_group"):
            return [m.get("name") for m in _l(g.get("members"))]
    return []


def primary_ip(d):
    for a in _l((d.get("network") or {}).get("adapters")):
        if str(a.get("status", "")).lower() == "up":
            ips = _l(a.get("ipv4"))
            if ips:
                return ips[0]
    return None


def build_number(d):
    os_ = d.get("os") or {}
    m = re.match(r"(\d+)", str(os_.get("build") or os_.get("version", "").split(".")[-1] or ""))
    return int(m.group(1)) if m else 0


def summarize(d):
    os_ = d.get("os") or {}
    sy = d.get("system") or {}
    hw = d.get("hardware") or {}
    sp = d.get("speed") or {}
    vols = _l(hw.get("volumes"))
    cpus = _l(hw.get("cpu"))
    return {
        "computer_name": sy.get("computer_name"),
        "os_caption": os_.get("caption"),
        "os_version": os_.get("display_version") or os_.get("version"),
        "os_build": os_.get("build"),
        "manufacturer": sy.get("manufacturer"),
        "model": sy.get("model"),
        "serial": sy.get("serial"),
        "domain": sy.get("domain"),
        "part_of_domain": sy.get("part_of_domain"),
        "current_user": sy.get("current_user") or sy.get("scan_user"),
        "cpu": cpus[0].get("name") if cpus else None,
        "memory_gb": hw.get("memory_total_gb"),
        "disk_total_gb": round(sum(_f(v.get("size_gb")) for v in vols), 1),
        "disk_free_gb": round(sum(_f(v.get("free_gb")) for v in vols), 1),
        "software_count": len(_l(d.get("software"))),
        "user_count": len(_l((d.get("users") or {}).get("local"))),
        "admin_count": len(admin_accounts(d)),
        "ip": primary_ip(d),
        "download_mbps": sp.get("download_mbps"),
        "upload_mbps": sp.get("upload_mbps"),
        "latency_ms": sp.get("latency_ms"),
        "is_admin_scan": bool(d.get("is_admin")),
        "limited_sections": _l(d.get("limited_sections")),
    }


def _flag(code, severity, category, title, detail):
    return {"code": code, "severity": severity, "category": category, "title": title, "detail": detail}


def compute_flags(d):
    flags = []
    os_ = d.get("os") or {}
    cap = str(os_.get("caption") or "")
    build = build_number(d)
    if "Windows 10" in cap:
        flags.append(_flag("os_eol", "high", "Operating system", "Windows 10 is past end of support",
                           f"{cap} (build {os_.get('build')}) no longer receives standard security updates."))
    elif "Windows 11" in cap and build and build < 22631:
        flags.append(_flag("os_outdated", "medium", "Operating system", "Outdated Windows 11 build",
                           f"Build {os_.get('build')} is older than 23H2 (22631)."))
    elif "Server" in cap and build and build < 14393:
        flags.append(_flag("os_eol", "high", "Operating system", "Unsupported Windows Server", cap))
    act = os_.get("activation_status")
    if act and act not in ("Licensed", "Unknown"):
        flags.append(_flag("not_activated", "medium", "Operating system", "Windows not activated", f"Status: {act}"))

    admins = admin_accounts(d)
    if len(admins) > 1:
        flags.append(_flag("extra_admins", "medium", "Users & privileges", f"{len(admins)} enabled local administrators",
                           ", ".join(a.get("name", "") for a in admins)))
    for u in _l((d.get("users") or {}).get("local")):
        if u.get("enabled") and u.get("password_required") is False:
            flags.append(_flag("no_password", "high", "Users & privileges", "Account without required password",
                               u.get("name", "")))

    sec = d.get("security") or {}
    if sec.get("uac_enabled") is False:
        flags.append(_flag("uac_off", "high", "Security", "User Account Control is disabled", "EnableLUA = 0"))
    fw_off = [p.get("profile") for p in _l((d.get("network") or {}).get("firewall")) if p.get("enabled") is False]
    if fw_off:
        flags.append(_flag("firewall_off", "high", "Security", "Firewall profile disabled", ", ".join(fw_off)))
    av = _l(sec.get("antivirus"))
    dfd = sec.get("defender") or {}
    if av:
        if not any(a.get("enabled") for a in av):
            flags.append(_flag("av_off", "high", "Security", "No active antivirus", ", ".join(a.get("name", "") for a in av)))
        elif not any(a.get("enabled") and a.get("up_to_date") for a in av):
            flags.append(_flag("av_outdated", "medium", "Security", "Antivirus definitions out of date", ""))
    elif dfd and dfd.get("antivirus_enabled") is False:
        flags.append(_flag("av_off", "high", "Security", "Microsoft Defender antivirus disabled", ""))
    bl = _l(sec.get("bitlocker"))
    os_drive = next((b for b in bl if str(b.get("mount", "")).upper().startswith("C")), None)
    if os_drive and str(os_drive.get("protection", "")).lower() not in ("on", "1"):
        flags.append(_flag("bitlocker_off", "medium", "Security", "OS drive not protected by BitLocker",
                           f"{os_drive.get('mount')} protection: {os_drive.get('protection')}"))

    for v in _l((d.get("hardware") or {}).get("volumes")):
        size, free = _f(v.get("size_gb")), _f(v.get("free_gb"))
        if size > 0 and (free / size < 0.15 or free < 10):
            flags.append(_flag("low_disk", "medium" if free / size >= 0.05 else "high", "Hardware",
                               f"Low disk space on {v.get('device')}", f"{free} GB free of {size} GB ({round(free / size * 100)}%)"))

    if d.get("limited_sections"):
        flags.append(_flag("limited_scan", "low", "Scan", "Scan ran without Administrator rights",
                           "Limited: " + ", ".join(_l(d.get("limited_sections")))))
    return flags


def status_from_flags(flags):
    sev = {f.get("severity") for f in flags}
    if "high" in sev:
        return "critical"
    if "medium" in sev:
        return "warning"
    return "ok"


def _by(items, key):
    return {str(i.get(key) or "").lower(): i for i in _l(items) if i.get(key)}


def diff_scans(a, b):
    sa, sb = _by(a.get("software"), "name"), _by(b.get("software"), "name")
    software = {
        "added": [sb[k] for k in sorted(set(sb) - set(sa))],
        "removed": [sa[k] for k in sorted(set(sa) - set(sb))],
        "updated": [{"name": sb[k].get("name"), "from": sa[k].get("version"), "to": sb[k].get("version")}
                    for k in sorted(set(sa) & set(sb)) if str(sa[k].get("version")) != str(sb[k].get("version"))],
    }

    def fields(d, spec):
        return {label: fn(d) for label, fn in spec.items()}

    def changes(spec):
        fa, fb = fields(a, spec), fields(b, spec)
        return [{"field": k, "from": fa[k], "to": fb[k]} for k in spec if str(fa[k]) != str(fb[k])]

    hw = lambda d: d.get("hardware") or {}
    os_spec = {
        "OS": lambda d: (d.get("os") or {}).get("caption"),
        "Version": lambda d: (d.get("os") or {}).get("display_version"),
        "Build": lambda d: (d.get("os") or {}).get("build"),
        "Activation": lambda d: (d.get("os") or {}).get("activation_status"),
        "Updates installed": lambda d: len(_l((d.get("os") or {}).get("hotfixes"))),
    }
    hw_spec = {
        "CPU": lambda d: ", ".join(c.get("name", "") for c in _l(hw(d).get("cpu"))),
        "Memory (GB)": lambda d: hw(d).get("memory_total_gb"),
        "Volumes": lambda d: ", ".join(f"{v.get('device')} {v.get('size_gb')}GB" for v in _l(hw(d).get("volumes"))),
        "Physical disks": lambda d: ", ".join(p.get("model", "") for p in _l(hw(d).get("physical_disks"))),
        "GPU": lambda d: ", ".join(g.get("name", "") for g in _l(hw(d).get("gpu"))),
        "BIOS": lambda d: (d.get("system") or {}).get("bios_version"),
    }
    net = lambda d: _l((d.get("network") or {}).get("adapters"))
    net_spec = {
        "Adapters": lambda d: ", ".join(sorted(x.get("name", "") for x in net(d))),
        "IPv4": lambda d: ", ".join(sorted(ip for x in net(d) for ip in _l(x.get("ipv4")))),
        "Gateways": lambda d: ", ".join(sorted(g for x in net(d) for g in _l(x.get("gateway")) if g)),
        "DNS": lambda d: ", ".join(sorted({s for x in net(d) for s in _l(x.get("dns")) if s})),
        "MAC": lambda d: ", ".join(sorted(x.get("mac", "") for x in net(d) if x.get("mac"))),
        "Wi-Fi SSID": lambda d: ((d.get("network") or {}).get("wifi") or {}).get("ssid"),
    }
    ua, ub = _by((a.get("users") or {}).get("local"), "name"), _by((b.get("users") or {}).get("local"), "name")
    user_changes = []
    for k in sorted(set(ub) - set(ua)):
        user_changes.append({"user": ub[k]["name"], "change": "Account added"})
    for k in sorted(set(ua) - set(ub)):
        user_changes.append({"user": ua[k]["name"], "change": "Account removed"})
    for k in sorted(set(ua) & set(ub)):
        x, y = ua[k], ub[k]
        if x.get("enabled") != y.get("enabled"):
            user_changes.append({"user": y["name"], "change": "Enabled" if y.get("enabled") else "Disabled"})
        if bool(x.get("is_admin")) != bool(y.get("is_admin")):
            user_changes.append({"user": y["name"], "change": "Granted Administrator" if y.get("is_admin") else "Removed from Administrators"})
        ga, gb = set(_l(x.get("groups"))), set(_l(y.get("groups")))
        if ga != gb:
            user_changes.append({"user": y["name"], "change": f"Groups: +{', '.join(sorted(gb - ga)) or '-'} / -{', '.join(sorted(ga - gb)) or '-'}"})
    return {
        "software": software,
        "os": changes(os_spec),
        "hardware": changes(hw_spec),
        "network": changes(net_spec),
        "users": user_changes,
    }
