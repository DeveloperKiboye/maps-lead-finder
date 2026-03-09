# 📍 Maps Lead Finder

A FastAPI web application that scrapes Google Maps and surfaces local businesses
**without websites** — perfect for freelancers and web developers hunting for
clients who need an online presence.

---

## ✨ Features

| Feature | Detail |
|---|---|
| Google Maps scraper | Playwright-powered, async, headless Chromium |
| Auto-scroll | Loads up to 100 listings per search |
| Data extraction | Name · Phone · Address · Rating · Reviews · Website · Maps URL |
| Opportunity Score | 0–100 scoring system (HIGH / MEDIUM / LOW) |
| Live results table | Filterable by opportunity level, sortable by score |
| Summary stats | Total scraped · Without websites · Highest score |
| Dark UI | Terminal-style interface with color-coded badges |

---

## 🗂 Project Structure

```
maps-lead-finder/
├── main.py            # FastAPI routes & app wiring
├── scraper.py         # Async Playwright scraping logic
├── utils.py           # Scoring, cleaning, helper functions
├── requirements.txt
├── render.yaml        # One-click Render deployment config
├── templates/
│   └── index.html     # Jinja2 template — search + results
└── static/
    └── style.css      # Dark-theme styles
```

---

## 🚀 Local Setup

### 1 — Clone / copy the project
```bash
cd maps-lead-finder
```

### 2 — Install Python dependencies
```bash
pip install -r requirements.txt
```

### 3 — Install Playwright browsers
```bash
playwright install chromium
playwright install-deps chromium   # Linux only — installs system deps
```

### 4 — Run the dev server
```bash
uvicorn main:app --reload
```

Open **http://localhost:8000** in your browser.

---

## 🔍 Usage

1. Type a query such as `barbershop Nairobi` or `car wash Westlands`.
2. Click **Generate Leads**.
3. Wait 2–4 minutes while the scraper works.
4. Browse the results table — rows are sorted by Opportunity Score (highest first).
5. Use the filter buttons to show only HIGH / MEDIUM / LOW leads.
6. Click **View ↗** to open any listing directly in Google Maps.

### Example queries
```
barbershop Nairobi
salon Westlands
car wash Nairobi CBD
gym Karen Nairobi
restaurant Kilimani
plumber Nairobi
dentist Thika
```

---

## 📊 Opportunity Score Logic

| Condition | Points |
|---|---|
| No website | +40 |
| Rating ≥ 4.0 | +25 |
| Reviews ≥ 30 | +20 |
| Phone number exists | +10 |
| Address exists | +5 |
| **Max total** | **100** |

| Score | Level |
|---|---|
| 80–100 | 🟢 HIGH |
| 50–79 | 🟠 MEDIUM |
| < 50 | 🔴 LOW |

---

## ☁️ Deploying to Render

### Option A — render.yaml (recommended)

The repo includes a `render.yaml` file. Simply:

1. Push the project to a GitHub repository.
2. Go to [render.com](https://render.com) → **New → Web Service**.
3. Connect your GitHub repo.
4. Render will auto-detect `render.yaml` and configure everything.
5. Click **Deploy** — done!

### Option B — Manual setup on Render

1. Push your code to GitHub.
2. Render → **New Web Service** → connect repo.
3. Fill in the settings:

| Field | Value |
|---|---|
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt && playwright install chromium && playwright install-deps chromium` |
| **Start Command** | `uvicorn main:app --host 0.0.0.0 --port 10000` |

4. Add environment variable:

| Key | Value |
|---|---|
| `PYTHONUNBUFFERED` | `1` |
| `PLAYWRIGHT_BROWSERS_PATH` | `/opt/render/.cache/ms-playwright` |

5. Click **Create Web Service**.

### ⚠️ Render notes

- Scraping can be slow on the free tier — upgrade to **Starter** ($7/mo) for
  better CPU and no instance sleep.
- Playwright's Chromium adds ~200 MB to the build — this is expected.
- The first deploy takes ~5 minutes (browser installation).
- Render's free tier **sleeps after 15 minutes of inactivity**; the first
  request after sleep takes ~30 s to wake. Use Starter to avoid this.

---

## 🛠 Tech Stack

- **Python 3.11+**
- **FastAPI** — async web framework
- **Playwright** — browser automation
- **Pandas** — in-memory data wrangling
- **Jinja2** — server-side HTML templating

---

## 📝 License

MIT — use freely, attribution appreciated.
