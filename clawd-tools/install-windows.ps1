param(
  [string]$WorkspacePath = ""
)

$ErrorActionPreference = "Stop"

Write-Host "OpenClaw Tools Installer (Windows)" -ForegroundColor Cyan

if ([string]::IsNullOrWhiteSpace($WorkspacePath)) {
  $default = Join-Path $HOME "clawd"
  $input = Read-Host "Enter your Clawd workspace path (default: $default)"
  if ([string]::IsNullOrWhiteSpace($input)) { $WorkspacePath = $default } else { $WorkspacePath = $input }
}

$src = Join-Path $PSScriptRoot "tools"
$dstTools = Join-Path $WorkspacePath "tools"

if (!(Test-Path $src)) { throw "Source tools folder not found: $src" }

New-Item -ItemType Directory -Force -Path $dstTools | Out-Null

Write-Host "Copying tools to: $dstTools" -ForegroundColor Green
Copy-Item -Path (Join-Path $src "*") -Destination $dstTools -Recurse -Force

Write-Host "" 
Write-Host "Done." -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "- Add any required env vars / secrets (do NOT commit them)" 
Write-Host "- Run the tools from inside your workspace as documented in tools/README.md" 
