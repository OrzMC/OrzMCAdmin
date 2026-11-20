param([switch]$Detach)
# Hermes gateway session guard (Windows) - DETECTOR ONLY
#
# The gateway must run in the signed-in user's interactive desktop session (Session 1) and must
# not be elevated. This script only *detects* drift and arms the repair; the repair itself lives in
# Scheduled Task "Hermes_Gateway_Reaper", because a process in the interactive session cannot even
# enumerate an elevated Session-0 gateway (its CommandLine reads back null and it cannot be killed).
#
# Why this replaced the old "Hermes_Gateway_Swap" design: the old script tested health with
#     if (-not ($sess | Where-Object { $_ -ne $inter })) { return }
# and `$_ -ne $inter` yielding the integer 0 (Session 0!) is *falsy* in PowerShell, so a gateway
# sitting in Session 0 was reported healthy and never repaired - which is why the gateway stayed in
# Session 0 for a whole day while the log showed nothing but "check:" lines.
#
# Usage:
#   (no switch)  detect + repair inline if this process can (cron passes -Detach)
#   -Detach      detect + arm the task (cron: the script is a gateway child, it must not kill its
#                own parent and then have nothing left to restart it)
# Log: %LOCALAPPDATA%\hermes\logs\gateway-session-guard.log
# Pause: create %LOCALAPPDATA%\hermes\gateway-session-guard.pause (maintenance/update), delete after.

$ErrorActionPreference = 'Continue'
$hh = "$env:LOCALAPPDATA\hermes"
$log = "$hh\logs\gateway-session-guard.log"
$pauseFile = "$hh\gateway-session-guard.pause"
$startTask = 'Hermes_Gateway_Session1'
$reaperTask = 'Hermes_Gateway_Reaper'

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
  $procs = @(Get-CimInstance Win32_Process -Filter "Name like 'python%'" |
      Where-Object { $_.CommandLine -and $_.CommandLine -match 'hermes_cli\.main\s+gateway\s+run' })
  if ($procs.Count -eq 0) {
    # Command line unreadable (e.g. another user's or an elevated process): fall back to gateway.pid
    $pidFile = Join-Path $hh 'gateway.pid'
    if (Test-Path $pidFile) {
      $gwPid = 0
      try { $gwPid = [int](Get-Content -Path $pidFile -Raw -ErrorAction Stop | ConvertFrom-Json).pid } catch { $gwPid = 0 }
      if ($gwPid -gt 0) {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$gwPid" -ErrorAction SilentlyContinue
        if ($proc) { $procs = @($proc) }
      }
    }
  }
  $procs
}

# Interactive session = the one holding explorer.exe. No explorer.exe -> nobody is logged on and
# there is no desktop to move the gateway to: touch nothing.
$expl = @(Get-CimInstance Win32_Process -Filter "Name='explorer.exe'")
if ($expl.Count -eq 0) { return }
$inter = [int]$expl[0].SessionId

$gw = @(GwProcs)
$sess = @($gw | ForEach-Object { [int]$_.SessionId } | Sort-Object -Unique)
$bad = @($sess | Where-Object { $_ -ne $inter })
$where = (($gw | ForEach-Object { "$($_.ProcessId)/s$($_.SessionId)" }) -join ',')
L "check: interactive=$inter gateway=$(if ($where) { $where } else { '<none>' })"

# Healthy: running, and every process in the desktop session -> silent (cron no_agent -> no message).
if ($gw.Count -gt 0 -and $bad.Count -eq 0) { return }

if (Test-Path $pauseFile) {
  L "misplaced/absent but PAUSED ($pauseFile) - no action"
  Write-Output "检测到 Hermes 网关状态异常（$where），但守门已暂停（$pauseFile），未做处理。"
  return
}

# Not running at all: nothing to kill, so any context can ask the interactive task to start it.
if ($gw.Count -eq 0) {
  $ul = Join-Path $hh 'logs\update.log'
  if (Test-Path $ul) {
    $age = (New-TimeSpan -Start (Get-Item $ul).LastWriteTime -End (Get-Date)).TotalMinutes
    if ($age -lt 20) { L ("gateway absent but update.log touched {0:N1} min ago - skip (update in progress)" -f $age); return }
  }
  if (DeliberatelyStopped) {
    L 'gateway absent: state is "stopped" (explicit hermes gateway stop) - not restarting'
    return
  }
  L "absent -> starting $startTask (interactive session $inter)"
  schtasks /run /tn $startTask 2>&1 | ForEach-Object { L "start: $_" }
  Write-Output "⚠ Hermes 网关没有在运行，已触发在交互会话 Session $inter 启动（计划任务 $startTask）。日志：$log"
  return
}

# Misplaced (running in Session 0 or another non-interactive session): hand it to the reaper, which
# runs as the same user at high integrity in Session 0 and can stop, kill and restart it.
L "misplaced: gateway=$where interactive=$inter -> arming $reaperTask"
schtasks /run /tn $reaperTask 2>&1 | ForEach-Object { L "arm: $_" }

if (-not $Detach) {
  # Inline path: wait for the reaper to land the gateway in the desktop session.
  for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 3
    $now = @(GwProcs)
    if ($now.Count -gt 0 -and -not (@($now | Where-Object { [int]$_.SessionId -ne $inter }).Count -gt 0)) { break }
  }
  $now = @(GwProcs)
  $after = (($now | ForEach-Object { "$($_.ProcessId)/s$($_.SessionId)" }) -join ',')
  L ("after swap: " + ($(if ($after) { $after } else { '<none>' })))
  Write-Output "已完成网关会话切换：现在 = $after（交互会话 Session $inter）。日志：$log"
  return
}

Write-Output "⚠ Hermes 网关运行在会话 $($sess -join ',')（非交互会话），已触发自动拉回（计划任务 $reaperTask），约 1 分钟内回到 Session $inter。日志：$log"
