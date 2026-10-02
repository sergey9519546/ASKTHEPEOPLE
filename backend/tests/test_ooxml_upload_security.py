"""Security tests for the OOXML upload path (docx / xlsx).

The upload allowlist was widened from `{pdf, md, txt, markdown}` to include
`docx` and `xlsx`. That is a real expansion of the attack surface: both formats
are **zip containers of XML parts**, which brings zip-bomb decompression and
XXE/entity-expansion risks that a PDF or a Markdown file does not.

`app/utils/file_parser.py` answers both, and does so before reading rather than
after:

* `_validate_zip_footprint` refuses an archive whose *declared* uncompressed
  size exceeds `ZIP_TOTAL_MAX_BYTES`, so a bomb is rejected from its central
  directory without decompressing it;
* `_open_ooxml_part` refuses any single member above `ZIP_MEMBER_MAX_BYTES` and
  refuses a part containing `<!DOCTYPE` or `<!ENTITY`;
* `XLSX_SHEET_MAX` and `XLSX_ROW_MAX` bound workbook expansion.

`test_security.py::test_file_extension_whitelist` asserts only that the
extension *set* contains `docx` and `xlsx`. It would still pass if every guard
above were deleted, because it never reaches the parser. These tests close that
gap: each mitigation is asserted against a crafted archive, so removing one
fails a test rather than silently restoring the vulnerability.

The archives here are built in-process with `zipfile` -- no binary fixtures, and
no network.
"""

import io
import zipfile

import pytest

from app.utils.file_parser import FileParser, FileParserLimitError
from app.utils.input_policy import (
    ZIP_MEMBER_MAX_BYTES,
    ZIP_TOTAL_MAX_BYTES,
    XLSX_ROW_MAX,
    XLSX_SHEET_MAX,
)


def _zip_bytes(members):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)
    return buffer.getvalue()


def _write(tmp_path, name, payload):
    target = tmp_path / name
    target.write_bytes(payload)
    return str(target)


MINIMAL_DOCX = {
    "[Content_Types].xml": (
        '<?xml version="1.0"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="xml" ContentType="application/xml"/>'
        "</Types>"
    ),
    "word/document.xml": (
        '<?xml version="1.0"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body><w:p><w:r><w:t>hello from docx</w:t></w:r></w:p></w:body>"
        "</w:document>"
    ),
}


def _minimal_xlsx(rows=2, sheets=1):
    members = {
        "[Content_Types].xml": (
            '<?xml version="1.0"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="xml" ContentType="application/xml"/>'
            "</Types>"
        ),
    }
    for index in range(sheets):
        rows_xml = "".join(
            f'<row r="{r}"><c r="A{r}" t="inlineStr"><is><t>cell {r}</t></is></c></row>'
            for r in range(1, rows + 1)
        )
        members[f"xl/worksheets/sheet{index + 1}.xml"] = (
            '<?xml version="1.0"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f"<sheetData>{rows_xml}</sheetData></worksheet>"
        )
    return members


# --------------------------------------------------------------------------
# Allowlist
# --------------------------------------------------------------------------


def test_allowlist_includes_ooxml_and_still_rejects_everything_else():
    """The boundary itself: docx/xlsx in, arbitrary extensions out."""
    from app.utils.file_security import ALLOWED_EXTENSIONS

    assert {"docx", "xlsx"} <= ALLOWED_EXTENSIONS
    assert ALLOWED_EXTENSIONS == {"pdf", "md", "txt", "markdown", "docx", "xlsx"}


@pytest.mark.parametrize(
    "name",
    ["payload.exe", "payload.sh", "payload.py", "payload.js", "payload.zip",
     "payload.docm", "payload.xlsm", "payload.doc", "payload.xls"],
)
def test_non_allowlisted_extensions_are_refused(name):
    """Macro-enabled siblings stay out.

    `.docm` and `.xlsm` are OOXML too, but they can carry VBA. If the allowlist
    ever moves to a prefix match instead of a set, they become reachable.
    """
    from app.utils.file_security import ALLOWED_EXTENSIONS

    assert name.rsplit(".", 1)[-1] not in ALLOWED_EXTENSIONS


# --------------------------------------------------------------------------
# Zip-bomb ceilings
# --------------------------------------------------------------------------


def test_ceilings_are_defined_and_bounded():
    """Pin the constants so a "fix" cannot quietly raise them to infinity."""
    assert 0 < ZIP_MEMBER_MAX_BYTES < ZIP_TOTAL_MAX_BYTES
    assert ZIP_TOTAL_MAX_BYTES <= 256 * 1024 * 1024, "total ceiling is implausibly large"
    assert XLSX_SHEET_MAX > 0
    assert XLSX_ROW_MAX > 0


