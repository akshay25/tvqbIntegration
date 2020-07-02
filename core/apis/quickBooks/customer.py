import requests
import urllib.parse

from django.conf import settings
from core.apis.quickBooks.authentication import get_access_token

def queryCustomer(customer_name):
    access_token = get_access_token()
    sql = "select * from Customer where DisplayName='{0}' and Active=true".format(customer_name)
    parsed_sql = urllib.parse.quote(sql)
    url = '{0}/v3/company/{1}/query?query={2}&minorversion=51'.format(settings.QBO_BASE_SANDBOX, settings.QBO_COMPANY_ID, parsed_sql)
    headers = _get_headers(access_token)
    r = requests.get(url = url, headers = headers)
    if r.status_code == 200:
        result = r.json()
        if len(result['QueryResponse'].keys()) == 0:
            return {'error': 'NO ITEM FOUND'}
        return {'Customer': result['QueryResponse']['Customer'][0]}
    else:
        pass


def _get_url():
    realm_id = settings.QBO_COMPANY_ID
    if settings.QB_ENVIRONMENT == 'production':
        base_url = settings.QBO_BASE_PROD
    else:
        base_url =  settings.QBO_BASE_SANDBOX

    route = '/v3/company/{0}/item?minorversion=51'.format(realm_id)
    return '{0}{1}'.format(base_url, route)

def _get_headers(access_token):
    auth_header = 'Bearer {0}'.format(access_token)
    headers = {
        'Authorization': auth_header,
        'Accept': 'application/json'
    }
    return headers
