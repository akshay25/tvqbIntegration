from django.conf import settings
import requests

from core.logger import logger
from core.apis.trackvia.authentication import get_access_token

def updateTvInvoiceStatus(invoice_id, status, view_id):
    #if not view_id:
    view_id = '4027'
    url = 'https://go.trackvia.com/accounts/21782/apps/49/tables/740/records/{0}?formId=5429&viewId={1}'.format(invoice_id, view_id)
    params = {
        'access_token': get_access_token(),
        'user_key': settings.TRACKVIA_USER_KEY
    }
    body = {
            'id': invoice_id,
            'data': [
                {'fieldMetaId': 21443, 'id': 279131, 'type': 'dropDown', 'value': status}
                ]
            }
    resp = requests.put(url = url, params = params, json = body)
    if resp.status_code != 200:
        logger.error('payment status not updated for invoice {0} | {1} | {2}'.format(invoice_id, resp.json(), resp.status_code))

def getFullInvoiceData(invoice_id, view_id):
    invoice_data = getInvoiceData(invoice_id, view_id)
    invoice_item_data = getInvoiceItems(invoice_id)

    return {
            'invoice_data': invoice_data,
            'invoice_items': invoice_item_data
            }

def getInvoiceData(invoice_id, view_id):
    #if not view_id:
    view_id = '4027'
    url = "https://go.trackvia.com/accounts/21782/apps/49/tables/740/records/{0}?viewId={1}&formId=5429".format(
        invoice_id, view_id)
    params = {
        'access_token': get_access_token(),
        'user_key': settings.TRACKVIA_USER_KEY
    }
    r = requests.get(url = url, params = params)
    if r.status_code != 200:
        # log
        pass
    mapper = {
            19117: 'INVOICE ID',
            18705: 'INVOICE DATE',
            18716: 'STATUS',
            18719: 'DELIVERY DETAILS',
            18720: 'PROJECT',
            18723: 'DUE DATE',
            18717: 'SALES ORDER',
            18314: 'CONTRACTOR',
            19497: 'CONTRACTOR EMAIL',
            16412: 'MARGIN %',
            16410: 'FREIGHT %',
            18316: 'PROCUREMENT MANAGER',
            21131: 'WAREHOUSING %',
            21440: 'NOTES',
            19545: 'INV SALES TAX',
            19546: 'INV FREIGHT',
            21130: 'INV WAREHOUSING',
            18042: 'PAYMENT TERMS',
            23350: 'SALE TAX'
            }
    ref_field_set = set([18720, 18717, 18314, 18042, 23350])
    data = r.json()['data']
    invoice = {}
    for field in data:
        if 'fieldMetaId' not in field or field['fieldMetaId'] not in mapper:
            continue
        key = mapper[field['fieldMetaId']]
        value = field['value'] if 'value' in field else ''
        if 'value' in field:
            if field['fieldMetaId'] in ref_field_set:
                value = field['identifier'] if 'identifier' in field else ''
            else:
                value =  field['value'] if 'value' in field else ''
        else:
            value = ''
        invoice[key] = value
    if 'PAYMENT TERMS' not in invoice or invoice['PAYMENT TERMS'] == '':
        invoice['PAYMENT TERMS'] = 'NET 30'
    invoice['tv_id'] = invoice_id
    return invoice

def getInvoiceItems(record_id):
    url = "https://go.trackvia.com/accounts/21782/apps/49/tables/724/records/filter?start=0&max=50&orderFields=253048,253044&ascending=false,true&query=&viewId=4029"
    body = {"operator":"AND","negated":False,"displayOrder":0,"fieldFilters":[{"fieldMetaId":18714,"relationshipId":4460,"value": record_id,"operator":"=","negated":False,"displayOrder":1}]}
    params = {
        'access_token': get_access_token(),
        'user_key': settings.TRACKVIA_USER_KEY
    }
    r = requests.post(url = url, params = params, json= body)
    if r.status_code != 200:
        #log
        pass
    response = r.json()
    return _invoiceItemsFormatter(response['records'])

def _invoiceItemsFormatter(response):
    mapper = {
            21100: 'Manufacturer',
            21103: 'Catalog',
            21369: 'Quantity',
            21102: 'Type',
            21106: 'Description',
            18536: 'Unit CN',
            18539: 'Total CN'
            }
    result = []
    for row in response:
        item = {}
        rowData = row['data']
        for field in rowData:
            if 'fieldMetaId' not in field or field['fieldMetaId'] not in mapper:
                continue
            key = mapper[field['fieldMetaId']]
            value = field['value'] if 'value' in field else ''
            item[key] = value
        result.append(item)
    return result



