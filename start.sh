#!/bin/bash
# TradeIQ Startup Script

set -e

echo "Starting TradeIQ Algo Trading Platform..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "Error: .env file not found. Copy .env.example to .env and configure."
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Function to check if service is ready
check_service() {
    local host=$1
    local port=$2
    local service=$3
    
    echo "Waiting for $service at $host:$port..."
    while ! nc -z $host $port 2>/dev/null; do
        sleep 2
    done
    echo "$service is ready!"
}

# Start PostgreSQL if using local
if [ "$DATABASE_URL" == *"localhost"* ] || [ "$DATABASE_URL" == *"127.0.0.1"* ]; then
    echo "Starting PostgreSQL..."
    docker-compose up -d postgres
    check_service localhost 5432 "PostgreSQL"
fi

# Start Redis if using local
if [ "$REDIS_URL" == *"localhost"* ] || [ "$REDIS_URL" == *"127.0.0.1"* ]; then
    echo "Starting Redis..."
    docker-compose up -d redis
    check_service localhost 6379 "Redis"
fi

# Run database migrations
echo "Running database migrations..."
cd backend
alembic upgrade head
cd ..

# Start backend
echo "Starting backend..."
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..

# Wait for backend to be ready
sleep 5
check_service localhost 8000 "Backend API"

# Start frontend
echo "Starting frontend..."
cd frontend
npm start &
FRONTEND_PID=$?
cd ..

echo ""
echo "TradeIQ Platform Started!"
echo "========================"
echo "Frontend: http://localhost:3000"
echo "Backend API: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"

# Trap SIGINT to kill background processes
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT

# Wait for processes
wait $BACKEND_PID $FRONTEND_PID