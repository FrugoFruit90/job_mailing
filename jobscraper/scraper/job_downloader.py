import logging
from bs4 import BeautifulSoup
import requests

from scraper.models import Company, Job

logger = logging.getLogger(__name__)


class PracujDownloader:
    def download_jobs(self, filter_url):
        page_number = 1
        while True:
            url = f'{filter_url}&pn={page_number}'
            response = requests.get(url, timeout=10)
            try:
                response.raise_for_status()
            except requests.HTTPError:
                logger.error('Could not get offers from pracuj.')
                return

            soup = BeautifulSoup(response.content, features='html.parser')
            jobs = soup.find('div', {'data-test': 'section-offers'})
            if not jobs:
                break

            for job in jobs:
                job_data = list(job.children)[0]
                job_id = job_data.attrs.get('data-test-offerid')
                if not job_id:
                    logger.error('Found job without id! Skipping.')
                    continue
                if Job.objects.filter(original_id=job_id).exists():
                    continue
                try:
                    self._add_job_quick(job_data, job_id)
                except Exception as ex:
                    logger.error('Error while adding job %s, %s', job_id, ex)

            page_number += 1

    def _add_job_quick(self, job_data, job_id):
        job_url = f'https://www.pracuj.pl/praca/,oferta,{job_id}'
        salary = job_data.find('span', attrs={'data-test': 'offer-salary'})
        salary = salary.text if salary else ''
        seniority = job_data.find('div', attrs={'data-test': 'section-company'}).next_sibling.find('li').text
        company = self._add_or_update_company(job_data)
        title = job_data.find('h2', attrs={'data-test': 'offer-title'}).text

        Job.objects.create(
            original_id=job_id,
            board='pracuj',
            salary_text=salary,
            company=company,
            seniority=seniority.lower(),
            title=title,
            url=job_url,
        )

    def _add_or_update_company(self, job_data):
        company = job_data.find('h3')
        company_url = company.parent.attrs.get('href')
        return Company.objects.update_or_create(
            name=company.text.lower().replace('sp. z o.o.', ''),
            defaults={
                'url': company_url,
                'size_from': 0,
                'size_to': 0,
            }
        )[0]