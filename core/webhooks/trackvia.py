from core.apis.quickBooks.authentication import refresh
from core.apis.quickBooks.bill.billEvaluator import updateBIllInQB
from core.apis.quickBooks.invoice.evaluator import updateInvoiceInQB, deleteInvoiceFromQB
from core.apis.trackvia.bills import getBillDetailsById
from core.apis.trackvia.invoice import getFullInvoiceData
from core.logger import logger
from core.tasks import isTestProject


def tv_invoice_webhook(event_type, record_id, table_id, view_id):
    if event_type == 'AFTER_CREATE':
        logger.error('ignoring invoice because AFTER_CREATE event is fired {0} | {1} | {2} | {3}'.format(
            table_id, view_id, record_id, event_type))
        return
    elif event_type == 'AFTER_UPDATE':
        record = getFullInvoiceData(record_id)
        if record['invoice_data']['STATUS'] != 'SENT' or isTestProject(record):
            logger.error(
                'ignoring as the record is not in SENT state or it is a test project. {0} | {1} | {2} | {3}'.format(
                    table_id, view_id, record_id, event_type))
            return
        refresh()
        updateInvoiceInQB(record)
    elif event_type == 'AFTER_DELETE':
        refresh()
        deleteInvoiceFromQB(record_id)


def tv_bill_webhook(event_type, record_id, table_id, view_id):
    if event_type == 'AFTER_CREATE':
        logger.error('ignoring bill because AFTER_CREATE event is fired {0} | {1} | {2} | {3}'.format(
            table_id, view_id, record_id, event_type))
        # return
    elif event_type == 'AFTER_UPDATE':
        bill_dict = getBillDetailsById(record_id)
        if bill_dict['STATUS'] != 'APPROVED':
            logger.error(
                'ignoring as the record is not in APPROVED state or it is a test project. {0} | {1} | {2} | {3}'.format(
                    table_id, view_id, record_id, event_type))
            # return
        refresh()
        updateBIllInQB(bill_dict)
    elif event_type == 'AFTER_DELETE':
        refresh()