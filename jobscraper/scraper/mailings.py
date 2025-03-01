from django.core.mail import EmailMessage
import os
import logging

logger = logging.getLogger(__name__)


def send_mail_with_offers(offers: list, is_test=False):
    """
    Send an email with job offers.

    Args:
        offers (list): List of job offers (dicts with title, company__name, url)
        is_test (bool): Whether this is a test email
    """
    if not offers:
        logger.warning("No offers to send. Skipping email.")
        return

    # Create email subject
    if is_test:
        subject = '[TEST] Job Scraper - New Job Offers'
    else:
        subject = f'Job Scraper - {len(offers)} New Job Offers'

    # Build email content
    content = '<h2>New Job Offers:</h2><br>'
    for offer in offers:
        company = offer.get('company__name', offer.get('company', 'Unknown Company'))
        title = offer.get('title', 'Untitled Job')
        url = offer.get('url', '#')
        content += f'<a href="{url}">{title} at {company}</a><br>'

    if is_test:
        content = '<p><strong>This is a test email from Job Scraper</strong></p>' + content


    recipients = os.environ.get('EMAIL_RECIPIENTS', '').split(',')
    if not recipients or recipients[0] == '':
        logger.error("No email recipients specified. Set EMAIL_RECIPIENTS environment variable.")
        return

    # Log what we're about to do
    logger.info(f"Sending email with {len(offers)} job offers to {', '.join(recipients)}")

    # Create and send email
    msg = EmailMessage(
        subject,
        body=content,
        to=recipients
    )
    msg.content_subtype = 'html'
    msg.send()

    logger.info(f"Email sent successfully to {', '.join(recipients)}")