FROM mcr.microsoft.com/playwright/python:v1.50.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD cd jobscraper && python manage.py migrate --fake scraper 0001_initial && python manage.py migrate && python manage.py scrape_jobs