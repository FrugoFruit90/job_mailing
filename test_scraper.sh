#!/bin/bash
# test_scraper.sh - A helper script to test the job scraper locally

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "Virtual environment not activated. Please activate it first."
    echo "Example: source venv/bin/activate"
    exit 1
fi

# Check if .env file exists
if [[ -f ".env" ]]; then
    echo "Found .env file. Using environment variables from there."
else
    echo "WARNING: No .env file found. Using default environment settings."
    echo "Consider creating a .env file for better configuration."
fi

# Navigate to project directory
cd jobscraper || exit

# Check database status
echo "Checking database..."
python manage.py check_db

# Prepare database
echo "Running migrations..."
python manage.py migrate

# Run the test command
echo "Running test scraper..."
python manage.py test_scraper --max-pages 1

echo "Test completed."

