from celery import shared_task
from celery.decorators import task

@shared_task
def adding_task(x, y):
    return x + y

@shared_task
def testFunc():
    return('first_task_done')
