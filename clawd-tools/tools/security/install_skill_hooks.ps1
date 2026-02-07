param(
  [ValidateSet('medium','high','low')]
  [string]$FailOn = 'medium'
)

$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $repoRoot

if (-not (Test-Path .git)) {
  throw "Not a git repo: $repoRoot"
}

# Ensure hooks dir exists
$hooksDir = Join-Path $repoRoot '.githooks'
New-Item -ItemType Directory -Force -Path $hooksDir | Out-Null

$preCommit = Join-Path $hooksDir 'pre-commit'
$prePush = Join-Path $hooksDir 'pre-push'

$preCommitContent = @"#!/usr/bin/env bash
# Clawdbot safety: scan skills before commit
set -euo pipefail
PYTHON_BIN=\"python\"
\"$PYTHON_BIN\" tools/security/skill_checker.py scan --fail-on $FailOn
"@

$prePushContent = @"#!/usr/bin/env bash
# Clawdbot safety: scan skills before push
set -euo pipefail
PYTHON_BIN=\"python\"
\"$PYTHON_BIN\" tools/security/skill_checker.py scan --fail-on $FailOn
"@

Set-Content -Path $preCommit -Value $preCommitContent -Encoding utf8 -NoNewline
Set-Content -Path $prePush -Value $prePushContent -Encoding utf8 -NoNewline

# Make hooks executable for Git Bash / WSL users (best-effort on Windows)
try {
  git update-index --chmod=+x .githooks/pre-commit 2>$null | Out-Null
  git update-index --chmod=+x .githooks/pre-push 2>$null | Out-Null
} catch {
  # ignore
}

git config core.hooksPath .githooks
Write-Host "Installed git hooks to .githooks and set core.hooksPath=.githooks (fail-on=$FailOn)." -ForegroundColor Green
