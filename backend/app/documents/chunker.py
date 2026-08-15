"""Document chunking for RAG (Retrieval-Augmented Generation).

Splits document text into chunks suitable for embedding and
vector-store ingestion.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Chunking strategy enum
# ---------------------------------------------------------------------------

class ChunkStrategy(str, Enum):
    PAGE = "page"
    PARAGRAPH = "paragraph"
    SEMANTIC = "semantic"
    SLIDING_WINDOW = "sliding_window"


# ---------------------------------------------------------------------------
# Chunk data-class
# ---------------------------------------------------------------------------

@dataclass
class Chunk:
    """A single text chunk ready for embedding."""
    chunk_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    index: int = 0
    page_number: int | None = None
    start_char: int = 0
    end_char: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# DocumentChunker
# ---------------------------------------------------------------------------

class DocumentChunker:
    """Split document text into chunks using various strategies."""

    DEFAULT_CHUNK_SIZE: int = 1000      # characters
    DEFAULT_OVERLAP: int = 200          # characters of overlap for sliding window
    MIN_CHUNK_SIZE: int = 50            # skip chunks shorter than this

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chunk_document(
        self,
        content: str,
        strategy: ChunkStrategy | str = ChunkStrategy.PARAGRAPH,
        *,
        chunk_size: int | None = None,
        overlap: int | None = None,
        page_markers: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        """Split *content* into chunks.

        Parameters
        ----------
        content : str
            Full document text.
        strategy : ChunkStrategy | str
            Chunking method.
        chunk_size : int, optional
            Target chunk size in characters (for sliding_window).
        overlap : int, optional
            Overlap in characters (for sliding_window).
        page_markers : bool
            If ``True``, ``\\f`` is treated as a page boundary.
        metadata : dict, optional
            Extra metadata attached to every chunk.

        Returns
        -------
        list[Chunk]
        """
        if not content or not content.strip():
            return []

        strategy = ChunkStrategy(strategy) if isinstance(strategy, str) else strategy
        chunk_size = chunk_size or self.DEFAULT_CHUNK_SIZE
        overlap = overlap or self.DEFAULT_OVERLAP
        meta = metadata or {}

        if strategy == ChunkStrategy.PAGE:
            chunks = self._chunk_by_page(content, page_markers, meta)
        elif strategy == ChunkStrategy.PARAGRAPH:
            chunks = self._chunk_by_paragraph(content, meta)
        elif strategy == ChunkStrategy.SEMANTIC:
            chunks = self._chunk_semantic(content, meta)
        elif strategy == ChunkStrategy.SLIDING_WINDOW:
            chunks = self._chunk_sliding_window(content, chunk_size, overlap, meta)
        else:
            chunks = self._chunk_by_paragraph(content, meta)

        # Assign sequential indices
        for i, chunk in enumerate(chunks):
            chunk.index = i

        return chunks

    # ------------------------------------------------------------------
    # Strategy: page
    # ------------------------------------------------------------------

    def _chunk_by_page(
        self,
        content: str,
        page_markers: bool,
        metadata: dict[str, Any],
    ) -> list[Chunk]:
        """Split by page boundaries (form-feed or page-number patterns)."""
        if page_markers or "\f" in content:
            pages = content.split("\f")
        else:
            # Heuristic: split on "Page N" patterns
            pages = re.split(r"(?i)(?=page\s+\d+)", content)

        chunks: list[Chunk] = []
        for page_num, page_text in enumerate(pages, start=1):
            text = page_text.strip()
            if len(text) < self.MIN_CHUNK_SIZE:
                continue
            chunks.append(Chunk(
                content=text,
                page_number=page_num,
                start_char=0,
                end_char=len(text),
                metadata={**metadata, "page": page_num},
            ))
        return chunks

    # ------------------------------------------------------------------
    # Strategy: paragraph
    # ------------------------------------------------------------------

    def _chunk_by_paragraph(
        self,
        content: str,
        metadata: dict[str, Any],
    ) -> list[Chunk]:
        """Split on double newlines (paragraph boundaries)."""
        paragraphs = re.split(r"\n\s*\n", content)
        chunks: list[Chunk] = []
        offset = 0
        for para in paragraphs:
            text = para.strip()
            if len(text) < self.MIN_CHUNK_SIZE:
                offset += len(para) + 2
                continue
            start = content.find(text, offset)
            end = start + len(text)
            chunks.append(Chunk(
                content=text,
                start_char=start,
                end_char=end,
                metadata=metadata,
            ))
            offset = end
        return chunks

    # ------------------------------------------------------------------
    # Strategy: semantic
    # ------------------------------------------------------------------

    def _chunk_semantic(
        self,
        content: str,
        metadata: dict[str, Any],
    ) -> list[Chunk]:
        """Split on semantic boundaries (headers, bullet lists, numbered lists).

        This is a heuristic approach — for production use an LLM-based
        semantic splitter.
        """
        # Split on lines that look like headers or list starts
        boundary_pattern = re.compile(
            r"(?=^(?:#{1,6}\s|[A-Z][A-Z\s]{5,}$|\d+\.\s|[-*•]\s))",
            re.MULTILINE,
        )
        sections = boundary_pattern.split(content)

        chunks: list[Chunk] = []
        offset = 0
        current_text = ""

        for section in sections:
            section = section.strip()
            if not section:
                continue

            # If the section is a header, start a new chunk
            is_header = bool(re.match(r"^(?:#{1,6}\s|[A-Z][A-Z\s]{5,}$)", section, re.MULTILINE))
            if is_header and current_text:
                if len(current_text.strip()) >= self.MIN_CHUNK_SIZE:
                    start = content.find(current_text.strip(), max(0, offset - len(current_text)))
                    chunks.append(Chunk(
                        content=current_text.strip(),
                        start_char=start,
                        end_char=start + len(current_text.strip()),
                        metadata=metadata,
                    ))
                offset += len(current_text)
                current_text = ""

            current_text += section + "\n\n"

        # Final chunk
        if current_text.strip() and len(current_text.strip()) >= self.MIN_CHUNK_SIZE:
            start = content.find(current_text.strip(), max(0, offset - len(current_text)))
            chunks.append(Chunk(
                content=current_text.strip(),
                start_char=start,
                end_char=start + len(current_text.strip()),
                metadata=metadata,
            ))

        return chunks

    # ------------------------------------------------------------------
    # Strategy: sliding_window
    # ------------------------------------------------------------------

    def _chunk_sliding_window(
        self,
        content: str,
        chunk_size: int,
        overlap: int,
        metadata: dict[str, Any],
    ) -> list[Chunk]:
        """Fixed-size chunks with overlap.

        Attempts to break at sentence boundaries when possible.
        """
        chunks: list[Chunk] = []
        start = 0
        text_len = len(content)

        while start < text_len:
            end = min(start + chunk_size, text_len)

            # Try to break at a sentence boundary
            if end < text_len:
                # Look for the last sentence-ending punctuation within the window
                window = content[start:end]
                last_period = max(
                    window.rfind(". "),
                    window.rfind(".\n"),
                    window.rfind("! "),
                    window.rfind("? "),
                )
                if last_period > chunk_size * 0.3:
                    end = start + last_period + 1

            text = content[start:end].strip()
            if len(text) >= self.MIN_CHUNK_SIZE:
                chunks.append(Chunk(
                    content=text,
                    start_char=start,
                    end_char=end,
                    metadata=metadata,
                ))

            # Advance with overlap
            start = end - overlap if end < text_len else text_len

        return chunks
