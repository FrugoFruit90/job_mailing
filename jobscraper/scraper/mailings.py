from django.core.mail import EmailMessage
import os


def send_mail_with_offers(offers: list):
    content = '<br><h2>Nowe oferty:</h2><br>'
    for offer in offers:
        company = offer.get('company__name', offer.get('company'))
        content += f'<a href="{offer["url"]}">{offer["title"]} w {company}</a><br>'

    # Get email recipients from environment variable or use default
    recipients = os.environ.get('EMAIL_RECIPIENTS', 'your.email@example.com').split(',')

    msg = EmailMessage(
        'Found a lot of new offers',
        body=content,
        to=recipients
    )
    msg.content_subtype = 'html'
    msg.send()