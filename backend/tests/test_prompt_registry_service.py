import pytest
import tempfile
from pathlib import Path
from app.services.prompt_registry_service import PromptRegistryService

@pytest.fixture
def mock_registry_file():
    content = """
# Prompt Registry

### Prompt: S00_ONTOLOGY (v1.0)
```text
Extract ontology for {domain}.
```

### Prompt: S02_PROFILE_SINGLE (v1.0)
```text
Profile for {name}
```

### Prompt: S02_PROFILE_SINGLE (v1.1)
```text
Updated profile for {name} with {detail}
```

### Prompt: S08_REPORT_EXECUTIVE (v2.0)
Generate an executive report.
"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
        f.write(content)
        temp_path = f.name
        
    yield temp_path
    
    Path(temp_path).unlink()

@pytest.fixture
def service(mock_registry_file):
    return PromptRegistryService(registry_path=mock_registry_file)

def test_template_resolution(service):
    prompt = service.get_prompt("S00_ONTOLOGY")
    assert "Extract ontology for {domain}." in prompt

def test_version_tracking(service):
    # Should get latest version by default
    latest = service.get_prompt("S02_PROFILE_SINGLE")
    assert "{detail}" in latest
    
    # Should be able to get specific version
    v1 = service.get_prompt("S02_PROFILE_SINGLE", version="1.0")
    assert "{detail}" not in v1
    assert "Profile for {name}" in v1

def test_parameter_injection(service):
    formatted = service.format_prompt("S00_ONTOLOGY", domain="technology")
    assert formatted == "Extract ontology for technology."
    
def test_parameter_injection_missing_args(service):
    with pytest.raises(ValueError, match="Missing required parameters"):
        service.format_prompt("S00_ONTOLOGY")

def test_parameter_injection_sanitization(service):
    # Tests that values are converted to strings and stripped
    formatted = service.format_prompt("S00_ONTOLOGY", domain="  finance  ")
    assert formatted == "Extract ontology for finance."

def test_cot_stripping(service):
    payload = "<think>We need to do X</think> Here is the output."
    stripped = service.strip_chain_of_thought(payload)
    assert stripped == "Here is the output."
    
    payload_multiline = "<think>\nThinking process...\n</think>\nActual content"
    stripped_multiline = service.strip_chain_of_thought(payload_multiline)
    assert stripped_multiline == "Actual content"

def test_reasoning_field_scrubbing(service):
    payload = '{"_reasoning": "Some thought process", "result": 42}'
    stripped = service.strip_chain_of_thought(payload)
    # The scrubbing might leave extra commas or spaces, but it shouldn't have the reasoning field.
    assert '"_reasoning"' not in stripped
    assert '"Some thought process"' not in stripped
    assert '"result": 42' in stripped
