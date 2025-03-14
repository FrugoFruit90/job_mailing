# Generated by Django 4.2.2 on 2025-03-02 09:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'db_table': 'grabbo_category',
            },
        ),
        migrations.CreateModel(
            name='Company',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('industry', models.CharField(blank=True, max_length=255)),
                ('size_from', models.IntegerField(default=0)),
                ('size_to', models.IntegerField(default=0)),
                ('url', models.CharField(blank=True, max_length=1024)),
                ('status', models.IntegerField(choices=[(0, 'Unknown'), (1, 'Fuck It'), (2, 'Interested'), (3, 'Hyped')], default=0)),
            ],
            options={
                'db_table': 'grabbo_company',
            },
        ),
        migrations.CreateModel(
            name='Salary',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'db_table': 'grabbo_salary',
            },
        ),
        migrations.CreateModel(
            name='Technology',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'db_table': 'grabbo_technology',
            },
        ),
        migrations.CreateModel(
            name='Job',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('board', models.IntegerField(choices=[(1, 'No Fluff'), (2, 'Just Join It'), (3, 'Pracuj')])),
                ('original_id', models.CharField(max_length=256)),
                ('title', models.CharField(max_length=256)),
                ('url', models.CharField(max_length=256)),
                ('description', models.TextField()),
                ('requirements', models.TextField()),
                ('responsibilities', models.TextField()),
                ('seniority', models.CharField(max_length=256)),
                ('salary_text', models.CharField(max_length=256)),
                ('status', models.IntegerField(choices=[(0, 'Unknown'), (1, 'Fuck It'), (2, 'Interested'), (3, 'Hyped')], default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('lena_comparibility', models.FloatField(default=0.0)),
                ('category', models.ForeignKey(db_column='category_id', null=True, on_delete=django.db.models.deletion.SET_NULL, to='scraper.category')),
                ('company', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='scraper.company')),
                ('salary', models.ForeignKey(db_column='salary_id', null=True, on_delete=django.db.models.deletion.SET_NULL, to='scraper.salary')),
                ('technology', models.ForeignKey(db_column='technology_id', null=True, on_delete=django.db.models.deletion.SET_NULL, to='scraper.technology')),
            ],
            options={
                'db_table': 'grabbo_job',
            },
        ),
    ]
