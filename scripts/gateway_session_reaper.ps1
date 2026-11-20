# Hermes gateway session reaper (Windows)
#
# Goal: the Hermes gateway MUST run in the signed-in user's interactive desktop session
#       (normally session 1) and MUST NOT be elevated. If it is found running in any other
#       session (session 0 - an elevated OpenSSH/service shell, i.e. no desktop, no UIA, no
#       user-level permissions, and the user's own clients get "gateway_other_session"), it is
#       stopped here and restarted through the Scheduled Task "Hermes_Gateway_Session1",
#       which is InteractiveToken + LeastPrivilege and therefore lands in the desktop session.
#
# Where it runs: Scheduled Task "Hermes_Gateway_Reaper"
#       principal = WangA, LogonType = S4U (no desktop -> session 0), RunLevel = Highest,
#       trigger = every 5 minutes + on demand.
#       It must be able to *read* a misplaced gateway's command line and to *kill* it, so it
#       cannot live in the interactive session (a least-privilege session-1 process cannot even
#       enumerate an elevated session-0 process - measured: CommandLine comes back null).
#
# Safety:
#   * no explorer.exe -> nobody is logged on -> do nothing at all;
#   * the pause file %LOCALAPPDATA%\hermes\gateway-session-guard.pause disables both stopping
#     and starting (maintenance / hermes update);
#   * a fresh update.log (touch < 20 min) is treated as "hermes is updating" -> hands off;
#   * MultipleInstances=IgnoreNew on both tasks keeps two gateways from racing.
#
# Silent on success: it only writes to logs\gateway-session-guard.log.

$ErrorActionPreference = 'Continue'
$hh = "$env:LOCALAPPDATA\hermes"
if (-not $hh -or -not (Test-Path $hh)) { $hh = 'C:\Users\WangA\AppData\Local\hermes' }
$log = "$hh\logs\gateway-session-guard.log"
$hermes = "$hh\bin\hermes.exe"
$pauseFile = "$hh\gateway-session-guard.pause"
$startTask = 'Hermes_Gateway_Session1'

function L($m) { "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $m" | Add-Content -Path $log -Encoding UTF8 }

function DeliberatelyStopped {
  # `hermes gateway stop` leaves gateway_state="stopped"; a crash/kill leaves the stale "running"
  # state behind. Only an explicit stop may keep the gateway down.
  $stateFile = Join-Path $hh 'gateway_state.json'
  if (-not (Test-Path $stateFile)) { return $false }
  try { $st = Get-Content -Path $stateFile -Raw -ErrorAction Stop | ConvertFrom-Json } catch { return $false }
  return ($st.gateway_state -eq 'stopped')
}

function GwProcs {
  @(Get-CimInstance Win32_Process -Filter "Name like 'python%'" |
      Where-Object { $_.CommandLine -and $_.CommandLine -match 'hermes_cli\.main\s+gateway\s+run' })
}

$gw = GwProcs
$expl = @(Get-CimInstance Win32_Process -Filter "Name='explorer.exe'")
if ($expl.Count -eq 0) {
  if ($gw.Count -gt 0) { L 'no interactive session (explorer.exe absent) - gateway left untouched' }
  return
}
$inter = [int]$expl[0].SessionId

# ── nothing running: let the interactive-session task bring it back ──────────
if ($gw.Count -eq 0) {
  if (Test-Path $pauseFile) { L "gateway absent but PAUSED ($pauseFile) - no action"; return }
  $ul = "$hh\logs\update.log"
  if (Test-Path $ul) {
    $age = (New-TimeSpan -Start (Get-Item $ul).LastWriteTime -End (Get-Date)).TotalMinutes
    if ($age -lt 20) { L ("gateway absent but update.log touched {0:N1} min ago - skip (update in progress)" -f $age); return }
  }
  if (DeliberatelyStopped) {
    L 'gateway absent: state is "stopped" (explicit hermes gateway stop) - not restarting'
    return
  }
  L "gateway absent -> starting $startTask (interactive session $inter)"
  schtasks /run /tn $startTask 2>&1 | ForEach-Object { L "start: $_" }
  return
}

$sess = @($gw | ForEach-Object { [int]$_.SessionId } | Sort-Object -Unique)
$where = ($gw | ForEach-Object { "$($_.ProcessId)/s$($_.SessionId)" }) -join ','
L "check: interactive=$inter gateway=$where"

# ── healthy: every gateway process is already in the desktop session ────────
# NB: never write `if (-not ($sess | Where-Object { $_ -ne $inter }))`. A pipeline that yields the
# integer 0 (a session-0 gateway) is falsy in PowerShell, so that test silently calls a misplaced
# gateway healthy -- exactly how the previous guard never fixed anything.
$misplaced = @($sess | Where-Object { $_ -ne $inter })
if ($misplaced.Count -eq 0) { return }

if (Test-Path $pauseFile) { L "misplaced ($where) but PAUSED ($pauseFile) - no action"; return }

# ── misplaced: stop it here (this session can), then restart in the desktop ──
L "misplaced: gateway=$where interactive=$inter -> swapping into session $inter"
& $hermes gateway stop 2>&1 | ForEach-Object { L "stop: $_" }
for ($i = 0; $i -lt 30; $i++) {
  Start-Sleep -Seconds 2
  if ((GwProcs).Count -eq 0) { break }
}
$left = GwProcs
if ($left.Count -gt 0) {
  $ids = @($left | ForEach-Object { [int]$_.ProcessId })
  $kids = @(Get-CimInstance Win32_Process | Where-Object { $ids -contains [int]$_.ParentProcessId } | ForEach-Object { [int]$_.ProcessId })
  L ("force kill " + (($ids + $kids) -join ','))
  foreach ($k in ($ids + $kids)) {
    taskkill /F /T /PID $k 2>&1 | ForEach-Object { L "kill: $_" }
    Stop-Process -Id $k -Force -ErrorAction SilentlyContinue
  }
  Start-Sleep -Seconds 5
}
L "starting $startTask (InteractiveToken -> session $inter)"
schtasks /run /tn $startTask 2>&1 | ForEach-Object { L "start: $_" }

for ($i = 0; $i -lt 20; $i++) {
  Start-Sleep -Seconds 3
  $now = GwProcs
  if ($now.Count -gt 0 -and -not (@($now | Where-Object { [int]$_.SessionId -ne $inter }))) { break }
}
$now = GwProcs
L ("after swap: " + ((($now | ForEach-Object { "$($_.ProcessId)/s$($_.SessionId)" }) -join ',') -replace '^$', '<none>'))
