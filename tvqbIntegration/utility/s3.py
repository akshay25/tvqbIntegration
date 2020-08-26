import boto3
from django.conf import settings

from botocore.exceptions import ClientError

def create_presigned_url(bucket_name, object_name, expiration=3600):
    """Generate a presigned URL to share an S3 object

    :param bucket_name: string
    :param object_name: string
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Presigned URL as string. If error, returns None.
    """

    # Generate a presigned URL for the S3 object
    s3_client = boto3.client('s3')
    try:
        response = s3_client.generate_presigned_url('get_object',
                                                    Params={'Bucket': bucket_name,
                                                            'Key': object_name},
                                                    ExpiresIn=expiration)
    except ClientError as e:
        logging.error(e)
        return None

    # The response contains the presigned URL
    return response


def upload_file(filename, filepath):
	s3 = boto3.resource('s3')
	s3.Object(settings.AWS_STORAGE_BUCKET_NAME, filename).upload_file(filepath)
	object_acl = s3.ObjectAcl(settings.AWS_STORAGE_BUCKET_NAME, filename)
	object_acl.put(ACL='public-read')
	return "https://{0}.s3-{1}.amazonaws.com/{2}".format(settings.AWS_STORAGE_BUCKET_NAME, settings.AWS_SES_REGION_NAME, filename)


def upload_file_and_get_presigned_url(filename, filepath):
	upload_file(filename, filepath)
	presigned_url = create_presigned_url(settings.AWS_STORAGE_BUCKET_NAME, filename, expiration=31536000)
	return presigned_url