import os
import typing as _t

# Provider modules
import openai_api as _openai
try:
    import gemini_api as _gemini
except Exception:  # pragma: no cover
    _gemini = None

_PROVIDER = os.environ.get("AI_PROVIDER", "openai").lower()


def _get_module():
    if _PROVIDER == "gemini" and _gemini is not None:
        return _gemini
    return _openai


# Facade: conversational assistant
# Returns the same structures as existing code expects

def conversational_facilitator(prompt: str, quadrants: _t.Optional[dict] = None):
    mod = _get_module()
    # Gemini provides conversational_facilitator; OpenAI provides same in openai_api
    if hasattr(mod, "conversational_facilitator"):
        return mod.conversational_facilitator(prompt, quadrants=quadrants)
    # Fallback to OpenAI if provider lacks function
    return _openai.conversational_facilitator(prompt, quadrants=quadrants)


# Facade: board executive summary
# Returns dict with {'summary': str} or {'error': ..., 'code': ...}

def summarize_board(quadrants: dict, tone: str = "neutral", length: str = "medium"):
    mod = _get_module()
    # Preferred provider-specific function name used in existing code
    if hasattr(mod, "summarize_board_with_openai"):
        return mod.summarize_board_with_openai(quadrants, tone=tone, length=length)
    # Try generic name if present on provider
    if hasattr(mod, "summarize_board"):
        return mod.summarize_board(quadrants, tone=tone, length=length)
    # Fallback to OpenAI implementation
    return _openai.summarize_board_with_openai(quadrants, tone=tone, length=length)


# Facade: goals↔status alignment scoring
# Returns {'score': int, 'rationale': str} or {'error': ..., 'code': ...}

def assess_goals_status_alignment(quadrants: dict):
    mod = _get_module()
    if hasattr(mod, "assess_goals_status_alignment"):
        return mod.assess_goals_status_alignment(quadrants)
    # Fallback to OpenAI implementation if provider lacks it
    return _openai.assess_goals_status_alignment(quadrants)
