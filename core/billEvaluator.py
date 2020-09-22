from core.apis.quickBooks.attachable import downloadFileFromLink, attachNoteToEntity
from core.apis.quickBooks.bill import updateBillInQB, createBillInQB, deleteBillInQB
from core.billToExpenseMapper import billToExpense
from core.models import BillExpenseReference
from core.email import send_email
from core.logger import logger

import os

from tvqbIntegration.utility.s3 import upload_file

file_root_path = '/tmp/'


def updateBIllInQB(bill_dict):
    bill_expense = billToExpense(bill_dict)
    bill_ref = BillExpenseReference().getBillExpenseReferanceByTvId(bill_id=bill_dict.get('bill_id'))
    if bill_ref:
        bill_expense['Id'] = bill_ref.qb_id
        updateBillInQB(bill_expense)
        logger.info('updateBIllInQB | updated bill in qb {0}'.format(bill_dict))
    else:
        bill_in_qb = createBillInQB(bill_expense)
        # if bill_dict.get('BILL PDF LINK'):
            # downloadAndForwardAttachable(bill_dict, bill_in_qb)

        bill_expense_ref = BillExpenseReference(
            tv_id=bill_dict.get('bill_id'),
            qb_id=bill_in_qb.get('Bill').get('Id')
        )
        try:
            bill_expense_ref.save()
            logger.info('updateBIllInQB | created bill in qb {0}'.format(bill_dict))
        except Exception as e:
            logger.error("updateBIllInQB | Error in updateBIllInQB {0}".format(bill_dict))
            logger.error(str(e))
    return


def downloadAndForwardAttachable(bill_dict, bill_in_qb):
    attachableName = bill_dict.get('BILL PDF') if len(bill_dict.get('BILL PDF')) else bill_in_qb.get('Bill').get('DocNumber') + ".pdf"
    downloadFileFromLink(
        attachableName,
        bill_dict.get('BILL PDF LINK')
    )
    s3AttachableName = "bill_attachments/" + attachableName
    s3_link = upload_file(
        s3AttachableName,
        file_root_path + attachableName,
        True
    )
    attachNoteToEntity(
        s3_link,
        bill_in_qb.get('Bill').get('Id'),
        'Bill'
    )
    deleteAttachemnt(attachableName)
    logger.info('downloadAndForwardAttachable | pushed to s3 | bill: {0}'.format(bill_dict))


def deleteAttachemnt(fileName):
    os.remove(file_root_path + fileName)


def deleteBillFromQB(tv_bill_id):
    bill = BillExpenseReference().getBillExpenseReferanceByTvId(bill_id=tv_bill_id)
    if not bill:
        logger.error("deleteBillFromQB: No bill found for {0}".format(tv_bill_id))
        return

    deleteBillInQB(bill.qb_id)

    bill.delete()
    bill.save()

    logger.info('deleted bill from qb: {0}'.format(bill.qb_id))
