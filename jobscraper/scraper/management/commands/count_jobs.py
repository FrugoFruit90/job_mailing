# jobscraper/scraper/management/commands/count_jobs.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count
from scraper.models import Job


class Command(BaseCommand):
    help = 'Count jobs and check date distribution'

    def handle(self, *args, **options):
        # Get today's date
        today = timezone.now().date()

        # Count total jobs
        total_jobs = Job.objects.count()

        # Count jobs created today
        today_jobs = Job.objects.filter(created_at__date=today).count()

        # Calculate percentage
        if total_jobs > 0:
            percentage = (today_jobs / total_jobs) * 100
        else:
            percentage = 0

        self.stdout.write(f"Date: {today}")
        self.stdout.write(f"Total jobs: {total_jobs}")
        self.stdout.write(f"Jobs created today: {today_jobs}")
        self.stdout.write(f"Percentage of jobs created today: {percentage:.2f}%")

        # Get a breakdown of dates
        date_stats = Job.objects.values('created_at__date') \
            .annotate(count=Count('id')) \
            .order_by('created_at__date')

        self.stdout.write("\nDate breakdown:")
        for stat in date_stats:
            date = stat['created_at__date']
            count = stat['count']
            self.stdout.write(f"  {date}: {count} jobs")