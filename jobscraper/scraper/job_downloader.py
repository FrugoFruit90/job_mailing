import logging
import random
import time

from bs4 import BeautifulSoup
import requests

from scraper.models import Company, Job

logger = logging.getLogger(__name__)


class PracujDownloader:
    def download_jobs(self, filter_url, max_pages=None):
        """
        Download jobs from pracuj.pl based on the filter URL.

        Args:
            filter_url (str): The URL with job search filters
            max_pages (int, optional): Maximum number of pages to scrape. If None, scrape all pages.

        Returns:
            int: Number of jobs added to the database
        """
        page_number = 1
        jobs_added = 0

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
            # Check if we've reached the maximum number of pages to scrape
            if max_pages and page_number > max_pages:
                logger.info(f"Reached max pages limit ({max_pages}). Stopping.")
                break

            url = f'{filter_url}&pn={page_number}'
            logger.info(f"Scraping page {page_number}: {url}")

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
                        # Calculate wait time first
                        wait_time = 2 ** retry_count + random.uniform(0, 1)
                        logger.warning(
                            f"HTTP error {e.response.status_code}: {e}. Retrying in {wait_time:.2f} seconds... (Attempt {retry_count}/{max_retries})"
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(f'Failed to get offers from pracuj after multiple attempts. Last error: {e}')
                        return jobs_added
                except requests.RequestException as e:
                    # This will catch connection errors, timeouts, etc.
                    retry_count += 1
                    if retry_count < max_retries:
                        # Calculate wait time first
                        wait_time = 2 ** retry_count + random.uniform(0, 1)
                        logger.warning(
                            f"Request error: {e}. Retrying in {wait_time:.2f} seconds... (Attempt {retry_count}/{max_retries})"
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(f'Failed to connect to pracuj after multiple attempts. Last error: {e}')
                        return jobs_added

            soup = BeautifulSoup(response.content, features='html.parser')
            jobs = soup.find('div', {'data-test': 'section-offers'})
            if not jobs:
                logger.info("No more job listings found on the page. Stopping.")
                break

            page_jobs_count = 0
            for job in jobs:
                job_data = list(job.children)[0]
                job_id = job_data.attrs.get('data-test-offerid')
                if not job_id:
                    logger.error('Found job without id! Skipping.')
                    continue
                if Job.objects.filter(original_id=job_id).exists():
                    logger.debug(f"Job {job_id} already exists in database. Skipping.")
                    continue

                try:
                    self._add_job_quick(job_data, job_id)
                    jobs_added += 1
                    page_jobs_count += 1
                except Exception as ex:
                    logger.error('Error while adding job %s, %s', job_id, ex)

            logger.info(f"Added {page_jobs_count} jobs from page {page_number}")

            if page_jobs_count == 0:
                # If we didn't add any jobs on this page, it might mean we've already
                # scraped all new jobs, so we can stop
                logger.info("No new jobs found on this page. Stopping.")
                break

            page_number += 1

            # Add a small delay between pages to be nice to the server
            time.sleep(random.uniform(1, 3))

        logger.info(f"Total jobs added: {jobs_added}")
        return jobs_added

    def _add_job_quick(self, job_data, job_id):
        job_url = f'https://www.pracuj.pl/praca/,oferta,{job_id}'
        salary = job_data.find('span', attrs={'data-test': 'offer-salary'})
        salary = salary.text if salary else ''

        # Get seniority level - handle potential structure changes
        section_company = job_data.find('div', attrs={'data-test': 'section-company'})
        if section_company and section_company.next_sibling and section_company.next_sibling.find('li'):
            seniority = section_company.next_sibling.find('li').text
        else:
            seniority = ''

        company = self._add_or_update_company(job_data)
        title = job_data.find('h2', attrs={'data-test': 'offer-title'}).text

        Job.objects.create(
            original_id=job_id,
            board=3,  # Pracuj
            salary_text=salary,
            company=company,
            seniority=seniority.lower(),
            title=title,
            url=job_url,
            description='',  # These fields are required but we're not fetching the details
            requirements='',
            responsibilities='',
        )

    def _add_or_update_company(self, job_data):
        company = job_data.find('h3')
        if not company:
            logger.warning("Company name not found in job data")
            company_name = "Unknown"
            company_url = ""
        else:
            company_url = company.parent.attrs.get('href') or ''
            company_name = company.text.lower()

        # Use the manager to properly handle company matching
        return Company.objects.create_or_update_if_better(
            name=company_name,
            url=company_url,
            size_from=0,
            size_to=0,
        )