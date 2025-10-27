"""Gmail API client wrapper."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import cast

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build
from loguru import logger

from gmail_digest_tool.models.email_models import EmailMessage

DEFAULT_SCOPES: tuple[str, ...] = ("https://www.googleapis.com/auth/gmail.readonly",)


class GmailClient:
    """Client responsible for interacting with the Gmail API."""

    def __init__(
        self,
        credentials_path: Path,
        token_path: Path,
        scopes: Sequence[str] = DEFAULT_SCOPES,
    ) -> None:
        """Initialize the Gmail client and ensure OAuth credentials are available."""
        self._credentials_path = credentials_path
        self._token_path = token_path
        self._scopes = tuple(scopes)
        self._service: Resource = self._build_service()

    def fetch_messages(
        self,
        query: str,
        label_ids: Sequence[str] | None = None,
        max_results: int | None = None,
        exclude_ids: set[str] | None = None,
    ) -> list[EmailMessage]:
        """Fetch Gmail messages that match the provided query."""
        excluded = exclude_ids or set()
        messages: list[EmailMessage] = []
        request = (
            self._service.users()
            .messages()
            .list(
                userId="me",
                q=query,
                labelIds=list(label_ids) if label_ids else None,
                maxResults=max_results,
            )
        )

        while request is not None:
            response = request.execute()
            for item in response.get("messages", []):
                message_id = item["id"]
                if message_id in excluded:
                    logger.info(
                        f"Skipping Gmail message {message_id} (already summarized)."
                    )
                    continue
                full_message = (
                    self._service.users()
                    .messages()
                    .get(userId="me", id=message_id, format="full")
                    .execute()
                )
                messages.append(EmailMessage.from_gmail_api(full_message))

            request = (
                self._service.users()
                .messages()
                .list_next(previous_request=request, previous_response=response)
            )

        logger.info(f"Fetched {len(messages)} messages from Gmail.")
        return messages

    def _build_service(self) -> Resource:
        """Instantiate the Gmail API service resource."""
        credentials = self._load_credentials()
        logger.debug("Building Gmail service client.")
        return build("gmail", "v1", credentials=credentials, cache_discovery=False)

    def _load_credentials(self) -> Credentials:
        """Load credentials from disk or initiate an OAuth flow."""
        credentials: Credentials | None = None
        if self._token_path.exists():
            loader = cast(
                Callable[[str, Sequence[str]], Credentials],
                Credentials.from_authorized_user_file,
            )
            credentials = loader(str(self._token_path), self._scopes)

        if credentials is not None:
            if credentials.valid:
                return credentials
            if credentials.expired and credentials.refresh_token:
                logger.info("Refreshing Gmail OAuth token.")
                request_factory = cast(Callable[[], Request], Request)
                credentials.refresh(request_factory())
                self._save_credentials(credentials)
                return credentials

        logger.info("Launching Gmail OAuth flow.")
        flow = InstalledAppFlow.from_client_secrets_file(
            str(self._credentials_path), scopes=self._scopes
        )
        new_credentials = cast(Credentials, flow.run_local_server(port=0))
        self._save_credentials(new_credentials)
        return new_credentials

    def _save_credentials(self, credentials: Credentials) -> None:
        """Persist credentials to disk for future executions."""
        self._token_path.parent.mkdir(parents=True, exist_ok=True)
        to_json = cast(Callable[[], str], credentials.to_json)
        self._token_path.write_text(to_json())
        logger.debug(f"Saved Gmail OAuth token to {self._token_path}")


def build_label_query(base_query: str, labels: Iterable[str]) -> str:
    """Combine base query with label filters."""
    label_query = " ".join(f"label:{label}" for label in labels)
    if base_query and label_query:
        return f"{base_query} {label_query}"
    return base_query or label_query
