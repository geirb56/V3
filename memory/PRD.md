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

### Backend
- API Endpoints:
  - `GET /api/workouts` - List all workouts
  - `GET /api/workouts/{id}` - Workout detail
  - `POST /api/workouts` - Create workout
  - `GET /api/stats` - Training statistics
  - `POST /api/coach/analyze` - AI analysis (with language, deep_analysis, user_id params)
  - `GET /api/coach/history` - Conversation history per user
  - `DELETE /api/coach/history` - Clear conversation history
  - `GET /api/messages` - Coach message history (legacy)

### Frontend Structure
- `/app/frontend/src/lib/i18n.js` - Translation dictionaries
- `/app/frontend/src/context/LanguageContext.jsx` - Language state management
- `/app/frontend/src/pages/Settings.jsx` - Language toggle UI

## Prioritized Backlog

### P0 - Critical (Next Phase)
- Garmin API integration for real workout imports

### P1 - High Priority
- Persistent conversation history with CardioCoach
- Training plan generation based on workout history
- Goal setting and tracking

### P2 - Medium Priority
- Weekly/monthly summary emails
- Export training data (CSV/JSON)
- Advanced analytics: training load, recovery metrics

### P3 - Nice to Have
- Strava integration
- Apple Health/Google Fit sync
- Additional languages (German, Spanish)

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
