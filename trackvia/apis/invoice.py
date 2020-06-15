from trackvia.apis.authentication import get_access_token
from django.conf import settings
import requests

def updateInvoice(data):
    pass

def readInvoice(invoice_id):
    #view_id = 4118
    #view_id = 4029
    #url = settings.TRACKVIA_BASE_URL + 'openapi/views/{0}/records/{1}'.format(view_id, invoice_id)
    #params = {
    #    'access_token': get_access_token(),
    #    'user_key': settings.TRACKVIA_USER_KEY
    #}
    #r = requests.get(url = url, params = params)
    #if r.status_code == 200:
    #    return r.json()

def getInvoiceItems(record_id:
    url = "https://go.trackvia.com/accounts/21782/apps/49/tables/724/records/filter?start=0&max=50&orderFields=253048,253044&ascending=false,true&query=&viewId=4029"
    body = {"operator":"AND","negated":False,"displayOrder":0,"fieldFilters":[{"fieldMetaId":18714,"relationshipId":4460,"value": record_id,"operator":"=","negated":False,"displayOrder":1}]}
    params = {
        'access_token': get_access_token(),
        'user_key': settings.TRACKVIA_USER_KEY
    }
    r = requests.post(url = url, params = params, json= body)
    if r.status_code == 200:
        return r.json()


