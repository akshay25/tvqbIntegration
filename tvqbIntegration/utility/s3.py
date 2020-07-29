import boto3
from django.conf import settings

def upload_file(filename, filepath):
	s3 = boto3.resource('s3')
	s3.Object(settings.AWS_STORAGE_BUCKET_NAME, filename).upload_file(filepath)
