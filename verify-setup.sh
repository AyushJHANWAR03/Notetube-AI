#!/bin/bash

echo "=================================="
echo "NoteTube AI - Setup Verification"
echo "=================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track status
ALL_GOOD=true

# Check Docker
echo "Checking Docker..."
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓${NC} Docker is installed"

    # Check if docker-compose is running
    if docker-compose ps | grep -q "Up"; then
        echo -e "${GREEN}✓${NC} Docker containers are running"
    else
        echo -e "${YELLOW}⚠${NC} Docker containers are not running"
        echo "  Run: docker-compose up -d"
        ALL_GOOD=false
    fi
else
    echo -e "${RED}✗${NC} Docker is not installed"
    ALL_GOOD=false
fi

echo ""

# Check Python
echo "Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✓${NC} $PYTHON_VERSION"
else
    echo -e "${RED}✗${NC} Python 3 is not installed"
    ALL_GOOD=false
fi

echo ""

# Check Node.js
echo "Checking Node.js..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✓${NC} Node.js $NODE_VERSION"
else
    echo -e "${RED}✗${NC} Node.js is not installed"
    ALL_GOOD=false
fi

echo ""

# Check Backend Setup
echo "Checking Backend..."
if [ -d "backend/venv" ]; then
    echo -e "${GREEN}✓${NC} Virtual environment exists"
else
    echo -e "${YELLOW}⚠${NC} Virtual environment not found"
    echo "  Run: cd backend && python3 -m venv venv"
    ALL_GOOD=false
fi

if [ -f "backend/.env" ]; then
    echo -e "${GREEN}✓${NC} Backend .env file exists"
else
    echo -e "${RED}✗${NC} Backend .env file not found"
    ALL_GOOD=false
fi

echo ""

# Check Frontend Setup
echo "Checking Frontend..."
if [ -d "frontend/node_modules" ]; then
    echo -e "${GREEN}✓${NC} Frontend dependencies installed"
else
    echo -e "${YELLOW}⚠${NC} Frontend dependencies not installed"
    echo "  Run: cd frontend && npm install"
    ALL_GOOD=false
fi

if [ -f "frontend/.env.local" ]; then
    echo -e "${GREEN}✓${NC} Frontend .env.local file exists"
else
    echo -e "${RED}✗${NC} Frontend .env.local file not found"
    ALL_GOOD=false
fi

echo ""

# Check Database
echo "Checking Database..."
if docker-compose ps | grep -q "postgres.*Up"; then
    echo -e "${GREEN}✓${NC} PostgreSQL container is running"

    # Try to connect
    if docker-compose exec -T postgres pg_isready -U notetube &> /dev/null; then
        echo -e "${GREEN}✓${NC} PostgreSQL is accepting connections"
    else
        echo -e "${YELLOW}⚠${NC} PostgreSQL is not ready yet"
    fi
else
    echo -e "${RED}✗${NC} PostgreSQL container is not running"
    ALL_GOOD=false
fi

echo ""

# Check Redis
echo "Checking Redis..."
if docker-compose ps | grep -q "redis.*Up"; then
    echo -e "${GREEN}✓${NC} Redis container is running"
else
    echo -e "${RED}✗${NC} Redis container is not running"
    ALL_GOOD=false
fi

echo ""

# Final Summary
echo "=================================="
if [ "$ALL_GOOD" = true ]; then
    echo -e "${GREEN}All checks passed! ✓${NC}"
    echo ""
    echo "You can now:"
    echo "  1. Start backend: cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
    echo "  2. Start frontend: cd frontend && npm run dev"
else
    echo -e "${YELLOW}Some checks failed. Please review above.${NC}"
    echo ""
    echo "See SETUP.md for detailed instructions."
fi
echo "=================================="
