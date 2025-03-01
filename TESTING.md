# Job Scraper Testing Guide

This guide explains how to test the refactored job scraper locally.

## Files Changed/Added

1. **New Command**: `jobscraper/scraper/management/commands/test_scraper.py`
   - A new command to test the scraper with a single URL and limited results

2. **Refactored Downloader**: `jobscraper/scraper/job_downloader.py`
   - Added `max_pages` parameter to limit pages scraped
   - Improved logging
   - Better error handling
   - Returns count of jobs added

3. **Updated Mailings**: `jobscraper/scraper/mailings.py`
   - Added test mode
   - Improved formatting
   - Better error handling

4. **Refactored Tasks**: `jobscraper/scraper/tasks.py`
   - Improved structure
   - Better logging
   - More informative return value

5. **Tests**: `jobscraper/scraper/tests.py`
   - Unit tests for the job downloader

6. **Test Script**: `test_scraper.sh`
   - Helper script to run the test command easily

## Setup for Testing

1. Make sure you have a virtual environment set up and activated:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up the database:
   ```bash
   cd jobscraper
   python manage.py migrate
   ```

## Running the Test

You can run the test in two ways:

### Option 1: Using the helper script

1. Make the script executable:
   ```bash
   chmod +x test_scraper.sh
   ```

2. Run the script:
   ```bash
   ./test_scraper.sh
   ```

3. The script will ask for your email if the `EMAIL_RECIPIENTS` environment variable is not set.

### Option 2: Running the command directly

1. Set the `EMAIL_RECIPIENTS` environment variable:
   ```bash
   export EMAIL_RECIPIENTS="your.email@example.com"
   ```

2. Run the test command:
   ```bash
   cd jobscraper
   python manage.py test_scraper --max-pages 1
   ```

## Command Options

The `test_scraper` command supports several options:

- `--url`: URL to scrape jobs from (default: a predefined Pracuj.pl URL)
- `--max-pages`: Maximum number of pages to scrape (default: 1)
- `--email`: Email to send results to (overrides `EMAIL_RECIPIENTS` env var)

Example with all options:
```bash
python manage.py test_scraper --url "https://www.pracuj.pl/praca/warszawa" --max-pages 2 --email "your.email@example.com"
```

## Running Unit Tests

You can run the unit tests with:
```bash
cd jobscraper
python manage.py test scraper
```

## What to Expect

When you run the test:

1. It will scrape one page from the job site
2. Add any new jobs to the database
3. Send you an email with the found jobs (limited to 20 most recent)
4. Show log output of what's happening

This allows you to verify that:
- The scraper can connect to the job site
- It can parse the HTML correctly
- The database connection works
- Email sending works

## Troubleshooting

- **Database Issues**: 
  - Run `python manage.py check_db` to verify database setup
  - If you get errors about missing tables, ensure migrations have run: `python manage.py migrate`
  - For local development, the migrations should create tables with the `grabbo_` prefix to match the models
  - If you're getting foreign key errors, you may need to add some test data to the category, salary, and technology tables
  
- **Email Issues**: 
  - Check your spam folder
  - Verify the email settings in `settings.py`
  - Ensure `EMAIL_RECIPIENTS` is set correctly in your environment

- **Parsing Issues**: 
  - The website structure might have changed; you may need to update the selectors in `job_downloader.py`
  - Use the `--max-pages 1` option to limit scraping during debugging

### Database Table Prefixes

The original project uses database tables with the `grabbo_` prefix instead of the default Django `scraper_` prefix that would normally be created. We handle this in two ways:

1. In the models, we specify the correct table name using the `db_table` Meta option:
   ```python
   class Meta:
       db_table = 'grabbo_company'  # Use existing table
   ```

2. For local development with SQLite, we've created a custom migration that creates the required tables with the `grabbo_` prefix if they don't exist yet.

This way, your code should work both with the existing production database and with a fresh local SQLite database without having to modify your models.