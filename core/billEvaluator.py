from core.apis.quickBooks.bill import updateBillInQB, createBillInQB, deleteBillInQB
from core.billToExpenseMapper import billToExpense
from core.models import BillExpenseReference


def updateBIllInQB(bill_dict):
    bill_expense = billToExpense(bill_dict)
    bill_ref = BillExpenseReference().getBillExpenseReferanceByTvId(bill_id=bill_dict.get('bill_id'))
    if bill_ref:
        bill_expense['Id'] = bill_ref.qb_id
        updateBillInQB(bill_expense)
        print('updated bill in qb')
    else:
        bill_in_qb = createBillInQB(bill_expense)
        bill_expense_ref = BillExpenseReference(
            tv_id=bill_dict.get('bill_id'),
            qb_id= bill_in_qb.get('Bill').get('Id')
            # bill_pdf=bill_dict.get('BILL PDF LINK')
        )
        try:
            bill_expense_ref.save()
            print('created invoice in qb')
        except Exception as e:
            print('Exception in creating BillExpenseReference as ' + str(e))
    return


def deleteBillFromQB(tv_bill_id):
    bill = BillExpenseReference.getBillExpenseReferanceByTvId(bill_id=tv_bill_id)
    if not bill:
        print('deleteBillFromQB: No bill found.')
        return

    deleteBillInQB(bill.qb_id)

    bill.delete()
    bill.save()

    print('deleted bill from qb: ', bill.qb_id)
