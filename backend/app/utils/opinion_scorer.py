"""
Opinion Scorer Utility
Extracts 2D coordinates (Polarity, Intensity) from agent text using LLM analysis.
"""

import json
import re
from typing import Tuple, Dict, Any, Optional
from ..config import Config
from ..services.camel_model_factory import create_camel_model
from ..utils.logger import get_logger

logger = get_logger('askthepeople.opinion_scorer')

SYSTEM_PROMPT = """
You are a Social Dynamics Analyzer. analyze the following agent message/action and assign it 2D coordinates representing its stance and engagement.

X-Axis (Polarity): -1.0 (Strongly Opposed/Critical) to 1.0 (Strongly Supportive/Constructive). 0.0 is Neutral.
Y-Axis (Intensity): 0.0 (Passive/Uncertain/Apathetic) to 1.0 (Aggressive/Certain/Passionate).
Z-Axis (Nuance): 0.0 (Simple/Dogmatic/Binary) to 1.0 (Complex/Nuanced/Balanced).

Main Topic Context: {topic_context}

Output ONLY a JSON object with keys "x", "y", "z", and "reason" (max 10 words).
Example: {"x": 0.8, "y": 0.5, "z": 0.3, "reason": "Strongly supportive with moderate passion and low nuance."}
"""

class OpinionScorer:
    def __init__(self, topic_context: str = "General social issues and policy"):
        self.topic_context = topic_context
        self.model = create_camel_model("actor", prefer_boost=False) # Use standard model for cost efficiency
    
    def score_text(self, text: str) -> Tuple[float, float, float, str]:
        """
        Score text for Polarity (x), Intensity (y), and Nuance (z)
        
        Returns:
            (x, y, z, reason)
        """
        if not text or len(text.strip()) < 5:
            return 0.0, 0.0, 0.0, "Neutral/Minimal content"
            
        prompt = f"Analyze this text: '{text}'"
        system_msg = SYSTEM_PROMPT.replace("{topic_context}", self.topic_context)
        
        try:
            # Note: Camel model interface (simplified for this utility)
            # In our system, the response is usually the content field of the message
            response = self.model.generate(
                system_message=system_msg,
                user_message=prompt
            )
            
            # Clean response to find JSON
            match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if match:
                data = json.loads(match.group())
                x = float(data.get("x", 0.0))
                y = float(data.get("y", 0.0))
                z = float(data.get("z", 0.0))
                reason = data.get("reason", "No reason provided")
                
                # Clamp values
                x = max(-1.0, min(1.0, x))
                y = max(0.0, min(1.0, y))
                z = max(0.0, min(1.0, z))
                
                return x, y, z, reason
                
        except Exception as e:
            logger.error(f"Opinion scoring failed: {e}")
            
        return 0.0, 0.0, 0.0, "Scoring error"

def get_opinion_scorer(topic: str = None) -> OpinionScorer:
    return OpinionScorer(topic or "General social issues")
