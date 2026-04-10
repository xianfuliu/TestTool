$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$workspaceRoot = Split-Path -Parent $root
$venvPython = Join-Path $workspaceRoot ".venv\Scripts\python.exe"
$pythonCommand = if (Test-Path $venvPython) { "`"$venvPython`"" } else { "python" }

function Get-LanIp {
  $ipconfig = ipconfig | Out-String
  $matches = [regex]::Matches($ipconfig, "IPv4[^\r\n:]*:\s*([0-9.]+)")
  foreach ($match in $matches) {
    $candidate = $match.Groups[1].Value
    if ($candidate -notlike "127.*" -and $candidate -notlike "169.254.*") {
      return $candidate
    }
  }
  return $null
}

function Test-IsAdmin {
  $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = New-Object Security.Principal.WindowsPrincipal($identity)
  return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Open-FirewallPortIfAdmin($port, $name) {
  if (-not (Test-IsAdmin)) {
    return
  }

  $existing = Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue
  if (-not $existing) {
    New-NetFirewallRule -DisplayName $name -Direction Inbound -Action Allow -Protocol TCP -LocalPort $port | Out-Null
  }
}

$lanIp = Get-LanIp
if (-not $lanIp) {
  throw "LAN IPv4 address was not found. Please make sure this computer is connected to the company network."
}

Open-FirewallPortIfAdmin 8000 "TestTool Django API 8000"
Open-FirewallPortIfAdmin 5173 "TestTool Vue Web 5173"

Write-Host ""
Write-Host "Starting TestTool for LAN access..." -ForegroundColor Cyan
Write-Host "Backend:  http://$lanIp`:8000" -ForegroundColor DarkCyan
Write-Host "Frontend: http://$lanIp`:5173" -ForegroundColor Green
Write-Host ""
Write-Host "If coworkers cannot access it, rerun this script as Administrator to open Windows Firewall ports automatically." -ForegroundColor Yellow
Write-Host "Close the two new terminal windows to stop the services." -ForegroundColor Yellow
Write-Host ""

Start-Process powershell -WorkingDirectory $backend -ArgumentList @(
  "-NoExit",
  "-Command",
  "$pythonCommand manage.py runserver 0.0.0.0:8000"
)

Start-Process powershell -WorkingDirectory $frontend -ArgumentList @(
  "-NoExit",
  "-Command",
  "npm run dev:lan"
)
