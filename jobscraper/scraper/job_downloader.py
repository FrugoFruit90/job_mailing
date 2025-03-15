import logging
import random
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from scraper.models import Company, Job

logger = logging.getLogger(__name__)


class PracujDownloader:
    def __init__(self):
        self.driver = None

    def _setup_driver(self):
        """Set up and configure Selenium WebDriver"""
        options = Options()
        options.add_argument("--headless")  # Run in headless mode
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")  # Hide automation

        # Add a realistic user agent
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36")

        # Create a new WebDriver
        self.driver = webdriver.Chrome(options=options)
        self.driver.set_window_size(1920, 1080)  # Set a standard window size

    def _close_driver(self):
        """Close the WebDriver if it exists"""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def download_jobs(self, filter_url, max_pages=None):
        """
        Download jobs from pracuj.pl based on the filter URL using Selenium.

        Args:
            filter_url (str): The URL with job search filters
            max_pages (int, optional): Maximum number of pages to scrape. If None, scrape all pages.

        Returns:
            int: Number of jobs added to the database
        """
        try:
            self._setup_driver()
            page_number = 1
            jobs_added = 0

            # Accept cookies once
            self._accept_cookies(filter_url)

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
                        # Load the page
                        self.driver.get(url)

                        # Wait for the job listings to load
                        wait = WebDriverWait(self.driver, 10)
                        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-test="section-offers"]')))

                        # Add random delay to mimic human behavior
                        time.sleep(random.uniform(2, 5))

                        # Scroll down the page slowly to load all content
                        self._scroll_page()

                        break  # Success, exit the retry loop
                    except (TimeoutException, WebDriverException) as e:
                        retry_count += 1
                        if retry_count < max_retries:
                            # Calculate wait time
                            wait_time = 2 ** retry_count + random.uniform(0, 1)
                            logger.warning(
                                f"Browser error: {e}. Retrying in {wait_time:.2f} seconds... (Attempt {retry_count}/{max_retries})"
                            )
                            time.sleep(wait_time)
                        else:
                            logger.error(f'Failed to get offers from pracuj after multiple attempts. Last error: {e}')
                            self._close_driver()
                            return jobs_added

                # Get page content and parse with BeautifulSoup
                page_source = self.driver.page_source
                soup = BeautifulSoup(page_source, features='html.parser')

                jobs = soup.find('div', {'data-test': 'section-offers'})
                if not jobs or not jobs.children:
                    logger.info("No more job listings found on the page. Stopping.")
                    break

                page_jobs_count = 0
                for job in jobs:
                    if hasattr(job, 'children'):
                        try:
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
                        except (IndexError, AttributeError) as e:
                            logger.error(f"Error processing job listing: {e}")

                logger.info(f"Added {page_jobs_count} jobs from page {page_number}")

                if page_jobs_count == 0:
                    # If we didn't add any jobs on this page, it might mean we've already
                    # scraped all new jobs, so we can stop
                    logger.info("No new jobs found on this page. Stopping.")
                    break

                page_number += 1

                # Add a random delay between pages to mimic human behavior
                time.sleep(random.uniform(3, 7))

            logger.info(f"Total jobs added: {jobs_added}")
            return jobs_added

        finally:
            # Make sure we always close the driver
            self._close_driver()

    def _accept_cookies(self, url):
        """Accept cookies dialog if it appears"""
        try:
            self.driver.get(url)

            # Wait up to 5 seconds for the cookie dialog to appear
            wait = WebDriverWait(self.driver, 5)
            cookie_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-test="button-submitCookie"]')))
            cookie_button.click()
            logger.info("Accepted cookies")

            # Wait a moment for the page to process the cookie acceptance
            time.sleep(1)
        except TimeoutException:
            # Cookie dialog might not appear if cookies already accepted
            logger.info("No cookie dialog found or already accepted")
            pass

    def _scroll_page(self):
        """Scroll down the page slowly to load all content"""
        # Get scroll height
        last_height = self.driver.execute_script("return document.body.scrollHeight")

        while True:
            # Scroll down in smaller steps to appear more human-like
            for i in range(3):
                scroll_amount = random.uniform(800, 1200)
                self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                time.sleep(random.uniform(0.5, 1.5))

            # Wait for potential new content to load
            time.sleep(random.uniform(1, 2))

            # Calculate new scroll height and compare with last scroll height
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

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