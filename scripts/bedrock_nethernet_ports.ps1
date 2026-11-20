# 基岩 NetherNet/both 模式端口放行（需以管理员身份运行）
# 用法：右键“以管理员身份运行 PowerShell” → .\bedrock_nethernet_ports.ps1
# 作用：放行 Windows 防火墙入站 TCP 19132/19133 + UDP 19134/19135（幂等，可重复执行）
# 注意：防火墙只是其中一层，路由器仍需把同样的端口转发到本机 LAN IP。

$ErrorActionPreference = "Stop"

$rules = @(
    @{ Name = "Bedrock Geyser 19132 TCP"; Proto = "TCP"; Port = 19132 },
    @{ Name = "Bedrock Geyser 19133 TCP"; Proto = "TCP"; Port = 19133 },
    @{ Name = "Bedrock NetherNet 19134 UDP"; Proto = "UDP"; Port = 19134 },
    @{ Name = "Bedrock NetherNet 19135 UDP"; Proto = "UDP"; Port = 19135 }
)

foreach ($r in $rules) {
    Get-NetFirewallRule -DisplayName $r.Name -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    New-NetFirewallRule -DisplayName $r.Name -Direction Inbound -Action Allow `
        -Protocol $r.Proto -LocalPort $r.Port -Profile Any -EdgeTraversalPolicy Block | Out-Null
    Write-Host "[OK] $($r.Name)  ($($r.Proto)/$($r.Port))"
}

Write-Host ""
Write-Host "已放行的入站端口："
Get-NetFirewallRule -Enabled True -Direction Inbound |
    Get-NetFirewallPortFilter |
    Where-Object { $_.LocalPort -in @('19132', '19133', '19134', '19135') } |
    Select-Object LocalPort, Protocol |
    Sort-Object LocalPort, Protocol |
    Format-Table -AutoSize

Write-Host "路由器仍需转发（WAN -> 本机 LAN IP）："
Write-Host "  TCP 19132, TCP 19133, UDP 19132, UDP 19133, UDP 19134, UDP 19135"
