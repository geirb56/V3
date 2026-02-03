# CardioCoach - AI-Powered Endurance Coaching App

## Overview
CardioCoach is an elite endurance coaching app specialized in running, cycling, and cardio-based sports. It provides data-driven performance insights with a calm, neutral, and precise tone.

## User Persona
- Serious endurance athletes (runners, cyclists)
- Data-driven athletes seeking performance analysis
- Users who prefer minimal, no-nonsense interfaces
- English and French speaking athletes

## Core Requirements (Static)
- NOT a medical application - performance coaching only
- Analyze training data: heart rate, pace, speed, duration, effort distribution
- Tone: Calm, neutral, precise - no hype, no motivation, no emojis
- Dark theme, minimal UI, no gamification, no social features
- Full bilingual support (English/French)

## What's Been Implemented

### Phase 1 - MVP (Feb 1, 2026)
- FastAPI backend with MongoDB integration
- Mock workout data (demo)
- Dashboard, Coach, Workout Detail, Progress pages
- AI Coach with GPT-5.2 via Emergent LLM key
- Obsidian Tactical dark theme

### Phase 2 - Bilingual Support (Feb 1, 2026)
- i18n system with explicit EN/FR dictionaries
- Language toggle in Settings page (EN/FR)
- All UI labels, buttons, screens translated
- AI Coach responds in selected language
- Language preference persisted in localStorage
- No screen duplication - single logic layer

### Phase 3 - Persistent Memory & Deep Analysis (Feb 1, 2026)
- Persistent AI coach memory per user (MongoDB 'conversations' collection)
- Coach remembers past workouts and prior advice
- Memory used subtly (no "as I said before")
- "Analyze" button on each workout detail page
- Auto-triggered deep technical analysis with structured output
- Expert-level, actionable insights (not generic)
- Clear history functionality
- Structured analysis format: Execution Assessment, Physiological Signals, Technical Observations, Actionable Insight

### Phase 4 - Contextual Baseline Comparison (Feb 1, 2026)
- Baseline metrics calculated from last 14 days of same workout type
- Comparison metrics: HR vs baseline, distance vs baseline, pace vs baseline
- Trend detection: Improving / Maintaining / Overload Risk
- Insights expressed in relative terms:
  - "slightly elevated compared to your recent baseline"
  - "consistent with your 7-day average"
  - "this represents a modest increase in training load"
- Calm, precise, non-alarmist tone maintained
- Structured deep analysis with 4 sections:
  1. EXECUTION ASSESSMENT (with baseline comparison)
  2. TREND DETECTION (improving/maintaining/overload risk)
  3. PHYSIOLOGICAL CONTEXT (zone distribution vs recent patterns)
  4. ACTIONABLE INSIGHT (based on current load vs baseline)

### Phase 5 - Hidden Insight Feature (Feb 1, 2026)
- Probabilistic "Hidden Insight" section (~60% chance of appearing)
- Focuses on non-obvious patterns:
  - Effort distribution anomalies
  - Pacing stability (drift patterns, splits)
  - Efficiency signals (pace-to-HR ratio)
  - Fatigue fingerprints (late-session degradation)
  - Aerobic signature patterns
- Variable length: sometimes one sentence, sometimes 2-3
- Uses curious phrasing: "Worth noting...", "Something subtle here...", "An interesting pattern..."
- Rules enforced: no motivation, no alarms, no medical terms
- Backend logs hidden insight inclusion status
- Goal: perceived coach intelligence without overuse

### Phase 6 - Adaptive Training Guidance (Feb 2, 2026)
- New /guidance page for short-term training recommendations
- No rigid schedules or fixed weekly plans
- Adapts based on completed workouts (analyzes last 14 days)
- Max 3 suggested sessions ahead
- Each suggestion includes:
  - Type (run/cycle/recovery)
  - Focus (aerobic base, speed, recovery, threshold)
  - Duration/Distance
  - Intensity (easy/moderate/hard)
  - "Why now" rationale tied to recent training
- Status indicators:
  - MAINTAIN: training balanced, continue approach
  - ADJUST: minor tweaks needed
  - HOLD STEADY: consolidate before adding more
- Calm, technical, non-motivational tone
- Full EN/FR support
- Disclaimer: "Guidance only. Not a fixed plan."

### Phase 7 - Garmin Connect Integration Structure (Feb 2, 2026) [DORMANT]
- Full OAuth 2.0 PKCE flow for Garmin Connect (backend only)
- Import running and cycling activities only
- Data mapping with graceful fallback for missing metrics
- **Note**: Backend endpoints exist but are NOT user-facing
- Requires GARMIN_CLIENT_ID and GARMIN_CLIENT_SECRET credentials

