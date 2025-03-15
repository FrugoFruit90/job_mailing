import logging
import random
import time
import asyncio
from asyncio import Future
from concurrent.futures import ThreadPoolExecutor

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from scraper.models import Company, Job

logger = logging.getLogger(__name__)


class PracujDownloader:
    def download_jobs(self, filter_url, max_pages=None):
        """
        Download jobs from pracuj.pl based on the filter URL using Playwright.

        Args:
            filter_url (str): The URL with job search filters
            max_pages (int, optional): Maximum number of pages to scrape. If None, scrape all pages.

        Returns:
            int: Number of jobs added to the database
        """
        # Create a new event loop to run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            return loop.run_until_complete(self._download_jobs_async(filter_url, max_pages))
        finally:
            loop.close()

    async def _download_jobs_async(self, filter_url, max_pages=None):
        """Async implementation of download_jobs using Playwright"""
        jobs_added = 0
        page_number = 1

        async with async_playwright() as p:
            # Launch browser - using Chromium which comes with Playwright
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # Set user agent to appear more like a regular browser
            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Referer': 'https://www.pracuj.pl/'
            })

            try:
                # Accept cookies first
                await self._accept_cookies(page, filter_url)

                while True:
                    # Check if we've reached the maximum number of pages to scrape
                    if max_pages and page_number > max_pages:
                        logger.info(f"Reached max pages limit ({max_pages}). Stopping.")
                        break

                    url = f'{filter_url}&pn={page_number}'
                    logger.info(f"Scraping page {page_number}: {url}")

                    max_retries = 3
                    retry_count = 0
                    success = False

                    while retry_count < max_retries and not success:
                        try:
                            # Navigate to the page
                            await page.goto(url, wait_until='networkidle')

                            # Wait for job listings to appear
                            await page.wait_for_selector('div[data-test="section-offers"]', timeout=10000)

                            # Add random delay to mimic human behavior
                            await asyncio.sleep(random.uniform(2, 5))

                            # Scroll down the page slowly to load all content
                            await self._scroll_page(page)

                            success = True
                        except Exception as e:
                            retry_count += 1
                            if retry_count < max_retries:
                                wait_time = 2 ** retry_count + random.uniform(0, 1)
                                logger.warning(
                                    f"Browser error: {e}. Retrying in {wait_time:.2f} seconds... (Attempt {retry_count}/{max_retries})"
                                )
                                await asyncio.sleep(wait_time)
                            else:
                                logger.error(
                                    f'Failed to get offers from pracuj after multiple attempts. Last error: {e}')
                                return jobs_added

                    # Get the HTML content and parse with BeautifulSoup
                    content = await page.content()
                    soup = BeautifulSoup(content, 'html.parser')

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

                                # This needs to be run in a thread because it's a sync operation
                                with ThreadPoolExecutor() as executor:
                                    # Create a future for checking if job exists
                                    job_exists_future = self._run_in_thread(
                                        executor,
                                        lambda: Job.objects.filter(original_id=job_id).exists()
                                    )
                                    job_exists = await job_exists_future

                                    if job_exists:
                                        logger.debug(f"Job {job_id} already exists in database. Skipping.")
                                        continue

                                    # Add the job (also in a thread)
                                    job_added_future = self._run_in_thread(
                                        executor,
                                        lambda: self._add_job_quick(job_data, job_id)
                                    )
                                    await job_added_future

                                    jobs_added += 1
                                    page_jobs_count += 1
                            except Exception as ex:
                                logger.error(f'Error while processing job: {ex}')

                    logger.info(f"Added {page_jobs_count} jobs from page {page_number}")

                    if page_jobs_count == 0:
                        # If we didn't add any jobs on this page, it might mean we've already
                        # scraped all new jobs, so we can stop
                        logger.info("No new jobs found on this page. Stopping.")
                        break

                    page_number += 1

                    # Add a random delay between pages to mimic human behavior
                    await asyncio.sleep(random.uniform(3, 7))

                logger.info(f"Total jobs added: {jobs_added}")
                return jobs_added

            finally:
                await browser.close()

    def _run_in_thread(self, executor, func):
        """Run a synchronous function in a thread and return a Future."""
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(executor, func)

    async def _accept_cookies(self, page, url):
        """Accept cookies dialog if it appears"""
        try:
            await page.goto(url, wait_until='domcontentloaded')

            # Wait up to 5 seconds for the cookie dialog and accept it
            try:
                cookie_button = await page.wait_for_selector(
                    'button[data-test="button-submitCookie"]',
                    timeout=5000
                )
                if cookie_button:
                    await cookie_button.click()
                    logger.info("Accepted cookies")

                    # Wait a moment for the page to process the cookie acceptance
                    await asyncio.sleep(1)
            except:
                # Cookie dialog might not appear if cookies already accepted
                logger.info("No cookie dialog found or already accepted")
                pass

        except Exception as e:
            logger.warning(f"Error during cookie acceptance: {e}")

    async def _scroll_page(self, page):
        """Scroll down the page slowly to load all content"""
        # Get current page height
        last_height = await page.evaluate('document.body.scrollHeight')

        while True:
            # Scroll down in smaller steps to appear more human-like
            for i in range(3):
                scroll_amount = random.uniform(800, 1200)
                await page.evaluate(f'window.scrollBy(0, {scroll_amount})')
                await asyncio.sleep(random.uniform(0.5, 1.5))

            # Wait for potential new content to load
            await asyncio.sleep(random.uniform(1, 2))

            # Calculate new scroll height and compare with last scroll height
            new_height = await page.evaluate('document.body.scrollHeight')
            if new_height == last_height:
                break
            last_height = new_height

    def _add_job_quick(self, job_data, job_id):
        """Add a job to the database based on parsed job data"""
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
        """Extract company info and create or update in database"""
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