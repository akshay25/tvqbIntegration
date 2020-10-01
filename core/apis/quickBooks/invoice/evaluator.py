from core.apis.quickBooks.invoice.fieldMapper import tvToqb
from core.apis.quickBooks.invoice.invoice import deleteInvoice, updateInvoice, createInvoice
from core.models import InvoiceRef


def updateInvoiceInQB(tv_invoice):
    qb_invoice = tvToqb(tv_invoice)
    invoices = InvoiceRef.objects.filter(tv_id=tv_invoice['invoice_data']['tv_id'])
    if len(invoices) == 1:
        qb_invoice['Id'] = invoices[0].qb_id
        updateInvoice(qb_invoice)
        print('updated invoice in qb')
    else:
        invoice = createInvoice(qb_invoice)
        invoice_ref = InvoiceRef(tv_id=tv_invoice['invoice_data']['tv_id'], qb_id=invoice['Invoice']['Id'])
        invoice_ref.save()
        print('created invoice in qb')
    return


def deleteInvoiceFromQB(tv_invoice_id):
    invoices = InvoiceRef.objects.filter(tv_id=tv_invoice_id)
    if len(invoices) == 0:
        print('deleteInvoiceFromQB: No invoice found.')
        return
    deleteInvoice(invoices[0].qb_id)
    invoices[0].delete()
    print('delete invoice from qb: ', invoices[0]['qb_id'])
