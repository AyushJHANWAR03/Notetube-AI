# NoteTube AI

> Transform YouTube videos into structured notes, flashcards, and searchable knowledge - powered by AI.

[![Live Demo](https://img.shields.io/badge/Live-notetubeai.in-blue?style=for-the-badge)](https://notetubeai.in)

![NoteTube AI Demo](https://notetubeai.in/og-image.png)

---

## The Problem

We've all been there:
- Watching a 2-hour tutorial, constantly pausing to take notes
- Rewinding the same 30 seconds five times to catch what was said
- Finishing a video and realizing you forgot the key points from the beginning
- Wanting to find "that one part" where they explained something specific
- No way to quickly review or test your understanding of video content

YouTube is an incredible learning resource, but the format isn't built for retention. You watch passively, and most of it fades away.

## The Solution

NoteTube AI transforms any YouTube video into an interactive learning experience:

1. **Paste a YouTube URL** - Get AI-generated notes, chapters, and flashcards
2. **Search semantically** - Find any moment using natural language ("where did they explain recursion?")
3. **Chat with the video** - Ask questions and get answers with timestamp references
4. **Save your own notes** - Capture transcript selections and rewrite them in your style
5. **Test yourself** - Auto-generated flashcards to reinforce learning

---

## Features

### AI-Powered Video Analysis
- **Structured Notes** - Comprehensive summary with key takeaways, organized by topic
- **Smart Chapters** - AI-generated chapters with timestamps and summaries (not YouTube's auto-chapters)
- **Flashcards** - Question-answer pairs automatically generated from video content
- **Difficulty Assessment** - AI estimates content difficulty level

### Semantic Search ("Take Me There")
- Natural language search across the entire video transcript
- Ask questions like "when do they talk about database indexing?"
- Get timestamp-accurate results - click to jump directly to that moment
- No more scrubbing through hours of content

### Interactive Chat
- Chat with AI about the video content
- Get answers with specific timestamp references
- Ask follow-up questions for deeper understanding
- Context-aware responses based on transcript

### User Notes
- Select any part of the transcript to save as a note
- AI-powered rewriting in different styles (formal, casual, bullet points)
- Organize notes by video

### Full Transcript Access
- Complete searchable transcript with timestamps
- Auto-scroll sync with video playback
- Click any line to jump to that moment
- Hindi transliteration support for regional content

---

## Tech Stack

### Frontend
| Technology | Purpose |
|------------|---------|
| Next.js 14 | React framework with App Router |
| TypeScript | Type-safe development |
| Tailwind CSS | Utility-first styling |
| Shadcn/UI | Component library |

### Backend
| Technology | Purpose |
|------------|---------|
| FastAPI | High-performance Python API |
| SQLAlchemy | Async ORM with PostgreSQL |
| Redis | Caching layer (24h TTL) |
| RQ (Redis Queue) | Background job processing |

### Database
| Technology | Purpose |
|------------|---------|
| PostgreSQL 16 | Primary database |
| 7 Tables | users, videos, transcripts, notes, jobs, chat_messages, exports |

### AI & External Services
| Service | Purpose |
|---------|---------|
| OpenAI GPT-4o-mini | Notes, chapters, flashcards generation |
| OpenAI GPT-3.5-turbo | Chat, semantic search, transliteration |
| Supadata.ai | YouTube transcript extraction |
| YouTube Data API | Video metadata |

### Infrastructure
| Technology | Purpose |
|------------|---------|
| DigitalOcean Droplet | Ubuntu VPS hosting |
| Nginx | Reverse proxy with SSL |
| PM2 | Process management |
| Let's Encrypt | SSL certificates |

---

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│   Next.js 14    │────▶│   FastAPI       │────▶│   PostgreSQL    │
│   Frontend      │     │   Backend       │     │   Database      │
│                 │     │                 │     │                 │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │                 │
                        │   Redis         │
                        │   Cache + Queue │
                        │                 │
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │                 │
                        │   RQ Worker     │
                        │   Background    │
                        │   Processing    │
                        │                 │
                        └────────┬────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
             ┌──────────┐ ┌──────────┐ ┌──────────┐
             │ Supadata │ │ OpenAI   │ │ YouTube  │
             │ API      │ │ API      │ │ API      │
             └──────────┘ └──────────┘ └──────────┘
```

---

## Video Processing Pipeline

When a user submits a YouTube URL, here's what happens:

```
1. URL Validation      → Extract video ID, validate format
2. Metadata Fetch      → Get title, thumbnail, duration from YouTube API
3. Transcript Extract  → Fetch transcript via Supadata (with Redis caching)
4. Parallel AI Processing (ThreadPoolExecutor):
   ├── Generate structured notes (GPT-4o-mini)
   └── Generate chapters with timestamps (GPT-4o-mini)
5. Database Storage    → Save all generated content
6. Progress Updates    → Real-time progress via polling (0% → 100%)
```

**Average processing time:** 30-60 seconds depending on video length

---

## Database Schema

```
users
├── id (UUID)
├── email, name, avatar_url
├── google_sub
├── videos_analyzed, video_limit
└── created_at, updated_at

videos
├── id (UUID)
├── user_id → users
├── youtube_video_id, original_url
├── title, thumbnail_url, duration_seconds
├── status (PENDING/PROCESSING/COMPLETED/FAILED)
└── processed_at

transcripts
├── id (UUID)
├── video_id → videos (unique)
├── language_code, provider
├── raw_text
└── segments (JSONB) [{text, start, duration}...]

notes
├── id (UUID)
├── video_id → videos (unique)
├── summary, bullets (JSONB)
├── chapters (JSONB), flashcards (JSONB)
├── user_notes (JSONB)
├── suggested_prompts (JSONB)
└── notes_model, notes_tokens

chat_messages
├── id (UUID)
├── video_id → videos, user_id → users
├── role (user/assistant)
└── content

jobs
├── id (UUID)
├── video_id → videos
├── type, status, progress (0-100)
└── error_message
```

---

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 16
- Redis

### Installation

```bash
# Clone the repo
git clone https://github.com/ayushjhanwar/notetube-ai.git
cd notetube-ai

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Configure your API keys
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Start Redis worker (new terminal)
cd backend && source venv/bin/activate
python -m rq.cli worker video_processing --url redis://localhost:6379/0

# Frontend setup (new terminal)
cd frontend
npm install
cp .env.example .env.local  # Configure settings
npm run dev
```

Visit `http://localhost:3000`

### Environment Variables

**Backend (.env)**
```env
DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/notetube_db
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=sk-...
SUPADATA_API_KEY=sd_...
YOUTUBE_API_KEY=AIza...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
JWT_SECRET_KEY=...
FRONTEND_URL=http://localhost:3000
```

**Frontend (.env.local)**
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_GOOGLE_CLIENT_ID=...
```

---

## API Endpoints

### Authentication
```
GET  /auth/google/login     → Initiate Google OAuth
GET  /auth/google/callback  → OAuth callback
GET  /api/me                → Get current user
```

### Videos
```
POST   /api/videos          → Submit video for processing
GET    /api/videos          → List user's videos
GET    /api/videos/{id}     → Get video details
DELETE /api/videos/{id}     → Delete video
```

### Notes & Chat
```
GET  /api/videos/{id}/notes            → Get generated notes
POST /api/videos/{id}/notes/user-notes → Save user note
POST /api/videos/{id}/chat             → Chat with video
GET  /api/videos/{id}/chat/history     → Get chat history
```

### AI Features
```
POST /api/videos/{id}/seek         → Semantic search ("Take Me There")
POST /api/videos/{id}/rewrite      → Rewrite text in different style
POST /api/videos/{id}/transliterate → Hindi transliteration
```

---

## Deployment

Deployed on DigitalOcean with:
- **Nginx** as reverse proxy
- **PM2** for process management
- **Let's Encrypt** SSL via Certbot
- **UFW** firewall

```bash
# PM2 processes on production
pm2 start "uvicorn app.main:app --host 127.0.0.1 --port 8000" --name backend
pm2 start "npm start" --name frontend
pm2 start "python -m rq.cli worker video_processing" --name worker
```

---

## Cost Analysis

**Per video processed:**
| Service | Cost |
|---------|------|
| Supadata API (transcript) | ~$0.01 |
| OpenAI GPT-4o-mini (notes + chapters) | ~$0.15-0.30 |
| OpenAI GPT-3.5-turbo (chat) | ~$0.01/message |
| **Total** | **~$0.20-0.35/video** |

---

## Roadmap

- [ ] Chrome extension for one-click analysis
- [ ] Export to Notion/Obsidian
- [ ] More flashcard generation options
- [ ] Multi-language transcript support
- [ ] Playlist batch processing
- [ ] Mobile app

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## License

MIT License

---

## Author

**Ayush Jhanwar**

[![GitHub](https://img.shields.io/badge/GitHub-ayushjhanwar-black?style=flat-square&logo=github)](https://github.com/ayushjhanwar)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Ayush_Jhanwar-blue?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/ayush-jhanwar-a674241a2/)

---

*Built with late nights, lots of chai, and the belief that learning from YouTube shouldn't be this hard.*
