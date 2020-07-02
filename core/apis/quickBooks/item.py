import requests
import urllib.parse

from django.conf import settings
from core.apis.quickBooks.authentication import get_access_token

def queryItem(item_name):
    access_token = get_access_token()
    sql = "select * from Item where Name = '{0}' and Active=true".format(item_name)
    parsed_sql = urllib.parse.quote(sql)
    url = '{0}/v3/company/{1}/query?query={2}&minorversion=51'.format(settings.QBO_BASE_SANDBOX, settings.QBO_COMPANY_ID, parsed_sql)
    headers = _get_headers(access_token)
    r = requests.get(url = url, headers = headers)
    if r.status_code == 200:
        result = r.json()
        if len(result['QueryResponse'].keys()) == 0:
            return {'error': 'NO ITEM FOUND'}
        return {'item': result['QueryResponse']['Item'][0]}
    else:
        pass


def createItem(item_data):
    data = {
            'Name': item_data['name'],
            'Type': 'NonInventory',
            "ExpenseAccountRef": {
                "name": "Cost of Goods Sold",
                "value": "80"
              },
            "IncomeAccountRef": {
                "name": "Sales of Product Income",
                "value": "79"
              },
            "AssetAccountRef": {
                "name": "Inventory Asset",
                "value": "81"
              }
            }
    access_token = get_access_token()
    url = _get_url()
    headers = _get_headers(access_token)
    r = requests.post(url = url, json = data, headers = headers)
    if r.status_code == 200:
        return r.json()
        #log invoice created with id
    else:
        #log invoice creation failed
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
