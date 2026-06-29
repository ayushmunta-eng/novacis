"""Document client implementations for the email intelligence POC."""

from document_client.base import BaseDocumentClient, DocumentRecord
from document_client.gdrive_client import GoogleDriveDocumentClient
from document_client.mock_client import MockDocumentClient

__all__ = ["BaseDocumentClient", "DocumentRecord", "GoogleDriveDocumentClient", "MockDocumentClient"]
