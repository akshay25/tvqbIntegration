from celery import shared_task

import re
import base64, hmac, hashlib, json
import traceback
from datetime import date, timedelta

from core.apis.quickBooks.bill import readBillFromQB
from core.apis.quickBooks.billpayment import readBillPayment
from core.apis.quickBooks.invoice import readInvoice
from core.apis.quickBooks.payment import readPayment
from core.apis.quickBooks.authentication import refresh
from core.apis.trackvia.bills import getBillDetailsById, updateTvBillStatus
from core.apis.trackvia.designfee import getDesignFeeDetailsById, updateDesignFeeStatus
from core.apis.trackvia.invoice import getFullInvoiceData, updateTvInvoiceStatus
from core.designFeeEvaluator import updateDesignFeeInQB
from core.evaluator import updateInvoiceInQB, deleteInvoiceFromQB
from core.billEvaluator import updateBIllInQB
from core.email import send_email
from core.logger import logger
from core.models import InvoiceRef, BillExpenseReference, DesignFeeRef
from tvqbIntegration.utility.s3 import upload_file

from django.conf import settings

invoice_table_id = '740'
invoice_view_id = '4027'
bill_table_id = '786'
bill_view_id = '4205'
designfee_table_id = '743'
designfee_view_id = '4047'


@shared_task
def process_tv_webhook(table_id, view_id, record_id, event_type):
    if invoice_table_id == table_id:
        if event_type == 'AFTER_CREATE':
            logger.error('ignoring invoice because AFTER_CREATE event is fired {0} | {1} | {2} | {3}'.format(
                table_id, view_id, record_id, event_type))
            return
        elif event_type == 'AFTER_UPDATE':
            record = getFullInvoiceData(record_id)
            if record['invoice_data']['STATUS'] != 'SENT' or isTestProject(record):
                logger.error('ignoring as the record is not in SENT state or it is a test project. {0} | {1} | {2} | {3}'.format(
                    table_id, view_id, record_id, event_type))
                return
            refresh()
            updateInvoiceInQB(record)
        elif event_type == 'AFTER_DELETE':
            refresh()
            deleteInvoiceFromQB(record_id)
    elif bill_table_id == table_id:
        if event_type == 'AFTER_CREATE':
            logger.error('ignoring bill because AFTER_CREATE event is fired {0} | {1} | {2} | {3}'.format(
                table_id, view_id, record_id, event_type))
            return
        elif event_type == 'AFTER_UPDATE':
            bill_dict = getBillDetailsById(record_id)
            if bill_dict['STATUS'] != 'APPROVED':
                logger.error('ignoring as the record is not in APPROVED state. {0} | {1} | {2} | {3}'.format(
                table_id, view_id, record_id, event_type))
                return
            refresh()
            updateBIllInQB(bill_dict)
        elif event_type == 'AFTER_DELETE':
            refresh()
    elif designfee_table_id == table_id:
        if event_type == 'AFTER_CREATE':
            logger.error('ignoring designfee because AFTER_CREATE event is fired {0} | {1} | {2} | {3}'.format(
                table_id, view_id, record_id, event_type))
            return
        elif event_type == 'AFTER_UPDATE':
            designfee_dict = getDesignFeeDetailsById(record_id)
            if designfee_dict.get('STATUS') != 'SEND INVOICE':  # Discuss the status
                logger.error('ignoring as the record is not in SEND INVOICE state. {0} | {1} | {2} | {3}'.format(
                    table_id, view_id, record_id, event_type))
                return
            refresh()
            updateDesignFeeInQB(designfee_dict)
        elif event_type == 'AFTER_DELETE':
            refresh()
            deleteInvoiceFromQB(record_id)
    else:
        pass


@shared_task
def process_qb_webhook(signature, body_unicode, verifier_token):
    logger.info('validating data.. ##################')
    if verifyWebhookData(body_unicode, signature, verifier_token):
        try:
            refresh()
            processWebhookData(body_unicode)
        except Exception as e:
            data = json.loads(body_unicode)
            payment_ids = []
            bill_payment_ids = []
            entities = data['eventNotifications'][0]['dataChangeEvent']['entities']
            for entity in entities:
                if entity['name'] == 'Payment':
                    payment_ids.append(entity['id'])
                if entity['name'] == 'BillPayment':
                    bill_payment_ids.append(entity['id'])
            logger.error('error updating payment status in trackvia: invoice_payment_ids:{0} or bill_payment_ids:{1} and got error {2}'.format(
                payment_ids, bill_payment_ids, traceback.format_exc()))
            send_email('TV-QBO integeration error'
                       'We got an error updating payment status in trackvia: invoice_payment_ids:{0} or bill_payment_ids:{1}.'.format(
                           payment_ids, bill_payment_ids))
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
        # print(hmac_hex_digest == decoded_hex_signature, ' ^^^^^^^^^^^^^')
        return hmac_hex_digest == decoded_hex_signature
    except Exception as e:
        return False


def processWebhookData(body_unicode):
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
        if checkIfDesignFee(invoice_id):
            process_DesignFee(invoice_id)
        else:
            process_invoice(invoice_id)


def checkIfDesignFee(invoice_id):
    designFeeRef = DesignFeeRef().getDesignFeeRefByTvId(invoice_id)
    return designFeeRef


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


def process_DesignFee(design_fee_qb_id):
    design_fee_qb_obj = readInvoice(design_fee_qb_id)
    logger.info("process_DesignFee | {0} | {1}".format(design_fee_qb_id, invoice))

    if design_fee_qb_obj == None:
        logger.error('design_fee_qb_obj not found for id {0}'.format(design_fee_qb_id))
        return

    total_amt = design_fee_qb_obj['Invoice']['TotalAmt']
    balance = design_fee_qb_obj['Invoice']['Balance']
    logger.info("process_DesignFee | {0} | {1}".format(total_amt, balance))

    design_fee_ref = DesignFeeRef().getDesignFeeRefByQbId(design_fee_qb_id)

    if not design_fee_ref:
        logger.error('process_DesignFee | DesignFee not found for id | {0}'.format(design_fee_qb_id))
        return

    design_fee_tv_id = design_fee_ref.tv_id

    if total_amt == balance:
        updateDesignFeeStatus(design_fee_tv_id, 'UNPAID')
    elif balance == 0:
        updateDesignFeeStatus(design_fee_tv_id, 'FULL')
    elif 0 < balance < total_amt:
        updateDesignFeeStatus(design_fee_tv_id, 'PARTIAL')

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
