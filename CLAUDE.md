# NoteTube AI - Development Guide

## Project Overview

NoteTube AI transforms YouTube videos into complete learning experiences with AI-powered notes, smart chapters, flashcards, chat, and semantic search.

**Live URL**: https://notetubeai.in

## Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.12)
- **Database**: PostgreSQL 16
- **Queue**: Redis + RQ (background workers)
- **ORM**: SQLAlchemy + Alembic migrations
- **AI**: OpenAI GPT-4
- **Auth**: Google OAuth + JWT
- **Email**: Resend
- **Transcripts**: Supadata.ai API

### Frontend
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Auth**: Google OAuth

## Project Structure

```
NoteTube AI/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/          # API endpoints
│   │   │   └── dependencies/    # Auth dependencies
│   │   ├── core/
│   │   │   ├── config.py        # Settings (env vars)
│   │   │   ├── database.py      # DB connection
│   │   │   └── security.py      # JWT handling
│   │   ├── models/              # SQLAlchemy models
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── services/            # Business logic
│   │   └── workers/             # RQ background jobs
│   ├── alembic/                 # Database migrations
│   └── .env                     # Environment variables
├── frontend/
│   ├── app/                     # Next.js pages
│   ├── components/              # React components
│   ├── contexts/                # Auth context
│   └── lib/                     # API client, types
└── docker-compose.yml           # Local PostgreSQL & Redis
```

## Development Commands

### Start Services (Development)

```bash
# Start PostgreSQL and Redis
docker-compose up -d

# Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Worker (separate terminal)
cd backend
source venv/bin/activate
OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES python -m rq.cli worker video_processing --url redis://localhost:6379/0

# Frontend
cd frontend
npm run dev
```

### Database

```bash
# Create migration
cd backend && alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Connect to local PostgreSQL
PGPASSWORD=postgres /Library/PostgreSQL/16/bin/psql -h localhost -p 5433 -U postgres -d notetube_db
```

## Key Features

1. **Take Me There** - AI semantic search to find any moment in video
2. **Transcript** - Full searchable transcript with timestamps
3. **User Notes** - Save selections and rewrite with AI
4. **Chat** - Chat with AI about video content
5. **Breakdown** - AI-generated chapters with summaries
6. **Flashcards** - Auto-generated flashcards for learning

## User Quota System

- Default: 5 videos per user
- Users can request limit increase via feedback modal
- Quota stored in `users` table: `videos_analyzed`, `video_limit`

## Environment Variables

### Backend (.env)
```
DATABASE_URL=postgresql+psycopg://...
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
OPENAI_API_KEY=...
SUPADATA_API_KEY=...
RESEND_API_KEY=...
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
```

### Frontend (.env.local)
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_GOOGLE_CLIENT_ID=...
```

## API Endpoints

### Auth
- `GET /auth/google/login` - Initiate OAuth
- `GET /auth/google/callback` - OAuth callback
- `GET /api/me` - Get current user

### Videos
- `POST /api/videos` - Submit video for processing
- `GET /api/videos` - List user's videos
- `GET /api/videos/{id}` - Get video details

### Users
- `GET /api/users/quota` - Get user quota info
- `POST /api/users/request-limit-increase` - Request more videos

## Production Deployment

### Backend (Railway/Render)
- Set all environment variables
- Use production DATABASE_URL
- Run `alembic upgrade head` on deploy
- Start with: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Run worker separately: `python -m rq.cli worker video_processing`

### Frontend (Vercel)
- Connect to GitHub repo
- Set environment variables
- Build command: `npm run build`

## Important Notes

- Video processing happens async via RQ workers
- Transcripts fetched from Supadata.ai (primary) or youtube-transcript-api (fallback)
- Welcome emails sent via Resend on user signup
- All API routes require JWT authentication (except auth routes)
