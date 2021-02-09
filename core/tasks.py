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
            record = getFullInvoiceData(record_id, view_id)
            if record['invoice_data']['STATUS'] != 'SENT' or isTestProject(record):
                logger.error('ignoring as the record is not in SENT state or it is a test project. {0} | {1} | {2} | {3}'.format(
                    table_id, view_id, record_id, event_type))
                return
            refresh()
            updateInvoiceInQB(record, view_id)
        elif event_type == 'AFTER_DELETE':
            refresh()
            deleteInvoiceFromQB(record_id)
    elif bill_table_id == table_id:
        if event_type == 'AFTER_CREATE':
            logger.error('ignoring bill because AFTER_CREATE event is fired {0} | {1} | {2} | {3}'.format(
                table_id, view_id, record_id, event_type))
            return
        elif event_type == 'AFTER_UPDATE':
            bill_dict = getBillDetailsById(record_id, view_id)
            if bill_dict['STATUS'] != 'APPROVED':
                logger.error('ignoring as the record is not in APPROVED state. {0} | {1} | {2} | {3}'.format(
                table_id, view_id, record_id, event_type))
                return
            refresh()
            updateBIllInQB(bill_dict, view_id)
        elif event_type == 'AFTER_DELETE':
            refresh()
    elif designfee_table_id == table_id:
        if event_type == 'AFTER_CREATE':
            logger.error('ignoring designfee because AFTER_CREATE event is fired {0} | {1} | {2} | {3}'.format(
                table_id, view_id, record_id, event_type))
            return
        elif event_type == 'AFTER_UPDATE':
            designfee_dict = getDesignFeeDetailsById(record_id, view_id)
            if designfee_dict.get('STATUS') != 'SENT':  # Discuss the status
                logger.error('ignoring as the record is not in SENT state. {0} | {1} | {2} | {3}'.format(
                    table_id, view_id, record_id, event_type))
                return
            refresh()
            updateDesignFeeInQB(designfee_dict, view_id)
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
            send_email('TV-QBO integeration error',
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
        if entity['name'] == 'Payment' and entity['operation'] != 'Delete':
            payment_ids.append(entity['id'])
        elif entity['name'] == 'BillPayment' and entity['operation'] != 'Delete':
            bill_payment_ids.append(entity['id'])

    logger.info("payment_ids: {0}, bill_payment_ids: {1}".format(payment_ids, bill_payment_ids))

    processInvoices(payment_ids)

    processBills(bill_payment_ids)

    return


def processInvoices(payment_ids):
    invoice_payment_mapping = []
    for payment_id in payment_ids:
        try:
            payment = readPayment(payment_id)
            if not payment:
                logger.error('processInvoices | payment not found for id {0}'.format(payment_id))
                continue
            lines = []
            if payment.get("Payment") and payment.get("Payment").get("Line"):
                lines = payment.get("Payment").get("Line")
            else:
                logger.error("processInvoices | got incorrect payment object {0}".format(payment))
            for line in lines:
                for ltxn in line['LinkedTxn']:
                    if ltxn['TxnType'] == 'Invoice' and ltxn.get("TxnId"):
                        invoice_payment_mapping.append({
                            "invoice_id": ltxn.get("TxnId"),
                            "payment_id": payment_id
                        })
        except Exception as e:
            logger.error("processInvoices | Unexpected error for payment {0} occurred as {1}".format(payment_id, e))
    invoice_payment_mapping = list(set(invoice_payment_mapping))
    for invoice_payment_map in invoice_payment_mapping:
        if checkIfDesignFee(invoice_payment_map):
            processDesignFee(invoice_payment_map)
        else:
            process_invoice(invoice_payment_map)


def checkIfDesignFee(invoice_id):
    designFeeRef = DesignFeeRef().getDesignFeeRefByQbId(invoice_id)
    return designFeeRef


def process_invoice(invoice_payment_map):
    invoice_id = invoice_payment_map.get("invoice_id")
    payment_id = invoice_payment_map.get("payment_id")
    invoice = readInvoice(invoice_id)

    if not invoice:
        logger.error('invoicein QB not found for {0} | {1}'.format(payment_id, invoice_id))
        return

    logger.info("process_invoice | info |{0} | {1} | {2}".format(payment_id, invoice_id, invoice))

    total_amt = invoice['Invoice']['TotalAmt']
    balance = invoice['Invoice']['Balance']
    logger.info("process_invoice | Sanity Log | {0} | {1} | {2} | {3}".format(
        total_amt, balance, invoice_id, payment_id))

    invoices = InvoiceRef.objects.filter(qb_id=invoice_id)
    if len(invoices) == 0:
        logger.error('process_invoice | invoices in SQL not found for id | {0} | {1}'.format(payment_id, invoice_id))
        return

    tv_invoice_id = invoices[0].tv_id
    view_id = invoices[0].view_id

    logger.info("process_invoice | MasterLog | {0} | {1} | {2}".format(payment_id, invoice_id, tv_invoice_id))

    if total_amt == balance:
        updateTvInvoiceStatus(tv_invoice_id, 'UNPAID', view_id, payment_id)
    elif balance == 0:
        updateTvInvoiceStatus(tv_invoice_id, 'FULL', view_id, payment_id)
    elif balance < total_amt and balance > 0:
        updateTvInvoiceStatus(tv_invoice_id, 'PARTIAL', view_id, payment_id)
    return


def processDesignFee(design_fee_payment_map):
    design_fee_qb_id = design_fee_payment_map.get("invoice_id")
    payment_id = design_fee_payment_map.get("payment_id")
    design_fee_qb_obj = readInvoice(design_fee_qb_id)

    if not design_fee_qb_obj:
        logger.error('processDesignFee | DesignFee in QB not found for {0} | {1}'.format(payment_id, design_fee_qb_id))
        return

    logger.info("processDesignFee | info | {0} | {1} | {2}}".format(payment_id, design_fee_qb_id, design_fee_qb_obj))

    total_amt = design_fee_qb_obj['Invoice']['TotalAmt']
    balance = design_fee_qb_obj['Invoice']['Balance']
    logger.info("processDesignFee | Sanity Log | {0} | {1} | {2} | {3}".format(
        total_amt, balance, design_fee_qb_id, payment_id))

    design_fee_ref = DesignFeeRef().getDesignFeeRefByQbId(design_fee_qb_id)

    if not design_fee_ref:
        logger.error('processDesignFee | DesignFee in SQL not found for id | {0} | {1}'.format(
            payment_id, design_fee_qb_id))
        return

    design_fee_tv_id = design_fee_ref.tv_id
    view_id = design_fee_ref.view_id

    logger.info("processDesignFee | MasterLog | {0} | {1} | {2}".format(payment_id, design_fee_qb_id, design_fee_tv_id))

    if total_amt == balance:
        updateDesignFeeStatus(design_fee_tv_id, 'UNPAID', view_id, payment_id)
    elif balance == 0:
        updateDesignFeeStatus(design_fee_tv_id, 'FULL', view_id, payment_id)
    elif 0 < balance < total_amt:
        updateDesignFeeStatus(design_fee_tv_id, 'PARTIAL', view_id, payment_id)

    return


def processBills(payment_ids):
    bill_payment_mapping = []
    for payment_id in payment_ids:
        try:
            payment = readBillPayment(payment_id)
            if not payment:
                logger.error('processBills | BillPayment not found for id | {0}'.format(payment_id))
                break
            lines = []
            if payment.get("BillPayment") and payment.get("BillPayment").get("Line"):
                lines = payment.get("BillPayment").get("Line")
            else:
                logger.error("processBills | got incorrect payment object {0}".format(payment))
            for line in lines:
                for ltxn in line['LinkedTxn']:
                    if ltxn['TxnType'] == 'Bill' and ltxn.get('TxnId'):  # Confirm this type
                        bill_payment_mapping.append({
                            "bill_id": ltxn.get("TxnId"),
                            "payment_id": payment_id
                        })
        except Exception as e:
            logger.error("processBills | Unexpected error for payment {0} occurred as {1}".format(payment_id, e))
    bill_payment_mapping = list(set(bill_payment_mapping))
    for bill_payment_mapping in bill_payment_mapping:
        process_bill(bill_payment_mapping)


def process_bill(bill_payment_mapping):
    bill_id = bill_payment_mapping.get("bill_id")
    payment_id = bill_payment_mapping.get("payment_id")
    bill = readBillFromQB(bill_id)

    if not bill:
        logger.error('process_bill | Bill in QB not found for {0} | {1}'.format(payment_id, bill_id))
        return

    logger.info("process_bill | info | {0} | {1} | {2}}".format(payment_id, bill_id, bill))

    total_amt = bill.get('Bill').get('TotalAmt')
    balance = bill.get('Bill').get('Balance')
    logger.info("process_bill | Sanity Log | {0} | {1} | {2} | {3}".format(
        total_amt, balance, bill_id, payment_id))

    bill_refs = BillExpenseReference.objects.filter(qb_id=bill_id)
    if len(bill_refs) == 0:
        logger.error('process_bill | Bill in SQL not found for id | {0} | {1}'.format(
            payment_id, bill_id))
        return

    tv_id = bill_refs[0].tv_id
    view_id = bill_refs[0].view_id

    logger.info("process_bill | MasterLog | {0} | {1} | {2}".format(payment_id, bill_id, tv_id))

    if total_amt == balance:
        updateTvBillStatus(tv_id, 'UNPAID', view_id, payment_id)
    elif balance == 0:
        updateTvBillStatus(tv_id, 'FULL', view_id, payment_id)
    elif 0 < balance < total_amt:
        updateTvBillStatus(tv_id, 'PARTIAL', view_id, payment_id)

    return
