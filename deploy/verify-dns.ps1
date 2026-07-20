# Verify public A record for ai4safe.cn (via Google DoH)
$ErrorActionPreference = "Stop"
$expected = "8.159.143.118"
$r = Invoke-RestMethod "https://dns.google/resolve?name=ai4safe.cn&type=A"
$answers = @()
if ($r.Answer) { $answers = @($r.Answer | Where-Object { $_.type -eq 1 } | ForEach-Object { $_.data }) }
Write-Output "ai4safe.cn A records: $($answers -join ', ')"
if ($answers -contains $expected) {
  Write-Output "OK: points to $expected"
  exit 0
}
Write-Output "FAIL: expected $expected. Add Aliyun DNS: Host=@ Type=A Value=$expected"
exit 1
