# coding=utf-8

import requests
import urllib.parse

from core.apis.quickBooks.authentication import get_access_token
from django.conf import settings

file_root_path = '/tmp/'


def downloadFileFromLink(link, file_name):
    resp = requests.get(link)
    with open(file_root_path + file_name, 'wb') as f:
        f.write(resp.content)


def uploadAttachableInQB(bill_id, pdf_name):
    access_token = get_access_token()
    url = _get_upload_url()
    headers = _get_upload_headers(access_token)

    request_body = {
        "AttachableRef": [
            {
                "EntityRef": {
                    "type": "Bill",
                    "value": bill_id
                }
            }
        ],
        "ContentType": "application/pdf",
        "FileName": pdf_name
    }
    resp = requests.post(
        url=url,
        json=request_body,
        headers=headers
    )
    print(resp.json())


def getAttachableRefForBill(bill_id):
    access_token = get_access_token()
    sqlQuery = "select Id from attachable where " \
               "AttachableRef.EntityRef.Type = {0} and AttachableRef.EntityRef.value = {1}" \
        .format('bill', bill_id)
    parsedSqlQuery = urllib.parse.quote(sqlQuery)
    url = '{0}/v3/company/{1}/query?query={2}&minorversion=51'.format(
        settings.QBO_BASE_URL, settings.QBO_COMPANY_ID, parsedSqlQuery)
    headers = _get_headers(access_token)
    response = requests.get(
        url=url,
        headers=headers
    )
    if response.status_code == 200:
        result = response.json()
        if result.get('QueryResponse'):
            return {
                'AttachableRef': result.get('QueryResponse').get('Attachable')
            }
        else:
            return {'error': 'NO AttachableRef FOUND'}
    else:
        print('Error: AttachableRef ', bill_id)


def getAttachableDetailsById(attachable_id):
    url = '{0}/v3/company/{1}/attachable/{1}?minorversion=51'.format(
        settings.QBO_BASE_URL, settings.QBO_COMPANY_ID, attachable_id)
    response = requests.get(url)
    if response.status_code == 200:
        result = response.json()
        if result.get('Attachable'):
            return result.get("Attachable")
        else:
            return {'error': 'NO Details for Attachable ' + attachable_id}
    else:
        print('Error: attachable_id ', attachable_id)


def deleteAttachable(bill_id):
    attachable_refs = getAttachableRefForBill(bill_id)
    access_token = get_access_token()
    headers = _get_delete_headers(access_token)

    if not attachable_refs:
        print('Error: No attachable for bill ', bill_id)
        return

    for attachable_ref in attachable_refs:
        attachable_ref_id = attachable_ref.get('Id')

        attachable_details = getAttachableDetailsById(attachable_ref_id)
        url = '{0}/v3/company/{1}/attachable?operation=delete&minorversion=51'.format(
            settings.QBO_BASE_URL, settings.QBO_COMPANY_ID)

        resp = requests.post(
            url=url,
            json=attachable_details,
            headers=headers
        )

        if resp.status_code == 200:
            result = resp.json()
            if result.get("Attachable") and result.get("Attachable").get('status') == 'Deleted':
                print('Attachable deleted for bill {0} with Id {1}'.
                      format(bill_id, attachable_ref_id))
        else:
            print('Error: delete attachable ', attachable_ref_id)


def _get_upload_url():
    realm_id = settings.QBO_COMPANY_ID
    route = '{0}/v3/company/{1}/upload?minorversion=52'.format(settings.QBO_BASE_URL, realm_id)
    return route


def _get_headers(access_token):
    auth_header = 'Bearer {0}'.format(access_token)
    headers = {
        'Authorization': auth_header,
        'Accept': 'text/plain'
    }
    return headers


def _get_upload_headers(access_token):
    auth_header = 'Bearer {0}'.format(access_token)
    headers = {
        'Authorization': auth_header,
        'Content-Type': 'multipart/form-data'
    }
    return headers


def _get_delete_headers(access_token):
    auth_header = 'Bearer {0}'.format(access_token)
    headers = {
        'Authorization': auth_header,
        'Content-Type': 'application/json'
    }
    return headers
