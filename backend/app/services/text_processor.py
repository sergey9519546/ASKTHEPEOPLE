"""
Text Processing Service
"""

from typing import List
from ..utils.file_parser import FileParser, split_text_into_chunks


class TextProcessor:
    """Text Processor"""
    
    @staticmethod
    def extract_from_files(file_paths: List[str]) -> str:
        """Extract text from multiple files"""
        return FileParser.extract_from_multiple(file_paths)
    
    @staticmethod
    def split_text(
        text: str,
        chunk_size: int = 500,
        overlap: int = 50
    ) -> List[str]:
        """
        Split text
        
        Args:
            text: Original text
            chunk_size: Chunk size
            overlap: Overlap size
            
        Returns:
            List of text chunks
        """
        return split_text_into_chunks(text, chunk_size, overlap)
    
    @staticmethod
    def preprocess_text(text: str) -> str:
        """
        Preprocess text
        - Remove extra whitespace
        - Standardize line breaks
        
        Args:
            text: Original text
            
        Returns:
            Processed text
        """
        import re
        
        # Standardize line breaks
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove consecutive empty lines (keep max two line breaks)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove leading/trailing whitespace around lines
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        return text.strip()
    
    @staticmethod
    def get_text_stats(text: str) -> dict:
        """Get text statistical information"""
        return {
            "total_chars": len(text),
            "total_lines": text.count('\n') + 1,
            "total_words": len(text.split()),
        }

