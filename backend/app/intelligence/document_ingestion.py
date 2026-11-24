from __future__ import annotations

import csv
import io
import re
import zipfile
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import PurePath

from docx import Document as DocxDocument
from openpyxl import load_workbook
from pptx import Presentation
from pypdf import PdfReader


MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_ARCHIVE_EXPANDED_BYTES = 100 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 10_000
MAX_EXTRACTED_CHARACTERS = 1_000_000
MAX_DOCUMENT_CHUNKS = 800
CHUNK_CHARACTERS = 1_800
CHUNK_OVERLAP_CHARACTERS = 240

SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".pptx", ".xlsx", ".txt", ".md", ".markdown",
    ".rst", ".csv", ".html", ".htm", ".json", ".xml", ".yaml", ".yml",
}


class DocumentExtractionError(ValueError):
    pass


@dataclass(frozen=True)
class DocumentSegment:
    text: str
    page_number: int | None = None


@dataclass(frozen=True)
class DocumentChunk:
    chunk_index: int
    content: str
    page_number: int | None
    character_count: int


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript"}:
            self._ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript"} and self._ignored_depth:
            self._ignored_depth -= 1
        elif tag.lower() in {"p", "div", "br", "li", "h1", "h2", "h3", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self.parts.append(data)


def _clean_text(value: str) -> str:
    value = value.replace("\x00", " ")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r" *\n *", "\n", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def extract_document(filename: str, data: bytes) -> tuple[list[DocumentSegment], str]:
    """Extract text from supported, non-executable document formats."""
    extension = PurePath(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise DocumentExtractionError(
            f"Unsupported file type '{extension or 'unknown'}'. "
            f"Supported types: {', '.join(sorted(SUPPORTED_EXTENSIONS))}."
        )
    if not data:
        raise DocumentExtractionError("The uploaded document is empty.")

    segments: list[DocumentSegment] = []
    try:
        if extension in {".docx", ".pptx", ".xlsx"}:
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    entries = archive.infolist()
                    expanded_size = sum(entry.file_size for entry in entries)
                    if len(entries) > MAX_ARCHIVE_ENTRIES:
                        raise DocumentExtractionError("Office archive contains too many entries.")
                    if expanded_size > MAX_ARCHIVE_EXPANDED_BYTES:
                        raise DocumentExtractionError(
                            "Office archive expands beyond the 100 MiB safety limit."
                        )
                    if any(entry.file_size / max(entry.compress_size, 1) > 500 for entry in entries):
                        raise DocumentExtractionError(
                            "Office archive has an excessive compression ratio."
                        )
            except zipfile.BadZipFile as exc:
                raise DocumentExtractionError("The Office file is not a valid ZIP-based document.") from exc

        if extension == ".pdf":
            reader = PdfReader(io.BytesIO(data), strict=False)
            if reader.is_encrypted:
                try:
                    if not reader.decrypt(""):
                        raise DocumentExtractionError("Password-protected PDFs are not supported.")
                except Exception as exc:
                    raise DocumentExtractionError("Password-protected PDFs are not supported.") from exc
            for index, page in enumerate(reader.pages, start=1):
                text = _clean_text(page.extract_text() or "")
                if text:
                    segments.append(DocumentSegment(text=text, page_number=index))
        elif extension == ".docx":
            document = DocxDocument(io.BytesIO(data))
            paragraphs = [_clean_text(item.text) for item in document.paragraphs]
            paragraphs.extend(
                _clean_text(cell.text)
                for table in document.tables
                for row in table.rows
                for cell in row.cells
            )
            text = "\n\n".join(item for item in paragraphs if item)
            if text:
                segments.append(DocumentSegment(text=text))
        elif extension == ".pptx":
            presentation = Presentation(io.BytesIO(data))
            for slide_number, slide in enumerate(presentation.slides, start=1):
                parts: list[str] = []
                for shape in slide.shapes:
                    if getattr(shape, "has_text_frame", False):
                        parts.extend(
                            paragraph.text.strip()
                            for paragraph in shape.text_frame.paragraphs
                            if paragraph.text.strip()
                        )
                    if getattr(shape, "has_table", False):
                        parts.extend(
                            " | ".join(cell.text.strip() for cell in row.cells)
                            for row in shape.table.rows
                        )
                slide_text = _clean_text("\n".join(parts))
                if slide_text:
                    segments.append(DocumentSegment(text=slide_text, page_number=slide_number))
        elif extension == ".xlsx":
            workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
            try:
                for worksheet in workbook.worksheets:
                    rows = []
                    for row in worksheet.iter_rows(values_only=True):
                        values = [str(value).strip() for value in row if value is not None and str(value).strip()]
                        if values:
                            rows.append(" | ".join(values))
                    sheet_text = _clean_text(f"Sheet: {worksheet.title}\n" + "\n".join(rows))
                    if sheet_text:
                        segments.append(DocumentSegment(text=sheet_text))
            finally:
                workbook.close()
        elif extension in {".html", ".htm"}:
            parser = _HTMLTextExtractor()
            parser.feed(data.decode("utf-8-sig", errors="strict"))
            text = _clean_text("".join(parser.parts))
            if text:
                segments.append(DocumentSegment(text=text))
        elif extension == ".csv":
            decoded = data.decode("utf-8-sig", errors="strict")
            rows = list(csv.reader(io.StringIO(decoded)))
            text = "\n".join(" | ".join(cell.strip() for cell in row) for row in rows)
            text = _clean_text(text)
            if text:
                segments.append(DocumentSegment(text=text))
        else:
            decoded = data.decode("utf-8-sig", errors="strict")
            if extension == ".xml":
                import xml.etree.ElementTree as element_tree

                root = element_tree.fromstring(decoded)
                decoded = "\n".join(part.strip() for part in root.itertext() if part.strip())
            text = _clean_text(decoded)
            if text:
                segments.append(DocumentSegment(text=text))
    except DocumentExtractionError:
        raise
    except Exception as exc:
        raise DocumentExtractionError(
            "Could not extract text from this file. Check that it is a valid, uncorrupted document."
        ) from exc

    total_characters = sum(len(segment.text) for segment in segments)
    if total_characters > MAX_EXTRACTED_CHARACTERS:
        raise DocumentExtractionError(
            f"Extracted text exceeds the {MAX_EXTRACTED_CHARACTERS:,}-character limit."
        )
    if not segments:
        raise DocumentExtractionError(
            "No selectable text was found. Scanned/image-only PDFs need OCR before ingestion."
        )
    return segments, extension.lstrip(".")


def chunk_document(
    segments: list[DocumentSegment],
    *,
    chunk_characters: int = CHUNK_CHARACTERS,
    overlap_characters: int = CHUNK_OVERLAP_CHARACTERS,
) -> list[DocumentChunk]:
    """Create bounded, overlapping chunks while retaining PDF page provenance."""
    if chunk_characters < 200:
        raise ValueError("chunk_characters must be at least 200")
    if overlap_characters < 0 or overlap_characters >= chunk_characters:
        raise ValueError("overlap_characters must be smaller than chunk_characters")

    chunks: list[DocumentChunk] = []
    for segment in segments:
        text = _clean_text(segment.text)
        if not text:
            continue
        start = 0
        while start < len(text):
            end = min(start + chunk_characters, len(text))
            if end < len(text):
                boundary = max(text.rfind("\n", start + chunk_characters // 2, end),
                               text.rfind(" ", start + chunk_characters // 2, end))
                if boundary > start:
                    end = boundary
            piece = text[start:end].strip()
            if piece:
                chunks.append(DocumentChunk(
                    chunk_index=len(chunks),
                    content=piece,
                    page_number=segment.page_number,
                    character_count=len(piece),
                ))
                if len(chunks) > MAX_DOCUMENT_CHUNKS:
                    raise DocumentExtractionError(
                        f"Document produced more than {MAX_DOCUMENT_CHUNKS} chunks."
                    )
            if end >= len(text):
                break
            start = max(start + 1, end - overlap_characters)

    return chunks
