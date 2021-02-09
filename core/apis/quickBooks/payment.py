import requests
from django.conf import settings
from core.apis.quickBooks.authentication import get_access_token
from core.logger import logger


def readPayment(payment_id):
    access_token = get_access_token()
    url = _get_url() + '/' + payment_id + '?minorversion=51'
    headers = _get_headers(access_token)
    r = requests.get(url=url, headers=headers)
    if r.status_code == 200:
        logger.debug("readPayment | API success for id {0}".format(payment_id))
        return r.json()
    else:
        print('log read invoice API failed', payment_id, r.json(), r.status_code)
        logger.debug("readPayment | API failed for id {0}".format(payment_id))
        return None


def _get_url():
    realm_id = settings.QBO_COMPANY_ID
    route = '{0}/v3/company/{1}/payment'.format(settings.QBO_BASE_URL, realm_id)
    return route


def _get_headers(access_token):
    auth_header = 'Bearer {0}'.format(access_token)
    headers = {
        'Authorization': auth_header,
        'Accept': 'application/json'
    }
    return headers