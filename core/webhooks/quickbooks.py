# coding=utf-8
import base64
import hashlib
import hmac
import json
import traceback

from core.apis.quickBooks.bill.bill import readBillFromQB
from core.apis.quickBooks.bill.billpayment import readBillPayment
from core.apis.quickBooks.invoice.invoice import readInvoice
from core.apis.quickBooks.payment import readPayment
from core.apis.trackvia.bills import updateTvBillStatus
from core.apis.trackvia.invoice import updateTvInvoiceStatus
from core.email import send_email
from core.logger import logger
from core.models import InvoiceRef, BillExpenseReference


def processInvoices(payment_ids):
    invoice_ids = []
    for payment_id in payment_ids:
        payment = readPayment(payment_id)
        if payment == None:
            logger.error('payment not found for id {0}'.format(payment_id))
            break
        lines = payment['Payment']['Line']
        for line in lines:
            for ltxn in line['LinkedTxn']:
                if ltxn['TxnType'] == 'Invoice':
                    invoice_ids.append(ltxn['TxnId'])
    invoice_ids = list(set(invoice_ids))
    for invoice_id in invoice_ids:
        process_invoice(invoice_id)


def process_invoice(invoice_id):
    invoice = readInvoice(invoice_id)
    logger.info("process_invoice | {0} | {1}".format(invoice_id, invoice))
    if invoice == None:
        logger.error('invoice not found for id {0}'.format(invoice_id))
        return
    total_amt = invoice['Invoice']['TotalAmt']
    balance = invoice['Invoice']['Balance']
    logger.info("process_invoice | {0} | {1}".format(total_amt, balance))
    invoices = InvoiceRef.objects.filter(qb_id=invoice_id)
    if len(invoices) == 0:
        logger.error('process_invoice | invoices not found for id | {0}'.format(invoice_id))
        return
    tv_invoice_id = invoices[0].tv_id
    if total_amt == balance:
        updateTvInvoiceStatus(tv_invoice_id, 'UNPAID')
    elif balance == 0:
        updateTvInvoiceStatus(tv_invoice_id, 'FULL')
    elif balance < total_amt and balance > 0:
        updateTvInvoiceStatus(tv_invoice_id, 'PARTIAL')
    return


def processBills(payment_ids):
    bill_ids = []
    for payment_id in payment_ids:
        payment = readBillPayment(payment_id)
        if not payment:
            logger.error('processBills | payment not found for id | {0}'.format(payment_id))
            break
        lines = payment['BillPayment']['Line']
        for line in lines:
            for ltxn in line['LinkedTxn']:
                if ltxn['TxnType'] == 'Bill':  # Confirm this type
                    bill_ids.append(ltxn['TxnId'])
    bill_ids = list(set(bill_ids))
    for bill_id in bill_ids:
        process_bill(bill_id)


def process_bill(bill_id):
    bill = readBillFromQB(bill_id)

    if not bill:
        logger.error('process_bill | bill not found for id | {0}'.format(bill_id))
        return

    logger.error('process_bill | {0}'.format(bill))

    total_amt = bill.get('Bill').get('TotalAmt')
    balance = bill.get('Bill').get('Balance')
    logger.error("process_bill | log2 | {0} | {1}".format(total_amt, balance))

    bill_refs = BillExpenseReference.objects.filter(qb_id=bill_id)
    if len(bill_refs) == 0:
        logger.error('process_bill | bill_ref not found for id | {0}'.format(bill_id))
        return

    tv_id = bill_refs[0].tv_id

    # bill_ref = BillExpenseReference().getBillExpenseReferanceByTvId(bill_id=bill_id)
    # if not bill_ref:
    #     print('billreferance not found for id ', bill_id)
    #     return

    # tv_id = bill_ref.tv_id

    if total_amt == balance:
        updateTvBillStatus(tv_id, 'UNPAID')
    elif balance == 0:
        updateTvBillStatus(tv_id, 'FULL')
    elif 0 < balance < total_amt:
        updateTvBillStatus(tv_id, 'PARTIAL')

    #   # Bill payment Logic
    return


def verifyQBWebhookData(body_unicode, signature, verifier_token):
    try:
        bvt = verifier_token.encode()
        body = body_unicode.encode()
        hmac_hex_digest = hmac.new(
            bvt,
            body,
            hashlib.sha256
        ).hexdigest()
        decoded_hex_signature = base64.b64decode(signature).hex()
        # print(hmac_hex_digest == decoded_hex_signature, ' ^^^^^^^^^^^^^')
        return hmac_hex_digest == decoded_hex_signature
    except Exception as e:
        return False


def processQBWebhookData(body_unicode):
    data = json.loads(body_unicode)
    logger.info("processWebhookData | {0}".format(body_unicode))
    payment_ids = []
    bill_payment_ids = []
    entities = data['eventNotifications'][0]['dataChangeEvent']['entities']
    for entity in entities:
        if entity['name'] == 'Payment':
            payment_ids.append(entity['id'])
        elif entity['name'] == 'BillPayment':
            bill_payment_ids.append(entity['id'])

    logger.info("payment_ids: {0}, bill_payment_ids: {1}".format(payment_ids, bill_payment_ids))

    processInvoices(payment_ids)

    processBills(bill_payment_ids)

    return


def decode_and_process_qb_webhook_data(data):
    payment_ids = []
    bill_payment_ids = []
    entities = data['eventNotifications'][0]['dataChangeEvent']['entities']
    for entity in entities:
        if entity['name'] == 'Payment':
            payment_ids.append(entity['id'])
        if entity['name'] == 'BillPayment':
            bill_payment_ids.append(entity['id'])
    logger.error(
        'error updating payment status in trackvia: invoice_payment_ids:{0} or bill_payment_ids:{1} and got error {2}'.format(
            payment_ids, bill_payment_ids, traceback.format_exc()))
    send_email('TV-QBO integeration error'
               'We got an error updating payment status in trackvia: invoice_payment_ids:{0} or bill_payment_ids:{1}.'.format(
        payment_ids, bill_payment_ids))

