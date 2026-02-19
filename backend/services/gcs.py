"""
Google Cloud Storage service for document storage and signed URLs.
"""
import logging
import os
from datetime import timedelta
from typing import Optional
from google.cloud import storage
from google.oauth2 import service_account
from google.auth import default

from config import get_settings

logger = logging.getLogger(__name__)


class GCSService:
    """Google Cloud Storage operations."""
    
    def __init__(self):
        """Initialize GCS client with service account credentials or ADC."""
        settings = get_settings()
        
        # Check if credentials file exists (local dev) or use ADC (Cloud Run)
        credentials_path = str(settings.gcp_credentials_path)
        if os.path.exists(credentials_path):
            logger.info(f"Using service account credentials from: {credentials_path}")
            credentials = service_account.Credentials.from_service_account_file(credentials_path)
            self.client = storage.Client(
                project=settings.gcp_project_id,
                credentials=credentials
            )
        else:
            logger.info("Credentials file not found, using Application Default Credentials (ADC)")
            # Use ADC - Cloud Run provides credentials automatically
            self.client = storage.Client(project=settings.gcp_project_id)
        
        self.bucket_raw_name = settings.gcs_bucket_raw
        self.bucket_processed_name = settings.gcs_bucket_processed
        self.signed_url_expiry_hours = settings.signed_url_expiry_hours
        
        logger.info(f"GCS client initialized for project: {settings.gcp_project_id}")
    
    def get_bucket(self, bucket_name: str) -> storage.Bucket:
        """Get a GCS bucket by name."""
        return self.client.bucket(bucket_name)
    
    def generate_upload_signed_url(
        self,
        filename: str,
        content_type: str = "application/pdf",
        bucket_name: Optional[str] = None
    ) -> dict:
        """
        Generate a signed URL for uploading a file directly from the client.
        
        Args:
            filename: Name of the file to upload
            content_type: MIME type of the file
            bucket_name: Optional bucket name (defaults to raw bucket)
        
        Returns:
            Dictionary with signed URL and blob info
        """
        if bucket_name is None:
            bucket_name = self.bucket_raw_name
            
        bucket = self.get_bucket(bucket_name)
        blob = bucket.blob(filename)
        
        # Generate signed URL for PUT operation
        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(hours=1),
            method="PUT",
            content_type=content_type
        )
        
        logger.info(f"Generated upload signed URL for: {filename}")
        
        return {
            "signed_url": url,
            "blob_name": filename,
            "bucket_name": bucket_name,
            "gcs_uri": f"gs://{bucket_name}/{filename}",
            "content_type": content_type
        }
    
    def generate_download_signed_url(
        self,
        blob_name: str,
        bucket_name: Optional[str] = None
    ) -> str:
        """
        Generate a signed URL for downloading a file.
        
        Args:
            blob_name: Name of the blob in GCS
            bucket_name: Optional bucket name (defaults to raw bucket)
        
        Returns:
            Signed URL string
        """
        if bucket_name is None:
            bucket_name = self.bucket_raw_name
            
        bucket = self.get_bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        # Generate signed URL for GET operation
        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(hours=self.signed_url_expiry_hours),
            method="GET"
        )
        
        logger.info(f"Generated download signed URL for: {blob_name}")
        return url
    
    def upload_file(
        self,
        source_file_path: str,
        destination_blob_name: str,
        bucket_name: Optional[str] = None,
        content_type: str = "application/pdf"
    ) -> str:
        """
        Upload a file from local filesystem to GCS.
        
        Args:
            source_file_path: Path to local file
            destination_blob_name: Name for the blob in GCS
            bucket_name: Optional bucket name
            content_type: MIME type
        
        Returns:
            GCS URI of uploaded file
        """
        if bucket_name is None:
            bucket_name = self.bucket_raw_name
            
        bucket = self.get_bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        
        blob.upload_from_filename(source_file_path, content_type=content_type)
        
        gcs_uri = f"gs://{bucket_name}/{destination_blob_name}"
        logger.info(f"Uploaded file to: {gcs_uri}")
        return gcs_uri
    
    def download_file(
        self,
        blob_name: str,
        destination_file_path: str,
        bucket_name: Optional[str] = None
    ) -> str:
        """
        Download a file from GCS to local filesystem.
        
        Args:
            blob_name: Name of the blob in GCS
            destination_file_path: Path to save the file locally
            bucket_name: Optional bucket name
        
        Returns:
            Path to downloaded file
        """
        if bucket_name is None:
            bucket_name = self.bucket_raw_name
            
        bucket = self.get_bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        blob.download_to_filename(destination_file_path)
        
        logger.info(f"Downloaded file from gs://{bucket_name}/{blob_name} to {destination_file_path}")
        return destination_file_path
    
    def blob_exists(self, blob_name: str, bucket_name: Optional[str] = None) -> bool:
        """Check if a blob exists in GCS."""
        if bucket_name is None:
            bucket_name = self.bucket_raw_name
            
        bucket = self.get_bucket(bucket_name)
        blob = bucket.blob(blob_name)
        return blob.exists()
    
    def delete_blob(self, blob_name: str, bucket_name: Optional[str] = None):
        """Delete a blob from GCS."""
        if bucket_name is None:
            bucket_name = self.bucket_raw_name
            
        bucket = self.get_bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.delete()
        
        logger.info(f"Deleted blob: gs://{bucket_name}/{blob_name}")

