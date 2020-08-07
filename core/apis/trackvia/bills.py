from django.conf import settings
import requests

from core.apis.trackvia.authentication import get_access_token

request_base_url = "https://go.trackvia.com/accounts/21782/apps/49/tables/786/records/{0}?viewId=4205&formId=6060"


def getBillDetailsById(bill_id):
    request_url = request_base_url.format(bill_id)
    params = {
        'access_token': get_access_token(),
        'user_key': settings.TRACKVIA_USER_KEY
    }

    response = requests.get(
        url=request_url,
        params=params)

    response_data_dict = response.json()['data']
    field_mappings = getFieldMappings()
    ref_field_mappings = getReferencedFieldMappings()
    return_dict = {}

    for field in response_data_dict:
        if 'fieldMetaId' not in field.keys or field['fieldMetaId'] not in field_mappings.keys():
            continue

        key_name = field_mappings.get(field.get('fieldMetaId'))
        value = field.get('value', '')

        if value in field.keys():
            if field.get('fieldMetaId') in ref_field_mappings.keys():
                value = field.get('identifier', '')
        else:
            value = ''

        return_dict[key_name] = value

    if response.status_code != 200:
        # log
        pass


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
        (19510, 'ILC NOTES')
    ))


def getReferencedFieldMappings():
    return dict((
        (20486, 'MANUFACTURER'),
        (22108, 'BILL PDF'),
        (20489, 'CREDIT CARD')
    ))


def updateTvInvoiceStatus(bill_id, status):
    url = 'https://go.trackvia.com/accounts/21782/apps/49/tables/786/records/{0}?formId=5429&viewId=4118'\
        .format(bill_id)
    params = {
        'access_token': get_access_token(),
        'user_key': settings.TRACKVIA_USER_KEY
    }
    body = {
            'id': bill_id,
            'data': [
                {'fieldMetaId': 24127, 'id': 279131, 'type': 'dropDown', 'value': status}
                ]
            }
    r = requests.put(url = url, params = params, json = body)
    if r.status_code != 200:
        print('payment status not updated')