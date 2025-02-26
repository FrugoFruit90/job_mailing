from django.core.management.base import BaseCommand
from tasks import download_and_send

class Command(BaseCommand):
    help = 'Scrape jobs from pracuj.pl and send email with results'

    def handle(self, *args, **options):
        self.stdout.write('Starting job scraping...')
        result = download_and_send()
        self.stdout.write(self.style.SUCCESS(f'Job scraping completed: {result}'))