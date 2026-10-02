"""
File parsing utility
Supports text extraction from PDF, Markdown, and TXT files
"""

import os
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional

from .input_policy import (
    EXTRACTED_TEXT_CHARACTERS_MAX,
    PDF_PAGE_MAX,
    XLSX_ROW_MAX,
    XLSX_SHEET_MAX,
    ZIP_MEMBER_MAX_BYTES,
    ZIP_TOTAL_MAX_BYTES,
)


class FileParserLimitError(ValueError):
    """Raised when extraction exceeds a declared resource ceiling."""


def _read_text_with_fallback(file_path: str) -> str:
    """
    Read text file, automatically detect encoding if UTF-8 fails.
    
    Adopts a multi-level fallback strategy:
    1. First attempt UTF-8 decoding
    2. Use charset_normalizer to detect encoding
    3. Fallback to chardet to detect encoding
    4. Finally fallback to UTF-8 + errors='replace'
    
    Args:
        file_path: File path
        
    Returns:
        Decoded text content
    """
    data = Path(file_path).read_bytes()
    
    # First try UTF-8
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        pass
    
    # Try detecting encoding using charset_normalizer
    encoding = None
    try:
        from charset_normalizer import from_bytes
        best = from_bytes(data).best()
        if best and best.encoding:
            encoding = best.encoding
    except Exception:
        pass
    
    # Fallback to chardet
    if not encoding:
        try:
            import chardet
            result = chardet.detect(data)
            encoding = result.get('encoding') if result else None
        except Exception:
            pass
    
    # Final fallback: use UTF-8 + replace
    if not encoding:
        encoding = 'utf-8'
    
    return data.decode(encoding, errors='replace')


