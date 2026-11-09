"""Expected, recoverable domain failures."""

__all__ = ["BZTagError", "ScanError", "MetadataError", "SorterError", "ActionError"]


class BZTagError(Exception):
    """Base for expected domain failures."""


class ScanError(BZTagError):
    """File and directory discovery failures."""


class MetadataError(BZTagError):
    """ID3 tag read/write failures."""


class SorterError(BZTagError):
    """Ordering failures (unknown or unavailable sort styles)."""


class ActionError(BZTagError):
    """CLI usage mistake on an otherwise valid target."""
