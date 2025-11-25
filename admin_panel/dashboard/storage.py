from django.conf import settings as django_settings
from storages.backends.s3boto3 import S3Boto3Storage


class MediaStorage(S3Boto3Storage):
    location = "media"
    
    @property
    def bucket_name(self):
        return django_settings.AWS_STORAGE_BUCKET_NAME or None
    
    @property
    def endpoint_url(self):
        return django_settings.AWS_S3_ENDPOINT_URL or None
    
    @property
    def access_key_id(self):
        return django_settings.AWS_ACCESS_KEY_ID or None
    
    @property
    def secret_access_key(self):
        return django_settings.AWS_SECRET_ACCESS_KEY or None
    
    @property
    def querystring_auth(self):
        return django_settings.AWS_QUERYSTRING_AUTH


class StaticStorage(S3Boto3Storage):
    location = "static"
    
    @property
    def bucket_name(self):
        return django_settings.AWS_STORAGE_BUCKET_NAME or None
    
    @property
    def endpoint_url(self):
        return django_settings.AWS_S3_ENDPOINT_URL or None
    
    @property
    def access_key_id(self):
        return django_settings.AWS_ACCESS_KEY_ID or None
    
    @property
    def secret_access_key(self):
        return django_settings.AWS_SECRET_ACCESS_KEY or None
    
    @property
    def querystring_auth(self):
        return django_settings.AWS_QUERYSTRING_AUTH

