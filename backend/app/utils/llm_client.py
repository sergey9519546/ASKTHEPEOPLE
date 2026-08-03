"""
LLM client wrapper
Uniformly uses OpenAI format for calls
"""

import hashlib
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
        routine_model: Optional[str] = None,
        timeout: Optional[float] = None,
        prefer_boost: bool = False,
    ):
        import os
        if prefer_boost and os.environ.get("LLM_BOOST_API_KEY"):
            self.api_key = api_key or os.environ.get("LLM_BOOST_API_KEY")
            self.base_url = base_url or os.environ.get("LLM_BOOST_BASE_URL") or Config.LLM_BASE_URL
            self.model = model or os.environ.get("LLM_BOOST_MODEL_NAME") or Config.LLM_MODEL_NAME
            self.routine_model = routine_model or os.environ.get("LLM_ROUTINE_MODEL_NAME") or self.model
        else:
            self.api_key = api_key or Config.LLM_API_KEY
            self.base_url = base_url or Config.LLM_BASE_URL
            self.model = model or Config.LLM_MODEL_NAME
            self.routine_model = routine_model or os.environ.get("LLM_ROUTINE_MODEL_NAME") or self.model

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
        response_format: Optional[Dict] = None,
        complexity: str = "complex"
    ) -> str:
        """
        Send chat request

        Args:
            messages: List of messages
            temperature: Temperature parameter
            max_tokens: Maximum tokens
            response_format: Response format (e.g., JSON mode)
            complexity: Task complexity ("routine" or "complex") to determine routing

        Returns:
            Model response text
        """
        target_model = self.routine_model if complexity == "routine" else self.model
        kwargs = {
            "model": target_model,
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
        max_tokens: int = 4096,
        complexity: str = "complex"
    ) -> Dict[str, Any]:
        """
        Send chat request and return JSON

        Args:
            messages: List of messages
            temperature: Temperature parameter
            max_tokens: Maximum tokens
            complexity: Task complexity ("routine" or "complex")

        Returns:
            Parsed JSON object
        """
        response = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            complexity=complexity,
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

    def chat_with_role_contract(
        self,
        system_prompt: str,
        user_prompt: str,
        context_prompts: Optional[List[str]] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        complexity: str = "complex",
    ) -> Dict[str, Any]:
        """Send a chat request under the prompt-prefixing structural contract.

        P0 prompt-prefixing fix (audit §5 P0). The contract is:

        - Separate roles. The fixed prefix lives in the `system` role; the
          user-controlled content lives in the `user` role; optional
          context lives in additional `user` messages BEFORE the user
          content. Textual instructions in the system prompt are not a
          security boundary on their own — they are reinforced by the
          role split, by the zero-tools rule, by the structured-output
          request, and by the deterministic truth + terminology
          validators below.
        - Zero tools. The OpenAI `tools` parameter is NEVER passed. The
          model cannot make external tool calls under this contract.
        - Structured output. JSON mode is requested. A JSON decode
          failure raises and is never silently coerced to a
          valid-looking empty object.
        - Deterministic validators. The response text is checked for
          the truth contract keywords (zero human respondents, not a
          forecast) and the terminology prohibited terms (respondent,
          poll, public opinion, etc.). A hit is logged at warning level
          but does not block; gate 5 lands the gate-level block.
        - Per-call record. The model release alias, the system and user
          prompt hashes, the temperature, the structured-output flag,
          and the output hash are returned in the result dict so the
          caller can attach them to the run manifest.

        The full prompt registry, model release ledger, per-prompt
        evaluation suite, and adversarial prompt-injection red team
        land with gate 1 / gate 5 in
        adr/ADR-0004-provider-adapters-and-prompt-registry.md and
        adr/ADR-00010-no-chain-of-thought-retention.md.
        """
        if not system_prompt or not isinstance(system_prompt, str):
            raise ValueError("system_prompt is required and must be a string")
        if not user_prompt or not isinstance(user_prompt, str):
            raise ValueError("user_prompt is required and must be a string")

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt},
        ]
        # Context messages come BEFORE the user content so that the
        # user content remains the last role seen by the model and the
        # context cannot displace it.
        for ctx in context_prompts or []:
            if not ctx:
                continue
            messages.append({"role": "user", "content": ctx})
        messages.append({"role": "user", "content": user_prompt})

        response_text = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            complexity=complexity,
        )

        # Clean markdown code fences before parsing.
        cleaned = response_text.strip()
        cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\n?```\s*$', '', cleaned)
        cleaned = cleaned.strip()
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"chat_with_role_contract: invalid JSON returned by model "
                f"({self.model!r}): {cleaned[:200]!r}"
            ) from e

        # Deterministic validators. These do not block; they record.
        truth_audit = _audit_response(parsed, response_text)
        target_model = self.routine_model if complexity == "routine" else self.model

        return {
            "data": parsed,
            "model": target_model,
            "system_prompt_sha256": _sha256(system_prompt),
            "user_prompt_sha256": _sha256(user_prompt),
            "context_prompt_sha256s": [_sha256(c) for c in (context_prompts or []) if c],
            "output_sha256": _sha256(response_text),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "structured_output": True,
            "tools_bound": False,
            "truth_audit": truth_audit,
        }


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# Truth contract keywords and terminology prohibited terms. The check is
# case-insensitive. Hits are recorded in the result's `truth_audit` field
# so the caller can decide what to do (warning log here, gate 5 lands the
# block).
_TRUTH_KEYWORDS_REQUIRED = (
    # Required in JSON output, per PRODUCT_TRUTH_CONTRACT.md:
    ("isForecast", "is_forecast", '"is_forecast"'),
)

_TRUTH_KEYWORDS_PROHIBITED = (
    # Output MUST NOT contain framing that implies real respondents,
    # measured public opinion, or a digital twin.
    "respondent",
    "public opinion",
    "polling",
    "poll result",
    "digital twin",
)


def _audit_response(parsed: Any, raw: str) -> Dict[str, Any]:
    """Run the deterministic truth + terminology validators on a response.

    The validators do not block; they record. The gate-5 eval suite
    owns the block-on-violation behavior; this layer records so the
    caller can attach the audit to the run manifest.
    """
    text = raw.lower()
    prohibited_hits = sorted({t for t in _TRUTH_KEYWORDS_PROHIBITED if t in text})
    required_hits: List[str] = []
    for kw in _TRUTH_KEYWORDS_REQUIRED:
        if not any(k.lower() in text for k in (kw if isinstance(kw, tuple) else (kw,))):
            required_hits.append(kw if isinstance(kw, str) else kw[0])
    return {
        "prohibited_term_hits": prohibited_hits,
        "required_keyword_misses": required_hits,
    }

