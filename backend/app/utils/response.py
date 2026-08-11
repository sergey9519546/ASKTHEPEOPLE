"""
Response Utilities for Truth Contract Enforcement
Provides helper functions to ensure all API responses include required metadata
"""

from datetime import datetime


_PUBLIC_SAFE_ERROR_MARKER = object()
_PUBLIC_SAFE_ERROR_ATTRIBUTE = "_askthepeople_public_safe_error"
_PUBLIC_SAFE_ERROR_STATUSES = {
    "report_dispatch_failed": frozenset({503}),
}


def mark_public_safe_error(response, code: str):
    """Mark one allowlisted error/status pair for production passthrough."""
    if code not in _PUBLIC_SAFE_ERROR_STATUSES:
        raise ValueError("public_safe_error_code_not_allowed")
    setattr(
        response,
        _PUBLIC_SAFE_ERROR_ATTRIBUTE,
        (_PUBLIC_SAFE_ERROR_MARKER, code),
    )
    return response


def get_public_safe_error_code(response) -> str | None:
    """Return a trusted allowlisted marker; never trust body/header metadata."""
    marker = getattr(response, _PUBLIC_SAFE_ERROR_ATTRIBUTE, None)
    if not (
        isinstance(marker, tuple)
        and len(marker) == 2
        and marker[0] is _PUBLIC_SAFE_ERROR_MARKER
    ):
        return None
    code = marker[1]
    allowed_statuses = _PUBLIC_SAFE_ERROR_STATUSES.get(code, frozenset())
    return code if response.status_code in allowed_statuses else None


def truth_response(data: dict) -> dict:
    """
    Wrap API response data with required truth contract metadata.
    
    Enforces Gate 1 requirement: All API responses must include metadata
    indicating synthetic origin and zero human respondents.
    
    Args:
        data: The actual response data payload
        
    Returns:
        dict: Response with truth contract metadata
    """
    return {
        "human_respondent_count": 0,
        "output_origin": "synthetic",
        "is_forecast": False,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "data": data
    }


def truth_metadata() -> dict:
    """
    Get truth contract metadata only (without data wrapper).
    
    Returns:
        dict: Truth contract metadata fields
    """
    return {
        "human_respondent_count": 0,
        "output_origin": "synthetic",
        "is_forecast": False,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
