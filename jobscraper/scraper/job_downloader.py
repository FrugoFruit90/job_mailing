import logging
import random
import time
import asyncio
from asyncio import Future
from concurrent.futures import ThreadPoolExecutor
import gc
import sys

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Error as PlaywrightError

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

        # Maximum pages to process before restarting browser
        # Setting to a very small number to ensure browser gets restarted frequently
        pages_per_browser = 2

        # Keep track of browser restarts to prevent infinite loops
        browser_restart_count = 0
        max_browser_restarts = 5

        while True:
            # Exit if we've restarted the browser too many times
            if browser_restart_count >= max_browser_restarts:
                logger.error(f"Too many browser restarts ({browser_restart_count}). Stopping.")
                break

            # Check if we've reached the maximum number of pages to scrape
            if max_pages and page_number > max_pages:
                logger.info(f"Reached max pages limit ({max_pages}). Stopping.")
                break

            try:
                # Process a batch of pages with a fresh browser instance
                logger.info(f"Starting new browser instance (restart #{browser_restart_count})")
                result, failed_page_offset = await self._process_batch(
                    filter_url,
                    start_page=page_number,
                    max_pages=pages_per_browser if not max_pages else min(pages_per_browser,
                                                                          max_pages - page_number + 1)
                )

                if result < 0:
                    # Negative return indicates an error, retry with a fresh browser
                    logger.warning(f"Browser error detected on page offset {failed_page_offset}. Restarting browser.")
                    browser_restart_count += 1
                    # Adjust page_number to retry from the failed page
                    page_number = page_number + failed_page_offset
                    continue

                # Update counters
                jobs_added += result
                page_number += pages_per_browser

                # Force garbage collection between batches
                gc.collect()

                # Reset restart counter on successful batch
                browser_restart_count = 0

            except Exception as e:
                logger.error(f"Fatal error during job processing: {e}")
                browser_restart_count += 1
                # Sleep a bit before retrying to avoid hammering the server
                await asyncio.sleep(5)

        logger.info(f"Total jobs added: {jobs_added}")
        return jobs_added

    async def _process_batch(self, filter_url, start_page, max_pages):
        """Process a batch of pages with a fresh browser instance"""
        batch_jobs_added = 0

        try:
            async with async_playwright() as p:
                # Launch browser with minimal memory usage settings
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-gpu',
                        '--disable-dev-shm-usage',
                        '--disable-setuid-sandbox',
                        '--no-sandbox',
                        '--single-process',
                        '--disable-extensions',
                        '--js-flags=--max-old-space-size=128'
                    ]
                )

                try:
                    # Process each page in the batch
                    for page_offset in range(max_pages):
                        current_page = start_page + page_offset
                        url = f'{filter_url}&pn={current_page}'
                        logger.info(f"Scraping page {current_page}: {url}")

                        # Create a new context for this page
                        try:
                            context = await browser.new_context(
                                viewport={'width': 1280, 'height': 800},
                                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'
                            )
                        except PlaywrightError as e:
                            logger.error(f"Failed to create browser context: {e}")
                            return -1, page_offset  # Return failed page offset

                        try:
                            # Process the page
                            page_jobs = await self._process_single_page(context, url, is_first_page=(current_page == 1))

                            if page_jobs < 0:
                                # Error in page processing
                                await context.close()
                                return -1, page_offset  # Signal an error with page offset

                            batch_jobs_added += page_jobs

                            # If no jobs found on this page, stop processing this batch
                            if page_jobs == 0:
                                await context.close()
                                break

                        except Exception as e:
                            logger.error(f"Error processing page {current_page}: {e}")
                            try:
                                await context.close()
                            except:
                                pass
                            return -1, page_offset  # Signal an error with page offset
                        finally:
                            # Always try to close the context
                            try:
                                await context.close()
                            except:
                                pass

                        # Brief pause between pages
                        await asyncio.sleep(random.uniform(1, 2))

                    return batch_jobs_added, -1  # Success, no page failure

                finally:
                    # Always close the browser
                    try:
                        await browser.close()
                    except:
                        pass

        except Exception as e:
            logger.error(f"Error initializing Playwright: {e}")
            return -1, 0  # First page failed

    async def _process_single_page(self, context, url, is_first_page=False):
        """Process a single page and extract jobs"""
        jobs_added = 0
        max_retries = 2

        for retry in range(max_retries):
            try:
                # Create a new page
                page = await context.new_page()

                try:
                    # Navigate to the page
                    if is_first_page:
                        # Accept cookies on the first page
                        await self._accept_cookies(page, url)
                    else:
                        await page.goto(url, wait_until='domcontentloaded', timeout=20000)
                        await page.wait_for_selector('div[data-test="section-offers"]', timeout=10000)

                    # Short delay
                    await asyncio.sleep(1)

                    # Minimal scrolling to save memory
                    await page.evaluate('window.scrollBy(0, 800)')

                    # Get content
                    content = await page.content()

                    # Process page content
                    jobs_added = await self._process_page_content(content)
                    return jobs_added

                except PlaywrightError as e:
                    if retry < max_retries - 1:
                        logger.warning(f"Playwright error on retry {retry}: {e}")
                        await asyncio.sleep(2)
                    else:
                        logger.error(f"Failed after {max_retries} retries: {e}")
                        return -1
                finally:
                    # Always close the page
                    try:
                        await page.close()
                    except:
                        pass

            except PlaywrightError as e:
                logger.error(f"Failed to create page: {e}")
                return -1

        return jobs_added

    async def _process_page_content(self, content):
        """Process page content in a memory-efficient way"""
        # Use the default HTML parser since lxml might not be available
        soup = BeautifulSoup(content, 'html.parser')

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

                        # Create a local function to avoid lambda issues
                        def check_job_exists(jid):
                            return Job.objects.filter(original_id=jid).exists()

                        # Check if job exists
                        job_exists_future = self._run_in_thread(
                            executor,
                            lambda: check_job_exists(job_id)
                        )

                        try:
                            job_exists = await job_exists_future
                        except Exception as e:
                            logger.error(f"Error checking if job exists: {e}")
                            continue

                        if job_exists:
                            logger.debug(f"Job {job_id} already exists in database. Skipping.")
                            continue

                        # Local function to add job
                        def add_job(jdata, jid):
                            return self._add_job_quick(jdata, jid)

                        # Process the job
                        job_added_future = self._run_in_thread(
                            executor,
                            lambda: add_job(job_data, job_id)
                        )

                        try:
                            job_added = await job_added_future
                            if job_added:
                                jobs_added += 1
                        except Exception as e:
                            logger.error(f"Error adding job: {e}")

                    except Exception as ex:
                        logger.error(f'Error while processing job: {ex}')

        # Clear variables to help garbage collection
        soup = None
        jobs_section = None
        content = None

        return jobs_added

    def _run_in_thread(self, executor, func):
        """Run a synchronous function in a thread and return a Future."""
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(executor, func)

    async def _accept_cookies(self, page, url):
        """Accept cookies dialog if it appears"""
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=20000)

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