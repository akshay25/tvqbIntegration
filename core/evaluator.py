from core.fieldMapper import tvToqb
from core.apis.quickBooks.invoice import deleteInvoice, updateInvoice, createInvoice

def updateInvoiceInQB(tv_invoice):
    qb_invoice = tbToqb(tv_invoice)
    invoices = InvoiceRef.objects.filter(tv_id=tv_invoice['INVOICE ID'])
    if len(invoices) == 1:
        qb_invoice['Id'] = invoices[0]['qb_id']
        print('update invoice in qb:', qb_invoice)
        #updateInvoice(qb_invoice)
    else:
        print('create invoice in qb:', qb_invoice)
        #invoice = createInvoice(qb_invoice)

        #invoice_ref = InvoiceRef(tv_id=tv_invoice['INVOICE ID'], qb_id=invoice['Id'])
        #invoice_ref.save()
    return

def deleteInvoiceFromQB(tv_invoice):
    invoices = InvoiceRef.objects.filter(tv_id=tv_invoice['INVOICE ID'])
    if len(invoices) == 0:
        return
    print('delete invoice from qb: ', invoices[0]['qb_id'])
    #deleteInvoice(invoices[0]['qb_id'])
