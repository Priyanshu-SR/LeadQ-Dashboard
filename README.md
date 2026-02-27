# ⚡ LeadQ — Lead Qualification Dashboard (complete access)

Full-access lead qualification dashboard for managers and admins. Browse all leads, filter by status and intent, view full phone numbers, complete chat histories, and AI-powered qualification analysis — all in a single responsive app backed by FastAPI and MongoDB.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?logo=mongodb&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)

> **Two dashboard versions exist:**
>
> | Version | Who it's for | Key difference |
> |---------|-------------|----------------|
> | 🔓 **Admin (this)** | Managers, admins | Full lead browsing, filters, unmasked phone numbers |
> | 🔒 **Sales Agent** | Sales team | Search-gated, masked numbers, no browsing |
>
> Both share the same `main.py` and `config.py` — only the `dashboard.html` differs.

---

## How It Works

```
WhatsApp → n8n Workflow → GPT Analysis → MongoDB
                                            ↑
                                     FastAPI reads
                                            ↓
                                   Dashboard (browser / Android app)
```

1. Customers chat on WhatsApp
2. **n8n** workflow captures messages into MongoDB (`customerChats` collection)
3. An **AI agent** (GPT) periodically analyses each conversation — writes qualification status, intent, confidence score, signals, and summary back into the document
4. **This app** reads MongoDB and presents everything in a browsable, filterable dashboard

---

## Features

- **Full lead browsing** — all analysed leads load on startup, scroll through entire database
- **Search by phone** — instant regex-based phone number search
- **Filter by status** — Qualified / Unqualified dropdown
- **Filter by intent** — Interested, Query, Not Interested, Junk, Failed
- **5 stat cards** — Total Leads, Qualified, Qual. Rate, Avg Confidence, Avg Messages
- **Intent breakdown bar** — color-coded segment chart with legend
- **Expandable lead cards** — click to reveal AI summary, signal chips, full chat history
- **Confidence gauge** — circular SVG gauge per lead (red → amber → green)
- **Full phone numbers** — unmasked display for admin use
- **Dark / Light theme** — sun/moon pill toggle with localStorage persistence
- **Auto-refresh** — syncs every 45 seconds, preserves expanded card states
- **Chat caching** — loaded chats survive re-render cycles (no duplicate API calls)
- **Robust sessionId matching** — handles string, integer, regex, and scan fallback
- **Fully responsive** — 6 breakpoints: small phones (380px) → large monitors (1441px+)
- **Touch-optimised** — 44px minimum tap targets, no sticky hover on mobile
- **Notch-safe** — `safe-area-inset` padding for modern phones
- **Android APK** — optional WebView wrapper for native app distribution

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI 0.115.6 + Uvicorn 0.34.0 |
| Database | MongoDB Atlas (Motor 3.7.0 async driver) |
| Frontend | Vanilla HTML/CSS/JS (single file, served by FastAPI) |
| Config | Pydantic Settings 2.7.1 + `.env` file |
| AI Pipeline | n8n + OpenAI GPT (separate workflow) |
| Fonts | DM Sans · Playfair Display · JetBrains Mono (Google Fonts CDN) |

---

## Project Structure

```
leadq-admin/
├── main.py             # FastAPI — API endpoints + serves dashboard
├── config.py           # Pydantic settings (reads .env)
├── dashboard.html      # Single-file responsive frontend (admin version)
├── requirements.txt    # Python dependencies
├── .env                # Environment variables (not committed)
├── .env.example        # Template for .env
├── .gitignore
├── Procfile            # For Railway/Render deployment
├── LICENSE
└── README.md           # This file
```

---

## File Documentation

### `config.py` — Application Settings

Centralized configuration using Pydantic Settings. All values can be overridden via environment variables or a `.env` file.

