from __future__ import annotations

from typing import Protocol


class ResearchProvider(Protocol):
    def scan(self, command: dict[str, object]) -> dict[str, object]:
        """Return a structured research pack from a market scan command."""


class AuditProvider(Protocol):
    def audit(self, research_record: dict[str, object]) -> dict[str, object]:
        """Return an audit report for a research record."""


class LibraryProvider(Protocol):
    def store(self, audit_report: dict[str, object], research_record: dict[str, object]) -> dict[str, object]:
        """Store an approved record in the canonical Library."""


class NotificationProvider(Protocol):
    def notify(self, event_type: str, message: str, entity_id: str | None = None) -> None:
        """Publish a notification."""


class LLMProvider(Protocol):
    def complete(self, prompt: str, payload: dict[str, object]) -> dict[str, object]:
        """Return model output for a prompt and structured payload."""


class AuthenticationProvider(Protocol):
    def current_user(self) -> dict[str, object]:
        """Return the current authenticated user."""


class StorageProvider(Protocol):
    def read(self, location: str) -> bytes:
        """Read bytes from a storage location."""

    def write(self, location: str, content: bytes) -> str:
        """Write bytes and return the stored location."""
