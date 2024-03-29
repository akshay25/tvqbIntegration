from django.db import models
from django.core.exceptions import ObjectDoesNotExist


class InvoiceRef(models.Model):
    tv_id = models.CharField(max_length=30)
    qb_id = models.CharField(max_length=30)
    view_id = models.CharField(max_length=30, null=True, blank=True)
    is_manual = models.BooleanField(null=True, blank=True, default=False)


class BillExpenseReference(models.Model):
    tv_id = models.CharField(max_length=30)
    qb_id = models.CharField(max_length=30)
    view_id = models.CharField(max_length=30, null=True, blank=True)

    objects = models.Manager()

    def getBillExpenseReferanceByTvId(self, bill_id):
        try:
            return BillExpenseReference.objects.get(tv_id=bill_id)
        except ObjectDoesNotExist:
            return None


class DesignFeeRef(models.Model):
    tv_id = models.CharField(max_length=30)
    qb_id = models.CharField(max_length=30)
    view_id = models.CharField(max_length=30, null=True, blank=True)

    objects = models.Manager()

    def getDesignFeeRefByTvId(self, df_id):
        try:
            return DesignFeeRef.objects.get(tv_id=df_id)
        except ObjectDoesNotExist:
            return None

    def getDesignFeeRefByQbId(self, df_id):
        try:
            return DesignFeeRef.objects.get(qb_id=df_id)
        except ObjectDoesNotExist:
            return None
