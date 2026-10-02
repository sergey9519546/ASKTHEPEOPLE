"""Tests for DOCX and XLSX extraction in FileParser.

The extractors are stdlib-only (zipfile + ElementTree) with declared
resource ceilings and a DTD rejection guard. Real OOXML archives are
built in-test; the ceilings are lowered via monkeypatch so the
fail-closed paths run against small files instead of 100MB payloads.
"""

import io
import zipfile
from xml.etree import ElementTree as ET

import pytest

from app.utils import file_parser
from app.utils.file_parser import FileParser, FileParserLimitError

_WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_SHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def _el(tag: str, text: str | None = None, **attrs) -> ET.Element:
    element = ET.Element(f"{{{_SHEET_NS}}}{tag}", {k: v for k, v in attrs.items()})
    if text is not None:
        element.text = text
    return element


# --- fixture builders ----------------------------------------------------- #


def _docx_document_xml(paragraphs: list[str]) -> bytes:
    """word/document.xml with one w:p per paragraph."""
    document = ET.Element(f"{{{_WORD_NS}}}document")
    body = ET.SubElement(document, f"{{{_WORD_NS}}}body")
    for text in paragraphs:
        p = ET.SubElement(body, f"{{{_WORD_NS}}}p")
        r = ET.SubElement(p, f"{{{_WORD_NS}}}r")
        t = ET.SubElement(r, f"{{{_WORD_NS}}}t")
        t.text = text
    return ET.tostring(document, encoding="utf-8", xml_declaration=True)


