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
- Mobile-first design

## What's Been Implemented

### Phase 1-7 - Previous Work
- FastAPI backend with MongoDB integration
- Mock workout data with dynamic dates (relative to today)
- Dashboard, Coach, Workout Detail, Progress, Guidance, Settings pages
- AI Coach with GPT-5.2 via Emergent LLM key
- Obsidian Tactical dark theme
- Full bilingual EN/FR support via i18n system
- Persistent AI coach memory per user
- Deep workout analysis with baseline comparison
- "Hidden Insight" feature (probabilistic, non-obvious patterns)
- Adaptive training guidance

### Phase 8 - Strava Integration (Feb 3, 2026)
- Full OAuth 2.0 flow for Strava API
- Backend endpoints: `/api/strava/status`, `/authorize`, `/callback`, `/sync`, `/disconnect`
- Generic "Data Sync" UI (no Strava/Garmin branding visible)
- Token refresh handling for expired tokens
- Import running and cycling activities only (up to 300 activities)
- Auto-sync triggered after successful connection
- Activities stored in MongoDB with `data_source: "strava"`
- **Ready for credentials**: Add `STRAVA_CLIENT_ID` and `STRAVA_CLIENT_SECRET` to `/app/backend/.env`
- **Redirect URI**: `https://endurance-ai-1.preview.emergentagent.com/api/strava/callback`

### Phase 9 - Weekly Review / Bilan de la semaine (Feb 8, 2026) ✅
**Complete redesign: "Digest" → "Bilan de la semaine"**

**Objective:** Transform the weekly summary into a true coach review that:
- Is readable in under 1 minute on mobile
- Makes the user understand their week immediately
- Tells them what to do next week

**New 6-Card Structure:**

1. **CARTE 1 - Coach Summary (Synthèse du coach)**
   - 1 sentence maximum
   - Calm, human, expert tone
   - Example: "Light but clean week, ideal to restart without creating fatigue."

2. **CARTE 2 - Visual Signals (Signaux clés)**
   - Volume: ↑/↓/stable + percentage
   - Intensity: Easy/Balanced/Sustained
   - Regularity: Low/Moderate/Good
   - Readable in <3 seconds

3. **CARTE 3 - Essential Numbers (Chiffres essentiels)**
   - Sessions count
   - Total distance (km)
   - Total duration (hours)
   - Comparison vs previous week only

4. **CARTE 4 - Coach Reading (Lecture du coach)**
   - 2-3 sentences maximum
   - Puts meaning on the numbers
   - Says what is GOOD and what to WATCH OUT for

5. **CARTE 5 - Recommendations (Préconisations) - MANDATORY**
   - 1-2 clear recommendations
   - ACTION-oriented
   - Applicable next week
   - No conditionals, no options

6. **CARTE 6 - Ask Coach (Question au coach) - Optional**
   - Discrete button: "Ask the coach"
   - Navigates to Coach Q&A

**Removed:**
- ❌ "View Full Analysis" button
- ❌ Zone distribution bar
- ❌ Old insights list

**Backend:**
- Updated `GET /api/coach/digest` to return new `WeeklyReviewResponse`:
  - `coach_summary` (1 phrase)
  - `coach_reading` (2-3 phrases)
  - `recommendations` (1-2 actions)
  - `metrics` (sessions, km, hours)
  - `comparison` (vs last week %)
  - `signals` (load/intensity/consistency)

**Frontend:**
- Renamed "Digest" → "Review" (EN) / "Bilan" (FR) in navigation
- Complete rewrite of `/app/frontend/src/pages/Digest.jsx`
- Updated all translations in `/app/frontend/src/lib/i18n.js`

**AI Prompts:**
- `WEEKLY_REVIEW_PROMPT_EN/FR` enforce:
  - 1 sentence coach summary
  - 2-3 sentence coach reading
  - 1-2 action-oriented recommendations
  - No markdown, no jargon, no report-style

**Test Report:** `/app/test_reports/iteration_15.json` (100% pass rate)

