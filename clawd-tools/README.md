# OpenClaw Tools Bundle (for Clawd/Clawdbot workspaces)

This folder contains the **self-improving ops tools** (memory, security, learning, token tracking, etc.) that are meant to live inside a **Clawd/Clawdbot workspace**.

## Where this goes

These tools should be copied into **your Clawd workspace** like:
- `~/clawd/tools` (Mac/Linux)
- `C:\Users\<you>\clawd\tools` (Windows)

This repo’s dashboard app can live anywhere. The tools bundle is what belongs in the Clawd workspace.

## What’s included (quick glance)

- **Security**: outbound filter, secret rotation tracker, audit logger, skill safety checker
- **Tokens**: token capture + dashboards, efficiency/budget helpers
- **Memory**: memory search, memory health scanner, memory extractor
- **Ops tracking**: learning database, relationship tracker, goal tracker, open loops
- **Workflow/ops helpers**: session handoff, context manager, daily digest, error logger, project monitor, API monitor

## Install (recommended)

### Windows (PowerShell)
From the repo root:

```powershell
powershell -ExecutionPolicy Bypass -File .\clawd-tools\install-windows.ps1
```

### Mac/Linux (bash)
From the repo root:

```bash
bash ./clawd-tools/install-mac.sh
```

## Secrets

Do **not** put secrets in this repo.

Use a `secrets/` folder inside your Clawd workspace (it is typically gitignored), or environment variables.
