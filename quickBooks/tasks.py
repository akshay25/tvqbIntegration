from celery import shared_task
from celery.contrib import rdb
from celery.decorators import task

import base64, hmac, hashlib, json

from quickBooks.apis.invoice import readInvoice

@shared_task
def process_webhook_data(signature, body_unicode, verifier_token):
    # validate data
    # process it
    print('validating data.. ##################')
    if verifyWebhookData(body_unicode, signature, verifier_token):
        processInvoiceWebhookData(body_unicode)
    else:
        print('webhook data temepered $$$$$$$---------')
        # log tempered webhook data
        return

@shared_task
def setInvoiceStatusInTV(qb_invoice_id, status):
    # call TV handlers to set invoice status
    print('------------------------')
    print('setStatusInTV', qb_invoice_id, status)

# HELPER functions
# -----------------------------------------------------#

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
    invoice_ids = []
    entities = data['eventNotifications'][0]['dataChangeEvent']['entities']
    for entity in entities:
        if entity['operation'] == 'Update':
             invoice_ids.append(entity['id'])
    print(invoice_ids, "!!!!!!!!!!!")
    for invoice_id in invoice_ids:
        process_invoice(invoice_id)
    return

def process_invoice(invoice_id):
    #rdb.set_trace()
    invoice = readInvoice(invoice_id)
    print(invoice)
    if invoice == None:
        print('invoice not found for id ', invoice_id)
        return
    total_amt = invoice['Invoice']['TotalAmt']
    balance = invoice['Invoice']['Balance']
    print(total_amt, balance, '************************')
    if total_amt == balance:
        print('tot_amt == balance')
        return
    elif balance == 0:
        setInvoiceStatusInTV.delay(invoice_id, 'FullPayment')
    elif balance < total_amt and balance > 0:
        setInvoiceStatusInTV.delay(invoice_id, 'PartialPayment')
    return
