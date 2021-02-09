# coding=utf-8

from django.conf import settings
import requests

from core.logger import logger
from core.apis.trackvia.authentication import get_access_token


request_base_url = "https://go.trackvia.com/accounts/21782/apps/49/tables/743/records/{0}?viewId={1}&formId=6544"


def getDesignFeeDetailsById(df_id, view_id):
    #if not view_id:
    view_id = '4046'
    request_url = request_base_url.format(df_id, view_id)
    params = {
        'access_token': get_access_token(),
        'user_key': settings.TRACKVIA_USER_KEY
    }

    response = requests.get(
        url=request_url,
        params=params)

    if response.status_code != 200:
        logger.error("getDesignFeeDetailsById | {0} | response status is {1}".format(df_id, response.status_code))
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

    return_dict['df_id'] = df_id
    return return_dict


def getFieldMappings():
    return dict((
        (18762, 'STATUS'),
        (18770, 'PROJECT'),
        (18771, 'PHASE'),
        (18760, 'TOTAL $'),  # MANUAL AMOUNT
        (23358, 'DESIGN INVOICE #'),
        (18759, 'DESCRIPTION'),
        (19235, 'SENT DATE'),
        (19234, 'DUE DATE'),
        (23355, 'SEND TO'),
    ))


def getReferencedFieldMappings():
    return dict((
        (18770, 'PROJECT'),
        (18771, 'PHASE'),
        (18315, 'DESIGNER TO INVOICE')
    ))


def updateDesignFeeStatus(df_id, status, view_id, payment_id):
    #if not view_id:
    view_id = '4046'
    url = 'https://go.trackvia.com/accounts/21782/apps/49/tables/743/records/{0}?formId=6544&viewId={1}'\
        .format(df_id, view_id)
    params = {
        'access_token': get_access_token(),
        'user_key': settings.TRACKVIA_USER_KEY
    }
    body = {
        'id': df_id,
        'data': [
            {
                'fieldMetaId': '24694',
                'id': '304680',
                'type': 'dropDown',
                'value': status
            }
        ]
    }
    resp = requests.put(url=url, params=params, json=body)
    if resp.status_code != 200:
        logger.error('updateDesignFeeStatus | payment status not updated for design fee, {0} | {1} | {2} | {3}'.format(
            df_id, payment_id, resp.json(), resp.status_code))
    else:
        logger.info('updateDesignFeeStatus | payment status updated for design fee, {0} | {1} | {2} | {3}'.format(
            df_id, payment_id, resp.json(), resp.status_code))

