from storages.backends.s3boto3 import S3Boto3Storage

from core.config import settings


class MediaStorage(S3Boto3Storage):
    bucket_name = settings.aws_storage_bucket_name
    location = "media"


class StaticStorage(S3Boto3Storage):
    bucket_name = settings.aws_storage_bucket_name
    location = "static"

