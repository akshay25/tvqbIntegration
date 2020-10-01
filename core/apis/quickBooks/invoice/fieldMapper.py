from core.apis.quickBooks.item import queryItem, createItem
from core.apis.quickBooks.customer import queryCustomer
from core.apis.quickBooks.taxcode import queryTaxCode
from core.email import send_email
from core.logger import logger

def tvToqb(fullInvoiceData):
    invoice_data = fullInvoiceData['invoice_data']
    items = fullInvoiceData['invoice_items']
    qb_invoice = _invoiceMapper(invoice_data)
    qb_invoice['Line'] = _itemsMapper(invoice_data, items)
    customer_name = invoice_data['CONTRACTOR']
    qb_invoice['CustomerRef'] = _customer_ref(customer_name, qb_invoice['DocNumber'])
    return qb_invoice

def _invoiceMapper(invoice_data):
    return {
        'DocNumber': invoice_data['INVOICE ID'],
        'DueDate': invoice_data['DUE DATE'],
        'CustomerMemo': {'value': invoice_data['NOTES']},
        'SalesTermRef': {'value': _salesTermMapper(invoice_data['PAYMENT TERMS'])},
        'BillEmail': {'Address': invoice_data['CONTRACTOR EMAIL']},
        'TxnDate': invoice_data['INVOICE DATE'],
        'TxnTaxDetail': _get_tax_details(invoice_data['SALE TAX'], invoice_data['INVOICE ID']),
        'CustomField': [
            {
                'DefinitionId': '1',
                'Name': 'Project',
                'Type': 'StringType',
                'StringValue': invoice_data['PROJECT']
            }, 
            {
                'DefinitionId': '2',
                'Name': 'Source Document',
                'Type': 'StringType',
                'StringValue': invoice_data['SALES ORDER']
            }
        ]
    }

def _customer_ref(cust_name, tv_invoice_id):
    result = queryCustomer(cust_name)
    if 'Customer' in result:
       return {'value': result['Customer']['Id']}
    else:
        logger.error('error finding customer: {0} in Quickbooks while processing trackvia invoice: {1}'.format(cust_name, tv_invoice_id))
        send_email('TV-QBO integeration error', 'We got an error finding customer: {0} in Quickbooks while processing trackvia invoice: {1}. Invoice creation/updation failed. Please create customer in quickbooks and retry.'.format(cust_name, tv_invoice_id))
        raise Exception()

def _itemsMapper(invoice_data, items):
    line_items = []
    for item in items:
        Description = "{0}/{1}".format(item['Type'], item['Description'])
        item_name= "{0} {1}".format(item['Manufacturer'].upper(), item['Catalog'].upper())
        Qty = item['Quantity']
        Rate = item['Unit CN']
        Amount = item['Total CN']
        ItemRef = _get_item_ref(item_name, invoice_data['INVOICE ID'])
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
    freight = _get_other_item(freight_data, invoice_data['INVOICE ID'])
    warehousing_data = {
            'ItemName': 'WAREHOUSING',
            'Description': invoice_data['WAREHOUSING %'],
            'Amount': invoice_data['INV WAREHOUSING']
            }
    warehousing = _get_other_item(warehousing_data, invoice_data['INVOICE ID'])
    line_items.extend([freight, warehousing])
    return line_items

# freight and warehousing
def _get_other_item(data, tv_invoice_id):
    ItemRef = _get_item_ref(data['ItemName'], tv_invoice_id)
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

def _get_item_ref(item_name, tv_invoice_id):
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
            logger.error('error creating item: {0} in Quickbooks while processing trackvia invoice: {1}'.format(item_name, tv_invoice_id))
            send_email('TV-QBO integeration error', 'We got an error creating item: {0} in Quickbooks while processing trackvia invoice: {1}. Invoice creation/updation failed. Please check line items in trackvia and retry.'.format(item_name, tv_invoice_id))
            raise Exception()
    return ItemRef

def _get_tax_details(sales_tax, tv_invoice_id):
    x = sales_tax.split(' - ')
    if len(x) != 2:
        return {}
    taxcode = queryTaxCode(x[1])
    if 'TaxCode' in taxcode:
        return {'TxnTaxCodeRef' : {'value': taxcode['TaxCode']['Id']}}
    else:
        logger.error('error finding taxcode: {0} in Quickbooks while processing trackvia invoice: {1}'.format(taxcode, tv_invoice_id))
        send_email('TV-QBO integeration error', 'We got an error finding taxcode: {0} in Quickbooks while processing trackvia invoice: {1}. Please update the invoice in Quickbooks manually.'.format(cust_name, tv_invoice_id))

def _salesTermMapper(term):
    mapper = {
        'NET 30': 3,
        'NET 15': 1,
        'NET 25': 2,
        'NET 60': 4
    }
    return mapper[term] if term in mapper else 3
