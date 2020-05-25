import requests
from django.conf import settings
from quickBooks.apis.authentication import get_access_token


def createInvoice(data):
    access_token = get_access_token()
    url = _get_url()
    headers = _get_headers(access_token)
    r = requests.post(url = url, json = data, headers = headers)
    if r.status_code == 200:
        #log invoice created with id
        pass
    else:
        #log invoice creation failed
        pass

def updateInvoice(data, is_sparse=true, retry_count = 5):
    invoice_id = data['Id']
    invoice = readInvoice(invoice_id)
    if invoice == None:
        if retry_count >= 0:
            updateInvoice(data, is_sparse, retry_count-1)
        else:
            #log unable to fetch invoice
            return
    access_token = get_access_token()
    url = _get_url()
    headers = _get_headers(access_token)
    data['sparse'] = is_sparse
    data['SyncToken'] = invoice['Invoice']['SyncToken']
    r = requests.post(url = url, json = data, headers = headers)
    if r.status_code == 200:
        return r.json()
    else if r.status_code == 5010:
        if retry_count > 0:
            return updateInvoice(data, is_sparse, retry_count-1)
        else:
            #log retry count over
            pass
    else
        # log the failed API reason
        pass

def readInvoice(invoice_id):
    access_token = get_access_token()
    url = _get_url() + '/' + invoice_id
    headers = _get_headers(access_token)
    r = requests.get(url = url, headers = headers)
    if r.status_code == 200:
        return r.json()
    else:
        #log read invoice API failed
        pass

def _get_url():
    realm_id = settings.QBO_COMPANY_ID
    if settings.ENVIRONMENT == 'production':
        base_url = settings.QBO_BASE_PROD
    else:
        base_url =  settings.QBO_BASE_SANDBOX

    route = '/v3/company/{0}/invoice'.format(realm_id)
    return '{0}{1}'.format(base_url, route)

def _get_headers(access_token):
    auth_header = 'Bearer {0}'.format(access_token)
    headers = {
        'Authorization': auth_header,
        'Accept': 'application/json'
    }
    return headers


