#!/bin/bash

# WattsUp Backend Server Startup Script

echo "🏢 WattsUp - NYC Electricity Bill Estimation Backend"
echo "=================================================="

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Check if CSV file exists
if [ ! -f "NYC_Building_Energy_Filtered_Clean.csv" ]; then
    echo "❌ Required CSV file not found: NYC_Building_Energy_Filtered_Clean.csv"
    exit 1
fi

echo "✅ Python 3 found"
echo "✅ CSV data file found"

# Install dependencies if needed
echo "📦 Installing/updating dependencies..."
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo "✅ Dependencies installed"

# Run system test
echo "🧪 Running system tests..."
python3 test_system.py

if [ $? -ne 0 ]; then
    echo "❌ System tests failed"
    exit 1
fi

echo "✅ System tests passed"

# Start the Flask server
echo "🚀 Starting Flask server..."
echo "📡 API will be available at: http://localhost:61188"
echo "💡 Press Ctrl+C to stop the server"
echo ""

python3 app.py
