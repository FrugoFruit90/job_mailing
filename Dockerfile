FROM mcr.microsoft.com/playwright/python:v1.50.0-jammy

WORKDIR /app

# Install additional system dependencies
RUN apt-get update && apt-get install -y \
    python3-lxml \
    --no-install-recommends && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Set memory limits for Python
ENV PYTHONUNBUFFERED=1
ENV PYTHONMALLOC=malloc
ENV PYTHONHASHSEED=0

CMD cd jobscraper && python manage.py migrate --fake scraper 0001_initial && python manage.py migrate && python manage.py scrape_jobs