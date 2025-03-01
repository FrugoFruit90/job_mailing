import logging
import random
import time

from bs4 import BeautifulSoup
import requests

from scraper.models import Company, Job

logger = logging.getLogger(__name__)


class PracujDownloader:
    def download_jobs(self, filter_url):
        page_number = 1
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.pracuj.pl/',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        while True:
            url = f'{filter_url}&pn={page_number}'

            max_retries = 3
            retry_count = 0
            while retry_count < max_retries:
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    response.raise_for_status()
                    break  # Success, exit the loop
                except requests.HTTPError as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        # Exponential backoff
                        wait_time = 2 ** retry_count + random.uniform(0, 1)
                        logger.warning(
                            f"Request failed, retrying in {wait_time:.2f} seconds... (Attempt {retry_count}/{max_retries})")
                        time.sleep(wait_time)
                    else:
                        logger.error('Could not get offers from pracuj after multiple attempts.')
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
            board=3,
            salary_text=salary,
            company=company,
            seniority=seniority.lower(),
            title=title,
            url=job_url,
            description='',
            requirements='',
            responsibilities='',
        )

    def _add_or_update_company(self, job_data):
        company = job_data.find('h3')
        company_url = company.parent.attrs.get('href') or ''
        company_name = company.text.lower()
        
        # Use the manager to properly handle company matching
        return Company.objects.create_or_update_if_better(
            name=company_name,
            url=company_url,
            size_from=0,
            size_to=0,
        )
