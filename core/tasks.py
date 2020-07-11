from celery import shared_task
from celery.contrib import rdb
from celery.decorators import task

import re
import base64, hmac, hashlib, json

from core.apis.quickBooks.invoice import readInvoice
from core.apis.quickBooks.payment import readPayment
from core.apis.trackvia.invoice import getFullInvoiceData, updateTvInvoiceStatus
from core.evaluator import updateInvoiceInQB, deleteInvoiceFromQB
from core.models import InvoiceRef

@shared_task
def process_tv_webhook(table_id, view_id, record_id, event_type):
    if event_type == 'AFTER_CREATE':
        print('ignoring because AFTER_CREATE event is fired')
        return
    elif event_type == 'AFTER_UPDATE':
        record = getFullInvoiceData(record_id)
        if record['invoice_data']['STATUS'] != 'SENT' or isTestProject(record):
            print('ignoring as the record is not in SENT state or it is a test project.')
            return
        updateInvoiceInQB(record)
    elif event_type == 'AFTER_DELETE':
        deleteInvoiceFromQB(record_id)

@shared_task
def process_qb_webhook(signature, body_unicode, verifier_token):
    print('validating data.. ##################')
    if verifyWebhookData(body_unicode, signature, verifier_token):
        processInvoiceWebhookData(body_unicode)
    else:
        print('webhook data temepered $$$$$$$---------')
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


def verifyWebhookData(body_unicode, signature, verifier_token):
    bvt = verifier_token.encode()
    body = body_unicode.encode()
    hmac_hex_digest = hmac.new(
        bvt,
        body,
        hashlib.sha256
    ).hexdigest()
    decoded_hex_signature = base64.b64decode(signature).hex()
    print(hmac_hex_digest == decoded_hex_signature, ' ^^^^^^^^^^^^^')
    return hmac_hex_digest == decoded_hex_signature

def processInvoiceWebhookData(body_unicode):
    data = json.loads(body_unicode)
    print('processInvoiceWebhookData')
    payment_ids = []
    entities = data['eventNotifications'][0]['dataChangeEvent']['entities']
    for entity in entities:
        if entity['name'] == 'Payment':
            payment_ids.append(entity['id'])
    print(payment_ids, "!!!!!!!!!!!")
    invoice_ids = []
    for payment_id in payment_ids:
        payment = readPayment(payment_id)
        if payment == None:
            print('payment not found for id ', payment_id)
            return
        lines = payment['Payment']['Line']
        for line in lines:
            for ltxn in line['LinkedTxn']:
                if ltxn['TxnType'] == 'Invoice':
                    invoice_ids.append(ltxn['TxnId'])
    invoice_ids = list(set(invoice_ids))
    for invoice_id in invoice_ids:
        process_invoice(invoice_id)
    return

def process_invoice(invoice_id):
    invoice = readInvoice(invoice_id)
    print(invoice)
    if invoice == None:
        print('invoice not found for id ', invoice_id)
        return
    total_amt = invoice['Invoice']['TotalAmt']
    balance = invoice['Invoice']['Balance']
    print(total_amt, balance, '************************')
    invoices = InvoiceRef.objects.filter(qb_id=invoice_id)
    if len(invoices) == 0:
        return
    tv_invoice_id = invoices[0].tv_id
    if total_amt == balance:
        updateTvInvoiceStatus(tv_invoice_id, 'UNPAID')
    elif balance == 0:
        updateTvInvoiceStatus(tv_invoice_id, 'FULL')
    elif balance < total_amt and balance > 0:
        updateTvInvoiceStatus(tv_invoice_id, 'PARTIAL')
    return
