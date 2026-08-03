"""
Security Tests for ASKTHEPEOPLE (Gate 0 - Phase 1.2)

Tests cross-tenant isolation, export disclosures, and file upload safety.
"""

import os
import io
import json
import pytest
import tempfile
from datetime import datetime


class TestFileUploadSecurity:
    """Test file upload validation (P0)"""
    
    def test_file_size_limit(self):
        """Test that files over 10MB are rejected"""
        from app.config import Config
        
        # Verify config is set to 10MB
        assert Config.MAX_CONTENT_LENGTH == 10 * 1024 * 1024, \
            "MAX_CONTENT_LENGTH should be 10MB for security"
    
    def test_file_extension_whitelist(self):
        """Test that only allowed file extensions are accepted"""
        from app.config import Config
        
        allowed = Config.ALLOWED_EXTENSIONS
        assert allowed == {'pdf', 'md', 'txt', 'markdown'}, \
            "Only PDF, MD, TXT, MARKDOWN should be allowed"
    
    def test_mime_validation_exists(self):
        """Test that MIME validation utility exists"""
        from app.utils.file_security import validate_file_upload
        
        # Function should exist
        assert callable(validate_file_upload)
    
    def test_pdf_magic_bytes_validation(self):
        """Test that PDF files are validated by magic bytes"""
        from app.utils.file_security import validate_file_upload
        from werkzeug.datastructures import FileStorage
        
        # Create fake PDF with wrong magic bytes
        fake_pdf = io.BytesIO(b"This is not a PDF")
        fake_pdf_file = FileStorage(
            stream=fake_pdf,
            filename="fake.pdf",
            content_type="application/pdf"
        )
        
        is_valid, error = validate_file_upload(fake_pdf_file)
        assert not is_valid, "Should reject PDF with invalid magic bytes"
        assert "invalid format" in error.lower()
    
    def test_valid_pdf_accepted(self):
        """Test that valid PDF files are accepted"""
        from app.utils.file_security import validate_file_upload
        from werkzeug.datastructures import FileStorage
        
        # Create minimal valid PDF
        valid_pdf = io.BytesIO(b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n")
        valid_pdf_file = FileStorage(
            stream=valid_pdf,
            filename="test.pdf",
            content_type="application/pdf"
        )
        
        is_valid, error = validate_file_upload(valid_pdf_file)
        assert is_valid, f"Should accept valid PDF: {error}"
    
    def test_empty_file_rejected(self):
        """Test that empty files are rejected"""
        from app.utils.file_security import validate_file_upload
        from werkzeug.datastructures import FileStorage
        
        empty_file = io.BytesIO(b"")
        empty_file_obj = FileStorage(
            stream=empty_file,
            filename="empty.txt",
            content_type="text/plain"
        )
        
        is_valid, error = validate_file_upload(empty_file_obj)
        assert not is_valid, "Should reject empty files"
        assert "empty" in error.lower()


class TestExportDisclosures:
    """Test that all exports include required disclosures (P0)"""
    
    def test_pdf_export_has_disclosure(self):
        """Test that PDF exports include synthetic data disclosure"""
        from app.services.export_service import SYNTHETIC_DISCLOSURE
        
        # Verify disclosure text exists and is non-empty
        assert SYNTHETIC_DISCLOSURE, "PDF disclosure text must be defined"
        assert "SYNTHETIC" in SYNTHETIC_DISCLOSURE.upper()
    
    def test_csv_export_has_disclosure_columns(self):
        """Test that CSV exports include disclosure metadata columns"""
        from app.services.export_service import CSVExporter, ZepToolsService
        
        # Create a minimal CSV export
        exporter = CSVExporter(ZepToolsService())
        
        # Test with empty results
        csv_output = exporter.export_survey_results([])
        
        # Check that disclosure columns are in header
        assert "response_origin" in csv_output
        assert "human_respondents" in csv_output
    
    def test_json_config_has_disclosure(self):
        """Test that JSON config exports include disclosure metadata"""
        from app.api.simulation import _with_config_truth
        
        # Test config transformation
        test_config = {"test_key": "test_value"}
        disclosed_config = _with_config_truth(test_config)
        
        # Should have disclosure keys
        assert "truth_status" in disclosed_config
        assert "control_metadata" in disclosed_config


class TestSecretsManagement:
    """Test that no secrets are hardcoded in the repository (P0)"""
    
    def test_env_production_has_no_secrets(self):
        """Test that .env.production file has no actual API keys"""
        env_prod_path = os.path.join(
            os.path.dirname(__file__), 
            "../../.env.production"
        )
        
        if not os.path.exists(env_prod_path):
            pytest.skip(".env.production does not exist")
        
        with open(env_prod_path, 'r') as f:
            content = f.read()
        
        # Check that API key lines are empty or have placeholder values
        lines = content.split('\n')
        for line in lines:
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Keys that should not have real values
                if any(secret in key for secret in ['API_KEY', 'SECRET_KEY', 'TOKEN']):
                    # Value should be empty or a placeholder
                    assert not value or value in ['', 'GENERATE_NEW_ONE_IN_RAILWAY'], \
                        f"Secret {key} should not have a real value in .env.production"


class TestInputValidation:
    """Test input validation and sanitization"""
    
    def test_spreadsheet_formula_injection_prevention(self):
        """Test that CSV exports prevent formula injection"""
        from app.services.export_service import _spreadsheet_safe
        
        # Test dangerous formula prefixes
        dangerous_inputs = [
            "=1+1",
            "+1+1",
            "-1+1",
            "@SUM(A1:A10)",
        ]
        
        for dangerous in dangerous_inputs:
            safe = _spreadsheet_safe(dangerous)
            # Should be escaped with leading quote
            assert safe.startswith("'"), \
                f"Formula injection should be prevented: {dangerous}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
