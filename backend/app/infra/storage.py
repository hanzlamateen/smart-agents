import boto3
import base64
import uuid
import logging
from botocore.exceptions import ClientError
from typing import Optional
from ..core.config import settings

logger = logging.getLogger("smart_agents")

class Storage:
    def __init__(self):
        self.endpoint_url = settings.s3_endpoint_url
        self.aws_access_key_id = settings.s3_access_key
        self.aws_secret_access_key = settings.s3_secret_key
        self.bucket_name = settings.s3_bucket_name
        self.public_url_base = settings.s3_public_url
        
        self.s3_client = boto3.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
        )

    def upload_base64_image(self, base64_string: str, folder: str = 'screenshots') -> Optional[dict]:
        """
        Uploads a base64 string as an image to S3.
        Returns a dict with 's3_key' and 'public_url'.
        """
        try:
            image_data = base64.b64decode(base64_string)
            key = f"{folder}/{uuid.uuid4()}.png"
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=image_data,
                ContentType='image/png'
                # ACL='public-read' # Using bucket policy instead
            )
            
            return {
                "s3_key": key,
                "public_url": f"{self.public_url_base}/{self.bucket_name}/{key}"
            }
        except Exception as e:
            logger.error(f"Failed to upload image to S3: {e}")
            return None

    def get_image_base64(self, key: str) -> Optional[str]:
        """
        Downloads an image from S3 and returns it as a base64 string.
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            image_data = response['Body'].read()
            return base64.b64encode(image_data).decode('utf-8')
        except ClientError as e:
            logger.error(f"Failed to download image from S3: {e}")
            return None

    def get_public_url(self, key: str) -> str:
        """Generate public URL for a key."""
        return f"{self.public_url_base}/{self.bucket_name}/{key}"


# Global instance
storage = Storage()
