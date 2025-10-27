#!/bin/bash

# Zero Trust Architecture System Stop Script
# This script stops all running components of the system

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_status "Stopping Zero Trust Architecture System..."

# Stop backend
if [ -f logs/backend.pid ]; then
    BACKEND_PID=$(cat logs/backend.pid)
    if kill -0 $BACKEND_PID 2>/dev/null; then
        kill $BACKEND_PID
        print_success "Backend stopped (PID: $BACKEND_PID)"
    else
        print_warning "Backend process not found"
    fi
    rm -f logs/backend.pid
else
    print_warning "Backend PID file not found"
fi

# Stop frontend
if [ -f logs/frontend.pid ]; then
    FRONTEND_PID=$(cat logs/frontend.pid)
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        kill $FRONTEND_PID
        print_success "Frontend stopped (PID: $FRONTEND_PID)"
    else
        print_warning "Frontend process not found"
    fi
    rm -f logs/frontend.pid
else
    print_warning "Frontend PID file not found"
fi

# Kill any remaining processes on the ports
print_status "Checking for remaining processes..."

# Kill processes on port 8000 (backend)
if lsof -ti:8000 >/dev/null 2>&1; then
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    print_status "Killed remaining processes on port 8000"
fi

# Kill processes on port 3000 (frontend)
if lsof -ti:3000 >/dev/null 2>&1; then
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    print_status "Killed remaining processes on port 3000"
fi

print_success "Zero Trust Architecture System stopped successfully"
