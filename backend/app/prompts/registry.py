"""
Prompt Registry for versioned prompt management.

Loads prompts from YAML files and provides SHA256 hashing for audit trails.
Gate 1 requirement for ADR-0004 provider adapters and prompt registry.
"""

import hashlib
import yaml
from pathlib import Path
from typing import Dict, Optional, Any


class PromptRegistry:
    """
    Versioned prompt registry with SHA256 hashing.
    
    Loads prompts from YAML files in the definitions/ directory.
    Each prompt has an ID, version, system/user templates, tools, and validators.
    """
    
    def __init__(self, definitions_path: Optional[Path] = None):
        """
        Initialize the prompt registry.
        
        Args:
            definitions_path: Path to the definitions directory. 
                            Defaults to backend/app/prompts/definitions/
        """
        if definitions_path is None:
            definitions_path = Path(__file__).parent / "definitions"
        
        self.definitions_path = Path(definitions_path)
        self.prompts: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._load_prompts()
    
    def _load_prompts(self) -> None:
        """Load all YAML prompt files from definitions directory."""
        if not self.definitions_path.exists():
            raise ValueError(
                f"Prompt definitions directory not found: {self.definitions_path}"
            )
        
        # Load all YAML files
        for yaml_file in self.definitions_path.glob("*.yaml"):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    prompt_data = yaml.safe_load(f)
                
                if not prompt_data or not isinstance(prompt_data, dict):
                    continue
                
                prompt_id = prompt_data.get("id")
                version = prompt_data.get("version")
                
                if not prompt_id or not version:
                    raise ValueError(
                        f"Prompt file {yaml_file.name} missing 'id' or 'version'"
                    )
                
                # Store prompt by ID and version
                if prompt_id not in self.prompts:
                    self.prompts[prompt_id] = {}
                
                self.prompts[prompt_id][version] = prompt_data
                
            except Exception as e:
                raise ValueError(
                    f"Failed to load prompt file {yaml_file.name}: {e}"
                ) from e
    
    def get_prompt(
        self, 
        prompt_id: str, 
        version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get a prompt by ID and optional version.
        
        Args:
            prompt_id: The prompt identifier (e.g., "ontology_generation")
            version: Optional version string (e.g., "1.0.0"). 
                    If None, returns the latest version.
        
        Returns:
            Dictionary containing:
                - id: Prompt ID
                - version: Version string
                - created_at: Creation date
                - system_prompt: System prompt text
                - user_prompt_template: User prompt template with {placeholders}
                - tools: List of tool names (empty for role contract)
                - validators: List of validator names
        
        Raises:
            ValueError: If prompt ID or version not found
        """
        if prompt_id not in self.prompts:
            raise ValueError(
                f"Prompt ID '{prompt_id}' not found in registry. "
                f"Available IDs: {list(self.prompts.keys())}"
            )
        
        versions = self.prompts[prompt_id]
        
        if version is None:
            # Return latest version (sort by semantic version)
            version = self._get_latest_version(versions)
        
        if version not in versions:
            raise ValueError(
                f"Version '{version}' not found for prompt '{prompt_id}'. "
                f"Available versions: {list(versions.keys())}"
            )
        
        return versions[version]
    
    def _get_latest_version(self, versions: Dict[str, Dict[str, Any]]) -> str:
        """Get the latest version from a dict of versions."""
        # Sort versions by semantic versioning (major.minor.patch)
        def version_key(v: str) -> tuple:
            try:
                parts = v.split('.')
                return tuple(int(p) for p in parts)
            except (ValueError, AttributeError):
                return (0, 0, 0)
        
        return max(versions.keys(), key=version_key)
    
    def get_sha256(
        self, 
        prompt_id: str, 
        version: Optional[str] = None
    ) -> str:
        """
        Get SHA256 hash of prompt content.
        
        The hash is computed over the concatenation of system_prompt and
        user_prompt_template to provide a stable content fingerprint.
        
        Args:
            prompt_id: The prompt identifier
            version: Optional version string
        
        Returns:
            SHA256 hash (hex string)
        """
        prompt = self.get_prompt(prompt_id, version)
        
        # Compute hash over system + user prompt concatenation
        system_prompt = prompt.get("system_prompt", "")
        user_template = prompt.get("user_prompt_template", "")
        
        content = f"{system_prompt}\n---\n{user_template}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
    
    def format_user_prompt(
        self,
        prompt_id: str,
        version: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Format a user prompt template with provided variables.
        
        Args:
            prompt_id: The prompt identifier
            version: Optional version string
            **kwargs: Variables to substitute in the template
        
        Returns:
            Formatted user prompt string
        
        Raises:
            ValueError: If required template variables are missing
        """
        prompt = self.get_prompt(prompt_id, version)
        template = prompt.get("user_prompt_template", "")
        
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise ValueError(
                f"Missing required variable {e} for prompt '{prompt_id}' v{version}"
            ) from e
    
    def list_prompts(self) -> Dict[str, list]:
        """
        List all available prompts and their versions.
        
        Returns:
            Dictionary mapping prompt IDs to lists of versions
        """
        return {
            prompt_id: list(versions.keys())
            for prompt_id, versions in self.prompts.items()
        }
