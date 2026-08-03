"""
Response Utilities for Truth Contract Enforcement
Provides helper functions to ensure all API responses include required metadata
"""

from datetime import datetime


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
