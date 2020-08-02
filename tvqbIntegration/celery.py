# http://docs.celeryproject.org/en/latest/django/first-steps-with-django.html
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tvqbIntegration.settings')

import django
django.setup()

pfiles = ['core.tasks']

app = Celery('tvqbIntegration')
app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks(pfiles, force=True)
