# jobscraper/scraper/management/commands/export_jobs_csv.py
import csv
import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from scraper.models import Job, JobBoard, HypeStatus


class Command(BaseCommand):
    help = 'Export job database to CSV file for analysis with pandas'

    def add_arguments(self, parser):
        parser.add_argument('--output', type=str, help='Output file path (default: jobs_export_YYYY-MM-DD.csv)')
        parser.add_argument('--board', type=int, help='Filter by job board (1=NoFluff, 2=JustJoin, 3=Pracuj)')
        parser.add_argument('--limit', type=int, help='Limit the number of records')

    def handle(self, *args, **options):
        # Prepare output file path
        output_path = options.get('output')
        if not output_path:
            date_str = timezone.now().strftime('%Y-%m-%d')
            output_path = f"jobs_export_{date_str}.csv"

        # Build the queryset
        queryset = Job.objects.all().select_related('company')

        # Apply filters if provided
        board_id = options.get('board')
        if board_id:
            queryset = queryset.filter(board=board_id)
            board_name = dict(JobBoard.choices).get(board_id, 'Unknown')
            self.stdout.write(f"Filtering jobs for board: {board_name} ({board_id})")

        # Apply limit if provided
        limit = options.get('limit')
        if limit:
            queryset = queryset[:limit]
            self.stdout.write(f"Limiting export to {limit} records")

        # Determine total count
        total_jobs = queryset.count()
        self.stdout.write(f"Exporting {total_jobs} jobs to {output_path}")

        # Define fieldnames for the CSV
        fieldnames = [
            'id', 'original_id', 'board', 'board_name',
            'title', 'url', 'seniority', 'salary_text',
            'company_id', 'company_name', 'company_url',
            'status', 'status_name', 'created_at',
            'lena_comparibility'
        ]

        # Write to CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            # Process in batches to avoid memory issues with large databases
            batch_size = 1000
            processed = 0

            for i in range(0, total_jobs, batch_size):
                batch = queryset[i:i + batch_size]
                for job in batch:
                    # Convert board ID to name
                    board_name = job.get_board_display()

                    # Convert status ID to name
                    status_name = job.get_status_display()

                    # Get company info safely
                    company_id = job.company.id if job.company else None
                    company_name = job.company.name if job.company else ''
                    company_url = job.company.url if job.company else ''

                    writer.writerow({
                        'id': job.id,
                        'original_id': job.original_id,
                        'board': job.board,
                        'board_name': board_name,
                        'title': job.title,
                        'url': job.url,
                        'seniority': job.seniority,
                        'salary_text': job.salary_text,
                        'company_id': company_id,
                        'company_name': company_name,
                        'company_url': company_url,
                        'status': job.status,
                        'status_name': status_name,
                        'created_at': job.created_at.isoformat() if job.created_at else '',
                        'lena_comparibility': job.lena_comparibility
                    })

                processed += len(batch)
                self.stdout.write(f"Progress: {processed}/{total_jobs} jobs processed")

        # Print summary
        file_size = os.path.getsize(output_path) / (1024 * 1024)  # Size in MB
        self.stdout.write(self.style.SUCCESS(
            f"Export complete! {total_jobs} jobs exported to {output_path} ({file_size:.2f} MB)"
        ))
        self.stdout.write(f"You can now analyze this data with pandas using:")
        self.stdout.write(f"import pandas as pd")
        self.stdout.write(f"df = pd.read_csv('{output_path}')")
        self.stdout.write(f"df.info()")