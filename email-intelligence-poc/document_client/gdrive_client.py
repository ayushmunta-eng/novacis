"""Google Drive document client implementation."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from config import Settings
from document_client.base import BaseDocumentClient, DocumentRecord


class GoogleDriveDocumentClient(BaseDocumentClient):
    """Document client that reads extractable text files from Google Drive."""

    SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
    SUPPORTED_MIME_TYPES = {
        "application/vnd.google-apps.document",
        "application/pdf",
        "text/plain",
    }

    def __init__(
        self,
        settings: Settings,
        credentials_path: str | Path = "credentials.json",
        token_path: str | Path = "token.json",
    ) -> None:
        """Create a Google Drive client using OAuth credential file paths."""
        self.settings = settings
        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path)
        self._service: Any | None = None

    def connect(self) -> None:
        """Authenticate with Google Drive and build the Drive v3 service."""
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        credentials = None
        if self.token_path.exists():
            credentials = Credentials.from_authorized_user_file(str(self.token_path), self.SCOPES)

        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                if not self.credentials_path.exists():
                    raise FileNotFoundError(
                        "Google Drive OAuth credentials.json was not found in the project root."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_path), self.SCOPES)
                credentials = flow.run_local_server(port=0)
            self.token_path.write_text(credentials.to_json(), encoding="utf-8")

        self._service = build("drive", "v3", credentials=credentials)

    def fetch_documents(self, limit: int, folder_id: str | None = None) -> list[DocumentRecord]:
        """Fetch supported Google Drive files and extract plain text content."""
        service = self._require_service()
        query_parts = ["trashed = false"]
        if folder_id:
            query_parts.append(f"'{folder_id}' in parents")
        mime_query = " or ".join(f"mimeType = '{mime_type}'" for mime_type in self.SUPPORTED_MIME_TYPES)
        query_parts.append(f"({mime_query})")

        response = (
            service.files()
            .list(
                q=" and ".join(query_parts),
                pageSize=limit,
                fields="files(id,name,mimeType,createdTime,modifiedTime,owners(displayName,emailAddress))",
                orderBy="modifiedTime desc",
            )
            .execute()
        )

        documents: list[DocumentRecord] = []
        for file_metadata in response.get("files", []):
            content = self._extract_text(file_metadata)
            if not content.strip():
                continue
            documents.append(
                {
                    "id": file_metadata["id"],
                    "name": file_metadata.get("name", "Untitled"),
                    "mime_type": file_metadata.get("mimeType", "unknown"),
                    "content": content,
                    "created_time": file_metadata.get("createdTime"),
                    "modified_time": file_metadata.get("modifiedTime"),
                    "owner": self._owner_name(file_metadata),
                }
            )
        return documents

    def disconnect(self) -> None:
        """Release the active Google Drive service reference."""
        self._service = None

    def _require_service(self) -> Any:
        """Return the active Google Drive service or raise a useful error."""
        if self._service is None:
            raise RuntimeError("Google Drive client is not connected.")
        return self._service

    def _extract_text(self, file_metadata: dict[str, Any]) -> str:
        """Extract plain text from a supported Google Drive file."""
        mime_type = file_metadata.get("mimeType")
        file_id = file_metadata["id"]
        if mime_type == "application/vnd.google-apps.document":
            return self._export_google_doc(file_id)
        if mime_type == "application/pdf":
            return self._download_pdf_text(file_id)
        if mime_type == "text/plain":
            return self._download_text_file(file_id)
        return ""

    def _export_google_doc(self, file_id: str) -> str:
        """Export a Google Docs document as plain text."""
        service = self._require_service()
        data = service.files().export_media(fileId=file_id, mimeType="text/plain").execute()
        return self._decode_bytes(data)

    def _download_text_file(self, file_id: str) -> str:
        """Download a plain text file from Google Drive."""
        service = self._require_service()
        data = service.files().get_media(fileId=file_id).execute()
        return self._decode_bytes(data)

    def _download_pdf_text(self, file_id: str) -> str:
        """Download a PDF file and extract readable text from its pages."""
        from PyPDF2 import PdfReader

        service = self._require_service()
        data = service.files().get_media(fileId=file_id).execute()
        reader = PdfReader(BytesIO(data))
        page_text = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(page_text)

    @staticmethod
    def _decode_bytes(data: bytes | str) -> str:
        """Decode Google API media response bytes into text."""
        if isinstance(data, str):
            return data
        return data.decode("utf-8", errors="replace")

    @staticmethod
    def _owner_name(file_metadata: dict[str, Any]) -> str:
        """Return a stable display value for the first document owner."""
        owners = file_metadata.get("owners") or []
        if not owners:
            return "Unknown owner"
        owner = owners[0]
        return owner.get("displayName") or owner.get("emailAddress") or "Unknown owner"
