import requests
import urllib.parse

from django.conf import settings
from core.apis.quickBooks.authentication import get_access_token

def queryTaxCode(tax_code_name):
    access_token = get_access_token()
    sql = "select * from TaxCode where Name='{0}' and Active=true".format(tax_code_name)
    parsed_sql = urllib.parse.quote(sql)
    url = '{0}/v3/company/{1}/query?query={2}&minorversion=51'.format(settings.QBO_BASE_URL, settings.QBO_COMPANY_ID, parsed_sql)
    headers = _get_headers(access_token)
    r = requests.get(url = url, headers = headers)
    if r.status_code == 200:
        result = r.json()
        if len(result['QueryResponse'].keys()) == 0:
            return {'error': 'NO ITEM FOUND'}
        return {'TaxCode': result['QueryResponse']['TaxCode'][0]}
    else:
        print('Error: queryCustomer', tax_code_name)

def _get_headers(access_token):
    auth_header = 'Bearer {0}'.format(access_token)
    headers = {
        'Authorization': auth_header,
        'Accept': 'application/json'
    }
    return headers
