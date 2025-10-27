#!/bin/bash

# Zero Trust Architecture System Launch Script
# This script initializes and starts all components of the system

set -e  # Exit on any error

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

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a port is in use
port_in_use() {
    lsof -i :$1 >/dev/null 2>&1
}

# Function to wait for a service to be ready
wait_for_service() {
    local url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=0
    
    print_status "Waiting for $service_name to be ready..."
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s "$url" >/dev/null 2>&1; then
            print_success "$service_name is ready!"
            return 0
        fi
        
        attempt=$((attempt + 1))
        sleep 2
    done
    
    print_error "$service_name failed to start within expected time"
    return 1
}

# Main execution
main() {
    print_status "Starting Zero Trust Architecture System..."
    print_status "================================================"
    
    # Check if running as root (needed for some system monitoring)
    if [ "$EUID" -eq 0 ]; then
        print_warning "Running as root. Some system monitoring features will be available."
    else
        print_warning "Not running as root. Some system monitoring features may be limited."
    fi
    
    # Check system requirements
    print_status "Checking system requirements..."
    
    # Check Python
    if ! command_exists python3; then
        print_error "Python 3 is required but not installed"
        exit 1
    fi
    
    # Check Node.js
    if ! command_exists node; then
        print_error "Node.js is required but not installed"
        exit 1
    fi
    
    # Check database (SQLite is built-in, so we skip PostgreSQL check)
    print_status "Using SQLite database (no additional setup required)"
    
    print_success "System requirements check passed"
    
    # Create necessary directories
    print_status "Creating necessary directories..."
    mkdir -p models logs
    
    # Check if ports are available
    if port_in_use 8000; then
        print_error "Port 8000 is already in use (backend)"
        exit 1
    fi
    
    if port_in_use 3000; then
        print_error "Port 3000 is already in use (frontend)"
        exit 1
    fi
    
    # Setup backend
    print_status "Setting up backend..."
    cd backend
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        print_status "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install Python dependencies
    print_status "Installing Python dependencies..."
    pip install -r requirements.txt
    
    # Set up environment variables for SQLite
    export DATABASE_URL="sqlite:///./zerotrust.db"
    export API_HOST="0.0.0.0"
    export API_PORT="8000"
    
    # Start backend in background (production mode for stability)
    print_status "Starting backend server..."
    nohup uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 > ../logs/backend.log 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > ../logs/backend.pid
    
    # Wait for backend to be ready (increased timeout)
    print_status "Waiting for Backend API to be ready..."
    sleep 5  # Give backend time to start
    
    # Check if backend is running
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        print_error "Backend process died"
        print_status "Backend logs:"
        tail -20 ../logs/backend.log
        exit 1
    fi
    
    # Try to connect to backend
    for i in {1..30}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            print_success "Backend API is ready"
            break
        fi
        if [ $i -eq 30 ]; then
            print_error "Backend API failed to start within expected time"
            print_status "Backend logs:"
            tail -20 ../logs/backend.log
            exit 1
        fi
        sleep 2
    done
    
    cd ..
    
    # Setup frontend
    print_status "Setting up frontend..."
    cd frontend
    
    # Install Node.js dependencies
    print_status "Installing Node.js dependencies..."
    npm install
    
    # Set up environment variables
    export API_URL="http://localhost:8000"
    export WS_URL="ws://localhost:8000/ws"
    
    # Start frontend in background
    print_status "Starting frontend server..."
    nohup npm run dev > ../logs/frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > ../logs/frontend.pid
    
    # Wait for frontend to be ready
    print_status "Waiting for Frontend to be ready..."
    sleep 10  # Give frontend time to start
    
    # Check if frontend is running
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        print_error "Frontend process died"
        print_status "Frontend logs:"
        tail -20 ../logs/frontend.log
        exit 1
    fi
    
    # Try to connect to frontend
    for i in {1..30}; do
        if curl -s http://localhost:3000 > /dev/null 2>&1; then
            print_success "Frontend is ready"
            break
        fi
        if [ $i -eq 30 ]; then
            print_error "Frontend failed to start within expected time"
            print_status "Frontend logs:"
            tail -20 ../logs/frontend.log
            exit 1
        fi
        sleep 2
    done
    
    cd ..
    
    # Final status
    print_success "================================================"
    print_success "Zero Trust Architecture System is ready!"
    print_success "================================================"
    print_status "Backend API: http://localhost:8000"
    print_status "Frontend UI: http://localhost:3000"
    print_status "API Documentation: http://localhost:8000/docs"
    print_status ""
    print_status "Process IDs:"
    print_status "  Backend: $BACKEND_PID"
    print_status "  Frontend: $FRONTEND_PID"
    print_status ""
    print_status "Logs:"
    print_status "  Backend: logs/backend.log"
    print_status "  Frontend: logs/frontend.log"
    print_status ""
    print_status "To stop the system:"
    print_status "  kill $BACKEND_PID $FRONTEND_PID"
    print_status "  or run: ./stop.sh"
    print_status ""
    print_status "System is now monitoring for events..."
    print_status "Open http://localhost:3000 in your browser to access the dashboard"
}

# Handle script interruption
cleanup() {
    print_status "Shutting down system..."
    
    if [ -f logs/backend.pid ]; then
        BACKEND_PID=$(cat logs/backend.pid)
        if kill -0 $BACKEND_PID 2>/dev/null; then
            kill $BACKEND_PID
            print_status "Backend stopped"
        fi
    fi
    
    if [ -f logs/frontend.pid ]; then
        FRONTEND_PID=$(cat logs/frontend.pid)
        if kill -0 $FRONTEND_PID 2>/dev/null; then
            kill $FRONTEND_PID
            print_status "Frontend stopped"
        fi
    fi
    
    print_success "System shutdown complete"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Run main function
main "$@"
