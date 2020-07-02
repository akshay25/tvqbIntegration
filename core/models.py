from django.db import models

class InvoiceRef(models.Model):
    tv_id = models.CharField(max_length=30)
    qb_id = models.CharField(max_length=30)
