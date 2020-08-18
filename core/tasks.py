from celery import shared_task
from celery.contrib import rdb

import re
import base64, hmac, hashlib, json
import traceback
from datetime import date, timedelta

from core.apis.quickBooks.bill import readBillFromQB
from core.apis.quickBooks.invoice import readInvoice
from core.apis.quickBooks.payment import readPayment
from core.apis.quickBooks.authentication import refresh
from core.apis.trackvia.bills import getBillDetailsById, updateTvBillStatus
from core.apis.trackvia.invoice import getFullInvoiceData, updateTvInvoiceStatus
from core.evaluator import updateInvoiceInQB, deleteInvoiceFromQB
from core.billEvaluator import updateBIllInQB
from core.models import InvoiceRef, BillExpenseReference
from tvqbIntegration.utility.s3 import upload_file

from django.conf import settings

invoice_table_id = '740'
invoice_view_id = '4027'
bill_table_id = '786'
bill_view_id = '4205'


@shared_task
def process_tv_webhook(table_id, view_id, record_id, event_type):
    if invoice_table_id == table_id and invoice_view_id == view_id:
        if event_type == 'AFTER_CREATE':
            print('ignoring invoice because AFTER_CREATE event is fired')
            return
        elif event_type == 'AFTER_UPDATE':
            record = getFullInvoiceData(record_id)
            if record['invoice_data']['STATUS'] != 'SENT' or isTestProject(record):
                print('ignoring as the record is not in SENT state or it is a test project.')
                return
            refresh()
            updateInvoiceInQB(record)
        elif event_type == 'AFTER_DELETE':
            refresh()
            deleteInvoiceFromQB(record_id)
    elif bill_table_id == table_id and bill_view_id == view_id:
        # from celery.contrib import rdb
        # rdb.set_trace()
        if event_type == 'AFTER_CREATE':
            print('ignoring bill because AFTER_CREATE event is fired')
            return
        elif event_type == 'AFTER_UPDATE':
            bill_dict = getBillDetailsById(record_id)
            if bill_dict['STATUS'] != 'APPROVED':
                print('ignoring as the record is not in SENT state or it is a test project.')
                return
            refresh()
            updateBIllInQB(bill_dict)
        elif event_type == 'AFTER_DELETE':
            refresh()
    else:
        pass


@shared_task
def process_qb_webhook(signature, body_unicode, verifier_token):
    print('validating data.. ##################')
    if verifyWebhookData(body_unicode, signature, verifier_token):
        try:
            refresh()
            processWebhookData(body_unicode)
        except Exception as e:
            data = json.loads(body_unicode)
            payment_ids = []
            entities = data['eventNotifications'][0]['dataChangeEvent']['entities']
            for entity in entities:
                if entity['name'] == 'Payment':
                    payment_ids.append(entity['id'])
            logger.error(
                'error updating payment status in trackvia: {0} and got error {2}'.format(', '.join(payment_ids),
                                                                                          traceback.format_exc()))
            send_email('TV-QBO integeration error',
                       'We got an error updating payment status in trackvia: {0}.'.format(', '.join(payment_ids)))
    else:
        print('webhook data temepered $$$$$$$---------')
        return


# @shared_task
# def process_qb_webhook(signature, body_unicode, verifier_token):
#     print('validating data.. ##################')
#     if verifyWebhookData(body_unicode, signature, verifier_token):
#         try:
#             refresh()
#             processInvoiceWebhookData(body_unicode)
#         except Exception as e:
#             data = json.loads(body_unicode)
#             payment_ids = []
#             entities = data['eventNotifications'][0]['dataChangeEvent']['entities']
#             for entity in entities:
#                 if entity['name'] == 'Payment':
#                     payment_ids.append(entity['id'])
#             logger.error('error updating payment status in trackvia: {0} and got error {2}'.format(', '.join(payment_ids), traceback.format_exc()))
#             send_email('TV-QBO integeration error', 'We got an error updating payment status in trackvia: {0}.'.format(', '.join(payment_ids)))
#     else:
#         print('webhook data temepered $$$$$$$---------')
#         return


# beat function
@shared_task
def push_logs_to_S3():
    yesterday = date.today() - timedelta(days=1)
    filepath = settings.BASE_DIR + '/debug.log.' + yesterday.strftime('%Y-%m-%d')
    filename = 'debug.log.' + yesterday.strftime('%Y-%m-%d')
    upload_file(filename, filepath)


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
    try:
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
    except Exception as e:
        return False


def processWebhookData(body_unicode):
    data = json.loads(body_unicode)
    print('processInvoiceWebhookData')
    payment_ids = []
    bill_payment_ids = []
    entities = data['eventNotifications'][0]['dataChangeEvent']['entities']
    for entity in entities:
        if entity['name'] == 'Payment':
            payment_ids.append(entity['id'])
        elif entity['name'] == 'Bill Payment':
            bill_payment_ids.append(entity['id'])

    print(payment_ids, "!!!!!!!!!!!")
    print(bill_payment_ids, " &&&&&&&&&&&")

    processInvoices(payment_ids)

    processBills(bill_payment_ids)

    return


def processInvoices(payment_ids):
    invoice_ids = []
    for payment_id in payment_ids:
        payment = readPayment(payment_id)
        if payment == None:
            print('payment not found for id ', payment_id)
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


def processBills(payment_ids):
    bill_ids = []
    for payment_id in payment_ids:
        payment = readPayment(payment_id)
        if not payment:
            print('payment not found for id ', payment_id)
            break
        lines = payment['Payment']['Line']
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
        print('bill not found for id ', bill_id)
        return

    print(bill)

    total_amt = bill.get('Bill').get('TotalAmt')
    balance = bill.get('Bill').get('Balance')
    print(total_amt, balance, '************************')

    bill_referance = BillExpenseReference.getBillExpenseReferanceByTvId(bill_id)

    if not bill_referance:
        return

    tv_id = bill_referance.tv_id

    if total_amt == balance:
        updateTvBillStatus(tv_id, 'UNPAID')
    elif balance == 0:
        updateTvBillStatus(tv_id, 'FULL')
    elif 0 < balance < total_amt:
        updateTvBillStatus(tv_id, 'PARTIAL')

    #   # Bill payment Logic
    return
