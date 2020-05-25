from celery import shared_task
from celery.decorators import task


@shared_task
def process_webhook_data(data):
    # validate data
    # process it
    print('validating data.. ##################')
    return
