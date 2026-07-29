"""
File parsing utility
Supports text extraction from PDF, Markdown, and TXT files
"""

import os
from pathlib import Path
from typing import List, Optional

from .input_policy import EXTRACTED_TEXT_CHARACTERS_MAX, PDF_PAGE_MAX


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
    
    SUPPORTED_EXTENSIONS = {'.pdf', '.md', '.markdown', '.txt'}
    
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

