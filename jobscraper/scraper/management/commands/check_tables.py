# jobscraper/scraper/management/commands/check_tables.py
from django.core.management.base import BaseCommand
from django.db import connections

class Command(BaseCommand):
    help = 'Check the structure of the database tables'

    def handle(self, *args, **options):
        self.stdout.write("Checking database table structures...")
        
        # Test connection
        with connections['default'].cursor() as cursor:
            # Check the structure of the grabbo_company table
            self.stdout.write("\nTable: grabbo_company")
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'grabbo_company'
                ORDER BY ordinal_position;
            """)
            company_columns = cursor.fetchall()
            for column in company_columns:
                self.stdout.write(f"  - {column[0]}: {column[1]} (Nullable: {column[2]})")
            
            # Check the structure of the grabbo_job table
            self.stdout.write("\nTable: grabbo_job")
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'grabbo_job'
                ORDER BY ordinal_position;
            """)
            job_columns = cursor.fetchall()
            for column in job_columns:
                self.stdout.write(f"  - {column[0]}: {column[1]} (Nullable: {column[2]})")
