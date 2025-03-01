#!/bin/bash
# test_scraper.sh - A helper script to test the job scraper locally

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "Virtual environment not activated. Please activate it first."
    echo "Example: source venv/bin/activate"
    exit 1
fi

# Check if EMAIL_RECIPIENTS environment variable is set
if [[ -z "$EMAIL_RECIPIENTS" ]]; then
    echo "EMAIL_RECIPIENTS environment variable not set. Using default email: janzysko@gmail.com"
    export EMAIL_RECIPIENTS="janzysko@gmail.com"
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