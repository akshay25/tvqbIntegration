from __future__ import absolute_import
from django.shortcuts import render

from requests import HTTPError
import json

from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseServerError,JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from core.tasks import process_qb_webhook, process_tv_webhook
from core.apis.quickBooks.invoice import createInvoice, updateInvoice, readInvoice

@csrf_exempt
def qbwebhook(request):
	if request.method == 'POST':
		try:
			body_unicode = request.body.decode('utf-8')
			signature = request.headers.get('Intuit-Signature')
			verifier_token = settings.QBO_WEBHOOK_VERIFIER
			process_qb_webhook.delay(signature, body_unicode, verifier_token)
			return HttpResponse("Hello, world. You're at the quickbooks webhook.")
		except Exception as e:
			print('qbwebhook error') # TODO:get stacktrace log
			return HttpResponseBadRequest(e)


@csrf_exempt
def tvwebhook(request):
	if request.method == 'GET':
		try:
			table_id = request.GET.get('tableId')
			view_id = request.GET.get('viewId')
			record_id = request.GET.get('recordId')
			event_type = request.GET.get('eventType')
			process_tv_webhook.delay(table_id, view_id, record_id, event_type)
			return HttpResponse("Hello, world. You're at the trackvia integrations.")
		except Exception as e:
			print('tvwebhook error') # TODO:get stacktrace
			return HttpResponseBadRequest(e)