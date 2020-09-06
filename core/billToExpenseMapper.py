from core.apis.quickBooks.item import queryItem
from core.apis.quickBooks.vendor import getVendor
from core.email import send_email
from core.logger import logger


item_1_name = "Cost of Goods Sold:Purchases"
freight_item_name = "Freight Charge"


def billToExpense(bill_dict):
    return _billMapper(bill_dict)


def _billMapper(bill_dict):
    return {
        'DocNumber': bill_dict['BILL #'],
        'TxnDate': bill_dict['BILL DATE'],
        'DueDate': bill_dict['DUE DATE'],
        'VendorRef': _getVendorRef(bill_dict['MANUFACTURER']),
        'TotalAmt': bill_dict.get('BILL TOTAL'),
        'Line': _getLineItems(
            bill_dict['SUBTOTAL'],
            bill_dict['FREIGHT'],
            bill_dict['PO# FROM DOCPARSER'],
            bill_dict['FREIGHT FROM DOCPARSER'])
    }


def _getVendorRef(name):
    vendorRef = getVendor(name)
    if not vendorRef:
        logger.error(
            'error finding customer: {0} in Quickbooks while processing trackvia bill'.format(name))
        send_email('TV-QBO integeration error',
                   'We got an error finding customer: {0} in Quickbooks while processing trackvia bill.'
                   ' Bill creation/updation failed. Please create customer in quickbooks and retry.'.format(
                       name))
        raise Exception()
    return { 'value': vendorRef['Vendor']['Id'] }


def _getLineItems(subtotal, freight_charge, po_from_docparser, freight_from_docparser):
    lineList = list()

    lineList.append(
        {
            'Description': po_from_docparser,
            'Amount': subtotal if subtotal else '0',
            'DetailType': 'AccountBasedExpenseLineDetail',
            'AccountBasedExpenseLineDetail': {
                'AccountRef': {
                    'value': '47'
                },
                'TaxCodeRef': {'value': 'TAX'}
            }
        }
    )

    freight_item = queryItem(freight_item_name)
    if freight_item and freight_item.get('item'):
        lineList.append(
            {
                'Description': freight_from_docparser,
                'Amount': freight_charge if freight_charge else '0',
                'DetailType': 'ItemBasedExpenseLineDetail',
                'ItemBasedExpenseLineDetail': {
                    'ItemRef': {
                        'name': freight_item.get('item').get('Name'),
                        'value': freight_item.get('item').get('Id')
                    },
                    'TaxCodeRef': {'value': 'NON'}
                }
            }
        )

    return lineList
