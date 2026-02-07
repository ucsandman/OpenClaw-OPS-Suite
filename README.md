# OpenClaw Dashboard

A beautiful, real-time dashboard for monitoring your AI agent's activity. Built for the OpenClaw/Clawdbot/Clawd ecosystem. Includes improved memory and security focused tools.

![Next.js](https://img.shields.io/badge/Next.js-14-black) ![Tailwind](https://img.shields.io/badge/Tailwind-CSS-38bdf8) ![Neon](https://img.shields.io/badge/Neon-Postgres-00e599) ![License](https://img.shields.io/badge/License-MIT-green)

![Dashboard Preview](docs/images/dashboard-main.jpg)

*Your AI agent's command center - token tracking, learning insights, project status, calendar, and more.*

## 🚀 One-Click Deploy

[![Deploy with Vercel](https://img.shields.io/badge/Deploy-Vercel-black?style=for-the-badge&logo=vercel)](https://vercel.com/new/clone?repository-url=https://github.com/ucsandman/OpenClaw-OPS-Suite&env=DATABASE_URL&envDescription=Your%20Neon%20PostgreSQL%20connection%20string&envLink=https://console.neon.tech)

**New to this?** Check out our [Quick Start Guide](QUICK-START.md) - no coding required!

**Already deployed?** Visit `/setup` for a guided walkthrough!

## Using this with Clawd/Clawdbot (recommended)

This repo includes a **tools bundle** (memory, security, learning, token tracking, etc.) designed to be installed into your **Clawd workspace**.

From this repo root:
- Windows: `powershell -ExecutionPolicy Bypass -File .\clawd-tools\install-windows.ps1`
- Mac/Linux: `bash ./clawd-tools/install-mac.sh`

See: [`clawd-tools/README.md`](clawd-tools/README.md)

### Tools bundle (at a glance)

Installed into your Clawd workspace, you get:
- **Security**: outbound filter, secret rotation tracker, audit logger, skill safety checker
- **Tokens**: token capture + dashboards, efficiency/budget helpers
- **Memory**: memory search, memory health scanner, memory extractor
- **Ops tracking**: learning database, relationship tracker, goal tracker, open loops
- **Workflow/ops helpers**: session handoff, context manager, daily digest, error logger, project monitor, API monitor

## Features

### 🧠 Memory & Ops Tools

- 🎯 **Token Budget Tracking** — Monitor usage with visual charts
- 📊 **Learning Database** — Track decisions, lessons, and outcomes over time
- 🤝 **Relationship Tracker (Mini‑CRM)** — Contacts, interactions, and follow‑up reminders
- 🎯 **Goal Tracking** — Goals, milestones, and progress
- 📝 **Content Tracker** — Capture writing ideas and content workflows
- 🧰 **Workflows / SOPs** — Document repeatable processes and runbooks

### 🔐 Security Tools

- 🔐 **Secure Settings Store** — Credentials encrypted and stored in your database
- 🧪 **Connection Tests** — Verify integrations before saving
- 🔍 **Security Scanner** — Pre‑deploy audit script (`node scripts/security-scan.js`)
- ✅ **Security Checklist** — Quick safe‑deploy reference (`docs/SECURITY-CHECKLIST.md`)
- 🧾 **Audit Template** — Full production audit methodology (`docs/SECURITY-AUDIT-TEMPLATE.md`)

### ⚡ Platform & UX

- 🔌 **Integrations Settings** — Configure services from the UI
- 📅 **Calendar Integration** — Upcoming events at a glance
- 🔄 **Real‑time Updates** — Auto‑refresh with configurable intervals
- 📱 **Mobile Responsive** — Works great on any device

## Quick Start (Local)

**Where to install it:** anywhere you want (Desktop, Documents, etc). It does **not** need to go inside your Clawdbot/Clawd folder. It’s a normal Next.js app.

**Recommended locations**
- Windows: `Documents\OpenClaw-OPS-Suite` or `Desktop\OpenClaw-OPS-Suite`
- Mac/Linux: `~/Desktop/OpenClaw-OPS-Suite` or `~/Projects/OpenClaw-OPS-Suite`

**Avoid** extracting into a very deep folder path on Windows (Node can hit path-length issues inside `node_modules`).

### 1) Download the project

- GitHub UI: **Code** → **Download ZIP**
- Direct ZIP link: https://github.com/ucsandman/OpenClaw-OPS-Suite/archive/refs/heads/main.zip

Extract the ZIP somewhere simple (example: `Desktop/OpenClaw-OPS-Suite`).

### 2) Set up your database

Create a free [Neon](https://neon.tech) PostgreSQL database.

### 3) Configure environment

Create `.env.local` (you can copy `.env.example`) and set:

```bash
DATABASE_URL=postgresql://...
```

### 4) Install and run

```bash
npm install
npm run dev
```

Open http://localhost:3000

## Security quick note (read this)

- **Local-only (http://localhost:3000):** you can run without `DASHBOARD_API_KEY`.
- **Public deployment (Vercel / any URL on the internet):** set `DASHBOARD_API_KEY` or your dashboard API data may be readable by anyone who has the link.

## Deployment

### Vercel (Recommended)

1. Push to GitHub (or fork this repo)
2. Import in [Vercel](https://vercel.com)
3. Add `DATABASE_URL` environment variable
4. **Set `DASHBOARD_API_KEY`** (protects your `/api/*` data)
5. Deploy!

### Other platforms

Any platform supporting Next.js 14+ will work. Just set the `DATABASE_URL` environment variable.

## Integrations Settings

Configure all your connected services directly from the dashboard:

1. Go to **Integrations** page
2. Click any service card to configure
3. Enter your API keys/credentials
4. Click **Test Connection** to verify
5. **Save Settings** stores encrypted in your Neon database

Supported integrations:
- 🗄️ Neon Database
- 📝 Notion
- 🐙 GitHub
- 🤖 OpenAI
- 🧠 Anthropic
- 🦁 Brave Search
- 🎙️ ElevenLabs
- 💬 Telegram
- 📅 Google Workspace
- ▲ Vercel
- 🐦 Twitter/X
- 🔥 Moltbook

## API Endpoints

All endpoints return JSON and support CORS.

| Endpoint | Description |
|----------|-------------|
| `/api/settings` | Integration credentials (CRUD) |
| `/api/settings/test` | Test connection with credentials |
| `/api/tokens` | Token usage snapshots |
| `/api/learning` | Decisions and lessons |
| `/api/inspiration` | Ideas and ratings |
| `/api/relationships` | Contacts and interactions |
| `/api/goals` | Goals and milestones |
| `/api/calendar` | Upcoming events |
| `/api/health` | Database connectivity check |

## 🔒 Security

We take security seriously. OpenClaw Dashboard includes:

- **Encrypted Credentials** - All API keys stored encrypted in your database
- **No Hardcoded Secrets** - Everything uses environment variables
- **Security Scanner** - Built-in tool to audit your deployment
- **Comprehensive Documentation** - Security guides and checklists

### Run Security Scan

Before deploying, scan your codebase:

```bash
node scripts/security-scan.js
```

### Security Documentation

- [Security Guide](docs/SECURITY.md) - How we protect your data
- [Security Checklist](docs/SECURITY-CHECKLIST.md) - Quick deployment checklist
- [Audit Template](docs/SECURITY-AUDIT-TEMPLATE.md) - Full audit methodology

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Styling**: Tailwind CSS
- **Database**: Neon PostgreSQL
- **Charts**: Recharts
- **Deployment**: Vercel

## Contributing

PRs welcome! This is a community project for the Clawd ecosystem.

## License

MIT

---

Built with 🔥 by [MoltFire](https://github.com/MoltFire)