```python
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    MONGO_URI: str = "mongodb+srv://user:pass@cluster0.xxxxx.mongodb.net/"
    MONGO_DB: str = "test"
    MONGO_COLLECTION: str = "customerChats"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `MONGO_URI` | `str` | — | MongoDB connection string (Atlas or local) |
| `MONGO_DB` | `str` | `test` | Database name containing lead documents |
| `MONGO_COLLECTION` | `str` | `customerChats` | Collection name where n8n writes chat data |
| `HOST` | `str` | `0.0.0.0` | Server bind address |
| `PORT` | `int` | `8000` | Server port |
| `CORS_ORIGINS` | `List[str]` | `["*"]` | Allowed CORS origins (JSON array) |

**How settings load (priority order):**
1. Environment variables (highest priority)
2. `.env` file values
3. Default values in code (lowest priority)

---

### `main.py` — FastAPI Application

**Startup (lifespan):**
- Connects to MongoDB via Motor async driver
- Validates connection with a ping
- Logs first document structure for debugging (sessionId type, output type)
- Configures CORS middleware (all origins allowed by default)

**Helper functions:**

| Function | Purpose |
|----------|---------|
| `serialize(obj)` | Converts BSON types (ObjectId, Decimal128, datetime) to JSON-safe values |
| `flatten_lead(doc)` | Extracts and normalizes lead fields from raw MongoDB document into a flat dict |
| `extract_chat(doc)` | Pulls chat messages array from document, handles both `dict` and `str` data formats |
| `find_by_session(col, sid)` | 4-strategy sessionId lookup: exact string → int cast → regex → scan fallback |

**API endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Serves `dashboard.html` |
| `GET` | `/api/health` | MongoDB ping + document count + analysis count |
| `GET` | `/api/leads` | List leads with search, filter, sort, pagination |
| `GET` | `/api/leads/{sessionId}` | Single lead + full chat history |
| `GET` | `/api/stats` | Aggregate stats: totals, rates, intent breakdown |

---

### `dashboard.html` — Admin Frontend

Single-file frontend (HTML + CSS + JS) with no build step required.

**UI sections (top to bottom):**
1. **Header** — Logo, live status indicator, theme toggle, sync button
2. **Stats grid** — 5 animated cards (Total, Qualified, Rate, Confidence, Messages)
3. **Intent bar** — Horizontal stacked bar chart + color-coded legend
4. **Controls** — Search input + Status dropdown + Intent dropdown
5. **Lead list** — Expandable cards with avatar, phone, badges, gauge
6. **Expanded detail** — AI summary bullets, signal chips, scrollable chat

**Theme system:** Dark/Light via CSS custom properties on `[data-theme]`. Toggle persists in localStorage.

**Auto-refresh:** Every 45s, fetches leads + stats. Expanded cards and loaded chats are preserved across refreshes via `openCards` Set and `chatCache` object.

---

## Prerequisites

- **Python 3.10+**
- **MongoDB Atlas** cluster (or local MongoDB) with the `customerChats` collection
- **n8n** with the Lead Qualification Agent workflow running

---

## Quick Start

### 1. Clone & setup

```bash
git clone https://github.com/yourusername/leadq-admin.git
cd leadq-admin
python3 -m venv venv
source venv/bin/activate          # Linux/Mac
# venv\Scripts\activate           # Windows
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
nano .env
```

```env
MONGO_URI=mongodb+srv://your_user:your_password@cluster0.xxxxx.mongodb.net/
MONGO_DB=test
MONGO_COLLECTION=customerChats
HOST=0.0.0.0
PORT=8000
```

### 3. Run

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Open [http://localhost:8000](http://localhost:8000) — all leads load immediately with filters and stats.

---

## API Reference

### `GET /api/health`

Check MongoDB connection and document counts.

```json
{
  "status": "ok",
  "database": "test",
  "collection": "customerChats",
  "totalDocuments": 150,
  "withAnalysis": 142
}
```

### `GET /api/leads`

List leads with optional search, filters, sorting, and pagination.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `search` | string | — | Phone number search (digits extracted → regex match) |
| `qualified` | bool | — | Filter: `true` or `false` |
| `intent` | string | — | `INTERESTED`, `QUERY`, `NOT_INTERESTED`, `JUNK`, `FAILED` |
| `sort` | string | `desc` | Sort by `analysedAt`: `asc` or `desc` |
| `skip` | int | `0` | Pagination offset |
| `limit` | int | `50` | Results per page (max 200) |

**Example:** `GET /api/leads?search=9122&qualified=true&intent=INTERESTED`

```json
{
  "leads": [
    {
      "sessionId": "919220908612",
      "messageLength": 36,
      "analysedAt": "2026-02-08T14:05:00.000Z",
      "leadAnalysed": true,
      "hasOutput": true,
      "qualified": true,
      "intent": "INTERESTED",
      "confidence": 0.68,
      "signals": ["price", "location", "site_visit"],
      "summary": [
        "Asked about 2BHK price range",
        "Requested site visit on weekend",
        "Inquired about loan options"
      ]
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 50,
  "hasMore": false
}
```

### `GET /api/leads/{sessionId}`

Get a single lead with full chat history. Uses robust 4-strategy lookup.

```json
{
  "sessionId": "919220908612",
  "qualified": true,
  "intent": "INTERESTED",
  "confidence": 0.68,
  "signals": ["price", "location"],
  "summary": ["Asked about price", "Requested site visit"],
  "chat": [
    { "type": "human", "content": "What is the price of 2BHK?" },
    { "type": "ai", "content": "The 2BHK units start from ₹45L..." },
    { "type": "human", "content": "Can I visit the site this Saturday?" }
  ]
}
```

**SessionId lookup strategy:**
1. Exact string match → `{"sessionId": "919220908612"}`
2. Integer cast → `{"sessionId": 919220908612}`
3. Regex match → `{"sessionId": {"$regex": "919220908612"}}`
4. Scan fallback → iterates last 200 documents for partial match

### `GET /api/stats`

Aggregate statistics across all analysed leads.

```json
{
  "total": 150,
  "qualified": 87,
  "notQualified": 63,
  "qualificationRate": 0.58,
  "avgConfidence": 0.62,
  "avgMessages": 12.4,
  "intentBreakdown": {
    "INTERESTED": 52,
    "QUERY": 48,
    "NOT_INTERESTED": 30,
    "JUNK": 15,
    "FAILED": 5
  }
}
```

---

## MongoDB Document Schema

The schema your n8n workflow writes:

```json
{
  "sessionId": "919220908612",
  "messages": [
    {
      "type": "human",
      "data": { "content": "What is the price?" }
    },
    {
      "type": "ai",
      "data": { "content": "The price starts from..." }
    }
  ],
  "leadAnalysed": true,
  "analysedAt": "2026-02-08T14:05:00.000Z",
  "messageLength": 36,
  "output": {
    "qualified": true,
    "intent": "INTERESTED",
    "confidence": 0.68,
    "signals": ["price", "location"],
    "summary": ["Asked about price", "Requested site visit"]
  }
}
```

| Field | Type | Written by | Description |
|-------|------|-----------|-------------|
| `sessionId` | string or int | n8n | Phone number / WhatsApp session identifier |
| `messages` | array | n8n | Raw chat messages (human + AI) |
| `leadAnalysed` | boolean | n8n agent | Whether AI analysis has been run |
| `analysedAt` | ISO string | n8n agent | Timestamp of last analysis |
| `messageLength` | int | n8n agent | Total message count at time of analysis |
| `output` | object | n8n agent | AI qualification results |
| `output.qualified` | boolean | n8n agent | Whether lead shows purchase intent |
| `output.intent` | string | n8n agent | One of: INTERESTED, QUERY, NOT_INTERESTED, JUNK, FAILED |
| `output.confidence` | float (0–1) | n8n agent | AI confidence the lead will convert |
| `output.signals` | string[] | n8n agent | Detected keywords: price, location, EMI, site_visit, etc. |
| `output.summary` | string[] | n8n agent | 3–5 bullet points summarizing user intent |

---

## Deployment

### Option A — VPS (Hostinger KVM / DigitalOcean / AWS)

```bash
ssh root@your-server-ip
mkdir -p /opt/leadq-admin && cd /opt/leadq-admin

# Upload files (scp, rsync, or git clone)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && nano .env
```

**Systemd service** (auto-start + auto-restart):

```bash
sudo nano /etc/systemd/system/leadq-admin.service
```

```ini
[Unit]
Description=LeadQ Admin Dashboard
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/leadq-admin
EnvironmentFile=/opt/leadq-admin/.env
ExecStart=/opt/leadq-admin/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8001
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable leadq-admin
sudo systemctl start leadq-admin
```

**Nginx reverse proxy + SSL:**

```nginx
server {
    listen 80;
    server_name admin.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/leadq-admin /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d admin.yourdomain.com
```

> **Running both dashboards on one server?** Use different ports and subdomains:
>
> | Dashboard | Port | Subdomain |
> |-----------|------|-----------|
> | Admin | 8001 | `admin.yourdomain.com` |
> | Sales Agent | 8000 | `leads.yourdomain.com` |

### Option B — Railway / Render

The included `Procfile` handles the start command:

```
web: uvicorn main:app --host 0.0.0.0 --port ${PORT:-8001}
```

Push to GitHub → connect repo → set env variables → deploy.

---

## Responsive Breakpoints

| Device | Breakpoint | Stats Grid | Notes |
|--------|-----------|------------|-------|
| Large monitors | ≥1441px | 5 columns | 1200px container, bigger text |
| Laptop | 1025–1440px | auto-fit | 960px container (default) |
| Tablet | 641–1024px | 3 columns | Full-width layout |
| Phone | 381–640px | 2 columns | Stacked filters, bigger touch targets |
| Small phone | ≤380px | 2 columns | Timestamps hidden, compact spacing |
| Landscape phone | height ≤500px | 5 columns | Compressed header and stats |
| Touch devices | `pointer: coarse` | — | 44px tap targets, active press states |
| Notched phones | `safe-area-inset` | — | Content avoids notch and home bar |

---

## n8n Workflow

The Lead Qualification Agent workflow (`Lead_Qualification_Agent.json`) runs on a schedule:

1. Queries MongoDB for unanalysed chats or chats with new messages
2. Extracts human messages from each conversation
3. Sends to GPT with qualification prompt
4. Writes structured `output` back:
   - `qualified` → boolean
   - `intent` → INTERESTED / QUERY / NOT_INTERESTED / JUNK / FAILED
   - `confidence` → 0 to 1
   - `signals` → detected keywords array
   - `summary` → 3–5 bullet points

Import the workflow JSON into n8n and configure MongoDB + OpenAI credentials.

---

## Useful Commands

```bash
# Service management
sudo systemctl status leadq-admin
sudo systemctl restart leadq-admin
sudo journalctl -u leadq-admin -f        # live logs

# API testing
curl http://localhost:8001/api/health
curl http://localhost:8001/api/stats
curl "http://localhost:8001/api/leads?limit=10"
curl "http://localhost:8001/api/leads?search=9122&qualified=true"
curl "http://localhost:8001/api/leads?intent=INTERESTED&sort=asc"
curl http://localhost:8001/api/leads/919220908612

# Quick debug
python3 -c "from config import settings; print(settings.MONGO_URI[:30] + '...')"
```

---

## Admin vs Sales Agent — Comparison

| Feature | Admin (this) | Sales Agent |
|---------|:---:|:---:|
| Browse all leads on load | ✅ | ❌ |
| Status filter dropdown | ✅ | ❌ (hidden) |
| Intent filter dropdown | ✅ | ❌ (hidden) |
| Full phone numbers | ✅ | ❌ (masked: `+91••••••12`) |
| Stat cards | 5 | 6 (adds Unqualified + Total Messages) |
| Intent breakdown | ✅ | ✅ |
| Search by number | ✅ (optional) | ✅ (required, min 4 digits) |
| Expand lead details | ✅ | ✅ |
| Chat history | ✅ | ✅ |
| Auto-refresh | Always (every 45s) | Only during active search |
| Lead count in toast | ✅ (`Connected — 142 leads`) | ❌ (`Connected`) |

---

## Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/csv-export`)
3. Commit changes (`git commit -m 'Add CSV export button'`)
4. Push (`git push origin feature/csv-export`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
