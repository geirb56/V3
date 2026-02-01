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

### Backend
- API Endpoints:
  - `GET /api/workouts` - List all workouts
  - `GET /api/workouts/{id}` - Workout detail
  - `POST /api/workouts` - Create workout
  - `GET /api/stats` - Training statistics
  - `POST /api/coach/analyze` - AI analysis (with language param)
  - `GET /api/messages` - Coach message history

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
