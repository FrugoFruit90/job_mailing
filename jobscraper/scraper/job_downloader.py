import logging
import random
import time
import asyncio
from asyncio import Future
from concurrent.futures import ThreadPoolExecutor
import gc

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
        # Maximum pages to process per browser instance to avoid memory leaks
        pages_per_browser = 5
        current_browser_pages = 0

        async with async_playwright() as p:
            # Launch browser with minimal memory usage settings
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--disable-gpu',
                    '--disable-dev-shm-usage',
                    '--disable-setuid-sandbox',
                    '--no-sandbox',
                    '--single-process',  # Use single process to reduce memory
                    '--disable-extensions',
                    '--disable-features=site-per-process',  # Reduce process count
                    '--js-flags=--max-old-space-size=128'  # Limit JS memory
                ]
            )

            try:
                # Process pages until we're done or hit max_pages
                while True:
                    # Check if we need to restart the browser to clear memory
                    if current_browser_pages >= pages_per_browser:
                        logger.info(f"Restarting browser after {pages_per_browser} pages to clear memory")
                        await browser.close()
                        # Force garbage collection
                        gc.collect()
                        # Restart browser with same memory-saving settings
                        browser = await p.chromium.launch(
                            headless=True,
                            args=[
                                '--disable-gpu',
                                '--disable-dev-shm-usage',
                                '--disable-setuid-sandbox',
                                '--no-sandbox',
                                '--single-process',
                                '--disable-extensions',
                                '--disable-features=site-per-process',
                                '--js-flags=--max-old-space-size=128'
                            ]
                        )
                        current_browser_pages = 0

                    # Check if we've reached the maximum number of pages to scrape
                    if max_pages and page_number > max_pages:
                        logger.info(f"Reached max pages limit ({max_pages}). Stopping.")
                        break

                    url = f'{filter_url}&pn={page_number}'
                    logger.info(f"Scraping page {page_number}: {url}")

                    # Create a new context for each page to isolate memory
                    context = await browser.new_context(
                        viewport={'width': 1280, 'height': 800},
                        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'
                    )

                    # Set up a new page with limited permissions and features
                    page = await context.new_page()
                    await page.set_extra_http_headers({
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Referer': 'https://www.pracuj.pl/'
                    })

                    max_retries = 3
                    retry_count = 0
                    success = False
                    page_jobs_added = 0

                    # Try to navigate and process the page
                    while retry_count < max_retries and not success:
                        try:
                            # Accept cookies on first page only
                            if page_number == 1:
                                await self._accept_cookies(page, url)
                            else:
                                # For subsequent pages, just navigate
                                await page.goto(url, wait_until='domcontentloaded', timeout=30000)

                                # Wait for job listings with timeout
                                await page.wait_for_selector('div[data-test="section-offers"]', timeout=10000)

                            # Add short delay
                            await asyncio.sleep(random.uniform(1, 2))

                            # Scroll only halfway down the page to save memory
                            await self._scroll_page_partial(page)

                            # Get the HTML content in chunks and process immediately
                            content = await page.content()

                            # Process the content with BeautifulSoup using memory-efficient methods
                            page_jobs_added = await self._process_page_content(content)
                            jobs_added += page_jobs_added

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
                                # Close the context to free memory even if we failed
                                await context.close()
                                return jobs_added

                    # Close the context to release memory
                    await context.close()

                    # Update counters
                    current_browser_pages += 1
                    page_number += 1

                    logger.info(f"Added {page_jobs_added} jobs from page {page_number - 1}")

                    # Force garbage collection
                    gc.collect()

                    if page_jobs_added == 0:
                        # If we didn't add any jobs on this page, it might mean we've already
                        # scraped all new jobs, so we can stop
                        logger.info("No new jobs found on this page. Stopping.")
                        break

                    # Add a small delay between pages
                    await asyncio.sleep(random.uniform(1, 2))

                logger.info(f"Total jobs added: {jobs_added}")
                return jobs_added

            finally:
                # Make sure we close the browser to free resources
                await browser.close()

    async def _process_page_content(self, content):
        """Process page content in a memory-efficient way"""
        # Use lxml parser which is faster and more memory efficient
        soup = BeautifulSoup(content, 'lxml')

        # Find the job listings section
        jobs_section = soup.find('div', {'data-test': 'section-offers'})
        if not jobs_section or not jobs_section.children:
            return 0

        jobs_added = 0
        # Use small ThreadPoolExecutor with limited workers
        with ThreadPoolExecutor(max_workers=2) as executor:
            for job in jobs_section:
                if hasattr(job, 'children'):
                    try:
                        job_data = list(job.children)[0]
                        job_id = job_data.attrs.get('data-test-offerid')
                        if not job_id:
                            logger.error('Found job without id! Skipping.')
                            continue

                        # Check if job exists
                        job_exists_future = self._run_in_thread(
                            executor,
                            lambda: Job.objects.filter(original_id=job_id).exists()
                        )
                        job_exists = await job_exists_future

                        if job_exists:
                            logger.debug(f"Job {job_id} already exists in database. Skipping.")
                            continue

                        # Process the job
                        job_added_future = self._run_in_thread(
                            executor,
                            lambda job_data=job_data, job_id=job_id: self._add_job_quick(job_data, job_id)
                        )
                        await job_added_future

                        jobs_added += 1
                    except Exception as ex:
                        logger.error(f'Error while processing job: {ex}')

        # Clear variables to help garbage collection
        soup = None
        jobs_section = None
        content = None
        gc.collect()

        return jobs_added

    def _run_in_thread(self, executor, func):
        """Run a synchronous function in a thread and return a Future."""
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(executor, func)

    async def _accept_cookies(self, page, url):
        """Accept cookies dialog if it appears"""
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)

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

    async def _scroll_page_partial(self, page):
        """Scroll down the page partially to save memory"""
        # Only scroll halfway down to reduce memory usage
        await page.evaluate('window.scrollBy(0, 800)')
        await asyncio.sleep(0.5)
        await page.evaluate('window.scrollBy(0, 800)')
        await asyncio.sleep(0.5)

    def _add_job_quick(self, job_data, job_id):
        """Add a job to the database based on parsed job data"""
        job_url = f'https://www.pracuj.pl/praca/,oferta,{job_id}'

        try:
            salary = job_data.find('span', attrs={'data-test': 'offer-salary'})
            salary = salary.text if salary else ''

            # Get seniority level - handle potential structure changes
            section_company = job_data.find('div', attrs={'data-test': 'section-company'})
            if section_company and section_company.next_sibling and section_company.next_sibling.find('li'):
                seniority = section_company.next_sibling.find('li').text
            else:
                seniority = ''

            company = self._add_or_update_company(job_data)
            title_element = job_data.find('h2', attrs={'data-test': 'offer-title'})
            title = title_element.text if title_element else 'Unknown Position'

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
            return True
        except Exception as e:
            logger.error(f"Error adding job {job_id}: {e}")
            return False

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