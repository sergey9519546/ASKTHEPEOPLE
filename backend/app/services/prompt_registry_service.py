import re
import json
from pathlib import Path
from typing import Optional, Dict

class PromptRegistryService:
    def __init__(self, registry_path: str = "docs/ai/PROMPT_REGISTRY.md"):
        self.registry_path = Path(registry_path)
        self.prompts = self._parse_registry()

    def _parse_registry(self) -> Dict[str, Dict[str, str]]:
        """
        Parses the markdown file for prompts.
        Looks for blocks like:
        ### Prompt: S00_ONTOLOGY (v1.0)
        ```text
        You are a helpful assistant. Hello {name}!
        ```
        """
        prompts = {}
        if not self.registry_path.exists():
            return prompts

        content = self.registry_path.read_text(encoding="utf-8")
        
        # Regex to match: ### Prompt: [ID] (v[version])
        pattern = re.compile(
            r'###\s+Prompt:\s+([A-Z0-9_]+)\s*\(v([0-9\.]+)\)\s*(.*?)(?=\n###|\Z)', 
            re.DOTALL | re.IGNORECASE
        )
        
        for match in pattern.finditer(content):
            prompt_id, version, template = match.groups()
            prompt_id = prompt_id.upper()
            template = template.strip()
            
            # If the template is wrapped in a code block, extract the content
            code_block_match = re.search(r'^```(?:[\w-]*)\n(.*?)\n```$', template, re.DOTALL | re.MULTILINE)
            if code_block_match:
                template = code_block_match.group(1).strip()
            
            if prompt_id not in prompts:
                prompts[prompt_id] = {}
            prompts[prompt_id][version] = template
            
        return prompts

    def get_prompt(self, prompt_id: str, version: Optional[str] = None) -> str:
        if prompt_id not in self.prompts:
            raise ValueError(f"Prompt ID '{prompt_id}' not found in registry.")
            
        versions = self.prompts[prompt_id]
        if not versions:
            raise ValueError(f"No versions found for prompt ID '{prompt_id}'.")
            
        if version:
            if version not in versions:
                raise ValueError(f"Version '{version}' not found for prompt ID '{prompt_id}'.")
            return versions[version]
            
        # Return the latest version
        # Assuming versions are sortable strings like '1.0', '1.1'
        latest_version = sorted(versions.keys(), key=lambda v: [int(x) for x in v.split('.')])[-1]
        return versions[latest_version]

    def format_prompt(self, prompt_id: str, version: Optional[str] = None, **kwargs) -> str:
        template = self.get_prompt(prompt_id, version)
        
        # Identify required parameters
        required_params = re.findall(r'\{([a-zA-Z0-9_]+)\}', template)
        missing_params = [p for p in required_params if p not in kwargs]
        
        if missing_params:
            raise ValueError(f"Missing required parameters for '{prompt_id}': {missing_params}")
            
        # Input sanitization
        sanitized_kwargs = {k: self._sanitize_input(v) for k, v in kwargs.items()}
        
        # We only format fields that exist in the template
        # to avoid KeyError if kwargs has extra keys.
        formatted = template.format(**sanitized_kwargs)
        return formatted

    def _sanitize_input(self, value) -> str:
        if value is None:
            return ""
        value = str(value)
        # Basic sanitization: escape potentially problematic sequences if needed
        # For now, just a strip and basic type casting.
        return value.strip()

    def strip_chain_of_thought(self, payload: str) -> str:
        """
        Enforces stripping of raw Chain-of-Thought (<think> tags) and 
        scrubs internal reasoning fields from output payloads.
        """
        # Strip <think>...</think> tags entirely
        stripped = re.sub(r'<think>.*?</think>', '', payload, flags=re.DOTALL | re.IGNORECASE)
        
        # Scrub common reasoning fields from JSON if present
        # This handles cases like "_reasoning": "...",
        # or "reasoning": "..."
        stripped = re.sub(r'"_reasoning"\s*:\s*".*?"\s*,?', '', stripped, flags=re.DOTALL)
        stripped = re.sub(r'"reasoning"\s*:\s*".*?"\s*,?', '', stripped, flags=re.DOTALL)
        stripped = re.sub(r'"internal_reasoning"\s*:\s*".*?"\s*,?', '', stripped, flags=re.DOTALL)
        
        # Clean up possible trailing commas in JSON output if needed, but 
        # a simple regex replace might break JSON. Just regexing fields.
        return stripped.strip()
