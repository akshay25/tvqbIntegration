# coding=utf-8

from django.conf import settings
import requests

from core.logger import logger
from core.apis.trackvia.authentication import get_access_token


request_base_url = "https://go.trackvia.com/accounts/21782/apps/49/tables/740/records/{0}?viewId={1}&formId=5429"
invoice_item_url = "https://go.trackvia.com/accounts/21782/apps/49/tables/724/records/filter?" \
                   "start=0&max=50&orderFields=253048,302092,253044&ascending=false,true,true&query=&viewId=4029"


def getCombinedManualInvoiceData(mi_id):
    manual_invoice_data = getManualInvoiceDetailsById(mi_id)
    manual_invoice_item_data = getManualInvoiceItems(mi_id)
    return {
        'invoice_data': manual_invoice_data,
        'invoice_items': manual_invoice_item_data,
        'is_manual': True
    }


def getManualInvoiceDetailsById(mi_id):
    view_id = '5374'
    request_url = request_base_url.format(mi_id, view_id)
    params = {
        'access_token': get_access_token(),
        'user_key': settings.TRACKVIA_USER_KEY
    }

    response = requests.get(
        url=request_url,
        params=params)

    if response.status_code != 200:
        logger.error("getManualInvoiceDetailsById | {0} | response status is {1}".format(mi_id, response.status_code))
        pass

    response_data_dict = response.json()['data']
    field_mappings = getFieldMappings()
    ref_field_mappings = getReferencedFieldMappings()
    return_dict = {}

    for field in response_data_dict:
        if field.get('fieldMetaId') not in field_mappings.keys() and \
                field.get('fieldMetaId') not in ref_field_mappings.keys():
            continue

        key_name = field_mappings.get(field.get('fieldMetaId'))
        if not key_name:
            key_name = ref_field_mappings.get(field.get('fieldMetaId'))
        value = field.get('value', '')

        if field.get('fieldMetaId') in ref_field_mappings.keys():
            value = field.get('identifier', '')

        return_dict[key_name] = value

    return_dict['tv_id'] = mi_id
    return_dict['CONTRACTOR'] = "Diego Rodriguez"  # Final Contractor name to be decided
    return return_dict


def getFieldMappings():
    return {
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


def getReferencedFieldMappings():
    return {
            18720: 'PROJECT',
            18717: 'SALES ORDER',
            18314: 'CONTRACTOR',
            18042: 'PAYMENT TERMS',
            23350: 'SALE TAX'
    }


def getManualInvoiceItems(mi_id):
    url = invoice_item_url
    body = {
        "operator": "AND",
        "negated": False,
        "displayOrder": 0,
        "fieldFilters": [{
            "fieldMetaId": 18714,
            "relationshipId": 4460,
            "value": mi_id,
            "operator": "=",
            "negated": False,
            "displayOrder": 1
        }]}
    params = {
        'access_token': get_access_token(),
        'user_key': settings.TRACKVIA_USER_KEY
    }
    response = requests.post(
        url=url,
        params=params,
        json=body
    )

    if response.status_code != 200:
        logger.error("getManualInvoiceItems | {0} | response status is {1}".format(mi_id, response.status_code))
        pass

    response = response.json()
    return invoiceItemsFormatter(response.get('records'))


def invoiceItemsFormatter(response):
    mapper = {
            # 21100: 'Manufacturer',
            # 21103: 'Catalog',
            21369: 'Quantity',
            21102: 'Type',
            21106: 'Description',
            18537: 'Unit DN',
            18540: 'Total DN'
            }
    invoice_item_list = list()
    for row in response:
        item_dict = dict()
        item_data = row.get('data')
        for field in item_data:
            if 'fieldMetaId' not in field or field.get('fieldMetaId') not in mapper:
                continue
            key = mapper.get(field.get('fieldMetaId'))
            value = field.get('value') if 'value' in field else ''
            item_dict[key] = value
        invoice_item_list.append(item_dict)
    return invoice_item_list


def updateManualInvoiceStatus(mi_id, status):
    view_id = '5374'
    url = 'https://go.trackvia.com/accounts/21782/apps/49/tables/740/records/{0}?formId=5249&viewId={1}'\
        .format(mi_id, view_id)
    params = {
        'access_token': get_access_token(),
        'user_key': settings.TRACKVIA_USER_KEY
    }
    body = {
        'id': mi_id,
        'data': [
            {
                'fieldMetaId': '18716',
                'id': '329344',
                'type': 'dropDown',
                'value': status
            }
        ]
    }
    resp = requests.put(url=url, params=params, json=body)
    if resp.status_code != 200:
        logger.error('payment status not updated for manual invoice, {0} | {1} | {2}'.format(
            mi_id, resp.json(), resp.status_code))

