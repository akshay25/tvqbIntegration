from core.apis.quickBooks.item import queryItem, createItem
from core.apis.quickBooks.customer import queryCustomer
from core.apis.quickBooks.invoice import createInvoice
from core.apis.quickBooks.taxcode import queryTaxCode

def tvToqb(fullInvoiceData):
    invoice_data = fullInvoiceData['invoice_data']
    items = fullInvoiceData['invoice_items']
    qb_invoice = _invoiceMapper(invoice_data)
    qb_invoice['Line'] = _itemsMapper(invoice_data, items)
    customer_name = invoice_data['CONTRACTOR']
    qb_invoice['CustomerRef'] = _customer_ref(customer_name)
    return qb_invoice

def _invoiceMapper(invoice_data):
    return {
        'DocNumber': invoice_data['INVOICE ID'],
        'DueDate': invoice_data['DUE DATE'],
        'CustomerMemo': {'value': invoice_data['NOTES']},
        'SalesTermRef': {'value': _salesTermMapper(invoice_data['PAYMENT TERMS'])},
        'BillEmail': {'Address': invoice_data['CONTRACTOR EMAIL']},
        'TxnDate': invoice_data['INVOICE DATE'],
        'TxnTaxDetail': _get_tax_details(invoice_data['SALE TAX']),
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

def _customer_ref(cust_name):
    result = queryCustomer(cust_name)
    if 'Customer' in result:
       return {'value': result['Customer']['Id']}
    else:
       print('customer not found')

def _itemsMapper(invoice_data, items):
    line_items = []
    for item in items:
        Description = "{0}/{1}".format(item['Type'], item['Description'])
        item_name= "{0} {1}".format(item['Manufacturer'].upper(), item['Catalog'].upper())
        Qty = item['Quantity']
        Rate = item['Unit CN']
        Amount = item['Total CN']
        ItemRef = _get_item_ref(item_name)
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
    freight = _get_other_item(freight_data)
    warehousing_data = {
            'ItemName': 'WAREHOUSING',
            'Description': invoice_data['WAREHOUSING %'],
            'Amount': invoice_data['INV WAREHOUSING']
            }
    warehousing = _get_other_item(warehousing_data)
    line_items.extend([freight, warehousing])
    return line_items

# freight and warehousing
def _get_other_item(data):
    ItemRef = _get_item_ref(data['ItemName'])
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

def _get_item_ref(item_name):
    result = queryItem(item_name)
    if 'item' in result:
        ItemRef = {
                'name': result['item']['Name'],
                'value': result['item']['Id']
                }
    else:
        item = createItem(item_name)
        ItemRef = {
               'name': item['Item']['Name'],
               'value': item['Item']['Id']
                }
    return ItemRef

def _get_tax_details(sales_tax):
    x = sales_tax.split(' - ')
    if len(x) != 2:
        return {}
    taxcode = queryTaxCode(x[1])
    if 'TaxCode' in taxcode:
        return {'TxnTaxCodeRef' : {'value': taxcode['TaxCode']['Id']}}
    else:
        return {}

def _salesTermMapper(term):
    mapper = {
        'NET 30': 3,
        'NET 15': 1,
        'NET 25': 2,
        'NET 60': 4
    }
    return mapper[term] if term in mapper else 3