### Phase 10 - Mobile Coach View (Feb 3, 2026) ✅
**Redesigned workout detail as "coach-in-your-pocket" experience**

**Structure (Top → Bottom):**
1. **Coach Sentence** (top card)
   - 1 sentence, max 18-20 words
   - Plain language, NO numbers overload
   - Explains what this session was compared to recent habits
   - Example: "Longer and a bit harder than what you've been doing lately."

2. **Session Snapshot** (3 compact cards in row)
   - **Intensity**: Pace + Avg HR + Label (Above/Below usual)
   - **Load**: Distance + Duration + Direction (↑ Higher / ↓ Lower)
   - **Type**: Easy / Sustained / Hard (color-coded badge)

3. **Coach Insight** (optional)
   - Max 2 short sentences
   - No jargon (no Z2/Z4, no physiology terms)
   - Example: "You combined volume and intensity. More demanding for recovery."

4. **Guidance** (optional)
   - Only if session is unusually intense
   - ONE suggestion, soft wording
   - Example: "An easy outing would help stabilize the rest of the week."

5. **Actions** (bottom)
   - Primary: "View detailed analysis" → Card-based detailed view
   - Secondary: "Ask the coach" → Coach chat

### Phase 11 - Card-Based Detailed Analysis (Feb 5, 2026) ✅
**Transformed detailed analysis from dense report to mobile card experience**

**Route:** `/workout/{id}/analysis`

**Structure (6 cards):**
1. **Header - Session Context**
   - Session name
   - 1 sentence max context
   - Example: "Sustained outing, noticeably more intense than your recent routine."

2. **Execution Card** (3 columns)
   - Intensity: Easy / Moderate / Sustained (color-coded badge)
   - Volume: Usual / Longer / One-off peak
   - Regularity: Stable / Unknown / Variable

3. **What It Means Card**
   - 2-3 short sentences
   - Simple language, no jargon
   - Explains the main signal (zone change, load spike)

4. **Recovery Card** (orange highlight)
   - 1 key message only
   - Neutral, non-alarmist tone
   - Example: "This session creates higher stress. The next 24-48h matter."

5. **Coach Advice Card** (blue highlight)
   - 1 clear actionable recommendation
   - Never more than one
   - Example: "Next session: strict easy, recovery priority."

6. **Go Further Accordion** (collapsed by default)
   - HR/pace deltas vs baseline
   - Zone breakdown
   - Physiological nuances
   - Can be ignored without losing comprehension

**Design Rules:**
- Scannable in <10 seconds
- Short sentences only
- Clear vocabulary
- Zero over-analysis visible by default
- Each card fits on mobile screen
- 100% EN or 100% FR (no mixing)

### Phase 12 - Conversational Coach Q&A (Feb 5, 2026) ✅
**Refactored coach chat from report-style to conversational coach-like responses**

**Response Format (Mandatory):**
1. **Direct Answer** (required)
   - 1-2 sentences maximum
   - Directly answers the question
   - Simple language

2. **Quick Context** (optional)
   - 1-3 bullet points maximum
   - Each bullet = one key piece of information
   - No unnecessary numbers

3. **Coach Tip** (required)
   - ONE single recommendation
   - Clear, concrete, immediately actionable

**Strict Style Rules (Forbidden):**
- NO stars (*, **, ****)
- NO markdown headers
- NO numbered lists (1., 2., 3.)
- NO walls of text
- NO academic or medical tone

**Tone:**
- Calm, confident, caring
- Precise but simple
- Like a coach speaking in the user's ear

**Golden Rule:**
If response looks like a report, it is WRONG and must be simplified.

**Language Enforcement:**
- 100% EN or 100% FR
- No language mixing allowed

### Phase 13 - Decision Assistant Dashboard (Feb 7, 2026) ✅
**Redesigned dashboard from data display to decision assistant**

**Philosophy:** CardioCoach is NOT a data dashboard. It's a decision assistant.
User should always know: "Am I doing too much?", "Am I doing too little?", "What should I do next?"

