from io import BytesIO

import pytest
from docx import Document as DocxDocument
from openpyxl import Workbook
from pptx import Presentation
from pptx.util import Inches
from pypdf import PdfWriter

from app.intelligence.document_ingestion import (
    DocumentExtractionError,
    DocumentSegment,
    chunk_document,
    extract_document,
)


def test_plain_text_extraction_and_cleaning():
    segments, kind = extract_document("lesson.txt", b"  First line  \r\n\r\nSecond   line ")
    assert kind == "txt"
    assert len(segments) == 1
    assert segments[0].text == "First line\n\nSecond line"


def test_markdown_and_html_extraction_skips_script_content():
    markdown, _ = extract_document("notes.md", b"# Title\n\nA useful lesson.")
    html, _ = extract_document(
        "page.html",
        b"<h1>Title</h1><script>steal secrets</script><p>Visible text</p>",
    )
    assert "A useful lesson" in markdown[0].text
    assert "Visible text" in html[0].text
    assert "steal secrets" not in html[0].text


def test_docx_extraction_includes_paragraphs_and_tables():
    document = DocxDocument()
    document.add_paragraph("Neural learning")
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Memory"
    table.cell(0, 1).text = "Recall"
    output = BytesIO()
    document.save(output)

    segments, kind = extract_document("brain.docx", output.getvalue())
    assert kind == "docx"
    assert "Neural learning" in segments[0].text
    assert "Memory" in segments[0].text
    assert "Recall" in segments[0].text


def test_powerpoint_extraction_preserves_slide_numbers_and_tables():
    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[5])
    title = slide.shapes.title
    title.text = "Working Memory"
    table_shape = slide.shapes.add_table(1, 2, Inches(1), Inches(2), Inches(5), Inches(1))
    table_shape.table.cell(0, 0).text = "Hippocampus"
    table_shape.table.cell(0, 1).text = "Episodic recall"
    output = BytesIO()
    presentation.save(output)

    segments, kind = extract_document("neuroscience.pptx", output.getvalue())
    assert kind == "pptx"
    assert segments[0].page_number == 1
    assert "Working Memory" in segments[0].text
    assert "Hippocampus" in segments[0].text
    assert "Episodic recall" in segments[0].text


def test_excel_extraction_preserves_sheet_names_and_cell_values():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Learning stages"
    sheet.append(["Stage", "Description"])
    sheet.append(["Observe", "Receive new information"])
    output = BytesIO()
    workbook.save(output)

    segments, kind = extract_document("learning.xlsx", output.getvalue())
    assert kind == "xlsx"
    assert "Sheet: Learning stages" in segments[0].text
    assert "Receive new information" in segments[0].text


def test_json_xml_and_yaml_are_ingested_as_text():
    json_segments, _ = extract_document("facts.json", b'{"mind": {"memory": "recall"}}')
    xml_segments, _ = extract_document("facts.xml", b"<mind><memory>recall</memory></mind>")
    yaml_segments, _ = extract_document("facts.yaml", b"mind:\\n  memory: recall")
    assert '"memory": "recall"' in json_segments[0].text
    assert "recall" in xml_segments[0].text
    assert "memory: recall" in yaml_segments[0].text


def test_office_archive_expansion_is_bounded(monkeypatch):
    class ExpandedEntry:
        file_size = 101 * 1024 * 1024
        compress_size = 1

    class FakeArchive:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def infolist(self):
            return [ExpandedEntry()]

    monkeypatch.setattr(
        "app.intelligence.document_ingestion.zipfile.ZipFile",
        lambda _data: FakeArchive(),
    )
    with pytest.raises(DocumentExtractionError, match="expands beyond"):
        extract_document("oversized.docx", b"not-used")


def test_pdf_extraction_retains_page_numbers():
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    output = BytesIO()
    writer.write(output)
    with pytest.raises(DocumentExtractionError, match="No selectable text"):
        extract_document("scanned.pdf", output.getvalue())


def test_chunker_keeps_page_provenance_and_overlap():
    text = " ".join(f"word{i}" for i in range(500))
    chunks = chunk_document(
        [DocumentSegment(text=text, page_number=3)],
        chunk_characters=600,
        overlap_characters=80,
    )
    assert len(chunks) > 1
    assert all(chunk.page_number == 3 for chunk in chunks)
    assert all(chunk.character_count <= 600 for chunk in chunks)
    assert chunks[0].content[-20:] in chunks[1].content


def test_chunker_rejects_invalid_overlap():
    with pytest.raises(ValueError):
        chunk_document([DocumentSegment("lesson")], chunk_characters=200, overlap_characters=200)


def test_unsupported_formats_are_rejected():
    with pytest.raises(DocumentExtractionError, match="Unsupported"):
        extract_document("archive.exe", b"arbitrary")