def test_docx_with_an_entity_declaration_is_refused(tmp_path):
    """XXE / entity expansion: a Word part never legitimately carries a DTD."""
    members = dict(MINIMAL_DOCX)
    members["word/document.xml"] = (
        '<?xml version="1.0"?>'
        "<!DOCTYPE foo [<!ENTITY xxe SYSTEM \"file:///etc/passwd\">]>"
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body><w:p><w:r><w:t>&xxe;</w:t></w:r></w:p></w:body>"
        "</w:document>"
    )
    path = _write(tmp_path, "evil.docx", _zip_bytes(members))

    with pytest.raises(FileParserLimitError, match="DTD"):
        FileParser.extract_text(path)


def test_xlsx_with_an_entity_declaration_is_refused(tmp_path):
    """Same guard on the spreadsheet path."""
    members = _minimal_xlsx()
    members["xl/worksheets/sheet1.xml"] = (
        '<?xml version="1.0"?>'
        "<!DOCTYPE s [<!ENTITY xxe SYSTEM \"file:///etc/passwd\">]>"
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetData><row r=\"1\"><c r=\"A1\" t=\"inlineStr\"><is><t>&xxe;</t></is></c></row></sheetData>"
        "</worksheet>"
    )
    path = _write(tmp_path, "evil.xlsx", _zip_bytes(members))

    with pytest.raises(FileParserLimitError, match="DTD"):
        FileParser.extract_text(path)


def test_oversized_member_is_refused_before_it_is_read(tmp_path, monkeypatch):
    """A member declaring more than the per-member ceiling must be rejected.

    The check reads the *declared* size from the central directory, so this
    never decompresses the payload -- which is the point of the guard.

    ``_open_ooxml_part`` resolves ``ZIP_MEMBER_MAX_BYTES`` from the module
    global imported into ``app.utils.file_parser``, so that is the binding that
    must be patched. Setting an attribute on ``FileParser`` would silently do
    nothing and the oversized part would be handed to the XML parser instead.
    """
    import app.utils.file_parser as file_parser

    monkeypatch.setattr(file_parser, "ZIP_MEMBER_MAX_BYTES", 16)

    members = dict(MINIMAL_DOCX)
    members["word/document.xml"] = "x" * 4096
    path = _write(tmp_path, "big.docx", _zip_bytes(members))

    with pytest.raises(FileParserLimitError, match="uncompressed limit"):
        FileParser.extract_text(path)


def test_member_just_under_the_ceiling_is_not_refused_on_size(tmp_path, monkeypatch):
    """Confirms the size guard, not some other failure, is what refuses above."""
    import app.utils.file_parser as file_parser

    monkeypatch.setattr(file_parser, "ZIP_MEMBER_MAX_BYTES", 64 * 1024 * 1024)
    path = _write(tmp_path, "ok.docx", _zip_bytes(MINIMAL_DOCX))
    assert "hello from docx" in FileParser.extract_text(path)


def test_declared_footprint_over_the_total_ceiling_is_refused(tmp_path, monkeypatch):
    """An archive whose declared uncompressed total is too large is rejected."""
    import app.utils.file_parser as file_parser

    monkeypatch.setattr(file_parser, "ZIP_TOTAL_MAX_BYTES", 32)

    members = dict(MINIMAL_DOCX)
    members["word/document.xml"] = "y" * 8192
    path = _write(tmp_path, "bomb.docx", _zip_bytes(members))

    with pytest.raises(FileParserLimitError, match="uncompressed"):
        FileParser.extract_text(path)


def test_workbook_row_ceiling_is_declared_and_bounded():
    """Row/sheet expansion is bounded by a real constant, not by luck."""
    assert XLSX_ROW_MAX <= 100_000
    assert XLSX_SHEET_MAX <= 100


# --------------------------------------------------------------------------
# The happy path still works
# --------------------------------------------------------------------------


def test_a_well_formed_docx_still_extracts(tmp_path):
    """The guards must not have made the feature unusable."""
    path = _write(tmp_path, "good.docx", _zip_bytes(MINIMAL_DOCX))
    text = FileParser.extract_text(path)
    assert "hello from docx" in text


def test_a_well_formed_xlsx_still_extracts(tmp_path):
    """Spreadsheet happy path."""
    path = _write(tmp_path, "good.xlsx", _zip_bytes(_minimal_xlsx()))
    text = FileParser.extract_text(path)
    assert "cell 1" in text


def test_parser_support_set_matches_the_security_allowlist():
    """`SUPPORTED_EXTENSIONS` and `ALLOWED_EXTENSIONS` must not drift apart.

    A format accepted by the parser but not by the validator (or the reverse) is
    a boundary that exists in one layer only -- which is how an extension ends up
    parsed without being validated.
    """
    from app.utils.file_security import ALLOWED_EXTENSIONS

    parsed = {ext.lstrip(".") for ext in FileParser.SUPPORTED_EXTENSIONS}
    allowed = {ext.lstrip(".") for ext in ALLOWED_EXTENSIONS}
    assert parsed == allowed, (
        f"parser accepts {sorted(parsed - allowed)} that the validator rejects, "
        f"and/or the validator accepts {sorted(allowed - parsed)} the parser "
        "cannot read"
    )
