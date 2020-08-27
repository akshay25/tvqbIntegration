import requests
import urllib.parse

from core.apis.quickBooks.authentication import get_access_token, refresh
from core.logger import logger
from django.conf import settings


def getVendor(name):
    access_token = get_access_token()
    sql = "select * from Vendor where DisplayName='{0}' and Active=true".format(name)
    parsed_sql = urllib.parse.quote(sql)
    url = '{0}/v3/company/{1}/query?query={2}&minorversion=52'.format(
        settings.QBO_BASE_URL, settings.QBO_COMPANY_ID, parsed_sql)
    headers = _get_headers(access_token)
    response = requests.get(
        url=url,
        headers=headers
    )
    if response.status_code == 200:
        result = response.json()
        if result.get('QueryResponse'):
            return {
                'Vendor': result.get('QueryResponse').get('Vendor')[0]
            }
        else:
            logger.error("getVendor error for " + name)
            return {'error': 'NO Vendor FOUND'}
    else:
        logger.error('Error: Vendor ', name)


def _get_headers(access_token):
    auth_header = 'Bearer {0}'.format(access_token)
    headers = {
        'Authorization': auth_header,
        'Accept': 'application/json'
    }
    return headers
