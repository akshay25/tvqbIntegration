from core.apis.quickBooks.item import queryItem, createItem
from core.apis.quickBooks.customer import queryCustomer
from core.apis.quickBooks.invoice import createInvoice
from core.apis.quickBooks.taxcode import queryTaxCode
from core.email import send_email
from core.logger import logger


def tvToqb(fullInvoiceData, is_manual):
    invoice_data = fullInvoiceData.get('invoice_data')
    items = fullInvoiceData.get('invoice_items')
    qb_invoice = _invoiceMapper(invoice_data, is_manual)
    qb_invoice['Line'] = _itemsMapper(invoice_data, items, is_manual)
    customer_name = invoice_data.get('CONTRACTOR')
    qb_invoice['CustomerRef'] = _customer_ref(customer_name, qb_invoice.get('DocNumber'), is_manual)
    return qb_invoice


def _invoiceMapper(invoice_data, is_manual):
    return_dict = {
        'DocNumber': invoice_data.get('INVOICE ID'),
        'DueDate': invoice_data.get('DUE DATE'),
        'CustomerMemo': {'value': invoice_data.get('NOTES')},
        'SalesTermRef': {'value': _salesTermMapper(invoice_data.get('PAYMENT TERMS'))},
        'BillEmail': {'Address': invoice_data.get('CONTRACTOR EMAIL')},
        'TxnDate': invoice_data.get('INVOICE DATE'),
        'CustomField': [
            {
                'DefinitionId': '1',
                'Name': 'Project',
                'Type': 'StringType',
                'StringValue': invoice_data.get('PROJECT')
            },
            {
                'DefinitionId': '2',
                'Name': 'Source Document',
                'Type': 'StringType',
                'StringValue': invoice_data.get('SALES ORDER')
            }
        ],
        'TxnTaxDetail': _get_tax_details(invoice_data.get('SALE TAX'), invoice_data.get('INVOICE ID'), is_manual)
    }

    return return_dict


def _customer_ref(cust_name, tv_invoice_id, is_manual):
    result = queryCustomer(cust_name)
    if 'Customer' in result:
        return {'value': result['Customer']['Id']}
    else:
        logger.error(
            'error finding customer: {0} in Quickbooks while processing trackvia {2} invoice: {1}'.format(
                cust_name,
                tv_invoice_id,
                "manual" if is_manual else ""))
        send_email('TV-QBO integeration error',
                   'We got an error finding customer: {0} in Quickbooks while processing trackvia {2} invoice: {1}. Invoice creation/updation failed. Please create customer in quickbooks and retry.'.format(
                       cust_name, tv_invoice_id, "manual" if is_manual else ""))
        raise Exception()


def _itemsMapper(invoice_data, items, is_manual):
    line_items = []

    for item in items:
        
        if is_manual:
            Description = item.get('Description')
            item_name = Description
        else:
            Description = "{0}/{1}".format(
                item['Type'],
                item['Description'])
            item_name = "{0} {1}".format(
                item.get('Manufacturer').upper().rstrip(),
                item.get('Catalog').upper().rstrip())

        Qty = item['Quantity']
        Rate = item['Unit DN'] if is_manual else item['Unit CN']
        Amount = item['Total DN'] if is_manual else item['Total CN']
        ItemRef = _get_item_ref(
            item_name,
            invoice_data['INVOICE ID'],
            is_manual
        )
        line_item = {
            'DetailType': 'SalesItemLineDetail',
            'Description': Description,
            'Amount': Amount,
            'SalesItemLineDetail': {
                'Qty': Qty,
                'UnitPrice': Rate,
                'ItemRef': ItemRef,
                'TaxCodeRef': {'value': 'TAX'}
            }
        }
        line_items.append(line_item)
    freight_data = {
        'ItemName': 'FREIGHT CHARGE',
        'Description': invoice_data['FREIGHT %'],
        'Amount': invoice_data['INV FREIGHT']
    }
    freight = _get_other_item(freight_data, invoice_data['INVOICE ID'], is_manual)
    warehousing_data = {
        'ItemName': 'WAREHOUSING',
        'Description': invoice_data['WAREHOUSING %'],
        'Amount': invoice_data['INV WAREHOUSING']
    }
    warehousing = _get_other_item(warehousing_data, invoice_data['INVOICE ID'], is_manual)
    line_items.extend([freight, warehousing])
    return line_items


# freight and warehousing
def _get_other_item(data, tv_invoice_id, is_manual):
    ItemRef = _get_item_ref(data['ItemName'], tv_invoice_id, is_manual)
    line_item = {
        'DetailType': 'SalesItemLineDetail',
        'Description': data['Description'],
        'Amount': data['Amount'],
        'SalesItemLineDetail': {
            'ItemRef': ItemRef,
            'TaxCodeRef': {'value': 'NON'}
        }
    }
    return line_item


def _get_item_ref(item_name, tv_invoice_id, is_manual):
    result = queryItem(item_name)
    if 'item' in result:
        ItemRef = {
            'name': result['item']['Name'],
            'value': result['item']['Id']
        }
    else:
        try:
            item = createItem(item_name)
            ItemRef = {
                'name': item['Item']['Name'],
                'value': item['Item']['Id']
            }
        except Exception as e:
            logger.error(
                'error creating item: {0} in Quickbooks while processing trackvia {2} invoice: {1}'.format(
                    item_name,
                    tv_invoice_id,
                    "manual" if is_manual else ""
                ))
            send_email('TV-QBO integeration error',
                       'We got an error creating item: {0} in Quickbooks while processing trackvia {2} invoice: {1}. Invoice creation/updation failed. Please check line items in trackvia and retry.'.format(
                           item_name, tv_invoice_id, "manual" if is_manual else ""))
            raise Exception()
    return ItemRef


def _get_tax_details(sales_tax, tv_invoice_id, is_manual):
    sales_tax = sales_tax.strip()
    taxquery = 'OUT_OF_SCOPE'
    if sales_tax != '':
        x = sales_tax.split(' - ')
        if len(x) != 2:
            logger.error(
                'error finding taxcode: {0} in trackvia {2} invoice while parsing sales tax: {1}'.format(
                    sales_tax, tv_invoice_id, "manual" if is_manual else ""))
        else:
            taxquery = x[1]
    taxcode = queryTaxCode(taxquery)
    if 'TaxCode' in taxcode:
        return {'TxnTaxCodeRef': {'value': taxcode['TaxCode']['Id']}}
    else:
        logger.error('error finding taxcode: {0} in Quickbooks while processing trackvia {2} invoice: {1}'.format(
            taxcode,
            tv_invoice_id,
            "manual" if is_manual else ""))
        send_email('TV-QBO integeration error',
                   'We got an error finding taxcode: {0} in Quickbooks while processing trackvia {2} invoice: {1}. Please update the invoice in Quickbooks manually.'.format(
                       sales_tax, tv_invoice_id, "manual" if is_manual else ""))


def _salesTermMapper(term):
    mapper = {
        'NET 30': 3,
        'NET 15': 1,
        'NET 25': 2,
        'NET 60': 4
    }
    return mapper[term] if term in mapper else 3
