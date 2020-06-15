#from django.shortcuts import render
from __future__ import absolute_import

from requests import HTTPError
import json

from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseServerError,JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from quickBooks.tasks import process_webhook_data
from quickBooks.apis.invoice import createInvoice, updateInvoice, readInvoice

@csrf_exempt
def webhook(request):
    if request.method == 'POST':
        body_unicode = request.body.decode('utf-8')
        signature = request.headers.get('Intuit-Signature')
        verifier_token = settings.QBO_VERIFIER_TOKEN
        process_webhook_data.delay(signature, body_unicode, verifier_token)
        return HttpResponse("Hello, world. You're at the quickbooks webhook.")
