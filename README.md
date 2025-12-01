# NoteTube AI

Transform YouTube videos into complete learning experiences with AI-powered notes, smart chapters, flashcards, and more.

**Live**: [notetubeai.in](https://notetubeai.in)

## Features

- **Take Me There** - AI semantic search to find any moment in the video
- **Transcript** - Full searchable transcript with timestamps and auto-scroll
- **User Notes** - Save selections from transcript and rewrite with AI
- **Chat** - Chat with AI about video content and get instant answers
- **Breakdown** - AI-generated chapters with summaries for easy navigation
- **Flashcards** - Auto-generated flashcards to test your knowledge

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, Python 3.12 |
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Database | PostgreSQL 16 |
| Queue | Redis + RQ Workers |
| AI | OpenAI GPT-4 |
| Auth | Google OAuth + JWT |
| Email | Resend |
| Transcripts | Supadata.ai |

## Local Development

### Prerequisites
- Python 3.12+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 16 (or use Docker)

### 1. Clone & Setup

```bash
git clone https://github.com/yourusername/notetube-ai.git
cd notetube-ai
```

### 2. Start Database & Redis

```bash
docker-compose up -d
```

### 3. Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file and configure
cp .env.example .env
# Edit .env with your API keys

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --port 8000
```

### 4. Start Worker (separate terminal)

```bash
cd backend
source venv/bin/activate
python -m rq.cli worker video_processing --url redis://localhost:6379/0
```

### 5. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Copy environment file
cp .env.example .env.local
# Edit .env.local with your settings

# Start dev server
npm run dev
```

### Access Points
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/docs

## Environment Variables

### Backend (.env)

```env
# Database
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5433/notetube_db

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Google OAuth
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# OpenAI
OPENAI_API_KEY=sk-...

# Supadata (transcripts)
SUPADATA_API_KEY=sd_...

# Resend (emails)
RESEND_API_KEY=re_...
RESEND_FROM_DOMAIN=yourdomain.com

# App URLs
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
ENVIRONMENT=development
```

### Frontend (.env.local)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-client-id
```

## Production Deployment

### Backend (Railway/Render)
1. Set all environment variables
2. Deploy command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Run migrations: `alembic upgrade head`
4. Deploy worker separately: `python -m rq.cli worker video_processing`

### Frontend (Vercel)
1. Connect GitHub repository
2. Set environment variables
3. Build command: `npm run build`
4. Output directory: `.next`

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

## License

MIT

---

Built by [Ayush](https://github.com/ayushjhanwar)
