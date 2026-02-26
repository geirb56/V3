# CardioCoach V3

> **The Silent Elite Coach** — An AI-powered endurance coaching application built for serious athletes who value data over motivation.

CardioCoach V3 is a full-stack application that combines a Python/FastAPI backend with a React frontend to deliver personalized training insights, AI-assisted coaching, periodization planning, and workout analytics for runners and cyclists.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Project Structure](#project-structure)
4. [Getting Started](#getting-started)
5. [Core Features](#core-features)
6. [RAG Engine](#rag-engine)
7. [API Reference](#api-reference)
8. [Testing](#testing)
9. [Internationalization](#internationalization)
10. [Design System](#design-system)
11. [Security](#security)
12. [Deployment](#deployment)
13. [Development Roadmap](#development-roadmap)
14. [Contributing](#contributing)
15. [Support](#support)

---

## Project Overview

CardioCoach V3 is an advanced AI-powered endurance coaching platform that analyzes your training data and delivers precise, data-driven feedback — without the hype.

### Key Highlights

- **AI Coach Chat** — Conversational coaching powered by a local Ollama LLM (phi3:mini / llama3.2 / qwen2.5) with Python template fallback
- **RAG Engine** — Retrieval-Augmented Generation for deterministic, fast (<1 s) coaching insights without cloud LLM dependency
- **Dashboard Insights** — Recovery score, training load analysis, and monthly performance summary
- **Weekly Review (Bilan)** — 6-card structured weekly analysis covering volume, intensity, recovery, and key workouts
- **Periodization Engine** — ACWR/TSB-based training phases (Build, Intensification, Taper, Race) for 5K through Ultra-trail goals
- **Garmin & Strava Sync** — OAuth2 PKCE integration to import workouts automatically
- **Subscription Management** — Stripe-powered tiers (Free / Starter / Confort / Pro) with per-tier message limits
- **Bilingual UI** — Full English and French support

### Technology Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python 3.11+) |
| Database | MongoDB (async via Motor) |
| AI / LLM | Ollama (local) + Python template fallback |
| RAG | Custom JSON knowledge base |
| Frontend | React 19, React Router 7 |
| Styling | Tailwind CSS 3, Shadcn/UI (Radix UI) |
| Charts | Recharts |
| Payments | Stripe (via emergentintegrations) |
| Data Sync | Garmin Connect API, Strava API |

**Language composition:** Python 57.6% · JavaScript 39.9% · CSS 1.4% · HTML 1.1%

---

## Architecture

### Backend

```
backend/
├── server.py           # FastAPI application, all API routes, auth, rate limiting
├── analysis_engine.py  # Deterministic workout & weekly analysis (no LLM)
├── chat_engine.py      # Template-based chat responses + message limit enforcement
├── coach_service.py    # Cascade strategy: RAG → LLM → template fallback
├── rag_engine.py       # RAG enrichment for dashboard, weekly review, workout analysis
├── llm_coach.py        # Ollama integration (GPT-4o-mini compatible interface)
├── training_engine.py  # Periodization: ACWR, TSB, training phases
├── knowledge_base.json # Coaching knowledge base for RAG retrieval
├── requirements.txt    # Python dependencies
└── docs/
    └── LLM_OLLAMA.md   # Ollama setup guide
```

The backend follows a **cascade strategy** for AI responses:

1. **RAG Engine** — Deterministic, knowledge-base-driven response (<1 s)
2. **LLM (Ollama)** — If available, enriches with natural language (15 s timeout)
3. **Template Fallback** — Pure Python templates if Ollama is unavailable

### Frontend

```
frontend/
├── src/
│   ├── pages/          # Route-level components
│   │   ├── Dashboard.jsx        # Main dashboard with recovery score
│   │   ├── Coach.jsx            # AI coach chat interface
│   │   ├── Digest.jsx           # Weekly review (Bilan)
│   │   ├── Progress.jsx         # Analytics & charts
│   │   ├── TrainingPlan.jsx     # Periodization planner
│   │   ├── WorkoutDetail.jsx    # Per-workout analysis
│   │   ├── DetailedAnalysis.jsx # Deep workout analysis
│   │   ├── Guidance.jsx         # Weekly guidance card
│   │   ├── Settings.jsx         # User settings & goals
│   │   └── Subscription.jsx     # Stripe subscription management
│   ├── components/     # Reusable UI components
│   │   ├── ChatCoach.jsx        # Chat message interface
│   │   ├── RecoveryGauge.jsx    # Recovery score gauge
│   │   ├── RAGSummary.jsx       # RAG-enriched summary card
│   │   ├── MetricCard.jsx       # Data metric display
│   │   ├── WorkoutCard.jsx      # Workout list item
│   │   ├── GoalSection.jsx      # Goal & event management
│   │   ├── LanguageSelector.jsx # EN/FR toggle
│   │   ├── StravaConnection.jsx # Strava OAuth connector
│   │   └── ui/                  # Shadcn/UI primitives
│   ├── context/        # React contexts (Language, Auth)
│   ├── hooks/          # Custom React hooks
│   └── lib/            # Utilities
├── tailwind.config.js
└── package.json
```

### Design System

The UI uses the **Obsidian Tactical** theme — a dark-only, data-focused design language.  
Full specification: [`design_guidelines.json`](design_guidelines.json)

- **Mode:** Dark only (no light mode)
- **Background:** `#050505` / Card: `#0A0A0A`
- **Primary:** `#3B82F6` (blue)
- **Fonts:** Manrope (body) · Barlow Condensed (headings) · JetBrains Mono (data)
- **Anti-patterns:** No gamification, no emojis, no rounded "friendly" UI

---

## Project Structure

```
V3/
├── backend/                # Python FastAPI backend
├── frontend/               # React frontend
├── tests/                  # Shared test utilities
│   ├── base_tester.py      # Base test class
│   └── __init__.py
├── backend_test.py         # Root-level integration tests
├── backend_test_hidden_insight.py  # Hidden insight tests
├── test_guidance.py        # Guidance endpoint tests
├── config.py               # Shared configuration
├── design_guidelines.json  # UI/UX design specification
├── memory/                 # Agent memory store
└── test_reports/           # Test output reports
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+ and Yarn
- MongoDB instance (local or Atlas)
- (Optional) [Ollama](https://ollama.com) for local LLM support

### Backend Setup

```bash
# 1. Navigate to the backend directory
cd backend

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create the environment file
cp .env.example .env
# Edit .env with your values (see Environment Variables below)

# 5. Start the server
uvicorn server:app --reload --host 0.0.0.0 --port 8001
```

### Frontend Setup

```bash
# 1. Navigate to the frontend directory
cd frontend

# 2. Install dependencies
yarn install

# 3. Create the environment file
echo "REACT_APP_BACKEND_URL=http://localhost:8001" > .env

# 4. Start the development server
yarn start
```

The frontend will be available at `http://localhost:3000`.

### Ollama Setup (Optional — AI Chat Enhancement)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Start the service
ollama serve &

# Pull a recommended model
ollama pull phi3:mini
# or for better quality:
ollama pull llama3.2:3b-instruct
```

See [`backend/docs/LLM_OLLAMA.md`](backend/docs/LLM_OLLAMA.md) for full details and model comparison.

### Running Tests

```bash
# Backend tests (from repository root)
pytest backend/tests/ -v

# Individual test files
pytest backend/tests/test_weekly_review.py -v
pytest backend/tests/test_dashboard_insight.py -v
pytest backend_test.py -v
```

---

## Core Features

### Dashboard Insights

**Route:** `GET /api/dashboard/insight`

Generates a monthly performance summary including:
- **Recovery Score** — Composite metric derived from recent training load, rest days, and heart rate trends
- **Volume analysis** — Total km/minutes vs. previous period
- **Key metrics** — Calories burned, elevation gain, session count
- **RAG-enriched commentary** — Personalised coaching message based on training patterns

### Weekly Review (Bilan)

**Route:** `GET /api/weekly-review`

Six-card structured analysis of the last 7 days:
1. **Volume** — Total distance and duration
2. **Intensity** — Zone distribution breakdown
3. **Recovery** — Rest quality indicators
4. **Key Workout** — Best session of the week
5. **Trend** — Week-over-week comparison
6. **Recommendation** — Next week guidance

### AI Coach Chat

**Route:** `POST /api/chat/send`

Conversational coaching with:
- Context-aware responses using recent workout data (personalized per user)
- Per-subscription message limits (Free: 10 · Starter: 25 · Confort: 50 · Pro: 150)
- Quick suggestion chips for common coaching questions
- LLM (Ollama) enrichment when available, Python templates as fallback
- Persistent conversation history stored in MongoDB

### Workout Analysis

**Route:** `GET /api/workouts/{id}/analysis`

Per-session detailed analysis:
- Intensity level classification (Easy / Moderate / Hard / Very Hard)
- Pace / speed / heart rate breakdown
- Effort zone distribution
- Actionable coaching feedback

**Route:** `POST /api/coach/analyze`  
Deep analysis using the coach cascade strategy (RAG → LLM → template).

### Training Plans & Periodization

**Route:** `GET /api/training/plan`

Evidence-based periodization engine supporting:

| Goal | Cycle Length | Long Run Ratio | Intensity |
|---|---|---|---|
| 5K | 6 weeks | 25% | 20% |
| 10K | 8 weeks | 30% | 18% |
| Half Marathon | 12 weeks | 35% | 15% |
| Marathon | 16 weeks | 40% | 12% |
| Ultra-trail | 20 weeks | 45% | 10% |

Calculates ACWR (Acute:Chronic Workload Ratio) and TSB (Training Stress Balance) to determine the current training phase: **Build → Intensification → Taper → Race**.

### User Goals & Events

**Routes:** `GET/POST /api/goals`, `GET/POST /api/events`

- Set a target race and goal distance
- Track weeks-to-race countdown
- Automatic phase determination based on event date

### Data Sync

**Garmin Connect:**
- OAuth2 with PKCE (S256 challenge)
- Routes: `GET /api/garmin/auth`, `GET /api/garmin/callback`, `POST /api/garmin/sync`
- Imports running and cycling activities with heart rate zones

**Strava:**
- OAuth2 integration
- Routes: `GET /api/strava/auth`, `GET /api/strava/callback`, `GET /api/strava/status`

### Subscription Management

**Routes:** `GET /api/subscription`, `POST /api/subscription/checkout`, `GET /api/subscription/status`

| Tier | Monthly | Annual | Messages/Month |
|---|---|---|---|
| Free (Gratuit) | €0 | €0 | 10 |
| Starter | €4.99 | €49.99 | 25 |
| Confort | €5.99 | €59.99 | 50 |
| Pro | €9.99 | €99.99 | 150 (fair-use) |

Payments are processed via Stripe Checkout. Webhook handling at `POST /api/webhooks/stripe`.

---

## RAG Engine

The RAG (Retrieval-Augmented Generation) engine (`backend/rag_engine.py`) provides fast, deterministic coaching enrichment without requiring a live LLM.

### Knowledge Base

`backend/knowledge_base.json` contains structured coaching knowledge:
- Training principles and periodization rules
- Heart rate zone guidance
- Recovery indicators
- Sport-specific advice (running, cycling)

### How It Works

1. **Metrics Calculation** — Computes key indicators from raw workout data (ACWR, weekly load, zone distribution)
2. **Context Retrieval** — Selects relevant knowledge fragments based on computed metrics
3. **Template Assembly** — Builds a structured response using pre-defined templates with variable substitution
4. **LLM Enrichment** (optional) — If Ollama is available, the assembled context is passed to the LLM for natural language enhancement

### Enrichment Entry Points

| Function | Endpoint |
|---|---|
| `generate_dashboard_rag()` | `GET /api/dashboard/insight` |
| `generate_weekly_review_rag()` | `GET /api/weekly-review` |
| `generate_workout_analysis_rag()` | `GET /api/workouts/{id}/analysis` |

---

## API Reference

### Authentication

The API uses a flexible authentication scheme (priority order):

1. **Bearer token** — `Authorization: Bearer <token>` (token prefixed with `user_` used directly as user ID; JWT validation planned)
2. **Header** — `X-User-Id: <user_id>`
3. **Query parameter** — `?user_id=<user_id>`
4. **Fallback** — `"default"` user

### Rate Limiting

- **60 requests/minute** per user
- **Burst limit:** 10 requests in 2 seconds
- Exceeded requests return `HTTP 429` with `retry_after: 60`

### Key Endpoints

#### Workouts

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/workouts` | List all workouts (`?user_id=`, `?limit=`, `?type=`) |
| `POST` | `/api/workouts` | Create a workout |
| `GET` | `/api/workouts/{id}` | Get workout by ID |
| `DELETE` | `/api/workouts/{id}` | Delete a workout |
| `GET` | `/api/workouts/{id}/analysis` | Get workout analysis |
| `GET` | `/api/stats` | Aggregate training statistics |

#### Coaching

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/chat/send` | Send a message to the AI coach |
| `GET` | `/api/chat/history` | Get conversation history |
| `GET` | `/api/chat/remaining` | Get remaining messages for current tier |
| `POST` | `/api/coach/analyze` | Deep workout analysis (cascade) |
| `GET` | `/api/weekly-review` | Weekly review (Bilan) |
| `GET` | `/api/dashboard/insight` | Dashboard RAG insight |
| `GET` | `/api/guidance` | Weekly guidance card |

#### Training & Goals

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/training/plan` | Get periodized training plan |
| `GET/POST` | `/api/goals` | Manage user goals |
| `GET/POST` | `/api/events` | Manage target events |

#### Data Sync

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/garmin/auth` | Start Garmin OAuth flow |
| `GET` | `/api/garmin/callback` | Garmin OAuth callback |
| `POST` | `/api/garmin/sync` | Sync Garmin activities |
| `GET` | `/api/garmin/status` | Garmin connection status |
| `GET` | `/api/strava/auth` | Start Strava OAuth flow |
| `GET` | `/api/strava/callback` | Strava OAuth callback |
| `GET` | `/api/strava/status` | Strava connection status |

#### Subscription

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/subscription` | Get current subscription |
| `POST` | `/api/subscription/checkout` | Create Stripe checkout session |
| `GET` | `/api/subscription/status` | Check checkout status |
| `POST` | `/api/webhooks/stripe` | Stripe webhook handler |

### Response Format

All responses follow standard HTTP status codes. Success responses return JSON objects. Errors return:

```json
{
  "detail": "Error description"
}
```

---

## Testing

### Test Coverage Overview

The project includes tests across multiple feature areas:

| Test File | Coverage Area |
|---|---|
| `backend/tests/test_dashboard_insight.py` | Dashboard RAG insight generation |
| `backend/tests/test_weekly_review.py` | Weekly review 6-card structure |
| `backend/tests/test_coach_conversational.py` | AI coach chat responses |
| `backend/tests/test_detailed_analysis.py` | Deep workout analysis |
| `backend/tests/test_enhanced_goal.py` | Goal management endpoints |
| `backend/tests/test_mobile_workout_analysis.py` | Mobile workout analysis |
| `backend/tests/test_new_features.py` | General new feature tests |
| `backend/tests/test_rag_endpoints.py` | RAG enrichment endpoints |
| `backend/tests/test_rag_enrichment.py` | RAG engine unit tests |
| `backend/tests/test_strava_integration.py` | Strava OAuth integration |
| `backend/tests/test_subscription_chat.py` | Subscription + message limits |
| `backend/tests/test_weekly_digest.py` | Weekly digest generation |
| `backend_test.py` | Root-level integration tests |
| `backend_test_hidden_insight.py` | Hidden insight feature tests |
| `test_guidance.py` | Guidance endpoint tests |

### Running Tests

```bash
# Run all backend tests
pytest backend/tests/ -v

# Run a specific test file
pytest backend/tests/test_weekly_review.py -v

# Run tests with output
pytest backend/tests/ -v -s

# Run root-level tests
pytest backend_test.py test_guidance.py -v
```

### Test Utilities

`tests/base_tester.py` provides a shared base class with helpers for:
- API request setup
- Test data fixtures
- Assertion utilities

---

## Internationalization

CardioCoach V3 supports **English** and **French** throughout the application.

- Language selection is available via the `LanguageSelector` component in the UI
- The language preference is stored in React context (`context/LanguageContext`)
- All API coaching endpoints accept a `language` parameter (`"en"` or `"fr"`)
- The `CoachRequest` model includes `language: Optional[str] = "en"`
- RAG templates and LLM prompts are generated in the requested language

---

## Design System

The design system is defined in [`design_guidelines.json`](design_guidelines.json) and implements the **Obsidian Tactical** visual language.

### Identity

- **Persona:** The Silent Elite Coach
- **Tone:** Calm, Neutral, Precise, Stoic
- **Keywords:** Endurance · Data · Precision · Obsidian · Tactical

### Color Palette

| Token | Value | Usage |
|---|---|---|
| `background` | `#050505` | Page background |
| `card` | `#0A0A0A` | Card background |
| `primary` | `#3B82F6` | Interactive elements, key data |
| `secondary` | `#262626` | Secondary surfaces |
| `muted` | `#171717` | Subtle backgrounds |
| `foreground` | `#EDEDED` | Primary text |
| `muted-foreground` | `#737373` | Secondary text |
| `border` | `#262626` | Dividers and borders |

### Typography

| Role | Font | Style |
|---|---|---|
| Headings | Barlow Condensed | uppercase, bold, tight tracking |
| Body | Manrope | normal tracking |
| Data / metrics | JetBrains Mono | xs, uppercase, wide tracking |
| Labels | JetBrains Mono | 10px, uppercase, widest tracking |

### Anti-Patterns

The design explicitly avoids: gamification badges, confetti animations, social sharing features, motivational slogans, emojis, light mode, and rounded "friendly" UI elements.

---

## Security

### Authentication

- Bearer token authentication (JWT validation planned; currently token-as-user-id for development)
- Fallback to `X-User-Id` header or `user_id` query parameter
- User isolation: all data queries are scoped to the authenticated `user_id`

### Rate Limiting

- In-memory rate limiter: 60 req/min per user, burst limit of 10 req/2 s
- Automatic stale-entry cleanup every 5 minutes

### Input Validation

- All request bodies validated with Pydantic v2 models and field validators
- Workout `type` is validated against an allowed set (`run`, `cycle`, `swim`)
- User-supplied `notes` are HTML-stripped (regex) and length-capped at 500 characters to prevent stored XSS

### API Keys & Secrets

- All secrets loaded from environment variables via `python-dotenv` — never hardcoded
- Garmin OAuth uses PKCE (S256) to prevent authorization code interception

### Database Security

- MongoDB connection string stored in `MONGO_URL` environment variable
- All queries are parameterized via Motor (async MongoDB driver)

### CORS

- Configurable `FRONTEND_URL` environment variable controls allowed origins
- Starlette `CORSMiddleware` applied at the application level

### Payments

- Stripe webhook signature verification (via `emergentintegrations`)
- Checkout sessions are server-side only — no client-side secret handling

---

## Deployment

### Environment Variables

Create a `.env` file in the `backend/` directory:

```env
# Database
MONGO_URL=mongodb://localhost:27017
DB_NAME=cardiocoach

# Stripe
STRIPE_API_KEY=sk_live_...

# Garmin Connect OAuth
GARMIN_CLIENT_ID=your_garmin_client_id
GARMIN_CLIENT_SECRET=your_garmin_client_secret
GARMIN_REDIRECT_URI=https://your-domain.com/api/garmin/callback

# Strava OAuth
STRAVA_CLIENT_ID=your_strava_client_id
STRAVA_CLIENT_SECRET=your_strava_client_secret
STRAVA_REDIRECT_URI=https://your-domain.com/api/strava/callback

# Frontend URL (for CORS)
FRONTEND_URL=https://your-domain.com

# Ollama (optional)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=phi3:mini
```

### Development

```bash
# Backend (hot reload)
cd backend && uvicorn server:app --reload --host 0.0.0.0 --port 8001

# Frontend (hot reload)
cd frontend && yarn start
```

### Production

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001 --workers 4

# Frontend
cd frontend
yarn build
# Serve the build/ directory with nginx or any static file server
```

The backend includes GZip compression middleware (responses > 1 KB are compressed automatically).

---

## Development Roadmap

### Completed in V3

- [x] FastAPI backend with async MongoDB (Motor)
- [x] RAG Engine with JSON knowledge base
- [x] Ollama LLM integration with Python template fallback
- [x] Dashboard Insights with Recovery Score
- [x] Weekly Review (Bilan) — 6-card structure
- [x] AI Coach Chat with per-tier message limits
- [x] Per-session Workout Analysis
- [x] Training Periodization Engine (ACWR, TSB, phases)
- [x] Goal & Event management
- [x] Garmin Connect OAuth2/PKCE integration
- [x] Strava OAuth integration
- [x] Stripe subscription management (4 tiers)
- [x] Bilingual UI (EN/FR)
- [x] Obsidian Tactical design system
- [x] Rate limiting middleware
- [x] Input validation and XSS protection
- [x] GZip response compression
- [x] Comprehensive test suite

### Planned

- [ ] Full JWT authentication
- [ ] Push notifications for weekly review
- [ ] Polar / Wahoo device integration
- [ ] iOS/Android PWA enhancements
- [ ] Advanced analytics dashboard
- [ ] Multi-sport support (swimming, triathlon)

---

## Contributing

### Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes following the code standards below
4. Write or update tests for your changes
5. Ensure all existing tests pass: `pytest backend/tests/ -v`
6. Open a Pull Request against `main` with a clear description

### Code Standards

**Python (backend):**
- Follow PEP 8; format with `black` and sort imports with `isort`
- Type hints required for all function signatures
- Pydantic models for all request/response bodies
- Run `flake8` and `mypy` before submitting

**JavaScript (frontend):**
- ESLint with React and React Hooks plugins (config in project root)
- Functional components with hooks only (no class components)
- Tailwind CSS utility classes; custom CSS only when unavoidable

**General:**
- Minimal dependencies — prefer the standard library or existing packages
- No secrets or API keys in source code
- All user inputs must be validated and sanitized

### Test Coverage Requirements

- New backend endpoints must have at least one test in `backend/tests/`
- Tests should use the `base_tester.py` utilities where applicable
- Tests must pass without a live MongoDB or Stripe connection (mock as needed)

---

## Support

- **Bug reports:** [Open an issue](https://github.com/geirb56/V3/issues)
- **Feature requests:** [Start a discussion](https://github.com/geirb56/V3/discussions)
- **Security vulnerabilities:** Report privately via GitHub Security Advisories

---

*CardioCoach V3 — Precision over motivation.*