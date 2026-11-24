from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class EpisodicTrace:
    """A stable index for a dated experience, not a neural engram."""

    content_sha256: str
    episode_type: str
    title: str
    source_type: str
    encoded_at: str


class HippocampalIndexer:
    """Create reproducible episode identifiers and preserve source provenance.

    Inspired by hippocampal indexing and pattern-separation ideas in the
    Complementary Learning Systems literature. Actual brain engrams are not
    equivalent to database rows or hashes.
    """

    @staticmethod
    def normalize_content(content: str) -> str:
        return re.sub(r"\s+", " ", content).strip()

    def encode(
        self,
        *,
        title: str,
        content: str,
        episode_type: str = "lesson",
        source_type: str = "owner_taught",
    ) -> EpisodicTrace:
        normalized = self.normalize_content(content)
        digest = hashlib.sha256(normalized.casefold().encode("utf-8")).hexdigest()
        return EpisodicTrace(
            content_sha256=digest,
            episode_type=episode_type,
            title=title.strip(),
            source_type=source_type,
            encoded_at=datetime.now(timezone.utc).isoformat(),
        )
