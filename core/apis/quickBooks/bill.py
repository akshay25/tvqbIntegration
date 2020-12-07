import requests
from django.conf import settings
from core.apis.quickBooks.authentication import get_access_token, refresh
from core.logger import logger


def createBillInQB(data):
    access_token = get_access_token()
    url = _get_url()
    headers = _get_headers(access_token)
    resp = requests.post(url=url, json=data, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    else:
        logger.error('failed expense creation, data={0}, resp={1}, status_code={2}', data, resp.json(), resp.status_code)
        pass


def _get_url():
    realm_id = settings.QBO_COMPANY_ID
    route = '{0}/v3/company/{1}/bill?minorversion=52'.format(settings.QBO_BASE_URL, realm_id)
    return route


def _get_read_url(bill_id):
    realm_id = settings.QBO_COMPANY_ID
    route = '{0}/v3/company/{1}/bill/{2}?minorversion=52'.format(
        settings.QBO_BASE_URL, realm_id, bill_id)
    return route


def _get_headers(access_token):
    auth_header = 'Bearer {0}'.format(access_token)
    headers = {
        'Authorization': auth_header,
        'Accept': 'application/json'
    }
    return headers


def updateBillInQB(data, is_sparse=False, retry_count=3):
    bill_id = data.get('Id')
    bill_dict = readBillFromQB(bill_id)
    if not bill_dict:
        if retry_count >= 0:
            updateBillInQB(data, is_sparse, retry_count-1)
            return
        else:
            # print('updateBillInQB unable to fetch bill')
            logger.error("updateBillInQB unable to fetch bill for {0}".format(bill_id))
            return

    access_token = get_access_token()
    url = _get_url()
    headers = _get_headers(access_token)
    data['sparse'] = is_sparse
    data['SyncToken'] = bill_dict.get('Bill').get('SyncToken')

    resp = requests.post(
        url=url,
        json=data,
        headers=headers
    )

    if resp.status_code == 200:
        return resp.json()
    elif resp.status_code == 501:
        print(resp.content)
        if retry_count > 0:
            logger.error("updateBillInQB failed update bill due to sync token | {0} | {1}".format(
                data, retry_count))
            # print('updateBillInQB failed update bill due to sync token', data, retry_count)
            return updateBillInQB(data, is_sparse, retry_count-1)
        else:
            logger.error("updateBillInQB failed update bill due to sync token | {0} | {1}".format(
                data, retry_count))
            # print('updateBillInQB failed update bill due to sync token', data, retry_count)
    else:
        logger.error("updateBillInQB failed update bill | {0} | {1} | {2}".format(
            data, resp.json(), resp.status_code))
        # print('updateBillInQB failed update bill', data, resp.json(), resp.status_code)
        pass


def deleteBillInQB(bill_id):
    bill = readBillFromQB(bill_id)
    if not bill:
        logger.error("log unable to fetch bill in deleteBillInQB for {0}".format(bill_id))
        # print('log unable to fetch bill in deleteBillInQB ', bill_id)
        return
    access_token = get_access_token()
    url = _get_url() + '/' + bill_id + '?operation=delete'
    data = {
        'Id': bill_id,
        'SyncToken': bill.get('Bill').get('SyncToken'),
    }
    headers = _get_headers(access_token)
    resp = requests.post(
        url=url,
        json=data,
        headers=headers
    )
    if resp.status_code == 200:
        # confirm logic
        return
    else:
        logger.error("log delete bill API failed | {0} | {1} | {2}".format(
            bill_id, resp.json(), resp.status_code))
        # print('log delete bill API failed', bill_id, resp.json(), resp.status_code)
        # confirm logic
        return {'error': "Not found"}


def readBillFromQB(bill_id):
    url = _get_read_url(bill_id)
    headers = _get_headers(get_access_token())
    resp = requests.get(url=url, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    else:
        logger.warn("log read bills API failed in readBillInQB() {0}".format(bill_id))
        # print('log read bills API failed in readBillInQB()', bill_id)
        return None
