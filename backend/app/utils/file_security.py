"""
Security utilities for file upload validation
"""

import os
import mimetypes
from typing import Optional, Tuple
from werkzeug.datastructures import FileStorage


# Allowed MIME types for uploads
ALLOWED_MIME_TYPES = {
    'application/pdf',
    'text/plain',
    'text/markdown',
    'text/x-markdown',
}

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown'}


def validate_file_upload(file: FileStorage, max_size_bytes: int = 10 * 1024 * 1024) -> Tuple[bool, Optional[str]]:
    """
    Validate uploaded file for security (P0 Gate 0 requirement).
    
    Checks:
    1. File extension whitelist
    2. MIME type validation
    3. File size limit
    
    Args:
        file: Flask FileStorage object
        max_size_bytes: Maximum file size in bytes (default 10MB)
        
    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, error_message) if invalid
    """
    if not file or not file.filename:
        return False, "No file provided"
    
    # 1. Check file extension
    if '.' not in file.filename:
        return False, "File must have an extension"
    
    ext = os.path.splitext(file.filename)[1].lower().lstrip('.')
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"File type '.{ext}' not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
    
    # 2. Check MIME type
    # Read first bytes to check MIME type
    file.seek(0)
    header = file.read(2048)
    file.seek(0)
    
    # Use mimetypes to guess based on extension as baseline
    guessed_type, _ = mimetypes.guess_type(file.filename)
    
    # Check PDF magic bytes
    if ext == 'pdf':
        if not header.startswith(b'%PDF-'):
            return False, "File claims to be PDF but has invalid format"
        if guessed_type and guessed_type not in ALLOWED_MIME_TYPES:
            return False, f"Invalid MIME type for PDF: {guessed_type}"
    
    # Check text files (should be readable as text)
    if ext in {'txt', 'md', 'markdown'}:
        try:
            # Try to decode as UTF-8 (will handle most text files)
            header.decode('utf-8', errors='strict')
        except UnicodeDecodeError:
            # Try common encodings
            try:
                header.decode('latin-1', errors='strict')
            except:
                return False, "Text file contains invalid encoding"
    
    # 3. Check file size (stream to avoid loading entire file into memory)
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Reset to beginning
    
    if file_size > max_size_bytes:
        size_mb = max_size_bytes / (1024 * 1024)
        return False, f"File size exceeds {size_mb}MB limit"
    
    if file_size == 0:
        return False, "File is empty"
    
    return True, None
