# NoteTube AI - Setup Checklist

Use this checklist to verify your setup is complete and ready for development.

## ✅ Phase 1: Foundation Setup - COMPLETE

### Infrastructure
- [x] Docker Compose file created
- [x] PostgreSQL container configured
- [x] Redis container configured
- [x] pgAdmin container configured

### Backend Setup
- [x] Project directory structure created
- [x] All database models implemented (8 tables)
- [x] Alembic migrations configured
- [x] Environment variables set (.env)
- [x] Dependencies listed (requirements.txt)
- [x] pytest configured
- [x] Test fixtures created
- [x] FastAPI app initialized
- [x] Core config module (Settings)
- [x] Database connection setup
- [x] Google OAuth credentials configured
- [x] OpenAI API key configured

### Frontend Setup
- [x] Next.js project structure created
- [x] TypeScript configured
- [x] Tailwind CSS configured
- [x] Environment variables set (.env.local)
- [x] API client created (axios)
- [x] TypeScript types defined
- [x] Jest testing configured
- [x] Landing page created
- [x] Dependencies listed (package.json)

### Documentation
- [x] README.md with project overview
- [x] SETUP.md with step-by-step instructions
- [x] .claude/notetube-ai-guide.md development guide
- [x] PHASE-1-COMPLETE.md summary
- [x] This CHECKLIST.md
- [x] verify-setup.sh script

---

## 🔄 Next Steps - Before Starting Phase 2

### 1. Start Infrastructure
```bash
cd "/Users/ayush/NoteTube AI"
docker-compose up -d
```

Verify:
- [ ] PostgreSQL running on port 5432
- [ ] Redis running on port 6379
- [ ] pgAdmin running on port 5050

### 2. Setup Backend Environment
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

Verify:
- [ ] Virtual environment created
- [ ] All dependencies installed without errors
- [ ] Python version 3.11+ confirmed

### 3. Initialize Database
```bash
# Make sure you're in backend/ with venv activated
alembic revision --autogenerate -m "Initial migration with all models"
alembic upgrade head
```

Verify:
- [ ] Migration file created in alembic/versions/
- [ ] Database tables created (check in pgAdmin)
- [ ] No migration errors

### 4. Test Backend
```bash
# In backend/ with venv activated
pytest
uvicorn app.main:app --reload
```

Verify:
- [ ] All tests pass
- [ ] Backend starts without errors
- [ ] http://localhost:8000/health returns {"status": "healthy"}
- [ ] http://localhost:8000/api/docs shows Swagger UI

### 5. Setup Frontend
```bash
cd frontend
npm install
npm run dev
```

Verify:
- [ ] Dependencies installed without errors
- [ ] Frontend starts without errors
- [ ] http://localhost:3000 shows landing page
- [ ] No console errors in browser

### 6. Optional: Verify Database in pgAdmin
- [ ] Access http://localhost:5050
- [ ] Login (admin@notetube.com / admin123)
- [ ] Add server connection
- [ ] View all 9 tables in notetube_db

---

## 🎯 Phase 2: Authentication - TO DO

### Backend - Authentication System
- [ ] Create Pydantic schemas (UserCreate, UserResponse, Token)
- [ ] Implement auth service (JWT, Google OAuth)
- [ ] Create auth endpoints
  - [ ] GET /auth/google/login
  - [ ] GET /auth/google/callback
  - [ ] GET /api/me
- [ ] Create auth dependencies (get_current_user)
- [ ] Write unit tests for auth service
- [ ] Write integration tests for auth endpoints
- [ ] Test Google OAuth flow end-to-end

### Frontend - Authentication UI
- [ ] Create AuthContext
- [ ] Create GoogleLoginButton component
- [ ] Create auth callback page
- [ ] Create protected route wrapper
- [ ] Update landing page with login button
- [ ] Create user profile component
- [ ] Write component tests
- [ ] Test auth flow end-to-end

---

## 📝 Development Checklist (Daily Use)

### Before Starting Work
- [ ] Activate backend venv: `source backend/venv/bin/activate`
- [ ] Check Docker containers: `docker-compose ps`
- [ ] Pull latest changes (if working with others)

### During Development (TDD)
- [ ] Write test first
- [ ] Run test (should fail)
- [ ] Implement feature
- [ ] Run test (should pass)
- [ ] Refactor if needed
- [ ] Commit changes

### Before Committing
- [ ] Run backend tests: `cd backend && pytest`
- [ ] Run frontend tests: `cd frontend && npm test`
- [ ] Check for linting errors
- [ ] Review changed files

### After Database Model Changes
- [ ] Create migration: `alembic revision --autogenerate -m "description"`
- [ ] Review migration file
- [ ] Apply migration: `alembic upgrade head`
- [ ] Update Pydantic schemas if needed

---

## 🚨 Common Issues & Solutions

### Docker Issues
**Problem**: Containers won't start
```bash
docker-compose down
docker-compose up -d
```

**Problem**: Port already in use
```bash
# Find and kill process using port 5432, 6379, or 5050
lsof -ti:5432 | xargs kill -9
```

### Backend Issues
**Problem**: Import errors
```bash
# Make sure venv is activated
source backend/venv/bin/activate
# Reinstall dependencies
pip install -r requirements-dev.txt
```

**Problem**: Database connection error
```bash
# Check if postgres is running
docker-compose ps
# Check DATABASE_URL in .env
```

**Problem**: Alembic migration errors
```bash
# Reset and re-run
alembic downgrade base
alembic upgrade head
```

### Frontend Issues
**Problem**: Module not found
```bash
rm -rf node_modules package-lock.json
npm install
```

**Problem**: Build errors
```bash
# Clear Next.js cache
rm -rf .next
npm run dev
```

---

## 📊 Current Progress

**Phase 1: Foundation** ✅ 100% Complete
- Infrastructure: ✅
- Backend Setup: ✅
- Frontend Setup: ✅
- Documentation: ✅

**Phase 2: Authentication** ⏳ 0% Complete
- Backend Auth: ⏳
- Frontend Auth: ⏳
- Testing: ⏳

**Phase 3: Video Processing** ⏳ 0% Complete
**Phase 4+**: Future phases...

---

## 🎓 Learning Resources

- [FastAPI Tutorial](https://fastapi.tiangolo.com/tutorial/)
- [Next.js Learn](https://nextjs.org/learn)
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [pytest Documentation](https://docs.pytest.org/)
- [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)

---

**Ready to start Phase 2?**

Run `./verify-setup.sh` to ensure everything is ready, then let's build authentication! 🚀
