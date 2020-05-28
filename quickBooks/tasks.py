from celery import shared_task
from celery.decorators import task

import base64
import hmac
import hashlib


@shared_task
def process_webhook_data(signature, data, verifier_token):
    # validate data
    # process it
    print('validating data.. ##################')
    if verifyWebhookData(data, signature, verifier_token):
        processInvoiceWebhookData(data)
    else:
        # log tempered webhook data
        return

@shared_task
def setInvoiceStatusInTV(qb_invoice_id, status):
    # call TV handlers to set invoice status
    print('------------------------')
    print('setStatusInTV', qb_invoice_id, status)
    pass

# HELPER functions
# -----------------------------------------------------#

def verifyWebhookData(request_body, signature, verifier_token):
    return True
   # hmac_hex_digest = hmac.new(
   #     verifier_token,    # token from quickbooks in bytes
   #     request_body,    # request_body = request.data
   #     hashlib.sha256
   # ).hexdigest()
   # decoded_hex_signature = base64.b64decode(signature()).hex()   # request.headers.get('intuit-signature')
   # return hmac_hex_digest == decoded_hex_signature

def processInvoiceWebhookData(data):
    invoice_ids = []
    entities = data['eventNotifications']['dataChangeEvent']['entities']
    for entity in entities:
        if entity['operation'] == 'Update':
             invoice_ids.append(entity['id'])
    for invoice_id in invoice_ids:
        process_invoice(invoice_id)
    return

def process_invoice(invoice_id):
    invoice = readInvoice(invoice_id)
    if invoice == None:
        return
    total_amt = invoice['Invoice']['TotalAmt']
    balance = invoice['Balance']
    if total_amt == balance:
        return
    elif balance == 0:
        setInvoiceStatusInTV.delay(invoice_id, 'FullPayment')
    elif balance < total_amt and balance > 0:
        setInvoiceStatusInTV.delay(invoice_id, 'PartialPayment')
    return
