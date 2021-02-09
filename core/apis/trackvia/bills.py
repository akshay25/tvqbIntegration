from django.conf import settings
import requests

from core.logger import logger
from core.apis.trackvia.authentication import get_access_token

request_base_url = "https://go.trackvia.com/accounts/21782/apps/49/tables/786/records/{0}?viewId={1}&formId=6060"


def getBillDetailsById(bill_id, view_id):
    #if not view_id:
    view_id = '4205'
    request_url = request_base_url.format(bill_id, view_id)
    params = {
        'access_token': get_access_token(),
        'user_key': settings.TRACKVIA_USER_KEY
    }

    response = requests.get(
        url=request_url,
        params=params)

    if response.status_code != 200:
        logger.error("getBillDetailsById | response code not 200 for bill {0} | {1}".format(
            bill_id, response.status_code))
        pass

    if not (response.json() and response.json().get('data')):
        logger.error("getBillDetailsById | response null for bill {0}".format(bill_id))
        return
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

    if return_dict.get('BILL PDF LINK') and return_dict.get('BILL PDF'):
        downloadAndSavePdf(return_dict.get('BILL PDF LINK'), return_dict.get('BILL PDF'))

    return_dict['bill_id'] = bill_id
    return return_dict


def getFieldMappings():
    return dict((
        (24127, 'STATUS'),
        (19508, 'BILL #'),
        (19507, 'BILL DATE'),
        (21776, 'DUE DATE'),
        (21764, 'PAYMENT TERMS'),
        (24096, 'BILL PDF LINK'),
        (24150, 'SUBTOTAL'),
        (21779, 'BILL TOTAL'),
        (19536, 'PO TOTAL'),
        (24152, 'DISCOUNT TOTAL'),
        (19631, 'PO #'),
        (21738, 'PO# FROM DOCPARSER'),
        (19728, 'SALES ORDER'),
        (19888, 'SHIPPING COMPANY'),
        (19889, 'TRACKING'),
        (24094, 'FREIGHT FROM DOCPARSER'),
        (19542, 'FREIGHT'),
        (21744, 'PAYMENT METHOD'),
        (21743, 'MANUAL PAYMENT METHOD'),
        (21740, 'PAYMENT STATUS'),
        (24125, 'PAYMENT AMOUNT 1'),
        (24126, 'PAYMENT AMOUNT 2'),
        (19509, 'ACCOUNTANT NOTES'),
        (19510, 'ILC NOTES'),
        (25352, 'ACCOUNTING CLASS')
    ))


def getReferencedFieldMappings():
    return dict((
        (20486, 'MANUFACTURER'),
        (22108, 'BILL PDF'),
        (20489, 'CREDIT CARD')
    ))


def updateTvBillStatus(bill_id, status, view_id, payment_id):
    #if not view_id:
    view_id = '4205'
    url = 'https://go.trackvia.com/accounts/21782/apps/49/tables/786/records/{0}?formId=6060&viewId={1}'\
        .format(bill_id, view_id)
    params = {
        'access_token': get_access_token(),
        'user_key': settings.TRACKVIA_USER_KEY
    }
    body = {
        'id': bill_id,
        'data': [
            {
                'fieldMetaId': 21740,
                'id': 286073,
                'type': 'dropDown',
                'value': status
            }
        ]
    }
    resp = requests.put(url=url, params=params, json=body)
    if resp.status_code != 200:
        logger.error('updateTvBillStatus | payment status not updated for bill, {0} | {1} | {2} | {3}'.format(
            bill_id, payment_id, resp.json(), resp.status_code))
    else:
        logger.info('updateTvBillStatus | payment status updated for bill fee, {0} | {1} | {2} | {3}'.format(
            bill_id, payment_id, resp.json(), resp.status_code))


def downloadAndSavePdf(pdf_link, pdf_name):
    r = requests.get(pdf_link)
    with open('/tmp/' + pdf_name, 'wb') as f:
        f.write(r.content)

