from django.core.mail import send_mail
from django.conf import settings

def send_email(subject, body):
	send_mail(
	    subject,
	    body,
	    settings.EMAIL_FROM,
	    settings.EMAIL_TO_LIST,
	    fail_silently=False,
	)