from core.apis.quickBooks.item import queryItem, createItem
from core.apis.quickBooks.customer import queryCustomer
from core.apis.quickBooks.invoice import createInvoice

def tvToqb(fullInvoiceData):
    invoice_data = fullInvoiceData['invoice_data']
    items = fullInvoiceData['invoice_items']
    qb_invoice = _invoiceMapper(invoice_data)
    qb_invoice['Line'] = _itemsMapper(invoice_data, items)
    customer_name = 'abc' #TODO
    qb_invoice['CustomerRef'] = _customer_ref(customer_name)
    return qb_invoice

def _invoiceMapper(invoice_data):
    return {
            'Client email': invoice_data['CONTRACTOR EMAIL'],
            'DocNumber': invoice_data['INVOICE ID'],
            'BillAddr': invoice_data['DELIVERY DETAILS'],
            'Terms': invoice_data['TERMS'] if 'TERMS' in invoice_data else 'NET 30',
            'Invoice Date': invoice_data['INVOICE DATE'],
            'DueDate': invoice_data['DUE DATE'],
            'ShipAddr': invoice_data['DELIVERY DETAILS'],
            'Project': invoice_data['PROJECT'],
            'Source document': invoice_data['SALES ORDER'],
            'Message on invoice': invoice_data['NOTES'],
            'SALES TAX': invoice_data['INV SALES TAX']
            }

def _customer_ref(cust_name):
    result = queryCustomer(cust_name)
    if 'customer' in result:
        return {'value': result['customer']['Id']}
    else:
        # raise error
        pass

def _itemsMapper(invoice_data, items):
    line_items = []
    for item in items:
        Description = "{0}/{1}".format(item['Type'], item['Description']),
        item_name= '{0} {1}'.format(item['Manufacturer'].upper(), item['Catalog'].upper()),
        Qty = item['Quantity'],
        Rate = item['Unit CN'],
        Amount = item['Total CN']
        result = queryItem(item_name)
        if 'item' in result:
            ItemRef = {
                    'name': result['item']['Name'],
                    'value': result['item']['Id']
                    }
        else:
            item = createItem(item_name)
            ItemRef = {
                   'name': result['Item']['Name'],
                   'value': result['Item']['Id']
                    }
        line_item = {
            'DetailType': 'SalesItemLineDetail',
            'Description': Description,
            'Amount': Amount,
            'SalesItemLineDetail': {
                'Qty': Qty,
                'UnitPrice': Rate,
                'ItemRef': ItemRef
                }
            }
        line_items.append(line_item)

    freight_data = {
            'ItemName': 'Freight',
            'Description': invoice_data['FREIGHT %'],
            'Amount': invoice_data['INV FREIGHT']
            }
    freight = _get_other_item(freight_data)
    warehousing_data = {
            'ItemName': 'Warehousing',
            'Description': invoice_data['WAREHOUSING %'],
            'Amount': invoice_data['INV WAREHOUSING']
            }
    warehousing = _get_other_item(warehousing_data)
    line_items.extend([freight, warehousing])
    return line_items

# freight and warehousing
def _get_other_item(data):
    result = queryItem(data['ItemName'])
    if 'item' in result:
        ItemRef = {
                'name': result['item']['Name'],
                'value': result['item']['Id']
                }
    else:
        item = createItem(item_name)
        ItemRef = {
               'name': result['Item']['Name'],
               'value': result['Item']['Id']
                }
    line_item = {
        'DetailType': 'SalesItemLineDetail',
        'Description': data['Description'],
        'Amount': data['Amount'],
        'SalesItemLineDetail': {
            'ItemRef': ItemRef
            }
        }
    return line_item
