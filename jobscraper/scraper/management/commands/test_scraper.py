# jobscraper/scraper/management/commands/test_scraper.py
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
import os

from scraper.job_downloader import PracujDownloader
from scraper.models import Job
from scraper.mailings import send_mail_with_offers


class Command(BaseCommand):
    help = 'Test job scraping with a single URL and limited results'

    def add_arguments(self, parser):
        parser.add_argument(
            '--url',
            type=str,
            default='https://www.pracuj.pl/praca/warszawa;wp/ostatnich%203%20dni;p,3?rd=0&et=3%2C17%2C4&ao=false&tc=0&wm=hybrid%2Cfull-office',
            help='URL to scrape jobs from'
        )
        parser.add_argument(
            '--max-pages',
            type=int,
            default=1,
            help='Maximum number of pages to scrape'
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Email to send results to (overrides EMAIL_RECIPIENTS env var)',
        )

    def handle(self, *args, **options):
        # Set email recipient for test
        if options['email']:
            os.environ['EMAIL_RECIPIENTS'] = options['email']
            self.stdout.write(f"Setting email recipient to: {options['email']}")
        elif not os.environ.get('EMAIL_RECIPIENTS'):
            raise CommandError(
                "No email recipient specified. Use --email option or set EMAIL_RECIPIENTS environment variable")

        url = options['url']
        max_pages = options['max_pages']

        self.stdout.write(f"Starting test scrape from: {url}")
        self.stdout.write(f"Max pages to scrape: {max_pages}")

        # Record jobs count before scraping
        jobs_before = Job.objects.count()
        self.stdout.write(f"Jobs in database before scraping: {jobs_before}")

        # Scrape jobs
        downloader = PracujDownloader()
        jobs_added = downloader.download_jobs(url, max_pages=max_pages)

        # Count new jobs
        jobs_after = Job.objects.count()
        new_jobs_count = jobs_after - jobs_before

        self.stdout.write(self.style.SUCCESS(f"Scraping completed. {new_jobs_count} new jobs added to database."))

        # Get jobs created today
        today_jobs = (
            Job.objects
            .filter(created_at__date=timezone.now().date())
            .values('title', 'company__name', 'url')
            .order_by('-created_at')[:20]  # Limit to 20 most recent for the test
        )

        if today_jobs:
            self.stdout.write(f"Sending email with {len(today_jobs)} jobs...")
            send_mail_with_offers(today_jobs, is_test=True)
            self.stdout.write(self.style.SUCCESS("Email sent successfully"))
        else:
            self.stdout.write(self.style.WARNING("No jobs found today to email"))

        return "Test completed successfully"
