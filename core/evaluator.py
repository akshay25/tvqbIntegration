from core.fieldMapper import tvToqb
from core.apis.quickBooks.invoice import deleteInvoice, updateInvoice, createInvoice
from .models import InvoiceRef


def updateInvoiceInQB(tv_invoice, view_id):
    is_manual = True if tv_invoice.get('is_manual') else False
    qb_invoice = tvToqb(tv_invoice, is_manual)
    invoices = InvoiceRef.objects.filter(tv_id=tv_invoice['invoice_data']['tv_id'])
    if len(invoices) == 1:
        qb_invoice['Id'] = invoices[0].qb_id
        updateInvoice(qb_invoice)
        print('updated invoice in qb')
    else:
        invoice = createInvoice(qb_invoice)
        invoice_ref = InvoiceRef(
            tv_id=tv_invoice['invoice_data']['tv_id'],
            qb_id=invoice['Invoice']['Id'],
            view_id=view_id,
            is_manual=is_manual
        )
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
