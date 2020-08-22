import boto3
from django.conf import settings


def upload_file(filename, filepath):
    s3 = boto3.resource('s3')
    s3.Object(settings.AWS_STORAGE_BUCKET_NAME, filename).upload_file(filepath)
    return "https://{0}.s3-{1}.amazonaws.com/{2}".format(
        settings.AWS_STORAGE_BUCKET_NAME, settings.AWS_SES_REGION_NAME, filename)
