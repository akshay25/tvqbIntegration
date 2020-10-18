# coding=utf-8
from core.apis.quickBooks.customer import queryCustomer
from core.apis.quickBooks.item import queryItem
from core.email import send_email
from core.logger import logger


def mapDesignFeeToQBAndReturn(tvDesignFeeDict):
    qbMappedData = getDesignFeeMapping(tvDesignFeeDict)
    customerName = tvDesignFeeDict.get('DESIGNER TO INVOICE')
    qbMappedData['CustomerRef'] = _customer_ref(
        customerName,
        tvDesignFeeDict.get('DESIGN INVOICE #'))
    qbMappedData['Line'] = _getLine(
        tvDesignFeeDict.get('PHASE'),
        tvDesignFeeDict.get('PHASE') + ' - ' + tvDesignFeeDict.get('DESCRIPTION'),
        tvDesignFeeDict.get('TOTAL $'),  # Check the amount of items
        tvDesignFeeDict.get('DESIGN INVOICE #')
    )
    return qbMappedData


def getDesignFeeMapping(designFeeDict):
    return {
        'DocNumber': designFeeDict.get('DESIGN INVOICE #'),
        'DueDate':designFeeDict.get('DUE DATE'),  # check is due date and submission date are same
        'TxnDate': designFeeDict.get('SENT DATE'),  # check is due date and submission date are same
        'TotalAmt': designFeeDict.get('TOTAL $')
    }


def _customer_ref(cust_name, df_id):
    result = queryCustomer(cust_name)
    if 'Customer' in result:
        return {
            'value': result['Customer']['Id']
        }
    else:
        logger.error(
            'error finding customer: {0} in Quickbooks while processing trackvia design fee: {1}'.format(cust_name,
                                                                                                         df_id))
        send_email('TV-QBO integeration error',
                   'We got an error finding customer: {0} in Quickbooks while processing trackvia trackvia design fee:'
                   ' {1}. design fee creation/updation failed. Please create customer in quickbooks and retry.'
                   ''.format(cust_name, df_id))
        raise Exception()


def _getLine(phase, description, amount, df_id):
    line_items = []
    if 'REIMBURSABLE' == phase:
        item_name = 'REIMBURSABLE'
    else:
        item_name = 'LIGHTING DESIGN SERVICES'

    itemRef = _get_item_ref(item_name, df_id)
    line_item = {
        'DetailType': 'SalesItemLineDetail',
        'Description': description,
        'Amount': amount,
        'SalesItemLineDetail': {
            'Qty': 1,
            'UnitPrice': amount,
            'ItemRef': itemRef,
            'TaxCodeRef': {'value': 'NON'}
        }
    }
    line_items.append(line_item)

    return line_items


def _get_item_ref(item_name, df_id):
    ItemRef = None
    result = queryItem(item_name)
    if 'item' in result:
        ItemRef = {
            'name': result['item']['Name'],
            'value': result['item']['Id']
        }
    else:
        logger.error('error querying item: {0} in Quickbooks while processing trackvia DesignerFee: {1}'.format(
            item_name, df_id))
        send_email('TV-QBO integeration error',
                   'We got an error creating item: {0} in Quickbooks while processing trackvia DesignerFee: {1}.'
                   ' Invoice creation/updation failed. Please check line items in trackvia and retry.'
                   ''.format(item_name, df_id))
    return ItemRef
