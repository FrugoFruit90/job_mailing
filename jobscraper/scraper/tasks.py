from django.core.paginator import Paginator
from django.utils import timezone
from scraper.job_downloader import PracujDownloader
from scraper.models import Job
from scraper.mailings import send_mail_with_offers

def download_and_send():
    # URLs for job search
    urls = [
        'https://www.pracuj.pl/praca/warszawa;wp/ostatnich%203%20dni;p,3?rd=0&et=3%2C17%2C4&ao=false&tc=0&wm=hybrid%2Cfull-office',
        "https://www.pracuj.pl/praca/ostatnich%203%20dni;p,3/praca%20zdalna;wm,home-office?et=3%2C17%2C4&ao=false&tc=0"
    ]

    downloader = PracujDownloader()
    for url in urls:
        downloader.download_jobs(url)

    # Filter jobs created today and exclude certain keywords
    new_offers = (
        Job
        .objects
        .filter(created_at__date=timezone.now().date())
        .exclude(title__icontains='developer')
        .exclude(title__icontains='programista')
        .exclude(title__icontains='sprzedawca')
        .exclude(title__icontains='handlowiec')
        .exclude(title__icontains='software developer')
        .exclude(title__icontains='technik')
        .exclude(title__icontains='kucharz')
        .exclude(title__icontains='kelner')
        .exclude(title__icontains='księgowa')
        .exclude(title__icontains='engineer')
        .exclude(title__icontains='inżynier')
        .exclude(title__icontains='sprzedaży')
        .exclude(title__icontains='instruktor')
        .exclude(title__icontains='telemarketing')
        .exclude(title__icontains='call center')
    )

    # Send emails in batches to avoid huge emails
    paginator = Paginator(new_offers, 100)
    for page in paginator.page_range:
        offers = paginator.page(page).object_list.values('title', 'company__name', 'url')
        send_mail_with_offers(offers)

    return "Success"