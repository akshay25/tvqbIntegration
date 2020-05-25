#from django.shortcuts import render
from __future__ import absolute_import

from requests import HTTPError
import json

from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseServerError
from django.http import HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from quickBooks.tasks import process_webhook_data

@csrf_exempt
def webhook(request):
    if request.method == 'POST':
        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)
        signature = body['intuit-signature']
        process_webhook_data.delay(body)
        return HttpResponse("Hello, world. You're at the quickbooks webhook.")