def _xlsx_shared_strings(values: list[str]) -> bytes:
    root = _el("sst", count=str(len(values)), uniqueCount=str(len(values)))
    for value in values:
        si = ET.SubElement(root, f"{{{_SHEET_NS}}}si")
        t = ET.SubElement(si, f"{{{_SHEET_NS}}}t")
        t.text = value
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _xlsx_workbook_xml(sheet_names: list[str]) -> bytes:
    root = _el("workbook")
    sheets = ET.SubElement(root, f"{{{_SHEET_NS}}}sheets")
    for index, name in enumerate(sheet_names, start=1):
        ET.SubElement(
            sheets,
            f"{{{_SHEET_NS}}}sheet",
            name=name,
            sheetId=str(index),
        )
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _xlsx_sheet_xml(rows: list[list[tuple[str, str]]]) -> bytes:
    """One worksheet; each row is a list of (kind, value) cell descriptors.

    kind: "s" = shared-string index, "inline" = inline string, "n" = number.
    """
    root = _el("worksheet")
    data = ET.SubElement(root, f"{{{_SHEET_NS}}}sheetData")
    for r_idx, row in enumerate(rows, start=1):
        row_el = ET.SubElement(data, f"{{{_SHEET_NS}}}row", r=str(r_idx))
        if not row:
            continue
        for c_idx, (kind, value) in enumerate(row, start=1):
            column = chr(ord("A") + c_idx - 1)
            if kind == "inline":
                cell = ET.SubElement(
                    row_el, f"{{{_SHEET_NS}}}c", r=f"{column}{r_idx}", t="inlineStr"
                )
                is_el = ET.SubElement(cell, f"{{{_SHEET_NS}}}is")
                t = ET.SubElement(is_el, f"{{{_SHEET_NS}}}t")
                t.text = value
            else:
                cell = ET.SubElement(
                    row_el, f"{{{_SHEET_NS}}}c", r=f"{column}{r_idx}", t=kind
                )
                v = ET.SubElement(cell, f"{{{_SHEET_NS}}}v")
                v.text = value
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _build_zip(members: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return buf.getvalue()


def _write_docx(tmp_path, document_xml: bytes, name: str = "test.docx"):
    path = tmp_path / name
    path.write_bytes(_build_zip({"word/document.xml": document_xml}))
    return path


def _write_xlsx(tmp_path, sheets: list[tuple[str, bytes]], name: str = "test.xlsx"):
    shared_xml = None
    if sheets and sheets[0][0] == "__shared__":
        shared_xml = sheets[0][1]
        sheets = sheets[1:]
    members: dict[str, bytes] = {
        "xl/workbook.xml": _xlsx_workbook_xml([title for title, _ in sheets]),
    }
    if shared_xml is not None:
        members["xl/sharedStrings.xml"] = shared_xml
    for index, (_, sheet_xml) in enumerate(sheets, start=1):
        members[f"xl/worksheets/sheet{index}.xml"] = sheet_xml
    path = tmp_path / name
    path.write_bytes(_build_zip(members))
    return path


# --- docx extraction ------------------------------------------------------ #


def test_docx_extraction_round_trip(tmp_path):
    path = _write_docx(tmp_path, _docx_document_xml(["Hello world"]))
    assert FileParser.extract_text(str(path)) == "Hello world"


def test_docx_multiple_paragraphs(tmp_path):
    path = _write_docx(
        tmp_path, _docx_document_xml(["First", "", "Second", "   ", "Third"])
    )
    assert FileParser.extract_text(str(path)) == "First\nSecond\nThird"


def test_docx_char_limit_enforced(tmp_path):
    path = _write_docx(tmp_path, _docx_document_xml(["x" * 100]))
    with pytest.raises(FileParserLimitError, match="exceeds the character limit"):
        FileParser.extract_text(str(path), max_characters=50)


def test_docx_dtd_rejected(tmp_path):
    evil = _docx_document_xml(["safe"]) + (
        b"<!DOCTYPE x [<!ENTITY hack SYSTEM 'file:///etc/passwd'>]>"
    )
    path = _write_docx(tmp_path, evil)
    with pytest.raises(FileParserLimitError, match="contains a DTD"):
        FileParser.extract_text(str(path))


def test_docx_member_uncompressed_cap(tmp_path, monkeypatch):
    monkeypatch.setattr(file_parser, "ZIP_MEMBER_MAX_BYTES", 50)
    path = _write_docx(tmp_path, _docx_document_xml(["word" * 50]))
    with pytest.raises(FileParserLimitError, match="uncompressed limit"):
        FileParser.extract_text(str(path))


def test_docx_total_footprint_cap(tmp_path, monkeypatch):
    monkeypatch.setattr(file_parser, "ZIP_TOTAL_MAX_BYTES", 50)
    path = _write_docx(tmp_path, _docx_document_xml(["word" * 50]))
    with pytest.raises(FileParserLimitError, match="declares more than"):
        FileParser.extract_text(str(path))


def test_docx_member_missing_rejected(tmp_path):
    path = tmp_path / "test.docx"
    path.write_bytes(_build_zip({"[Content_Types].xml": b"<Types/>"}))
    with pytest.raises(ValueError, match="Not a valid .docx"):
        FileParser.extract_text(str(path))


def test_not_a_zip_rejected(tmp_path):
    path = tmp_path / "test.docx"
    path.write_bytes(b"PK\x03\x04" + b"\x00" * 40)
    with pytest.raises(ValueError, match="not a zip container"):
        FileParser.extract_text(str(path))


def test_doc_refused(tmp_path):
    path = tmp_path / "test.doc"
    path.write_bytes(b"dummy")
    with pytest.raises(ValueError, match="Unsupported file format: .doc"):
        FileParser.extract_text(str(path))


def test_unsupported_suffix_refused(tmp_path):
    path = tmp_path / "test.unknown"
    path.write_bytes(b"dummy")
    with pytest.raises(ValueError, match="Unsupported file format: .unknown"):
        FileParser.extract_text(str(path))


# --- xlsx extraction ------------------------------------------------------ #


def test_xlsx_extraction_round_trip(tmp_path):
    shared = ["A1", "B1", "A2", "B2"]
    path = _write_xlsx(
        tmp_path,
        [
            (
                "__shared__",
                _xlsx_shared_strings(shared),
            ),
            (
                "Sheet1",
                _xlsx_sheet_xml(
                    [[("s", "0"), ("s", "1")], [("s", "2"), ("s", "3")]]
                ),
            ),
        ],
    )
    assert (
        FileParser.extract_text(str(path)) == "Sheet1: A1; B1\nSheet1: A2; B2"
    )


def test_xlsx_inline_strings_and_numbers(tmp_path):
    shared = ["shared value"]
    path = _write_xlsx(
        tmp_path,
        [
            ("__shared__", _xlsx_shared_strings(shared)),
            (
                "Sheet1",
                _xlsx_sheet_xml(
                    [
                        [("s", "0"), ("n", "42")],
                        [("inline", "inline text"), ("n", "3.14")],
                    ]
                ),
            ),
        ],
    )
    assert (
        FileParser.extract_text(str(path))
        == "Sheet1: shared value; 42\nSheet1: inline text; 3.14"
    )


def test_xlsx_char_limit_enforced(tmp_path):
    path = _write_xlsx(
        tmp_path,
        [
            (
                "Sheet1",
                _xlsx_sheet_xml([[("inline", "x" * 100)]]),
            )
        ],
    )
    with pytest.raises(FileParserLimitError, match="exceeds the character limit"):
        FileParser.extract_text(str(path), max_characters=50)


def test_xlsx_sheet_cap_enforced(tmp_path, monkeypatch):
    monkeypatch.setattr(file_parser, "XLSX_SHEET_MAX", 2)
    path = _write_xlsx(
        tmp_path,
        [
            ("One", _xlsx_sheet_xml([[("n", "1")]])),
            ("Two", _xlsx_sheet_xml([[("n", "2")]])),
            ("Three", _xlsx_sheet_xml([[("n", "3")]])),
        ],
    )
    with pytest.raises(FileParserLimitError, match="-sheet limit"):
        FileParser.extract_text(str(path))


def test_xlsx_row_cap_enforced(tmp_path, monkeypatch):
    monkeypatch.setattr(file_parser, "XLSX_ROW_MAX", 2)
    path = _write_xlsx(
        tmp_path,
        [
            (
                "Sheet1",
                _xlsx_sheet_xml(
                    [[("n", "1")], [("n", "2")], [("n", "3")]]
                ),
            )
        ],
    )
    with pytest.raises(FileParserLimitError, match="-row limit"):
        FileParser.extract_text(str(path))


def test_xlsx_dtd_rejected(tmp_path):
    evil = _xlsx_sheet_xml([[("n", "1")]]) + (
        b"<!DOCTYPE x [<!ENTITY hack SYSTEM 'file:///etc/passwd'>]>"
    )
    path = _write_xlsx(tmp_path, [("Sheet1", evil)])
    with pytest.raises(FileParserLimitError, match="contains a DTD"):
        FileParser.extract_text(str(path))


def test_xlsx_without_shared_strings_is_legal(tmp_path):
    """sharedStrings.xml is optional; a workbook without it extracts."""
    path = _write_xlsx(
        tmp_path,
        [("Sheet1", _xlsx_sheet_xml([[("inline", "only cell")]]))],
    )
    assert FileParser.extract_text(str(path)) == "Sheet1: only cell"


def test_xlsx_workbook_missing_uses_part_names(tmp_path):
    """Without xl/workbook.xml the sheet-part stem is the display name."""
    members = {"xl/worksheets/sheet1.xml": _xlsx_sheet_xml([[("n", "7")]])}
    path = tmp_path / "test.xlsx"
    path.write_bytes(_build_zip(members))
    assert FileParser.extract_text(str(path)) == "sheet1: 7"


if __name__ == "__main__":
    pytest.main([__file__])
