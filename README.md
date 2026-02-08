# iConcierge

AI-powered booking assistant that automates service appointments. Users describe what they need in natural language, and the system finds providers, calls them via voice agents, checks calendar availability, and presents ranked options — all in real time.

Works for any appointment-based service: haircuts, car repairs, vet visits, tutoring, home cleaning, and more.

## How It Works

1. **Chat** — User describes what they need ("I need a haircut tomorrow afternoon near Alexanderplatz")
2. **Search** — System finds matching providers via Google Places
3. **Call** — Voice agents (ElevenLabs) call providers simultaneously to check availability
4. **Rank** — Results are scored by rating, distance, availability, and user preferences
5. **Confirm** — User picks the best option from a ranked shortlist

Real-time progress is streamed to the frontend via WebSocket.

## Tech Stack

| Layer    | Stack                                              |
|----------|----------------------------------------------------|
| Backend  | Python 3.11, FastAPI, SQLAlchemy async, Pydantic v2 |
| Frontend | Next.js, React, TypeScript, Tailwind, shadcn/ui    |
| Database | PostgreSQL 16                                       |
| AI/Voice | OpenAI (intent parsing), ElevenLabs (voice calls)  |
| APIs     | Google Maps, Google Calendar (OAuth 2.0)            |

## Quick Start (Docker)

The fastest way to get everything running:

```bash
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys (see Environment section below)

cp frontend/.env.example frontend/.env.local
# Edit frontend/.env.local

docker-compose up
```

This starts PostgreSQL, the backend (port 8000), and the frontend (port 3000).

## Manual Setup

### Backend

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
# Fill in your API keys

alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
pnpm install

cp .env.example .env.local
# Set NEXT_PUBLIC_API_URL=http://localhost:8000

pnpm dev
```

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string (asyncpg) |
| `OPENAI_API_KEY` | OpenAI API key for intent parsing |
| `GOOGLE_MAPS_API_KEY` | Google Maps / Places API key |
| `GOOGLE_CLIENT_ID` | Google OAuth 2.0 client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth 2.0 client secret |
| `TOKEN_ENCRYPTION_KEY` | Fernet key for encrypting OAuth tokens |
| `ELEVENLABS_API_KEY` | ElevenLabs API key for voice calls |
| `ELEVENLABS_AGENT_ID` | ElevenLabs agent ID |
| `ELEVENLABS_WEBHOOK_SECRET` | Webhook signature verification |
| `DEFAULT_TIMEZONE` | User timezone (default: `Europe/Berlin`) |

Generate the Fernet encryption key:

```bash
python3.11 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Frontend (`frontend/.env.local`)

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend URL (`http://localhost:8000`) |
| `NEXT_PUBLIC_WS_URL` | WebSocket URL (`ws://localhost:8000`) |
| `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` | Google Maps client-side key |

## Development

```bash
# Backend tests
cd backend && python3.11 -m pytest

# Backend lint
python3.11 -m ruff check .

# Frontend tests
cd frontend && pnpm test:run

# Frontend lint
pnpm lint
```

## API Docs

With the backend running, visit:

- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>
