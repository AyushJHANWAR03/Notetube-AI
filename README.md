# NoteTube AI - YouTube Smart Notes Hub

Transform YouTube videos into complete learning experiences with AI-generated notes, quizzes, flashcards, and interactive features.

## Features

- **AI-Powered Notes**: Automatic summaries, bullet points, and key timestamps
- **Interactive Learning**: Quizzes, interview mode, and flashcards
- **Chat with Video**: Ask questions about the video content
- **Export Options**: PDF and Markdown exports
- **Personal Library**: Track all your processed videos

## Tech Stack

### Backend
- FastAPI (Python 3.11+)
- PostgreSQL
- Redis
- SQLAlchemy + Alembic
- OpenAI API
- Google OAuth

### Frontend
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- React

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose

### 1. Clone and Setup

```bash
cd "NoteTube AI"
```

### 2. Start Infrastructure

```bash
# Start Postgres, Redis, and pgAdmin
docker-compose up -d

# Check containers are running
docker-compose ps
```

### 3. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-dev.txt

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload
```

Backend will be available at: http://localhost:8000
API Docs: http://localhost:8000/api/docs

### 4. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at: http://localhost:3000

### 5. Access pgAdmin (Optional)

- URL: http://localhost:5050
- Email: admin@notetube.com
- Password: admin123

Add server:
- Host: postgres
- Port: 5432
- Database: notetube_db
- Username: notetube
- Password: notetube123

## Environment Variables

Backend `.env` is already configured with development credentials.

For production, update:
- JWT_SECRET_KEY
- Database credentials
- Firebase credentials (download service account JSON)

## Running Tests

### Backend Tests

```bash
cd backend
pytest                          # Run all tests
pytest --cov=app                # With coverage
pytest tests/unit -v            # Unit tests only
pytest tests/integration -v     # Integration tests only
```

### Frontend Tests

```bash
cd frontend
npm test                        # Run tests
npm test -- --watch             # Watch mode
npm test -- --coverage          # With coverage
```

## Development Workflow

We follow a **TDD + Feature-by-Feature** approach:

1. **Backend First**: Implement API endpoint + tests
2. **Frontend Second**: Build UI consuming the API
3. **Integration**: Test end-to-end flow

### Current Phase: Phase 2 - Authentication

Next steps:
- [ ] Backend: Google OAuth integration
- [ ] Backend: JWT token management
- [ ] Backend: Auth endpoints
- [ ] Frontend: Login page
- [ ] Frontend: Auth context
- [ ] Tests: Auth flow

## Project Structure

```
NoteTube-AI/
├── backend/          # FastAPI backend
│   ├── app/
│   │   ├── api/      # API routes
│   │   ├── core/     # Config, database
│   │   ├── models/   # SQLAlchemy models
│   │   ├── schemas/  # Pydantic schemas
│   │   ├── services/ # Business logic
│   │   └── workers/  # Background jobs
│   ├── tests/        # Pytest tests
│   └── alembic/      # Database migrations
├── frontend/         # Next.js frontend
└── docker-compose.yml
```

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## Contributing

This is a learning project. Feel free to:
- Report bugs
- Suggest features
- Submit pull requests

## License

MIT

---

**Built with ❤️ using FastAPI, Next.js, and OpenAI**