class FileParser:
    """File Parser"""

    # `.doc` (the pre-2007 OLE binary format) is deliberately NOT supported:
    # it has no stdlib reader and no safe in-process parser short of new
    # dependencies; it is refused with the standard unsupported-format error.
    # `.docx`/`.xlsx` are OOXML zip containers parsed fail-closed below.
    SUPPORTED_EXTENSIONS = {'.pdf', '.md', '.markdown', '.txt', '.docx', '.xlsx'}
    
    @classmethod
    def extract_text(
        cls,
        file_path: str,
        *,
        max_characters: int = EXTRACTED_TEXT_CHARACTERS_MAX,
        max_pdf_pages: int = PDF_PAGE_MAX,
    ) -> str:
        """
        Extract text from file
        
        Args:
            file_path: File path
            
        Returns:
            Extracted text content
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        suffix = path.suffix.lower()
        
        if suffix not in cls.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file format: {suffix}")
        
        if suffix == '.pdf':
            return cls._extract_from_pdf(
                file_path,
                max_characters=max_characters,
                max_pages=max_pdf_pages,
            )
        elif suffix == '.docx':
            return cls._extract_from_docx(
                file_path,
                max_characters=max_characters,
            )
        elif suffix == '.xlsx':
            return cls._extract_from_xlsx(
                file_path,
                max_characters=max_characters,
            )
        elif suffix in {'.md', '.markdown'}:
            text = cls._extract_from_md(file_path)
        elif suffix == '.txt':
            text = cls._extract_from_txt(file_path)
        else:
            raise ValueError(f"Cannot process file format: {suffix}")

        if len(text) > max_characters:
            raise FileParserLimitError(
                "Extracted text exceeds the character limit."
            )
        return text
    
    @staticmethod
    def _extract_from_pdf(
        file_path: str,
        *,
        max_characters: int = EXTRACTED_TEXT_CHARACTERS_MAX,
        max_pages: int = PDF_PAGE_MAX,
    ) -> str:
        """Extract text from PDF"""
        if max_characters < 1:
            raise FileParserLimitError(
                "PDF extraction character limit must be positive."
            )
        if max_pages < 1:
            raise FileParserLimitError(
                "PDF extraction page limit must be positive."
            )
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ImportError("PyMuPDF required: pip install PyMuPDF")
        
        text_parts = []
        extracted_characters = 0
        with fitz.open(file_path) as doc:
            if len(doc) > max_pages:
                raise FileParserLimitError(
                    f"PDF exceeds the {max_pages}-page limit."
                )
            for page in doc:
                text = page.get_text()
                if text.strip():
                    separator_characters = 2 if text_parts else 0
                    extracted_characters += len(text) + separator_characters
                    if extracted_characters > max_characters:
                        raise FileParserLimitError(
                            "PDF extracted text exceeds the character limit."
                        )
                    text_parts.append(text)
        
        return "\n\n".join(text_parts)
    
    @staticmethod
    def _extract_from_md(file_path: str) -> str:
        """Extract text from Markdown, supports auto encoding detection"""
        return _read_text_with_fallback(file_path)
    
    @staticmethod
    def _extract_from_txt(file_path: str) -> str:
        """Extract text from TXT, supports auto encoding detection"""
        return _read_text_with_fallback(file_path)

    # --- OOXML (docx / xlsx) extraction --------------------------------- #
    #
    # Both formats are zip containers of XML parts. Extraction is stdlib-only
    # (zipfile + ElementTree): no new dependencies, and every resource the
    # archive declares is ceiling-checked BEFORE it is read, so a zip bomb
    # is refused by its own central directory rather than by OOM.
    #
    # The XML parser itself gets a belt-and-braces guard: OOXML parts from
    # Word/Excel never carry a DTD, so any <!DOCTYPE / <!ENTITY construct is
    # rejected outright — that closes the entity-expansion (billion laughs)
    # family before ElementTree ever sees the bytes.

    @staticmethod
    def _open_ooxml_part(archive: zipfile.ZipFile, name: str) -> bytes:
        """Read one zip member after size and DTD guards."""
        info = archive.getinfo(name)
        if info.file_size > ZIP_MEMBER_MAX_BYTES:
            raise FileParserLimitError(
                f"Archive member {name} exceeds the "
                f"{ZIP_MEMBER_MAX_BYTES}-byte uncompressed limit."
            )
        data = archive.read(name)
        if b"<!DOCTYPE" in data or b"<!ENTITY" in data:
            # OOXML does not use DTDs; their presence means either a
            # malformed export or an entity-expansion payload.
            raise FileParserLimitError(
                f"Archive member {name} contains a DTD, which OOXML parts "
                "never legitimately carry; refusing to parse it."
            )
        return data

    @staticmethod
    def _validate_zip_footprint(file_path: str) -> zipfile.ZipFile:
        """Open an OOXML archive after checking its declared uncompressed size."""
        try:
            archive = zipfile.ZipFile(file_path)
        except zipfile.BadZipFile:
            raise ValueError(
                "Not a valid OOXML archive: the file is not a zip container."
            ) from None
        total = sum(info.file_size for info in archive.infolist())
        if total > ZIP_TOTAL_MAX_BYTES:
            archive.close()
            raise FileParserLimitError(
                "Archive declares more than "
                f"{ZIP_TOTAL_MAX_BYTES} bytes uncompressed; refusing it."
            )
        return archive

    @staticmethod
    def _extract_from_docx(
        file_path: str,
        *,
        max_characters: int = EXTRACTED_TEXT_CHARACTERS_MAX,
    ) -> str:
        """Extract body text from a Word .docx (OOXML) document.

        Walks ``word/document.xml`` paragraph by paragraph, joining run
        text. Table cell text is included because tables are paragraphs in
        OOXML. Headers/footers are intentionally skipped: they carry page
        furniture, not report content.
        """
        if max_characters < 1:
            raise FileParserLimitError(
                "DOCX extraction character limit must be positive."
            )
        archive = FileParser._validate_zip_footprint(file_path)
        try:
            try:
                document = FileParser._open_ooxml_part(
                    archive, "word/document.xml"
                )
            except KeyError:
                raise ValueError(
                    "Not a valid .docx document: word/document.xml is missing."
                )
            root = ET.fromstring(document)
            word_ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
            paragraphs = []
            extracted_characters = 0
            # Iterate paragraphs directly so runs inside one paragraph join
            # without separators, while paragraphs join with newlines.
            for paragraph in root.iter(f"{word_ns}p"):
                runs = [
                    text.text or ""
                    for text in paragraph.iter(f"{word_ns}t")
                ]
                line = "".join(runs).strip()
                if not line:
                    continue
                separator_characters = 1 if paragraphs else 0
                extracted_characters += len(line) + separator_characters
                if extracted_characters > max_characters:
                    raise FileParserLimitError(
                        "DOCX extracted text exceeds the character limit."
                    )
                paragraphs.append(line)
            return "\n".join(paragraphs)
        finally:
            archive.close()

    @staticmethod
    def _extract_from_xlsx(
        file_path: str,
        *,
        max_characters: int = EXTRACTED_TEXT_CHARACTERS_MAX,
    ) -> str:
        """Extract cell text from an Excel .xlsx (OOXML) workbook.

        Output is one line per populated row, ``Sheet: cell; cell; ...``,
        in sheet/row order — a shape an LLM can read directly. Shared
        strings, inline strings, and numeric/formula-cached values are
        handled; the formula itself is never executed.
        """
        if max_characters < 1:
            raise FileParserLimitError(
                "XLSX extraction character limit must be positive."
            )
        archive = FileParser._validate_zip_footprint(file_path)
        try:
            # Shared strings: <si> may hold multiple <t> runs (rich text).
            shared_strings: List[str] = []
            try:
                shared_bytes = FileParser._open_ooxml_part(
                    archive, "xl/sharedStrings.xml"
                )
                shared_root = ET.fromstring(shared_bytes)
                for si in shared_root:
                    shared_strings.append(
                        "".join(t.text or "" for t in si.iter(
                            "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"
                        ))
                    )
            except KeyError:
                pass  # workbooks without shared strings are legal

            # Sheet display names from xl/workbook.xml when available.
            sheet_names: Dict[str, str] = {}
            try:
                workbook_bytes = FileParser._open_ooxml_part(
                    archive, "xl/workbook.xml"
                )
                workbook_root = ET.fromstring(workbook_bytes)
                main_ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
                for index, sheet in enumerate(workbook_root.iter(f"{main_ns}sheet"), 1):
                    target = f"sheet{index}"
                    # sheetId order matches worksheets/sheetN.xml numbering in
                    # every producer we support; the r:id -> rels mapping is
                    # the general case and is deliberately not chased here.
                    sheet_names[target] = sheet.get("name") or target
            except KeyError:
                pass

            worksheet_names = sorted(
                name for name in archive.namelist()
                if name.startswith("xl/worksheets/sheet")
                and name.endswith(".xml")
            )
            if len(worksheet_names) > XLSX_SHEET_MAX:
                raise FileParserLimitError(
                    f"Workbook exceeds the {XLSX_SHEET_MAX}-sheet limit."
                )

            lines: List[str] = []
            extracted_characters = 0

            def _append_line(line: str) -> None:
                nonlocal extracted_characters
                separator_characters = 1 if lines else 0
                extracted_characters += len(line) + separator_characters
                if extracted_characters > max_characters:
                    raise FileParserLimitError(
                        "XLSX extracted text exceeds the character limit."
                    )
                lines.append(line)

            for worksheet in worksheet_names:
                try:
                    sheet_bytes = FileParser._open_ooxml_part(archive, worksheet)
                except FileParserLimitError:
                    raise
                sheet_root = ET.fromstring(sheet_bytes)
                main_ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
                key = worksheet.rsplit("/", 1)[-1][: -len(".xml")]
                display = sheet_names.get(key, key)
                rows_emitted = 0
                for row in sheet_root.iter(f"{main_ns}row"):
                    cells = []
                    for cell in row.iter(f"{main_ns}c"):
                        cell_type = cell.get("t")
                        if cell_type == "inlineStr":
                            value = "".join(
                                t.text or ""
                                for t in cell.iter(f"{main_ns}t")
                            )
                        else:
                            v = cell.find(f"{main_ns}v")
                            if v is None or v.text is None:
                                continue
                            if cell_type == "s":
                                try:
                                    value = shared_strings[int(v.text)]
                                except (ValueError, IndexError):
                                    continue
                            else:
                                value = v.text
                        if value:
                            cells.append(value)
                    if not cells:
                        continue
                    rows_emitted += 1
                    if rows_emitted > XLSX_ROW_MAX:
                        raise FileParserLimitError(
                            f"Sheet '{display}' exceeds the {XLSX_ROW_MAX}-row limit."
                        )
                    _append_line(f"{display}: " + "; ".join(cells))
            return "\n".join(lines)
        finally:
            archive.close()

    @classmethod
    def extract_from_multiple(cls, file_paths: List[str]) -> str:
        """
        Extract text from multiple files and merge
        
        Args:
            file_paths: List of file paths
            
        Returns:
            Merged text
        """
        all_texts = []
        
        for i, file_path in enumerate(file_paths, 1):
            try:
                text = cls.extract_text(file_path)
                filename = Path(file_path).name
                all_texts.append(f"=== Document {i}: {filename} ===\n{text}")
            except Exception as e:
                all_texts.append(f"=== Document {i}: {file_path} (Failed to extract: {str(e)}) ===")
        
        return "\n\n".join(all_texts)


def split_text_into_chunks(
    text: str, 
    chunk_size: int = 500, 
    overlap: int = 50
) -> List[str]:
    """
    Split text into chunks
    
    Args:
        text: Original text
        chunk_size: Character count per chunk
        overlap: Overlap character count
        
    Returns:
        List of text chunks
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if not isinstance(chunk_size, int) or isinstance(chunk_size, bool):
        raise ValueError("chunk_size must be an integer")
    if not isinstance(overlap, int) or isinstance(overlap, bool):
        raise ValueError("overlap must be an integer")
    if not 1 <= chunk_size <= 100_000:
        raise ValueError("chunk_size must be between 1 and 100000")
    if not 0 <= overlap < chunk_size:
        # overlap >= chunk_size makes `start = end - overlap` stop advancing,
        # which previously allowed one request to spin forever.
        raise ValueError("overlap must be non-negative and smaller than chunk_size")
    estimated_chunks = (
        1 if len(text) <= chunk_size
        else (len(text) + (chunk_size - overlap) - 1) // (chunk_size - overlap)
    )
    if estimated_chunks > 10_000:
        raise ValueError("text would produce more than 10000 chunks")

    if len(text) <= chunk_size:
        return [text] if text.strip() else []
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try splitting at sentence boundaries
        if end < len(text):
            # Find nearest sentence end character
            for sep in ['.\n', '!\n', '?\n', '\n\n', '. ', '! ', '? ']:
                last_sep = text[start:end].rfind(sep)
                if last_sep != -1 and last_sep > chunk_size * 0.3:
                    end = start + last_sep + len(sep)
                    break
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Next chunk starts from overlap position
        start = end - overlap if end < len(text) else len(text)
    
    return chunks

