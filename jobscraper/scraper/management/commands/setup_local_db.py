# jobscraper/scraper/management/commands/setup_local_db.py
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Set up local database with correct table names for development'

    def handle(self, *args, **options):
        self.stdout.write('Setting up local database tables...')

        # Check if we're using SQLite
        db_engine = connection.vendor
        if db_engine != 'sqlite':
            self.stdout.write(self.style.WARNING(
                f'This command is intended for SQLite databases only. '
                f'Detected: {db_engine}. Skipping setup.'
            ))
            return

        # Check if the tables already exist
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='grabbo_company';")
            company_exists = cursor.fetchone() is not None

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='grabbo_job';")
            job_exists = cursor.fetchone() is not None

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='grabbo_category';")
            category_exists = cursor.fetchone() is not None

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='grabbo_salary';")
            salary_exists = cursor.fetchone() is not None

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='grabbo_technology';")
            tech_exists = cursor.fetchone() is not None

        # If tables already exist, we're done
        if company_exists and job_exists and category_exists and salary_exists and tech_exists:
            self.stdout.write(self.style.SUCCESS('All necessary tables already exist.'))
            return

        # Create tables
        with connection.cursor() as cursor:
            # Create company table if it doesn't exist
            if not company_exists:
                self.stdout.write('Creating grabbo_company table...')
                cursor.execute('''
                CREATE TABLE "grabbo_company" (
                    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                    "name" varchar(255) NOT NULL,
                    "industry" varchar(255) NOT NULL,
                    "size_from" integer NOT NULL,
                    "size_to" integer NOT NULL,
                    "url" varchar(1024) NOT NULL,
                    "status" integer NOT NULL
                );
                ''')

            # Create category table if it doesn't exist
            if not category_exists:
                self.stdout.write('Creating grabbo_category table...')
                cursor.execute('''
                CREATE TABLE "grabbo_category" (
                    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                    "name" varchar(255) NOT NULL
                );
                ''')
                # Insert a default category
                cursor.execute('INSERT INTO "grabbo_category" ("name") VALUES ("Default");')

            # Create salary table if it doesn't exist
            if not salary_exists:
                self.stdout.write('Creating grabbo_salary table...')
                cursor.execute('''
                CREATE TABLE "grabbo_salary" (
                    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                    "amount_from" integer NOT NULL,
                    "amount_to" integer NOT NULL,
                    "currency" varchar(10) NOT NULL
                );
                ''')
                # Insert a default salary
                cursor.execute(
                    'INSERT INTO "grabbo_salary" ("amount_from", "amount_to", "currency") VALUES (0, 0, "PLN");')

            # Create technology table if it doesn't exist
            if not tech_exists:
                self.stdout.write('Creating grabbo_technology table...')
                cursor.execute('''
                CREATE TABLE "grabbo_technology" (
                    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                    "name" varchar(255) NOT NULL
                );
                ''')
                # Insert a default technology
                cursor.execute('INSERT INTO "grabbo_technology" ("name") VALUES ("Default");')

            # Create job table if it doesn't exist
            if not job_exists:
                self.stdout.write('Creating grabbo_job table...')
                cursor.execute('''
                CREATE TABLE "grabbo_job" (
                    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                    "board" integer NOT NULL,
                    "original_id" varchar(256) NOT NULL,
                    "title" varchar(256) NOT NULL,
                    "url" varchar(256) NOT NULL,
                    "seniority" varchar(256) NOT NULL,
                    "salary_text" varchar(256) NOT NULL,
                    "status" integer NOT NULL,
                    "created_at" datetime NOT NULL,
                    "lena_comparibility" real NOT NULL,
                    "company_id" integer,
                    "description" text NOT NULL,
                    "requirements" text NOT NULL,
                    "responsibilities" text NOT NULL,
                    "category_id" integer,
                    "salary_id" integer,
                    "technology_id" integer,
                    FOREIGN KEY ("company_id") REFERENCES "grabbo_company" ("id"),
                    FOREIGN KEY ("category_id") REFERENCES "grabbo_category" ("id"),
                    FOREIGN KEY ("salary_id") REFERENCES "grabbo_salary" ("id"),
                    FOREIGN KEY ("technology_id") REFERENCES "grabbo_technology" ("id")
                );
                ''')

        self.stdout.write(self.style.SUCCESS('Local database setup completed successfully.'))