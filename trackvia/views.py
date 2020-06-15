#from django.shortcuts import render
from __future__ import absolute_import

from requests import HTTPError
import json

from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseServerError,JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def webhook(request):
    if request.method == 'GET':
        try:
            #TODO: handle webhook call and enqueue it to celery
            return HttpResponse("Hello, world. You're at the trackvia integrations.")
        except Exception as e:
            print(e)
            return HttpResponseBadRequest(e)