### Phase 8 - Strava Integration (Feb 3, 2026) [ACTIVE]
- Full OAuth 2.0 flow for Strava API
- Endpoints:
  - `GET /api/strava/status` - Connection status
  - `GET /api/strava/authorize` - Initiate OAuth flow
  - `GET /api/strava/callback` - Handle OAuth callback
  - `POST /api/strava/sync` - Sync activities from Strava
  - `DELETE /api/strava/disconnect` - Disconnect account
- Import running and cycling activities only (run/ride types)
- Data mapping with graceful fallback for missing metrics:
  - activity_id, activity_type, start_time, duration, distance
  - average_heart_rate, average_pace/speed
  - elevation_gain, calories (optional)
  - data_source = "strava"
- Token refresh handling for expired tokens
- Settings page shows generic "Data Sync" section:
  - No Strava/Garmin branding visible
  - Connection status, Last sync timestamp, Workout count
  - Connect Account / Sync Now / Disconnect buttons
- Coach NEVER mentions Strava in responses
- Full EN/FR translation support
- **Note**: Requires STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET credentials to enable

### Backend API Endpoints
- `GET /api/workouts` - List all workouts
- `GET /api/workouts/{id}` - Workout detail
- `POST /api/workouts` - Create workout
- `GET /api/stats` - Training statistics
- `POST /api/coach/analyze` - AI analysis (with language, deep_analysis, user_id params)
- `GET /api/coach/history` - Conversation history per user
- `DELETE /api/coach/history` - Clear conversation history
- `POST /api/coach/guidance` - Generate adaptive training guidance
- `GET /api/coach/guidance/latest` - Get most recent guidance
- `GET /api/strava/status` - Strava connection status
- `GET /api/strava/authorize` - Initiate Strava OAuth
- `GET /api/strava/callback` - Handle OAuth callback
- `POST /api/strava/sync` - Sync activities from Strava
- `DELETE /api/strava/disconnect` - Disconnect Strava account
- `GET /api/garmin/*` - Dormant Garmin endpoints (backend only)
- `GET /api/messages` - Coach message history (legacy)

### Frontend Structure
- `/app/frontend/src/lib/i18n.js` - Translation dictionaries
- `/app/frontend/src/context/LanguageContext.jsx` - Language state management
- `/app/frontend/src/pages/Settings.jsx` - Data Sync + Language UI

## Prioritized Backlog

### P0 - Completed
- ✅ Strava API integration structure

### P1 - High Priority (Next)
- Weekly Digest + Executive Summary feature (proactive coach intelligence)
- Prompt user for real Strava API credentials to enable actual data sync

### P2 - Medium Priority
- Replace mocked workout data with MongoDB collections populated by API syncs
- Weekly/monthly summary emails
- Export training data (CSV/JSON)
- Advanced analytics: training load, recovery metrics
- Fix AI response format inconsistency for deep analysis

### P3 - Nice to Have
- Additional languages (German, Spanish)
- Apple Health/Google Fit sync

### Deprioritized
- Garmin activation (dormant)
- server.py refactoring (post-MVP)

## Tech Stack
- Backend: FastAPI, MongoDB, emergentintegrations
- Frontend: React, Tailwind CSS, Recharts, Shadcn/UI
- AI: OpenAI GPT-5.2 via Emergent LLM key
- i18n: Custom React Context with explicit dictionaries

## Design System
- Theme: Obsidian Tactical
- Fonts: Barlow Condensed (headings), Manrope (body), JetBrains Mono (data)
- Primary: #3B82F6 (Electric Blue)
- Background: #050505 (Deep Black)

## Environment Variables

### Backend (.env)
```
MONGO_URL="mongodb://localhost:27017"
DB_NAME="test_database"
CORS_ORIGINS="*"
EMERGENT_LLM_KEY=<your_key>
STRAVA_CLIENT_ID=<your_id>
STRAVA_CLIENT_SECRET=<your_secret>
STRAVA_REDIRECT_URI=<your_redirect>
FRONTEND_URL=<frontend_url>
# Dormant
GARMIN_CLIENT_ID=
GARMIN_CLIENT_SECRET=
GARMIN_REDIRECT_URI=
```

## Testing
- Unit tests: `/app/backend/tests/test_strava_integration.py`
- Test reports: `/app/test_reports/`
