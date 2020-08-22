from core.apis.quickBooks.item import queryItem
from core.apis.quickBooks.vendor import getVendor
from core.email import send_email
from core.logger import logger


item_1_name = "Cost of Goods Sold:Purchases"
item_2_name = "Freight"


def billToExpense(bill_dict):
    return _billMapper(bill_dict)


def _billMapper(bill_dict):
    return {
        'TxnDate': bill_dict.get('BILL DATE'),
        'DueDate': bill_dict.get('DUE DATE'),
        'VendorRef': _getVendorRef(bill_dict.get('MANUFACTURER')),
        'TotalAmt': bill_dict.get('BILL TOTAL'),
        'Line': _getLineItems(
            bill_dict.get('SUBTOTAL'),
            bill_dict.get('FREIGHT'),
            bill_dict.get('PO# FROM DOCPARSER'),
            bill_dict.get('FREIGHT FROM DOCPARSER')),
        # 'status': _getPaymentStatus(bill_dict.get('PAYMENT STATUS')),
        'SyncToken': 1
        # 'BillPDF': bill_dict.get('BILL PDF LINK')
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
        # raise Exception()

    return {
        'name': vendorRef.get('DisplayName', 'Robertson & Associates') if vendorRef else 'Robertson & Associates',
        'value': vendorRef.get('Id', '49') if vendorRef else '49',
    }


def _getPaymentStatus(key):
    status_mapping_dict = {
        'UNPAID': 'Pending'
    }
    return status_mapping_dict.get(key, 'Draft')  # Discus Logic


def _getLineItems(subtotal, freight_charge, po_from_docparser, freight_from_docparser):
    lineList = []

    item_1 = queryItem(item_1_name)
    if item_1 and item_1.get('item'):
        lineList.append(
            {
                # 'Id': '1',
                # 'LineNum': '1',
                'Description': po_from_docparser,
                'Amount': subtotal if subtotal else '0',
                'DetailType': 'ItemBasedExpenseLineDetail',  # Logic to be discussed
                'ItemBasedExpenseLineDetail': {
                    'Qty': '1',  # item_1.get('item').get('#### '),
                    'UnitPrice': item_1.get('item').get('Unit CN'),
                    # 'Amount': item_1.get('item').get('Total CN'),
                    'ItemRef': {
                        'name': item_1.get('item').get('Name'),
                        'value': item_1.get('item').get('Id')
                    },
                    'TaxCodeRef': {'value': 'TAX'}
                }
            }
        )

    item_2 = queryItem(item_2_name)
    if item_2 and item_2.get('item'):
        lineList.append(
            {
                # 'Id': '1',
                # 'LineNum': '2',
                'Description': freight_from_docparser,
                'Amount': freight_charge if freight_charge else '0',
                'DetailType': 'ItemBasedExpenseLineDetail',  # Logic to be discussed
                'ItemBasedExpenseLineDetail': {
                    'Qty': '1',  # item_1.get('item').get('#### '),
                    'UnitPrice': item_2.get('item').get('Unit CN'),
                    # 'Amount': item_2.get('item').get('Total CN'),
                    'ItemRef': {
                        'name': item_2.get('item').get('Name'),
                        'value': item_2.get('item').get('Id')
                    },
                    'TaxCodeRef': {'value': 'TAX'}
                }
            }
        )

    return lineList
