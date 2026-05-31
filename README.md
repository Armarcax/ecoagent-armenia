# 🌿 EcoAgent Armenia

**ՀՀ Բnapahpanakan Orensdrutyun AI Agent**

ՀՀ բnap ahpanakan orensdrutyun, normer, standartner —
hayeren, karchucvackov, hgumnerrov.

---

## 🏗️ Architecture

```
arlis.am + EU/ISO → Knowledge Base (RAG) → Claude API → Next.js Dashboard
```

---

## ⚡ Grancarkman Qayler

### 1. Backend

```bash
cd backend
pip install -r requirements.txt

# .env stexcel
cp ../.env.example .env
# Lrecel ANTHROPIC_API_KEY

# API Gorcarkir
cd api
python main.py
# → http://localhost:8000
```

### 2. Frontend

```bash
cd frontend
npm install
cp ../.env.example .env.local
# Lrecel NEXT_PUBLIC_API_URL=http://localhost:8000

npm run dev
# → http://localhost:3000
```

### 3. Scraper (optional — seed data karas)

```bash
cd backend
python scraper/arlis_scraper.py
# → scraped_laws.json
```

---

## 📁 Nakhagits Structure

```
ecoagent/
├── backend/
│   ├── scraper/
│   │   └── arlis_scraper.py    ← arlis.am scraper
│   ├── rag/
│   │   └── rag_engine.py       ← Claude RAG engine
│   ├── api/
│   │   └── main.py             ← FastAPI backend
│   └── requirements.txt
├── frontend/
│   └── src/app/page.tsx        ← Next.js dashboard
├── .env.example
└── README.md
```

---

## 🎯 MVP Olortner

- ✅ Shanarararutyun (SHAG, taphonn, aghtotum)
- 🔄 Hanqardyunaberdutyun
- 🔄 ESG Reporting
- 🔄 Gjughatntesatyun

---

## 🔄 Roadmap

| Phase | Nkaragrutyun | Zhamkert |
|---|---|---|
| MVP | Shanarararutyun module + seed data | Week 1 |
| v0.2 | Ijakan arlis.am scraping | Week 2-3 |
| v0.3 | Pgvector + Supabase | Week 4 |
| v1.0 | Bolor olortner + API | Month 2 |

---

## 🧠 Tech Stack

- **AI**: Claude claude-sonnet-4-5 (Anthropic)
- **Backend**: Python FastAPI + RAG
- **Frontend**: Next.js 14 + TypeScript
- **DB (prod)**: Supabase + pgvector
- **Scraping**: httpx + BeautifulSoup
