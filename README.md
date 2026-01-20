# Authoricy SEO Analyzer

Automated SEO analysis system powered by DataForSEO API and Claude AI.

## Features

- **45+ DataForSEO endpoints** across 4 collection phases
- **Parallel execution** for fast data collection (15-30 seconds)
- **Claude AI analysis** for executive and tactical reports
- **PDF generation** with WeasyPrint
- **Email delivery** via Resend
- **Webhook support** for Tally forms

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          API ENDPOINT                                    │
│                        (FastAPI / Vercel)                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  POST /api/analyze     → Trigger analysis                               │
│  POST /api/webhook/tally → Tally form webhook                           │
│  GET  /api/jobs/:id    → Check job status                               │
│                                                                         │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     DATA COLLECTION ORCHESTRATOR                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Phase 1: Foundation (8 endpoints)                                      │
│  ├── Domain overview, historical data                                   │
│  ├── Competitor identification                                          │
│  └── Technical baseline (Lighthouse)                                    │
│                                                                         │
│  Phase 2: Keyword Intelligence (12 endpoints)                           │
│  ├── Ranked keywords, keyword universe                                  │
│  ├── Intent classification                                              │
│  ├── Keyword expansion (suggestions + related)                          │
│  └── Gap identification, difficulty scoring                             │
│                                                                         │
│  Phase 3: Competitive & Backlinks (14 endpoints)                        │
│  ├── Competitor metrics                                                 │
│  ├── Keyword overlaps                                                   │
│  ├── Backlink profile (links, anchors, referring domains)               │
│  └── Link gap analysis, velocity                                        │
│                                                                         │
│  Phase 4: AI & Technical (11 endpoints)                                 │
│  ├── AI visibility (ChatGPT, Google AI)                                 │
│  ├── Brand mentions, sentiment                                          │
│  ├── Google Trends                                                      │
│  └── Technical audits                                                   │
│                                                                         │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        CLAUDE ANALYSIS                                   │
│                      (Executive + Tactical)                             │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     PDF GENERATION + EMAIL                               │
└─────────────────────────────────────────────────────────────────────────┘
```

## Setup

### 1. Clone and install

```bash
cd authoricy-analyzer
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

Required credentials:
- **DATAFORSEO_LOGIN**: Your DataForSEO account email
- **DATAFORSEO_PASSWORD**: Your DataForSEO API password
- **ANTHROPIC_API_KEY**: Your Claude API key

### 3. Test locally

```bash
# Run a test analysis
python scripts/test_local.py example.com --skip-ai

# With full AI analysis
python scripts/test_local.py example.com -o results.json

# Different market
python scripts/test_local.py example.com --market "United States" --language en
```

### 4. Run API server

```bash
# Development
uvicorn api.analyze:app --reload

# Production
uvicorn api.analyze:app --host 0.0.0.0 --port 8000
```

### 5. Test API

```bash
# Trigger analysis
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"domain": "example.com", "email": "test@example.com"}'

# Check status
curl http://localhost:8000/api/jobs/{job_id}
```

## Deployment

### Vercel

1. Create `vercel.json`:
```json
{
  "builds": [
    {"src": "api/analyze.py", "use": "@vercel/python"}
  ],
  "routes": [
    {"src": "/api/(.*)", "dest": "api/analyze.py"}
  ]
}
```

2. Deploy:
```bash
vercel
```

### Railway

1. Connect GitHub repo to Railway
2. Add environment variables
3. Deploy automatically

## Project Structure

```
authoricy-analyzer/
├── api/
│   └── analyze.py          # FastAPI endpoint
├── src/
│   ├── collector/
│   │   ├── client.py       # DataForSEO HTTP client
│   │   ├── orchestrator.py # Coordinates all phases
│   │   ├── phase2.py       # Keyword intelligence
│   │   ├── phase3.py       # Competitive & backlinks
│   │   └── phase4.py       # AI & technical
│   └── utils/
│       └── config.py       # Configuration
├── scripts/
│   └── test_local.py       # Local testing script
├── requirements.txt
├── .env.example
└── README.md
```

## Cost Estimation

Per analysis:
- **DataForSEO**: $1.50-3.00 (45 endpoints)
- **Claude Sonnet**: $0.30-0.50 (~50K input + ~8K output)
- **Total**: ~$2-4 per analysis

Monthly (100 analyses):
- DataForSEO: ~$200
- Claude: ~$40
- Infrastructure: $0-20 (Vercel/Railway free tier)
- **Total**: ~$240-260/month

## Next Steps

- [ ] Add Phase 1 collector (foundation data)
- [ ] Add Claude analyzer module
- [ ] Add PDF generation with WeasyPrint
- [ ] Add email delivery with Resend
- [ ] Add admin UI
- [ ] Connect to Lovable frontend

## License

Proprietary - Authoricy
