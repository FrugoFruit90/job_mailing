# jobscraper/scraper/migrations/0002_create_tables_if_needed.py
from django.db import migrations, models
import django.db.models.deletion


def forwards_func(apps, schema_editor):
    """
    Check if the tables exist. If not, create them.
    This will run only on SQLite, as PostgreSQL should already have the tables.
    """
    if schema_editor.connection.vendor != 'sqlite':
        # Skip this migration for PostgreSQL
        return

    # Create Company table if it doesn't exist
    schema_editor.execute("""
    CREATE TABLE IF NOT EXISTS grabbo_company (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(255) NOT NULL,
        industry VARCHAR(255) DEFAULT '',
        size_from INTEGER DEFAULT 0,
        size_to INTEGER DEFAULT 0,
        url VARCHAR(1024) DEFAULT '',
        status INTEGER DEFAULT 0
    )
    """)

    # Create Category, Salary, and Technology tables if they don't exist
    schema_editor.execute("""
    CREATE TABLE IF NOT EXISTS grabbo_category (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(255) NOT NULL
    )
    """)

    schema_editor.execute("""
    CREATE TABLE IF NOT EXISTS grabbo_salary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_amount DECIMAL(10, 2),
        to_amount DECIMAL(10, 2),
        currency VARCHAR(10)
    )
    """)

    schema_editor.execute("""
    CREATE TABLE IF NOT EXISTS grabbo_technology (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(255) NOT NULL
    )
    """)

    # Create Job table if it doesn't exist
    schema_editor.execute("""
    CREATE TABLE IF NOT EXISTS grabbo_job (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        board INTEGER NOT NULL,
        original_id VARCHAR(256) NOT NULL,
        title VARCHAR(256) NOT NULL,
        url VARCHAR(256) NOT NULL,
        description TEXT DEFAULT '',
        requirements TEXT DEFAULT '',
        responsibilities TEXT DEFAULT '',
        seniority VARCHAR(256) DEFAULT '',
        salary_text VARCHAR(256) DEFAULT '',
        status INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        lena_comparibility FLOAT DEFAULT 0.0,
        company_id INTEGER,
        category_id INTEGER,
        salary_id INTEGER,
        technology_id INTEGER,
        FOREIGN KEY (company_id) REFERENCES grabbo_company (id) ON DELETE SET NULL,
        FOREIGN KEY (category_id) REFERENCES grabbo_category (id) ON DELETE SET NULL,
        FOREIGN KEY (salary_id) REFERENCES grabbo_salary (id) ON DELETE SET NULL,
        FOREIGN KEY (technology_id) REFERENCES grabbo_technology (id) ON DELETE SET NULL
    )
    """)


class Migration(migrations.Migration):
    dependencies = [
        ('scraper', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(forwards_func),
    ]