import logging
from django.core.paginator import Paginator
from django.utils import timezone

from scraper.job_downloader import PracujDownloader
from scraper.models import Job
from scraper.mailings import send_mail_with_offers

logger = logging.getLogger(__name__)


def download_and_send():
    """
    Download jobs from predefined URLs and send email with new offers.
    Returns a string with the result.
    """
    # URLs for job search
    urls = [
        'https://www.pracuj.pl/praca/warszawa;wp/ostatnich%203%20dni;p,3?rd=0&et=3%2C17%2C4&ao=false&tc=0&wm=hybrid%2Cfull-office',
        "https://www.pracuj.pl/praca/ostatnich%203%20dni;p,3/praca%20zdalna;wm,home-office?et=3%2C17%2C4&ao=false&tc=0"
    ]

    # Initialize counters
    total_jobs_added = 0

    # Download jobs from each URL
    downloader = PracujDownloader()
    for url in urls:
        logger.info(f"Downloading jobs from {url}")
        jobs_added = downloader.download_jobs(url)
        total_jobs_added += jobs_added
        logger.info(f"Added {jobs_added} jobs from {url}")

    logger.info(f"Total jobs added: {total_jobs_added}")

    # Filter jobs created today and exclude certain keywords
    excluded_terms = [
        'developer', 'programista', 'sprzedawca', 'handlowiec',
        'software developer', 'technik', 'kucharz', 'kelner',
        'księgowa', 'engineer', 'inżynier', 'sprzedaży',
        'instruktor', 'telemarketing', 'call center'
    ]

    # Start with jobs created today
    query = Job.objects.filter(created_at__date=timezone.now().date())

    # Exclude unwanted job titles
    for term in excluded_terms:
        query = query.exclude(title__icontains=term)

    new_offers = query.order_by('-created_at')

    logger.info(f"Found {new_offers.count()} new relevant job offers")

    # Send emails in batches to avoid huge emails
    if new_offers.exists():
        paginator = Paginator(new_offers, 100)
        for page in paginator.page_range:
            offers = paginator.page(page).object_list.values('title', 'company__name', 'url')
            logger.info(f"Sending email batch {page} with {len(offers)} offers")
            send_mail_with_offers(offers)
    else:
        logger.info("No new offers to send")

    return f"Success: Added {total_jobs_added} jobs, found {new_offers.count()} relevant offers"