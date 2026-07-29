"""
LLM client wrapper
Uniformly uses OpenAI format for calls
"""

import json
import re
from typing import Optional, Dict, Any, List
from openai import OpenAI

from ..config import Config


class LLMClient:
    """LLM Client"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        prefer_boost: bool = False,
    ):
        import os
        if prefer_boost and os.environ.get("LLM_BOOST_API_KEY"):
            self.api_key = api_key or os.environ.get("LLM_BOOST_API_KEY")
            self.base_url = base_url or os.environ.get("LLM_BOOST_BASE_URL") or Config.LLM_BASE_URL
            self.model = model or os.environ.get("LLM_BOOST_MODEL_NAME") or Config.LLM_MODEL_NAME
        else:
            self.api_key = api_key or Config.LLM_API_KEY
            self.base_url = base_url or Config.LLM_BASE_URL
            self.model = model or Config.LLM_MODEL_NAME

        self.timeout = timeout if timeout is not None else Config.LLM_TIMEOUT

        if not self.api_key:
            raise ValueError("LLM_API_KEY NOT CONFIGURED")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None
    ) -> str:
        """
        Send chat request
        
        Args:
            messages: List of messages
            temperature: Temperature parameter
            max_tokens: Maximum tokens
            response_format: Response format (e.g., JSON mode)
            
        Returns:
            Model response text
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if response_format:
            kwargs["response_format"] = response_format
        
        import time
        max_retries = 3
        base_delay = 2.0
        
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content
                if content is None:
                    raise ValueError(f"LLM returned empty content (finish_reason={response.choices[0].finish_reason})")
                break
            except Exception as e:
                # Include standard OpenAI errors and general exceptions
                if attempt == max_retries - 1:
                    raise e
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"LLM chat request failed (attempt {attempt+1}/{max_retries}): {e}. Retrying in {base_delay}s...")
                time.sleep(base_delay)
                base_delay *= 2
        
        # Some models (like MiniMax M2.5) may include <think> reasoning in content, which needs removal
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        return content
    
    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        Send chat request and return JSON
        
        Args:
            messages: List of messages
            temperature: Temperature parameter
            max_tokens: Maximum tokens
            
        Returns:
            Parsed JSON object
        """
        response = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        # Clean up markdown code block tags
        cleaned_response = response.strip()
        cleaned_response = re.sub(r'^```(?:json)?\s*\n?', '', cleaned_response, flags=re.IGNORECASE)
        cleaned_response = re.sub(r'\n?```\s*$', '', cleaned_response)
        cleaned_response = cleaned_response.strip()

        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON format returned from LLM: {cleaned_response}")

