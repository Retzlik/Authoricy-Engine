# Authoricy Intelligence System

**World-Class Automated SEO Analysis powered by DataForSEO API and Claude AI.**

## Overview

Authoricy Intelligence System is a production-ready automated SEO analysis platform that delivers comprehensive domain analysis, competitive intelligence, and strategic recommendations. The system combines extensive data collection (60 DataForSEO endpoints) with AI-powered analysis (4 Claude analysis loops) to generate world-class SEO reports.

### Key Capabilities

- **Complete Domain Analysis** with 12-24 month historical trends
- **Full Keyword Universe Mapping** with topical coverage analysis
- **4-Competitor Deep Dive** with trajectory comparison
- **Comprehensive Backlink Intelligence** with link gap identification
- **Industry-Leading AI Visibility Assessment** (10 dedicated endpoints)
- **Multi-Page Technical Audit** with Core Web Vitals
- **AI-Synthesized Strategic Recommendations**

### Quality Targets

| Metric | Target |
|--------|--------|
| Total API Endpoints | 60 |
| Data Collection Cost | $0.95-1.28/report |
| Analysis Cost (Claude) | $0.80-1.25/report |
| **Total Cost per Report** | **$1.75-2.53** |
| Execution Time | 3-5 minutes |
| Quality Score | ≥8/10 |

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          INPUT LAYER                                     │
│  • Target Domain    • Market/Language    • Industry    • Email           │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    DATA COLLECTION ENGINE (60 Endpoints)                 │
├─────────────────────────────────────────────────────────────────────────┤
│  Phase 1: Foundation (8 endpoints)     │ Phase 2: Keywords (16 endpoints)│
│  Phase 3: Competitive (19 endpoints)   │ Phase 4: AI & Tech (17 endpoints)│
│                                                                          │
│  Parallel execution | 45-90 seconds | $0.95-1.28                        │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      ANALYSIS ENGINE (4 Loops)                           │
├─────────────────────────────────────────────────────────────────────────┤
│  Loop 1: Data Interpretation      → Structured findings                  │
│  Loop 2: Strategic Synthesis      → Prioritized recommendations         │
│  Loop 3: SERP Enrichment          → Content requirements                │
│  Loop 4: Quality Review           → Executive summary + quality gate    │
│                                                                          │
│  Claude Sonnet 4 | $0.80-1.25 | Quality Gate ≥8/10                      │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         REPORT GENERATION                                │
│  External Report (10-15 pages)    │    Internal Report (40-60 pages)    │
│  Executive-focused, Sales-enabling │    Tactical playbook                │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           DELIVERY LAYER                                 │
│  • Email via Resend    • PDF attachment    • Follow-up sequences        │
└─────────────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
authoricy-engine/
├── api/
│   └── analyze.py              # FastAPI endpoints
├── src/
│   ├── collector/              # Data collection (60 endpoints)
│   │   ├── client.py           # DataForSEO HTTP client
│   │   ├── orchestrator.py     # Collection coordination
│   │   ├── phase1.py           # Foundation data (8 endpoints)
│   │   ├── phase2.py           # Keyword intelligence (16 endpoints)
│   │   ├── phase3.py           # Competitive analysis (19 endpoints)
│   │   └── phase4.py           # AI & technical (17 endpoints)
│   ├── analyzer/               # Claude AI analysis
│   │   ├── client.py           # Claude API client
│   │   ├── engine.py           # Analysis orchestration
│   │   ├── loop1.py            # Data interpretation
│   │   ├── loop2.py            # Strategic synthesis
│   │   ├── loop3.py            # SERP enrichment
│   │   └── loop4.py            # Quality review
│   ├── reporter/               # PDF generation
│   │   ├── generator.py        # Report orchestration
│   │   ├── external.py         # External report (lead magnet)
│   │   ├── internal.py         # Internal report (strategy guide)
│   │   └── charts.py           # SVG chart generation
│   ├── delivery/               # Email delivery
│   │   └── email.py            # Resend integration
│   ├── models/                 # Shared data models
│   └── utils/
│       └── config.py           # Configuration management
├── scripts/
│   └── test_local.py           # Local testing
├── requirements.txt
└── README.md
```

## Setup

### 1. Clone and Install

```bash
git clone <repository-url>
cd authoricy-engine
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

**Required:**
- `DATAFORSEO_LOGIN`: DataForSEO account email
- `DATAFORSEO_PASSWORD`: DataForSEO API password
- `ANTHROPIC_API_KEY`: Claude API key

**Optional:**
- `RESEND_API_KEY`: Resend API key for email delivery
- `FROM_EMAIL`: Sender email address

### 3. Run Locally

```bash
# Test data collection only
python scripts/test_local.py example.com --skip-ai

# Full analysis with AI
python scripts/test_local.py example.com -o results.json

# Different market
python scripts/test_local.py example.com --market "United States" --language en
```

### 4. Run API Server

```bash
# Development
uvicorn api.analyze:app --reload

# Production
uvicorn api.analyze:app --host 0.0.0.0 --port 8000
```

### 5. API Usage

```bash
# Trigger analysis
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"domain": "example.com", "email": "you@example.com"}'

# Check status
curl http://localhost:8000/api/jobs/{job_id}
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/api/health` | Detailed health status |
| `POST` | `/api/analyze` | Trigger analysis |
| `GET` | `/api/jobs/{id}` | Get job status |
| `POST` | `/api/webhook/tally` | Tally form webhook |

## Cost Breakdown

### Per Report
| Component | Cost |
|-----------|------|
| Phase 1: Foundation (8 endpoints) | $0.12-0.15 |
| Phase 2: Keywords (16 endpoints) | $0.25-0.35 |
| Phase 3: Competitive (19 endpoints) | $0.40-0.50 |
| Phase 4: AI & Tech (17 endpoints) | $0.30-0.40 |
| **Data Collection Total** | **$0.95-1.28** |
| Loop 1-4: Claude Analysis | $0.80-1.25 |
| **Grand Total** | **$1.75-2.53** |

### Monthly (100 analyses)
- DataForSEO: ~$100-130
- Claude AI: ~$80-125
- Infrastructure: ~$10-50
- **Total: ~$190-305/month**

## Output Reports

### External Report (Lead Magnet)
- **Pages:** 10-15
- **Audience:** Executives
- **Purpose:** Create urgency, demonstrate expertise
- **Sections:** Executive Summary, Current Position, Competitive Landscape, Opportunity, Roadmap, Next Steps

### Internal Report (Strategy Guide)
- **Pages:** 40-60
- **Audience:** SEO practitioners
- **Purpose:** Tactical implementation playbook
- **Sections:** Complete domain analysis, Keyword universe, Competitive intelligence, Backlink strategy, AI visibility playbook, Content strategy, Technical register, Implementation plan

## Technology Stack

| Component | Technology |
|-----------|------------|
| Runtime | Python 3.11+ |
| Framework | FastAPI |
| HTTP Client | httpx |
| Data Source | DataForSEO API |
| AI Engine | Claude API (Sonnet 4) |
| PDF Generation | WeasyPrint |
| Email Delivery | Resend |

## Deployment

### Railway
```bash
railway up
```

### Vercel
Create `vercel.json`:
```json
{
  "builds": [{"src": "api/analyze.py", "use": "@vercel/python"}],
  "routes": [{"src": "/api/(.*)", "dest": "api/analyze.py"}]
}
```

## License

Proprietary - Authoricy

---

*Built with precision for world-class SEO intelligence.*
