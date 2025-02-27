# jobscraper/scraper/management/commands/check_db.py
from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError

class Command(BaseCommand):
    help = 'Check database connection and configuration'

    def handle(self, *args, **options):
        # Print all database settings
        from django.conf import settings
        self.stdout.write(f"DATABASE ENGINE: {settings.DATABASES['default']['ENGINE']}")
        
        # Check if SQLite or PostgreSQL
        is_sqlite = 'sqlite' in settings.DATABASES['default']['ENGINE']
        
        if is_sqlite:
            self.stdout.write(f"Using SQLite database at: {settings.DATABASES['default']['NAME']}")
        else:
            # PostgreSQL details (with password masked)
            db_settings = settings.DATABASES['default']
            self.stdout.write(f"Database name: {db_settings.get('NAME', 'not set')}")
            self.stdout.write(f"Database user: {db_settings.get('USER', 'not set')}")
            self.stdout.write(f"Database host: {db_settings.get('HOST', 'not set')}")
            self.stdout.write(f"Database port: {db_settings.get('PORT', 'not set')}")
        
        # Test connection
        try:
            connections['default'].cursor()
            self.stdout.write(self.style.SUCCESS('Database connection successful'))
            
            # List all tables in the database
            with connections['default'].cursor() as cursor:
                if is_sqlite:
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                else:
                    cursor.execute("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public'
                        ORDER BY table_name;
                    """)
                tables = [row[0] for row in cursor.fetchall()]
                self.stdout.write("Tables in database:")
                for table in tables:
                    self.stdout.write(f"  - {table}")
                
        except OperationalError as e:
            self.stdout.write(self.style.ERROR(f'Database connection failed: {e}'))
