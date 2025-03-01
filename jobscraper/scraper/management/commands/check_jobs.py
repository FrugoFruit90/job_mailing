# jobscraper/scraper/management/commands/jobs_per_day.py
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.db.models.functions import TruncDate
from scraper.models import Job, JobBoard
import datetime


class Command(BaseCommand):
    help = 'Show jobs created per day in February 2025'

    def add_arguments(self, parser):
        parser.add_argument('--board', type=int, help='Filter by job board (1=NoFluff, 2=JustJoin, 3=Pracuj)')
        parser.add_argument('--month', type=int, default=2, help='Month to analyze (default: February)')
        parser.add_argument('--year', type=int, default=2025, help='Year to analyze (default: 2025)')

    def handle(self, *args, **options):
        board_id = options.get('board')
        month = options.get('month')
        year = options.get('year')

        # Calculate start and end dates for the month
        start_date = datetime.date(year, month, 1)
        if month == 12:
            end_date = datetime.date(year + 1, 1, 1)
        else:
            end_date = datetime.date(year, month + 1, 1)

        # Build the queryset
        queryset = Job.objects.filter(
            created_at__gte=start_date,
            created_at__lt=end_date
        )

        if board_id:
            queryset = queryset.filter(board=board_id)
            board_name = dict(JobBoard.choices).get(board_id, 'Unknown')
            self.stdout.write(f"Showing jobs for board: {board_name} ({board_id})")

        # Group by day and count
        jobs_per_day = (
            queryset
            .annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )

        # Display the results
        month_name = start_date.strftime('%B')
        self.stdout.write(f"\nJobs created per day in {month_name} {year}:")
        self.stdout.write("=" * 40)

        total_jobs = 0
        max_count = 0
        max_day = None

        # Create a dictionary of all days in the month
        all_days = {}
        current_date = start_date
        while current_date < end_date:
            all_days[current_date] = 0
            current_date += datetime.timedelta(days=1)

        # Fill in the actual counts
        for entry in jobs_per_day:
            day = entry['day']
            count = entry['count']
            all_days[day] = count
            total_jobs += count

            if count > max_count:
                max_count = count
                max_day = day

        # Print with bar chart
        for day, count in all_days.items():
            bar = "█" * int(count / (max_count or 1) * 40)
            self.stdout.write(f"{day.strftime('%Y-%m-%d')} | {count:4d} | {bar}")

        self.stdout.write("=" * 40)
        self.stdout.write(f"Total jobs created: {total_jobs}")

        if max_day:
            self.stdout.write(f"Most active day: {max_day.strftime('%Y-%m-%d')} with {max_count} jobs")
        else:
            self.stdout.write("No jobs found in the specified period.")