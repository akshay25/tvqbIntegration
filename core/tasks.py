from celery import shared_task

import re
import json

from core.apis.quickBooks.authentication import refresh
from core.webhooks.quickbooks import verifyQBWebhookData, processQBWebhookData, decode_and_process_qb_webhook_data
from core.webhooks.trackvia import tv_invoice_webhook, tv_bill_webhook
from core.logger import logger

invoice_table_id = '740'
invoice_view_id = '4027'
bill_table_id = '786'
bill_view_id = '4205'


@shared_task
def process_tv_webhook(table_id, view_id, record_id, event_type):
    if invoice_table_id == table_id:
        tv_invoice_webhook(event_type, record_id, table_id, view_id)
    elif bill_table_id == table_id:
        tv_bill_webhook(event_type, record_id, table_id, view_id)
    else:
        pass


@shared_task
def process_qb_webhook(signature, body_unicode, verifier_token):
    logger.info('validating data.. ##################')
    if verifyQBWebhookData(body_unicode, signature, verifier_token):
        try:
            refresh()
            processQBWebhookData(body_unicode)
        except Exception as e:
            data = json.loads(body_unicode)
            decode_and_process_qb_webhook_data(data)
    else:
        logger.error('webhook data temepered | {0} | {1} | {2}'.format(signature, body_unicode, verifier_token))
        return


# HELPER functions
# -----------------------------------------------------#

def isTestProject(record):
    if 'PROJECT' not in record['invoice_data']:
        return False
    project = record['invoice_data']['PROJECT']
    if re.search('test', project, re.IGNORECASE):
        return True
    return False


