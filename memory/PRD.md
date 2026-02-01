# CardioCoach - AI-Powered Endurance Coaching App

## Overview
CardioCoach is an elite endurance coaching app specialized in running, cycling, and cardio-based sports. It provides data-driven performance insights with a calm, neutral, and precise tone.

## User Persona
- Serious endurance athletes (runners, cyclists)
- Data-driven athletes seeking performance analysis
- Users who prefer minimal, no-nonsense interfaces

## Core Requirements (Static)
- NOT a medical application - performance coaching only
- Analyze training data: heart rate, pace, speed, duration, effort distribution
- Tone: Calm, neutral, precise - no hype, no motivation, no emojis
- Dark theme, minimal UI, no gamification, no social features

## What's Been Implemented (Feb 1, 2026)

### Backend
- FastAPI backend with MongoDB integration
- Mock workout data (7 sample workouts for demo)
- API Endpoints:
  - `GET /api/workouts` - List all workouts
  - `GET /api/workouts/{id}` - Workout detail
  - `POST /api/workouts` - Create workout
  - `GET /api/stats` - Training statistics
  - `POST /api/coach/analyze` - AI analysis
  - `GET /api/messages` - Coach message history

### Frontend
- Dashboard: Training overview, stats cards, recent workouts list
- Coach: AI chat interface with suggestion prompts
- Workout Detail: Full metrics, effort zone distribution
- Progress: Charts, trends, all workouts list
- Obsidian Tactical dark theme
- Responsive design (desktop sidebar + mobile bottom nav)

### Integrations
- OpenAI GPT-5.2 via Emergent LLM key for AI coaching

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
- Dark mode variations

## Tech Stack
- Backend: FastAPI, MongoDB, emergentintegrations
- Frontend: React, Tailwind CSS, Recharts, Shadcn/UI
- AI: OpenAI GPT-5.2 via Emergent LLM key

## Design System
- Theme: Obsidian Tactical
- Fonts: Barlow Condensed (headings), Manrope (body), JetBrains Mono (data)
- Primary: #3B82F6 (Electric Blue)
- Background: #050505 (Deep Black)
