# Prints where the running Hermes gateway lives: pid, session, elevation.
# Session 1 + not elevated = GUI/UIA/permission-sensitive tools work and the user's own
# desktop clients can attach. Session 0 or elevated = they do not (see gateway_other_session).
$ErrorActionPreference = 'Continue'
$hh = "$env:LOCALAPPDATA\hermes"
$pidFile = Join-Path $hh 'gateway.pid'
if (-not (Test-Path $pidFile)) { Write-Host '  gateway session: (not running)'; return }
try { $gwPid = [int](Get-Content -Path $pidFile -Raw | ConvertFrom-Json).pid } catch { Write-Host '  gateway session: (no pid)'; return }
$p = Get-CimInstance Win32_Process -Filter "ProcessId=$gwPid" -ErrorAction SilentlyContinue
if (-not $p) { Write-Host "  gateway pid $gwPid is not running (stale gateway.pid)"; return }
$elevated = 'unknown'
try {
    Add-Type -Namespace HermesProbe -Name Token -MemberDefinition @'
[DllImport("kernel32.dll", SetLastError=true)] public static extern IntPtr OpenProcess(uint access, bool inherit, uint pid);
[DllImport("kernel32.dll", SetLastError=true)] public static extern IntPtr GetCurrentProcess();
[DllImport("advapi32.dll", SetLastError=true)] public static extern bool OpenProcessToken(IntPtr process, uint access, out IntPtr token);
[DllImport("advapi32.dll", SetLastError=true)] public static extern bool GetTokenInformation(IntPtr token, int cls, out int info, int len, out int ret);
[DllImport("kernel32.dll", SetLastError=true)] public static extern bool CloseHandle(IntPtr handle);
'@ -ErrorAction Stop
    $h = [HermesProbe.Token]::OpenProcess(0x1000, $false, [uint32]$gwPid)   # PROCESS_QUERY_LIMITED_INFORMATION
    if ($h -ne [IntPtr]::Zero) {
        $tok = [IntPtr]::Zero
        if ([HermesProbe.Token]::OpenProcessToken($h, 0x0008, [ref]$tok)) {   # TOKEN_QUERY
            $info = 0; $ret = 0
            if ([HermesProbe.Token]::GetTokenInformation($tok, 20, [ref]$info, 4, [ref]$ret)) {  # TokenElevation
                $elevated = if ($info -ne 0) { 'elevated' } else { 'not elevated' }
            }
            [void][HermesProbe.Token]::CloseHandle($tok)
        }
        [void][HermesProbe.Token]::CloseHandle($h)
    }
} catch { }
$sess = [int]$p.SessionId
$verdict = if ($sess -eq 1 -and $elevated -eq 'not elevated') { 'OK' } else { 'WRONG - session guard/unreaper will move it back' }
Write-Host ("  gateway pid {0}: session {1}, {2} -> {3}" -f $gwPid, $sess, $elevated, $verdict)
