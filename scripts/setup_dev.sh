#!/bin/bash
# Development environment setup script for SVO2-SAM3 Analyzer

set -e

echo "=== SVO2-SAM3 Analyzer Development Setup ==="
echo ""

# Check if running on Linux
if [[ "$(uname)" != "Linux" ]]; then
    echo "Error: This script is intended for Linux (Ubuntu 22.04)"
    exit 1
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Project directory: $PROJECT_DIR"
echo ""

# 1. Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

if [[ $PYTHON_MAJOR -ge 3 ]] && [[ $PYTHON_MINOR -ge 10 ]]; then
    print_status "Python $PYTHON_VERSION"
else
    print_error "Python 3.10+ required (found $PYTHON_VERSION)"
    exit 1
fi

# 2. Create virtual environment
echo ""
echo "Setting up Python virtual environment..."
if [[ ! -d "$PROJECT_DIR/.venv" ]]; then
    python3 -m venv "$PROJECT_DIR/.venv"
    print_status "Virtual environment created"
else
    print_status "Virtual environment exists"
fi

# 3. Activate virtual environment and install dependencies
echo ""
echo "Installing Python dependencies..."
source "$PROJECT_DIR/.venv/bin/activate"
pip install --upgrade pip
pip install -e "$PROJECT_DIR[dev]"
print_status "Python dependencies installed"

# 4. Check Node.js version
echo ""
echo "Checking Node.js version..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    print_status "Node.js $NODE_VERSION"
else
    print_warning "Node.js not found. Please install Node.js 18+"
fi

# 5. Install frontend dependencies
echo ""
echo "Installing frontend dependencies..."
if [[ -d "$PROJECT_DIR/frontend" ]] && command -v npm &> /dev/null; then
    cd "$PROJECT_DIR/frontend"
    npm install
    print_status "Frontend dependencies installed"
    cd "$PROJECT_DIR"
else
    print_warning "Skipping frontend dependencies (npm not found)"
fi

# 6. Copy environment file
echo ""
echo "Setting up environment file..."
if [[ ! -f "$PROJECT_DIR/.env" ]]; then
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    print_status "Created .env file from template"
else
    print_status ".env file exists"
fi

# 7. Create data directories
echo ""
echo "Creating data directories..."
mkdir -p "$PROJECT_DIR/data"/{svo2,output,models,cache}
mkdir -p "$PROJECT_DIR/logs"
print_status "Data directories created"

# 8. Check Docker
echo ""
echo "Checking Docker..."
if command -v docker &> /dev/null; then
    print_status "Docker installed"
    echo "Starting PostgreSQL and Redis..."
    cd "$PROJECT_DIR"
    docker compose up -d postgres redis
    print_status "Services started"
else
    print_warning "Docker not found. Please install Docker to run PostgreSQL and Redis"
fi

# 9. Check GPU
echo ""
echo "Checking GPU..."
if command -v nvidia-smi &> /dev/null; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n1)
    print_status "GPU detected: $GPU_NAME"
else
    print_warning "nvidia-smi not found. GPU acceleration may not be available"
fi

# 10. Summary
echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Review and edit .env file if needed"
echo "2. Install ZED SDK 5.1: ./scripts/setup_zed_sdk.sh"
echo "3. Download SAM 3 model: python scripts/download_sam3.py"
echo "4. Run database migrations: alembic upgrade head"
echo "5. Start backend: uvicorn backend.app.main:app --reload"
echo "6. Start frontend: cd frontend && npm run dev"
echo ""
