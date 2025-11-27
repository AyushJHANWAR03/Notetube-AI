# NoteTube AI - Development Guide

## Project Overview

YouTube Smart Notes Hub - A web app that transforms YouTube videos into complete learning experiences with AI-generated notes, quizzes, flashcards, and interactive features.

---

## Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL (Docker)
- **Queue**: Redis (Docker)
- **ORM**: SQLAlchemy
- **Migrations**: Alembic
- **Testing**: pytest, pytest-asyncio, httpx
- **Auth**: Google OAuth + JWT
- **LLM**: OpenAI (gpt-4o-mini primary)
- **Transcript**: youtube-transcript-api
- **Worker**: RQ (Redis Queue) or Celery

### Frontend
- **Framework**: Next.js 14+ (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State**: React Context + hooks
- **Testing**: Jest + React Testing Library
- **E2E**: Playwright (optional)

### Infrastructure
- **Storage**: Firebase Storage (PDFs/exports)
- **Deployment**: Docker Compose (dev), Railway/Render/Vercel (prod)

---

## Development Approach: TDD + Feature-by-Feature

### Workflow
1. **Backend First**: Build API endpoint + tests
2. **Frontend Second**: Build UI consuming the API
3. **Integration**: Test end-to-end flow
4. **Iterate**: Refine based on testing

### Testing Strategy

#### Backend Tests
- **Unit Tests**: Services, utilities, business logic
- **Integration Tests**: API endpoints with test database
- **Coverage Target**: 80%+

```python
# Example test structure
tests/
├── unit/
│   ├── test_transcript_service.py
│   ├── test_llm_service.py
│   └── test_auth_service.py
├── integration/
│   ├── test_auth_api.py
│   ├── test_videos_api.py
│   └── test_jobs_api.py
└── conftest.py  # Shared fixtures
```

#### Frontend Tests
- **Component Tests**: React Testing Library
- **Integration Tests**: User flows
- **E2E (optional)**: Playwright for critical paths

---

## Project Structure

```
NoteTube-AI/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py
│   │   │   │   ├── videos.py
│   │   │   │   ├── jobs.py
│   │   │   │   ├── quiz.py
│   │   │   │   ├── chat.py
│   │   │   │   └── exports.py
│   │   │   └── dependencies.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py         # Settings (Pydantic BaseSettings)
│   │   │   ├── security.py       # JWT, password hashing
│   │   │   └── database.py       # DB connection, session
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── video.py
│   │   │   ├── job.py
│   │   │   ├── transcript.py
│   │   │   ├── notes.py
│   │   │   ├── quiz.py
│   │   │   └── chat.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── user.py           # Pydantic schemas
│   │   │   ├── video.py
│   │   │   ├── job.py
│   │   │   ├── notes.py
│   │   │   └── quiz.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py
│   │   │   ├── transcript_service.py
│   │   │   ├── llm_service.py
│   │   │   ├── quiz_service.py
│   │   │   └── export_service.py
│   │   ├── workers/
│   │   │   ├── __init__.py
│   │   │   └── video_processor.py
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   ├── youtube.py        # YouTube URL parsing
│   │   │   └── chunking.py       # Transcript chunking
│   │   └── main.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── unit/
│   │   └── integration/
│   ├── alembic/
│   │   ├── versions/
│   │   ├── env.py
│   │   └── alembic.ini
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── app/
│   │   ├── (auth)/
│   │   │   ├── login/
│   │   │   └── callback/
│   │   ├── (dashboard)/
│   │   │   ├── dashboard/
│   │   │   └── videos/
│   │   │       └── [id]/
│   │   ├── layout.tsx
│   │   └── page.tsx              # Landing page
│   ├── components/
│   │   ├── ui/                   # Reusable UI components
│   │   ├── video/
│   │   │   ├── VideoPlayer.tsx
│   │   │   ├── NotesPanel.tsx
│   │   │   └── ChatSection.tsx
│   │   └── auth/
│   │       └── GoogleLoginButton.tsx
│   ├── lib/
│   │   ├── api.ts                # API client
│   │   ├── auth.ts               # Auth utilities
│   │   └── types.ts              # TypeScript types
│   ├── contexts/
│   │   └── AuthContext.tsx
│   ├── __tests__/
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   └── next.config.js
├── docker-compose.yml
├── .gitignore
└── README.md
```

---

## Feature Development Roadmap

### Phase 1: Foundation Setup
- [x] Project structure
- [ ] Docker Compose (Postgres + Redis)
- [ ] Backend scaffolding (FastAPI + Alembic)
- [ ] Frontend scaffolding (Next.js)
- [ ] Environment configuration
- [ ] Database models
- [ ] Initial migrations

### Phase 2: Authentication
#### Backend
- [ ] Google OAuth integration
- [ ] JWT token generation/validation
- [ ] User model + CRUD
- [ ] Auth endpoints:
  - `GET /auth/google/login`
  - `GET /auth/google/callback`
  - `GET /api/me`
- [ ] Auth middleware/dependencies
- [ ] Tests: Auth flow, token validation

#### Frontend
- [ ] Auth context
- [ ] Google login button
- [ ] Callback handling
- [ ] Protected route wrapper
- [ ] Landing page with sign-in
- [ ] Tests: Auth flow

### Phase 3: Video Submission & Job System
#### Backend
- [ ] Video model
- [ ] Job model
- [ ] YouTube URL validation
- [ ] Endpoints:
  - `POST /api/videos`
  - `GET /api/jobs/{job_id}`
  - `GET /api/videos/{video_id}`
- [ ] Redis queue setup
- [ ] Basic worker structure
- [ ] Tests: Video creation, job lifecycle

#### Frontend
- [ ] Video submission form
- [ ] URL validation
- [ ] Job status polling
- [ ] Loading states
- [ ] Tests: Form submission, polling

### Phase 4: Transcript Processing
#### Backend
- [ ] Transcript model
- [ ] Transcript service (youtube-transcript-api)
- [ ] Transcript chunking utility
- [ ] Worker: Fetch transcript job
- [ ] Error handling (no captions)
- [ ] Tests: Mock transcript fetch, chunking logic

#### Frontend
- [ ] Display transcript in UI
- [ ] Transcript tab
- [ ] Tests: Transcript rendering

### Phase 5: AI Notes Generation
#### Backend
- [ ] Notes model
- [ ] LLM service (OpenAI integration)
- [ ] Chunk summarization pipeline
- [ ] Global summary generation
- [ ] Key timestamps extraction
- [ ] Flashcards generation
- [ ] Action items extraction
- [ ] Topics + difficulty detection
- [ ] Endpoint: `GET /api/videos/{video_id}/notes`
- [ ] Tests: Mock OpenAI, validate pipeline

#### Frontend
- [ ] Video player component (YouTube iframe API)
- [ ] Notes panel with tabs:
  - Summary
  - Bullet notes
  - Timestamps (clickable)
  - Flashcards
  - Transcript
- [ ] Timestamp click → seekTo()
- [ ] Tests: Component tests, timestamp handling

### Phase 6: Quiz System
#### Backend
- [ ] Quiz question model
- [ ] Quiz session model
- [ ] Quiz answer model
- [ ] Quiz generation (LLM)
- [ ] Endpoints:
  - `POST /api/videos/{video_id}/quiz/sessions`
  - `POST /api/quiz/sessions/{session_id}/submit`
- [ ] Evaluation logic
- [ ] Tests: Question generation, evaluation

#### Frontend
- [ ] Quiz UI
- [ ] Question display (MCQ, T/F, short answer)
- [ ] Answer submission
- [ ] Results display with explanations
- [ ] Timestamp jump from results
- [ ] Tests: Quiz flow

### Phase 7: Interview Mode
#### Backend
- [ ] Interview question generation
- [ ] Free-text answer evaluation (LLM)
- [ ] Endpoint: `POST /api/videos/{video_id}/interview/answer`
- [ ] Tests: Mock evaluation

#### Frontend
- [ ] Interview mode UI
- [ ] Free-text answer input
- [ ] Feedback display
- [ ] Tests: Answer submission

### Phase 8: Chat with Video
#### Backend
- [ ] Chat message model
- [ ] Chat service (RAG-style with transcript)
- [ ] Auto-suggested prompts generation
- [ ] Endpoints:
  - `GET /api/videos/{video_id}/chat/suggestions`
  - `GET /api/videos/{video_id}/chat/history`
  - `POST /api/videos/{video_id}/chat`
- [ ] Tests: Chat context, suggestions

#### Frontend
- [ ] Chat UI component
- [ ] Auto-suggested prompt buttons
- [ ] Chat history
- [ ] Message input
- [ ] Tests: Chat interaction

### Phase 9: Export Functionality
#### Backend
- [ ] Export model
- [ ] Firebase Storage integration
- [ ] PDF generation (ReportLab / WeasyPrint)
- [ ] Markdown export
- [ ] Endpoints:
  - `POST /api/videos/{video_id}/export/pdf`
  - `POST /api/videos/{video_id}/export/markdown`
  - `GET /api/exports/{export_id}`
- [ ] Tests: Export generation

#### Frontend
- [ ] Export buttons
- [ ] Download handling
- [ ] Tests: Export trigger

### Phase 10: User Library
#### Backend
- [ ] Endpoint: `GET /api/me/videos`
- [ ] Pagination
- [ ] Filtering/sorting
- [ ] Tests: Library queries

#### Frontend
- [ ] Dashboard/library page
- [ ] Video cards (thumbnail, title, status)
- [ ] Navigation to video detail
- [ ] Tests: Library rendering

---

## Environment Variables & Secrets

### Backend `.env`
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/notetube_db

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Google OAuth
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# OpenAI
OPENAI_API_KEY=sk-...

# Firebase
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_STORAGE_BUCKET=your-bucket.appspot.com
FIREBASE_CREDENTIALS_PATH=/path/to/serviceAccountKey.json

# App
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
```

### Frontend `.env.local`
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

---

## How to Provide API Keys & Secrets to Claude

When Claude needs credentials:

### 1. **Environment Variables** (Preferred)
```bash
# You can paste in chat:
"Here are the env vars:
GOOGLE_CLIENT_ID=123456.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=ABC123XYZ
OPENAI_API_KEY=sk-proj-..."
```

### 2. **Create `.env` file locally** and tell Claude
```bash
# You create the file, then say:
"I've created backend/.env with the keys, you can read it"
```

### 3. **Firebase Service Account**
- Download JSON from Firebase Console
- Save as `backend/firebase-key.json`
- Tell Claude: "Firebase key is in backend/firebase-key.json"

### 4. **For Google OAuth Setup**
- Go to: https://console.cloud.google.com/apis/credentials
- Create OAuth 2.0 Client ID
- Authorized redirect URIs:
  - `http://localhost:8000/auth/google/callback` (dev)
  - `https://your-domain.com/auth/google/callback` (prod)
- Copy Client ID & Secret

### 5. **For OpenAI**
- Go to: https://platform.openai.com/api-keys
- Create new key
- Copy and provide to Claude

---

## Docker Compose Setup

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: notetube
      POSTGRES_PASSWORD: notetube123
      POSTGRES_DB: notetube_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  pgadmin:
    image: dpage/pgadmin4
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@notetube.com
      PGADMIN_DEFAULT_PASSWORD: admin
    ports:
      - "5050:80"
    depends_on:
      - postgres

volumes:
  postgres_data:
```

**Start**: `docker-compose up -d`
**Stop**: `docker-compose down`

---

## Database Migrations (Alembic)

```bash
# Create migration
alembic revision --autogenerate -m "create users table"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## Testing Commands

### Backend
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test
pytest tests/integration/test_auth_api.py -v

# Run with print statements
pytest -s
```

### Frontend
```bash
# Run tests
npm test

# Watch mode
npm test -- --watch

# Coverage
npm test -- --coverage
```

---

## API Documentation

FastAPI auto-generates docs:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Common Patterns

### 1. Protected API Endpoint
```python
from app.api.dependencies import get_current_user

@router.get("/videos")
async def list_videos(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # current_user is authenticated
    pass
```

### 2. Frontend API Call
```typescript
// lib/api.ts
async function fetchVideos() {
  const token = localStorage.getItem('token');
  const res = await fetch(`${API_URL}/videos`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  return res.json();
}
```

### 3. Worker Job
```python
# workers/video_processor.py
from rq import Queue
from redis import Redis

redis_conn = Redis()
queue = Queue(connection=redis_conn)

def process_video(video_id: str):
    # 1. Fetch transcript
    # 2. Generate notes
    # 3. Update DB
    pass

# Enqueue
job = queue.enqueue(process_video, video_id="123")
```

---

## Cost Estimation

### OpenAI API (gpt-4o-mini)
- **Input**: $0.15 / 1M tokens
- **Output**: $0.60 / 1M tokens
- **Per 20-min video**: ~₹0.40

### Firebase Storage
- **Free tier**: 5GB storage, 1GB/day download
- **Paid**: $0.026/GB/month

### Infrastructure (Railway/Render)
- **Hobby plan**: ~$5-10/month
- **Production**: ~$20-30/month

---

## Troubleshooting

### Database connection failed
- Check Docker: `docker-compose ps`
- Check env: `echo $DATABASE_URL`

### Redis connection failed
- Check Redis: `docker logs <redis-container>`
- Test connection: `redis-cli ping`

### Google OAuth error
- Check redirect URI matches exactly
- Enable Google+ API in console

### OpenAI API error
- Check API key validity
- Monitor quota: https://platform.openai.com/usage

---

## Next Steps After Setup

1. **Run initial migration**
   ```bash
   cd backend
   alembic upgrade head
   ```

2. **Start backend**
   ```bash
   uvicorn app.main:app --reload
   ```

3. **Start frontend**
   ```bash
   cd frontend
   npm run dev
   ```

4. **Begin Phase 2: Authentication**
   - Backend: Implement Google OAuth
   - Frontend: Build login page
   - Test end-to-end auth flow

---

## Resources

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Next.js Docs](https://nextjs.org/docs)
- [SQLAlchemy Docs](https://docs.sqlalchemy.org/)
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [YouTube Transcript API](https://github.com/jdepoix/youtube-transcript-api)
- [OpenAI API Docs](https://platform.openai.com/docs)

---

**Ready to build! 🚀**

Start with: `docker-compose up -d` → backend setup → auth implementation