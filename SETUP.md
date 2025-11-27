# NoteTube AI - Quick Setup Guide

## Phase 1: Foundation Setup ✅ COMPLETE

All foundational components have been created! Here's what's ready:

### ✅ What's Been Set Up

1. **Docker Infrastructure**
   - PostgreSQL database
   - Redis queue
   - pgAdmin for database management

2. **Backend (FastAPI)**
   - Complete project structure
   - All database models (8 tables)
   - Alembic migrations ready
   - pytest configuration with fixtures
   - Environment variables configured
   - Google OAuth & OpenAI API keys integrated

3. **Frontend (Next.js 14)**
   - TypeScript configuration
   - Tailwind CSS setup
   - App Router structure
   - API client with axios
   - Type definitions
   - Jest testing setup
   - Landing page

### 🚀 Next Steps to Get Running

#### Step 1: Start Infrastructure (1 minute)

```bash
# Make sure you're in the project root
cd "/Users/ayush/NoteTube AI"

# Start Docker containers
docker-compose up -d

# Verify containers are running
docker-compose ps
```

You should see 3 containers running:
- notetube-postgres (port 5432)
- notetube-redis (port 6379)
- notetube-pgadmin (port 5050)

#### Step 2: Setup Backend (2-3 minutes)

```bash
cd backend

# Create Python virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# OR on Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-dev.txt

# Create initial database migration
alembic revision --autogenerate -m "Initial migration with all models"

# Apply migrations to database
alembic upgrade head

# Start backend server
uvicorn app.main:app --reload
```

Backend will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/api/docs
- **Health Check**: http://localhost:8000/health

#### Step 3: Setup Frontend (2-3 minutes)

Open a new terminal:

```bash
cd "/Users/ayush/NoteTube AI/frontend"

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at:
- **App**: http://localhost:3000

#### Step 4: Verify Everything Works

1. **Test Backend**:
   ```bash
   cd backend
   pytest
   ```

2. **Visit Frontend**: Open http://localhost:3000 in your browser

3. **Check API Docs**: Open http://localhost:8000/api/docs

### 📊 Database Access (Optional)

Access pgAdmin to view your database:
1. Go to: http://localhost:5050
2. Login:
   - Email: `admin@notetube.com`
   - Password: `admin123`
3. Add Server:
   - Name: NoteTube DB
   - Host: `postgres` (container name)
   - Port: `5432`
   - Database: `notetube_db`
   - Username: `notetube`
   - Password: `notetube123`

### 🔑 API Keys Configured

Your credentials are already set up in `backend/.env`:
- ✅ Google OAuth Client ID & Secret
- ✅ OpenAI API Key
- ✅ Database connection
- ✅ Redis connection
- ✅ JWT secret key

For Firebase (needed later for exports):
- Download service account JSON from Firebase Console
- Save as `backend/firebase-key.json`

### 📁 Project Structure Created

```
NoteTube-AI/
├── backend/
│   ├── app/
│   │   ├── api/routes/      # API endpoints (Phase 2+)
│   │   ├── core/            # ✅ Config & database
│   │   ├── models/          # ✅ All 8 DB models
│   │   ├── schemas/         # Pydantic schemas (Phase 2+)
│   │   ├── services/        # Business logic (Phase 2+)
│   │   ├── workers/         # Background jobs (Phase 3+)
│   │   └── main.py          # ✅ FastAPI app
│   ├── tests/               # ✅ pytest setup
│   ├── alembic/             # ✅ Migrations
│   ├── .env                 # ✅ Your credentials
│   └── requirements.txt     # ✅ Dependencies
├── frontend/
│   ├── app/                 # ✅ Next.js App Router
│   ├── components/          # UI components (Phase 2+)
│   ├── lib/                 # ✅ API client & types
│   ├── .env.local           # ✅ Frontend config
│   └── package.json         # ✅ Dependencies
└── docker-compose.yml       # ✅ Infrastructure
```

### ✅ Database Models Created

All tables from your LLD are ready:
1. **users** - User accounts (Google OAuth)
2. **videos** - Processed YouTube videos
3. **jobs** - Background processing jobs
4. **transcripts** - Video transcripts
5. **notes** - AI-generated notes
6. **quiz_questions** - Quiz question bank
7. **quiz_sessions** - Quiz attempts
8. **quiz_answers** - User answers
9. **chat_messages** - Chat history
10. **exports** - PDF/Markdown exports

### 🎯 What's Next: Phase 2 - Authentication

Now that the foundation is complete, we'll build:

**Backend:**
1. Google OAuth integration
2. JWT token generation/validation
3. Auth endpoints:
   - `GET /auth/google/login`
   - `GET /auth/google/callback`
   - `GET /api/me`
4. Auth middleware
5. Tests for auth flow

**Frontend:**
1. Auth context
2. Google login button
3. Callback handling
4. Protected routes
5. User profile display

### 🐛 Troubleshooting

**Docker containers won't start:**
```bash
docker-compose down
docker-compose up -d
```

**Backend dependencies fail:**
```bash
# Make sure you're in venv
which python  # Should show path to venv
pip install --upgrade pip
pip install -r requirements-dev.txt
```

**Database migration errors:**
```bash
# Reset migrations
alembic downgrade base
alembic upgrade head
```

**Frontend won't start:**
```bash
rm -rf node_modules package-lock.json
npm install
```

### 📚 Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com
- **Next.js Docs**: https://nextjs.org/docs
- **Alembic Tutorial**: https://alembic.sqlalchemy.org/en/latest/tutorial.html
- **Your Design Doc**: See the uploaded LLD for full architecture

---

**Ready to code! 🎉**

Run the setup steps above, then we'll start building Phase 2: Authentication!
