from django.db import models
from django.core.exceptions import ObjectDoesNotExist


class InvoiceRef(models.Model):
    tv_id = models.CharField(max_length=30)
    qb_id = models.CharField(max_length=30)


class BillExpenseReference(models.Model):
    tv_id = models.CharField(max_length=30)
    qb_id = models.CharField(max_length=30)

    objects = models.Manager()

    def getBillExpenseReferanceByTvId(self, bill_id):
        try:
            return BillExpenseReference.objects.get(tv_id=bill_id)
        except ObjectDoesNotExist:
            return None


