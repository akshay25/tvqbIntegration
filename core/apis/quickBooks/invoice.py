import requests
from django.conf import settings
from core.apis.quickBooks.authentication import get_access_token


def createInvoice(data):
    access_token = get_access_token()
    url = _get_url()
    headers = _get_headers(access_token)
    r = requests.post(url = url, json = data, headers = headers)
    if r.status_code == 200:
        return r.json()
    else:
        print('failed invoice creation', data, r.json(), r.status_code)
        pass

def updateInvoice(data, is_sparse=False, retry_count = 3):
    invoice_id = data['Id']
    invoice = readInvoice(invoice_id)
    if invoice == None:
        if retry_count >= 0:
            updateInvoice(data, is_sparse, retry_count-1)
        else:
            print('log unable to fetch invoice')
            return
    access_token = get_access_token()
    url = _get_url()
    headers = _get_headers(access_token)
    data['sparse'] = is_sparse
    data['SyncToken'] = invoice['Invoice']['SyncToken']
    r = requests.post(url = url, json = data, headers = headers)
    if r.status_code == 200:
        return r.json()
    elif r.status_code == 5010:
        print(r.content)
        if retry_count > 0:
            print('failed update invoice due to sync token', data, retry_count)
            return updateInvoice(data, is_sparse, retry_count-1)
        else:
            print('failed update invoice due to sync token', data, retry_count)
    else:
        print('failed update invoice', data, r.json(), r.status_code)
        pass

def readInvoice(invoice_id):
    access_token = get_access_token()
    url = _get_url() + '/' + invoice_id + '?minorversion=51'
    headers = _get_headers(access_token)
    r = requests.get(url = url, headers = headers)
    if r.status_code == 200:
        return r.json()
    else:
        print('log read invoice API failed', invoice_id)
        return {'error': "Not found"}

def deleteInvoice(invoice_id):
    invoice = readInvoice(invoice_id)
    if invoice == None:
        print('log unable to fetch invoice', invoice_id)
        return
    access_token = get_access_token()
    url = _get_url() + '/' + invoice_id + '?operation=delete'
    data = {'Id': invoice_id, 'SyncToken': invoice['Invoice']['SyncToken']}
    headers = _get_headers(access_token)
    r = requests.post(url = url, json = data,headers = headers)
    if r.status_code == 200:
       return
    else:
       print('log delete invoice API failed', invoice_id, r.json(), r.status_code)
       return {'error': "Not found"}

def _get_url():
    realm_id = settings.QBO_COMPANY_ID
    route = '{0}/v3/company/{1}/invoice'.format(settings.QBO_BASE_URL, realm_id)
    return route

def _get_headers(access_token):
    auth_header = 'Bearer {0}'.format(access_token)
    headers = {
        'Authorization': auth_header,
        'Accept': 'application/json'
    }
    return headers


