SCRIPT = r'''# =====================================================================
#  Temprudence Technologies - Windows Inventory Scanner v__VERSION__
#  A Division of YFI Enterprises, LLC
#  Run in an elevated PowerShell (Run as Administrator) for a full scan.
#  Optional environment switches before running:
#    $env:TT_NOUPLOAD = '1'     save results locally only
#    $env:TT_NOSPEED  = '1'     skip the throughput test
# =====================================================================
$ErrorActionPreference = 'SilentlyContinue'
$ProgressPreference = 'SilentlyContinue'
$ConsoleUrl = '__CONSOLE_URL__'
$EnrollKey = '__ENROLL_KEY__'
$ScannerVersion = '__VERSION__'
try { [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12 } catch {}

function Iso($d) { if ($d) { try { return ([datetime]$d).ToUniversalTime().ToString('o') } catch { return [string]$d } }; return $null }
function Step($m) { Write-Host "  [*] $m" -ForegroundColor Cyan }
function Arr($x) { $l = New-Object System.Collections.ArrayList; foreach ($i in @($x)) { if ($null -ne $i) { [void]$l.Add($i) } }; return ,$l }

Write-Host ''
Write-Host '  TEMPRUDENCE TECHNOLOGIES - Windows Inventory Scanner' -ForegroundColor White
Write-Host '  Veteran Owned - Faith Based - Ethical - Principled' -ForegroundColor DarkGray
Write-Host ''
$limited = New-Object System.Collections.ArrayList
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) { Write-Host '  [!] Not running as Administrator - some sections will be limited.' -ForegroundColor Yellow }

# ---------------- System & OS ----------------
Step 'System and operating system'
$cs = Get-CimInstance Win32_ComputerSystem
$bios = Get-CimInstance Win32_BIOS
$osi = Get-CimInstance Win32_OperatingSystem
$csp = Get-CimInstance Win32_ComputerSystemProduct
$cv = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
$uacVal = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System').EnableLUA
$tz = Get-TimeZone
$system = [ordered]@{
  computer_name = $env:COMPUTERNAME
  dns_hostname = $cs.DNSHostName
  domain = $cs.Domain
  part_of_domain = [bool]$cs.PartOfDomain
  workgroup = $cs.Workgroup
  domain_role = $cs.DomainRole
  manufacturer = $cs.Manufacturer
  model = $cs.Model
  system_type = $cs.SystemType
  serial = $bios.SerialNumber
  uuid = $csp.UUID
  bios_vendor = $bios.Manufacturer
  bios_version = $bios.SMBIOSBIOSVersion
  bios_date = Iso $bios.ReleaseDate
  timezone = $tz.DisplayName
  timezone_id = $tz.Id
  current_user = $cs.UserName
  scan_user = "$env:USERDOMAIN\$env:USERNAME"
}
$act = 'Unknown'
$lic = Get-CimInstance SoftwareLicensingProduct -Filter "ApplicationID='55c92734-d682-4d71-983e-d6ec3f16059f' AND PartialProductKey IS NOT NULL" | Select-Object -First 1
if ($lic) { $act = switch ([int]$lic.LicenseStatus) { 0 {'Unlicensed'} 1 {'Licensed'} 2 {'OOB Grace'} 3 {'OOT Grace'} 4 {'Non-Genuine Grace'} 5 {'Notification'} 6 {'Extended Grace'} default {'Unknown'} } }
$hotfixes = New-Object System.Collections.ArrayList
foreach ($h in @(Get-HotFix)) { $io = $null; try { $io = Iso $h.InstalledOn } catch {}; [void]$hotfixes.Add([ordered]@{ id = $h.HotFixID; description = $h.Description; installed_on = $io }) }
$ubr = ''; if ($null -ne $cv.UBR) { $ubr = ".$($cv.UBR)" }
$os = [ordered]@{
  caption = $osi.Caption
  version = $osi.Version
  display_version = $(if ($cv.DisplayVersion) { $cv.DisplayVersion } else { $cv.ReleaseId })
  build = "$($osi.BuildNumber)$ubr"
  edition_id = $cv.EditionID
  architecture = $osi.OSArchitecture
  install_date = Iso $osi.InstallDate
  last_boot = Iso $osi.LastBootUpTime
  registered_owner = $osi.RegisteredUser
  organization = $osi.Organization
  language = $osi.MUILanguages -join ', '
  activation_status = $act
  hotfixes = $hotfixes
}

# ---------------- Software ----------------
Step 'Installed applications'
$software = New-Object System.Collections.ArrayList
$seen = @{}
$paths = @(
  @('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*', '64-bit'),
  @('HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*', '32-bit'),
  @('HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*', 'Current user')
)
foreach ($p in $paths) {
  foreach ($app in @(Get-ItemProperty $p[0])) {
    if (-not $app.DisplayName -or $app.SystemComponent -eq 1 -or $app.ParentKeyName) { continue }
    $k = "$($app.DisplayName)|$($app.DisplayVersion)"
    if ($seen.ContainsKey($k)) { continue }
    $seen[$k] = 1
    $idt = $null
    if ([string]$app.InstallDate -match '^\d{8}$') { $s = [string]$app.InstallDate; $idt = "$($s.Substring(0,4))-$($s.Substring(4,2))-$($s.Substring(6,2))" }
    $size = $null; if ($app.EstimatedSize) { $size = [math]::Round($app.EstimatedSize / 1024, 1) }
    [void]$software.Add([ordered]@{ name = ([string]$app.DisplayName).Trim(); version = [string]$app.DisplayVersion; publisher = $app.Publisher; install_date = $idt; arch = $p[1]; size_mb = $size })
  }
}

# ---------------- Hardware ----------------
Step 'Hardware configuration'
$cpus = Arr (Get-CimInstance Win32_Processor | ForEach-Object { [ordered]@{ name = ([string]$_.Name).Trim(); manufacturer = $_.Manufacturer; cores = $_.NumberOfCores; logical = $_.NumberOfLogicalProcessors; max_clock_mhz = $_.MaxClockSpeed; socket = $_.SocketDesignation } })
$mods = Arr (Get-CimInstance Win32_PhysicalMemory | ForEach-Object { [ordered]@{ capacity_gb = [math]::Round($_.Capacity / 1GB, 1); speed_mhz = $_.Speed; manufacturer = $_.Manufacturer; part_number = ([string]$_.PartNumber).Trim(); slot = $_.DeviceLocator } })
$vols = Arr (Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | ForEach-Object { [ordered]@{ device = $_.DeviceID; label = $_.VolumeName; filesystem = $_.FileSystem; size_gb = [math]::Round($_.Size / 1GB, 1); free_gb = [math]::Round($_.FreeSpace / 1GB, 1) } })
$pmedia = @{}; foreach ($pd in @(Get-PhysicalDisk)) { $pmedia[[string]$pd.FriendlyName] = [string]$pd.MediaType }
$pdisks = Arr (Get-CimInstance Win32_DiskDrive | ForEach-Object { $mt = $pmedia[[string]$_.Model]; if (-not $mt) { $mt = $_.MediaType }; [ordered]@{ model = $_.Model; interface = $_.InterfaceType; media_type = $mt; size_gb = [math]::Round($_.Size / 1GB, 1); serial = ([string]$_.SerialNumber).Trim(); partitions = $_.Partitions } })
$gpus = Arr (Get-CimInstance Win32_VideoController | ForEach-Object { [ordered]@{ name = $_.Name; driver_version = $_.DriverVersion; vram_mb = [math]::Round($_.AdapterRAM / 1MB); resolution = "$($_.CurrentHorizontalResolution)x$($_.CurrentVerticalResolution)" } })
$batStatus = @{ 1 = 'Discharging'; 2 = 'On AC power'; 3 = 'Fully charged'; 4 = 'Low'; 5 = 'Critical'; 6 = 'Charging'; 7 = 'Charging (high)'; 8 = 'Charging (low)'; 9 = 'Charging (critical)'; 11 = 'Partially charged' }
$bats = Arr (Get-CimInstance Win32_Battery | ForEach-Object { [ordered]@{ name = $_.Name; charge_pct = $_.EstimatedChargeRemaining; status = $batStatus[[int]$_.BatteryStatus] } })
$hardware = [ordered]@{
  cpu = $cpus
  memory_total_gb = [math]::Round($cs.TotalPhysicalMemory / 1GB, 1)
  memory_modules = $mods
  volumes = $vols
  physical_disks = $pdisks
  gpu = $gpus
  battery = $bats
}

# ---------------- Network ----------------
Step 'Network configuration'
$cfgs = @(Get-CimInstance Win32_NetworkAdapterConfiguration)
$adapters = New-Object System.Collections.ArrayList
foreach ($na in @(Get-NetAdapter)) {
  $c = $cfgs | Where-Object { $_.InterfaceIndex -eq $na.ifIndex } | Select-Object -First 1
  $ipv4 = New-Object System.Collections.ArrayList; $ipv6 = New-Object System.Collections.ArrayList; $subs = New-Object System.Collections.ArrayList
  if ($c -and $c.IPAddress) {
    for ($i = 0; $i -lt $c.IPAddress.Count; $i++) {
      $ip = $c.IPAddress[$i]
      if ($ip -match ':') { [void]$ipv6.Add($ip) } else { [void]$ipv4.Add($ip); if ($c.IPSubnet -and $c.IPSubnet.Count -gt $i) { [void]$subs.Add($c.IPSubnet[$i]) } }
    }
  }
  [void]$adapters.Add([ordered]@{
    name = $na.Name; description = $na.InterfaceDescription; mac = $na.MacAddress; status = [string]$na.Status
    link_speed = [string]$na.LinkSpeed; link_speed_bps = [int64]$na.ReceiveLinkSpeed; media_type = [string]$na.MediaType
    physical = [bool]$na.HardwareInterface; ipv4 = $ipv4; ipv6 = $ipv6; subnet = $subs
    gateway = (Arr $c.DefaultIPGateway); dns = (Arr $c.DNSServerSearchOrder); dhcp = [bool]$c.DHCPEnabled
    dhcp_server = $c.DHCPServer; dns_suffix = $c.DNSDomain
  })
}
$wifi = $null
$w = @(netsh wlan show interfaces 2>$null)
if (($w | Where-Object { $_ -match '^\s*SSID\s*:' }).Count -gt 0) {
  $wifi = [ordered]@{}
  foreach ($line in $w) {
    if ($line -match '^\s*(SSID|BSSID|State|Signal|Authentication|Cipher|Radio type|Channel|Receive rate \(Mbps\)|Transmit rate \(Mbps\))\s*:\s*(.+)$') {
      $key = (($matches[1] -replace '\(Mbps\)', 'mbps') -replace '[^A-Za-z]+', '_').Trim('_').ToLower()
      $wifi[$key] = $matches[2].Trim()
    }
  }
}
$firewall = Arr (Get-NetFirewallProfile | ForEach-Object { [ordered]@{ profile = $_.Name; enabled = (([string]$_.Enabled) -eq 'True'); inbound = [string]$_.DefaultInboundAction; outbound = [string]$_.DefaultOutboundAction } })
$is = Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings'
$winhttp = ((@(netsh winhttp show proxy) -join ' ') -replace '\s+', ' ').Trim()
$proxy = [ordered]@{ enabled = ([int]$is.ProxyEnable -eq 1); server = $is.ProxyServer; bypass = $is.ProxyOverride; auto_config_url = $is.AutoConfigURL; winhttp = $winhttp }
$network = [ordered]@{ adapters = $adapters; wifi = $wifi; firewall = $firewall; proxy = $proxy }

# ---------------- Throughput ----------------
$speed = [ordered]@{ target = $ConsoleUrl; latency_ms = $null; latency_min_ms = $null; download_mbps = $null; upload_mbps = $null; download_mb = 10; upload_mb = 5; error = $null }
if ($env:TT_NOSPEED -ne '1') {
  Step 'Network throughput test (to console)'
  try {
    $lat = @()
    for ($i = 0; $i -lt 5; $i++) { $sw = [Diagnostics.Stopwatch]::StartNew(); Invoke-WebRequest -UseBasicParsing -Uri "$ConsoleUrl/api/agent/ping" -TimeoutSec 15 -ErrorAction Stop | Out-Null; $sw.Stop(); $lat += $sw.Elapsed.TotalMilliseconds }
    $m = $lat | Measure-Object -Average -Minimum
    $speed.latency_ms = [math]::Round($m.Average, 1); $speed.latency_min_ms = [math]::Round($m.Minimum, 1)
    $wc = New-Object Net.WebClient
    $sw = [Diagnostics.Stopwatch]::StartNew(); $bytes = $wc.DownloadData("$ConsoleUrl/api/agent/speedtest/download?mb=10&k=$EnrollKey"); $sw.Stop()
    $speed.download_mbps = [math]::Round(($bytes.Length * 8 / 1000000) / $sw.Elapsed.TotalSeconds, 2)
    $payload = New-Object byte[] (5MB); (New-Object Random).NextBytes($payload)
    $wc2 = New-Object Net.WebClient; $wc2.Headers.Add('Content-Type', 'application/octet-stream')
    $sw = [Diagnostics.Stopwatch]::StartNew(); $null = $wc2.UploadData("$ConsoleUrl/api/agent/speedtest/upload?k=$EnrollKey", 'POST', $payload); $sw.Stop()
    $speed.upload_mbps = [math]::Round(($payload.Length * 8 / 1000000) / $sw.Elapsed.TotalSeconds, 2)
  } catch { $speed.error = $_.Exception.Message }
} else { $speed.error = 'Skipped' }

# ---------------- Users & privileges ----------------
Step 'Users, groups and privileges'
$adminSid = 'S-1-5-32-544'
$groups = New-Object System.Collections.ArrayList
$memberMap = @{}
$adminGroupName = 'Administrators'
foreach ($g in @(Get-LocalGroup)) {
  if ([string]$g.SID -eq $adminSid) { $adminGroupName = $g.Name }
  $members = New-Object System.Collections.ArrayList
  try {
    foreach ($mm in @(Get-LocalGroupMember -Group $g -ErrorAction Stop)) { [void]$members.Add([ordered]@{ name = [string]$mm.Name; type = [string]$mm.ObjectClass; source = [string]$mm.PrincipalSource }) }
  } catch {
    try {
      $adsi = [ADSI]"WinNT://$env:COMPUTERNAME/$($g.Name),group"
      foreach ($o in @($adsi.psbase.Invoke('Members'))) { $n = $o.GetType().InvokeMember('Name', 'GetProperty', $null, $o, $null); [void]$members.Add([ordered]@{ name = "$env:COMPUTERNAME\$n"; type = 'Unknown'; source = 'ADSI' }) }
    } catch {}
  }
  foreach ($mm in $members) {
    $full = ([string]$mm.name).ToLower(); if ($full -notmatch '\\') { $full = ("$env:COMPUTERNAME\$full").ToLower() }
    if (-not $memberMap.ContainsKey($full)) { $memberMap[$full] = New-Object System.Collections.ArrayList }
    [void]$memberMap[$full].Add($g.Name)
  }
  [void]$groups.Add([ordered]@{ name = $g.Name; sid = [string]$g.SID; description = $g.Description; is_admin_group = ([string]$g.SID -eq $adminSid); members = $members })
}
$localUsers = New-Object System.Collections.ArrayList
foreach ($u in @(Get-LocalUser)) {
  $full = ("$env:COMPUTERNAME\$($u.Name)").ToLower()
  $gs = New-Object System.Collections.ArrayList; if ($memberMap.ContainsKey($full)) { $gs = $memberMap[$full] }
  [void]$localUsers.Add([ordered]@{
    name = $u.Name; full_name = $u.FullName; enabled = [bool]$u.Enabled; description = $u.Description
    last_logon = Iso $u.LastLogon; password_last_set = Iso $u.PasswordLastSet; password_required = [bool]$u.PasswordRequired
    password_expires = Iso $u.PasswordExpires; sid = [string]$u.SID; groups = $gs; is_admin = ($gs -contains $adminGroupName)
  })
}
$sessions = New-Object System.Collections.ArrayList
foreach ($line in @(quser 2>$null | Select-Object -Skip 1)) { [void]$sessions.Add(([string]$line).Trim()) }
$users = [ordered]@{ local = $localUsers; groups = $groups; admin_group = $adminGroupName; sessions = $sessions; current_user = $cs.UserName }

# ---------------- Security & settings ----------------
Step 'Security settings'
$bitlocker = New-Object System.Collections.ArrayList
if ($isAdmin) {
  try { foreach ($b in @(Get-BitLockerVolume -ErrorAction Stop)) { [void]$bitlocker.Add([ordered]@{ mount = $b.MountPoint; protection = [string]$b.ProtectionStatus; status = [string]$b.VolumeStatus; encryption_pct = $b.EncryptionPercentage; method = [string]$b.EncryptionMethod }) } } catch { [void]$limited.Add('bitlocker') }
} else { [void]$limited.Add('bitlocker') }
$av = New-Object System.Collections.ArrayList
try { foreach ($a in @(Get-CimInstance -Namespace root/SecurityCenter2 -ClassName AntiVirusProduct -ErrorAction Stop)) { $hex = '{0:X6}' -f [int]$a.productState; [void]$av.Add([ordered]@{ name = $a.displayName; enabled = ($hex.Substring(2, 2) -in @('10', '11')); up_to_date = ($hex.Substring(4, 2) -eq '00'); state_hex = $hex }) } } catch {}
$defender = $null
try { $mp = Get-MpComputerStatus -ErrorAction Stop; $defender = [ordered]@{ antivirus_enabled = [bool]$mp.AntivirusEnabled; realtime = [bool]$mp.RealTimeProtectionEnabled; signature_age_days = $mp.AntivirusSignatureAge; signature_version = $mp.AntivirusSignatureVersion; last_quick_scan = Iso $mp.QuickScanEndTime } } catch {}
$secureBoot = $null
if ($isAdmin) { try { $secureBoot = [bool](Confirm-SecureBootUEFI -ErrorAction Stop) } catch { $secureBoot = $null } } else { [void]$limited.Add('secure_boot') }
$tpm = $null
if ($isAdmin) { try { $t = Get-Tpm -ErrorAction Stop; $tpm = [ordered]@{ present = [bool]$t.TpmPresent; ready = [bool]$t.TpmReady } } catch {} } else { [void]$limited.Add('tpm') }
$security = [ordered]@{ uac_enabled = ($uacVal -eq 1); bitlocker = $bitlocker; antivirus = $av; defender = $defender; secure_boot = $secureBoot; tpm = $tpm }

# ---------------- Compile & upload ----------------
$result = [ordered]@{
  scanner_version = $ScannerVersion
  scanned_at = (Get-Date).ToUniversalTime().ToString('o')
  is_admin = $isAdmin
  limited_sections = $limited
  system = $system
  os = $os
  hardware = $hardware
  software = $software
  network = $network
  speed = $speed
  users = $users
  security = $security
}
$json = $result | ConvertTo-Json -Depth 10 -Compress
$out = Join-Path $env:TEMP ('Temprudence_Inventory_{0}_{1}.json' -f $env:COMPUTERNAME, (Get-Date -Format 'yyyyMMdd_HHmmss'))
[IO.File]::WriteAllText($out, $json, (New-Object Text.UTF8Encoding $false))
Write-Host "  [+] Results saved to $out" -ForegroundColor Green
if ($env:TT_NOUPLOAD -ne '1') {
  Step 'Uploading results to the Temprudence console'
  try {
    $r = Invoke-RestMethod -Method Post -Uri "$ConsoleUrl/api/agent/upload" -Headers @{ 'X-Enroll-Key' = $EnrollKey } -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($json)) -TimeoutSec 180 -ErrorAction Stop
    Write-Host "  [+] Upload complete for $($r.computer_name)." -ForegroundColor Green
    Write-Host "      View it at: $ConsoleUrl/computers/$($r.computer_id)" -ForegroundColor Green
  } catch {
    Write-Host "  [!] Upload failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host '      Import the saved JSON file from the console: Scan a computer > Import scan file.' -ForegroundColor Yellow
  }
}
Write-Host ''
'''

VERSION = "1.0.0"


def build_script(console_url: str, key: str) -> str:
    return (SCRIPT.replace("__CONSOLE_URL__", console_url.rstrip("/"))
            .replace("__ENROLL_KEY__", key)
            .replace("__VERSION__", VERSION)
            .replace("\n", "\r\n"))
