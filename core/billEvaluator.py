from core.apis.quickBooks.attachable import downloadFileFromLink, attachNoteToEntity
from core.apis.quickBooks.bill import updateBillInQB, createBillInQB, deleteBillInQB
from core.billToExpenseMapper import billToExpense
from core.models import BillExpenseReference
from tvqbIntegration.utility.s3 import upload_file

file_root_path = '/tmp/'

def updateBIllInQB(bill_dict):
    bill_expense = billToExpense(bill_dict)
    bill_ref = BillExpenseReference().getBillExpenseReferanceByTvId(bill_id=bill_dict.get('bill_id'))
    if bill_ref:
        bill_expense['Id'] = bill_ref.qb_id
        updateBillInQB(bill_expense)
        print('updated bill in qb')
    else:
        bill_in_qb = createBillInQB(bill_expense)
        if bill_dict.get('BILL PDF LINK'):
            downloadAndForwardAttachable(bill_dict, bill_in_qb)

        bill_expense_ref = BillExpenseReference(
            tv_id=bill_dict.get('bill_id'),
            qb_id=bill_in_qb.get('Bill').get('Id')
            # bill_pdf=bill_dict.get('BILL PDF LINK')
        )
        try:
            bill_expense_ref.save()
            print('created bill in qb')
        except Exception as e:
            print('Exception in creating BillExpenseReference as ' + str(e))
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
        file_root_path + attachableName
    )
    attachNoteToEntity(
        s3_link,
        bill_in_qb.get('Bill').get('Id'),
        'Bill'
    )
    print('pushed to s3')


def deleteBillFromQB(tv_bill_id):
    bill = BillExpenseReference().getBillExpenseReferanceByTvId(bill_id=tv_bill_id)
    if not bill:
        print('deleteBillFromQB: No bill found.')
        return

    deleteBillInQB(bill.qb_id)

    bill.delete()
    bill.save()

    print('deleted bill from qb: ', bill.qb_id)