**Structure (Mobile-first, glanceable in <5 seconds):**

1. **Coach Insight** (top priority, blue highlight)
   - 1 sentence only, max 15 words
   - Action-oriented, tells user what to do
   - Examples: "Low load this week; add an easy session to maintain progress."

2. **This Week** (3 cards)
   - Sessions: count of workouts
   - Volume: total km
   - Load Signal: Low (orange) / Balanced (green) / High (red)
   - NO HR numbers, NO pace numbers - only interpreted signals

3. **Last 30 Days** (compact summary)
   - Total volume (km)
   - Active weeks count
   - Trend: Up (green ↗) / Stable (gray −) / Down (orange ↘)
   - NO daily breakdown, NO charts

4. **Recent Workouts** (compact list)
   - Last 4 workouts
   - Name, date, distance, duration
   - Links to workout detail

**Backend:**
- `GET /api/dashboard/insight` - Returns coach_insight, week stats, month stats
- Load signal thresholds: >80km=high, >40km=balanced, else=low
- Trend calculation: >15% change=up/down, else=stable

**Design Rules:**
- Signal over data: no raw statistics without interpretation
- No walls of text, no reports
- If it looks like a training report, it is WRONG
- Coach tone: calm, human, concise

**Backend:**
- `GET /api/coach/workout-analysis/{workout_id}` - Mobile coach view
- Returns: coach_summary, intensity, load, session_type, insight, guidance
- Session type calculated from HR + load + zone distribution

**Design Rules:**
- Readable in under 10 seconds
- Feels coached, not analyzed
- One idea per block
- Max 2 lines per text block
- No stars, no heavy markdown
- White space > density

### Backend API Endpoints
- `GET /api/workouts` - List all workouts
- `GET /api/workouts/{id}` - Workout detail
- `POST /api/workouts` - Create workout
- `GET /api/stats` - Training statistics
- `POST /api/coach/analyze` - AI analysis
- `GET /api/coach/history` - Conversation history
- `DELETE /api/coach/history` - Clear history
- `POST /api/coach/guidance` - Adaptive guidance
- `GET /api/coach/guidance/latest` - Latest guidance
- `GET /api/coach/digest` - Weekly digest
- `GET /api/coach/digest/latest` - Latest digest
- `GET /api/strava/*` - Strava OAuth endpoints
- `GET /api/garmin/*` - Dormant Garmin endpoints

### Navigation Structure
- Dashboard (home)
- Bilan / Review (weekly review)
- Coach (AI chat)
- Progress (trends)
- Settings (data sync, language)

## Prioritized Backlog

### P0 - Completed ✅
- ✅ Strava API integration structure
- ✅ Weekly Digest + Executive Summary

### P1 - High Priority (Next)
- Add real Strava API credentials to enable actual workout import
- Replace mock workout data with synced Strava data

### P2 - Medium Priority
- Recovery score calculation based on training load
- "Ask about this insight" follow-up capability
- Weekly/monthly summary emails
- Export training data (CSV/JSON)

### P3 - Nice to Have
- Additional languages (German, Spanish)
- Apple Health/Google Fit sync

### Deprioritized
- Garmin activation (dormant)
- server.py refactoring (post-MVP)
- Sync progress indicators
- Background sync scheduling

## Tech Stack
- Backend: FastAPI, MongoDB, emergentintegrations
- Frontend: React, Tailwind CSS, Recharts, Shadcn/UI
- AI: OpenAI GPT-5.2 via Emergent LLM key
- i18n: Custom React Context with explicit EN/FR dictionaries

## Design System
- Theme: Obsidian Tactical
- Fonts: Barlow Condensed (headings), Manrope (body), JetBrains Mono (data)
- Primary: #3B82F6 (Electric Blue)
- Background: #050505 (Deep Black)
- Mobile-first responsive design

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
- Unit tests: `/app/backend/tests/`
- Test reports: `/app/test_reports/`
- Latest: `iteration_15.json` - Weekly Review tests (100% pass rate)
