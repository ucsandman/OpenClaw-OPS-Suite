# Quick Start Guide (No Coding Required!)

This guide will get you up and running in 5 minutes, even if you've never used a terminal before.

## What You Need

1. **A Computer** (Windows, Mac, or Linux)
2. **Internet Connection**
3. **5 Minutes**

That's it!

---

## Step 1: Install Node.js (One-Time Setup)

Node.js is what runs the dashboard. If you don't have it:

1. Go to **[nodejs.org](https://nodejs.org/)**
2. Click the big green **"LTS"** button
3. Run the installer (just click Next → Next → Finish)
4. Restart your computer

**How to check if it worked:**
- Open Command Prompt (Windows) or Terminal (Mac)
- Type `node --version` and press Enter
- You should see a version number like `v20.x.x`

---

## Step 2: Get a Free Database

Your dashboard needs somewhere to store data. Neon gives you a free database:

1. Go to **[neon.tech](https://neon.tech/)**
2. Click **"Start Free"** and create an account (GitHub login works!)
3. Create a new project (any name is fine)
4. On your project page, find the **Connection String**
5. Copy it - it looks like: `postgresql://user:pass@ep-xyz.us-east-2.aws.neon.tech/neondb`

**Keep this safe - you'll need it in the next step!**

---

## Step 3: Download & Install

**Where to put it:** extract it anywhere you want (Desktop, Documents, etc). It does **not** need to go in any Clawdbot/Clawd folder.

**Recommended locations**
- Windows: `Documents\OpenClaw-OPS-Suite` or `Desktop\OpenClaw-OPS-Suite`
- Mac/Linux: `~/Desktop/OpenClaw-OPS-Suite` or `~/Projects/OpenClaw-OPS-Suite`

**Avoid** extracting into a very deep folder path on Windows (Node can hit path-length issues inside `node_modules`).

### Option A: One-Click Install (Easiest)

1. Download the ZIP:
   - GitHub UI: **Code** → **Download ZIP**
   - Direct link: https://github.com/ucsandman/OpenClaw-OPS-Suite/archive/refs/heads/main.zip
2. Extract the ZIP to a folder (like Desktop)
3. Open the extracted folder

**Windows:**
- Double-click `install-windows.bat`
- Paste your database connection string when asked
- Wait for it to finish

**Mac/Linux:**
- Open Terminal
- Navigate to the folder: `cd ~/Desktop/OpenClaw-OPS-Suite-main`
- Run: `chmod +x install-mac.sh && ./install-mac.sh`
- Paste your database connection string when asked

### Option B: Deploy to Cloud (No Installation)

Want it running 24/7 without leaving your computer on?

Security note:
- **Local-only**: you can run without `DASHBOARD_API_KEY`
- **Public deployment**: set `DASHBOARD_API_KEY` or your `/api/*` data may be readable by anyone who has the link

1. Click the **Deploy with Vercel** button in the README
2. Connect your GitHub account
3. Paste your `DATABASE_URL` when prompted
4. **Set `DASHBOARD_API_KEY`**
5. Done! You get a free URL like `your-dashboard.vercel.app`

---

## Optional: Install the OpenClaw Tools into your Clawd workspace

If you’re using Clawd/Clawdbot, you can install the included ops tools bundle into your workspace.

From the repo root:

**Windows:**
```powershell
powershell -ExecutionPolicy Bypass -File .\clawd-tools\install-windows.ps1
```

**Mac/Linux:**
```bash
bash ./clawd-tools/install-mac.sh
```

---

## Step 4: Start the Dashboard

After installation:

**Windows:** Double-click `START-DASHBOARD.bat`

**Mac/Linux:** Run `./start-dashboard.sh`

Your browser will open to **http://localhost:3000** 🎉

---

## Troubleshooting

### "node is not recognized"
→ Node.js isn't installed. Go back to Step 1.

### "Cannot connect to database"
→ Double-check your connection string. Make sure you copied the whole thing.

### "Port 3000 is already in use"
→ Another app is using that port. Close it, or edit `.env.local` and add `PORT=3001`

### The page is blank or shows errors
→ Try refreshing. If that doesn't work, check that your database URL is correct in `.env.local`

---

## Getting Help

- **GitHub Issues:** [Report a bug](../../issues)
- **Documentation:** Check the `docs/` folder
- **Community:** Join the Clawdbot Discord

---

## What's Next?

Once your dashboard is running:

1. Visit the **Setup** page (`/setup`) for a guided tour
2. Configure your **Integrations** (API keys, etc.)
3. Start tracking your AI agent's activity!

Happy dashboarding! 🚀
