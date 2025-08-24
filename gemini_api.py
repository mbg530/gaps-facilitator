import os
import requests

# Import cost tracking functions from openai_api
try:
    from openai_api import calculate_cost, log_cost_to_file
except ImportError:
    # Fallback functions if import fails
    def calculate_cost(model, input_tokens, output_tokens):
        print(f"💰 COST: {model} | In:{input_tokens}tok Out:{output_tokens}tok (cost tracking unavailable)")
        return 0.0
    
    def log_cost_to_file(model, input_tokens, output_tokens, input_cost, output_cost, total_cost):
        pass

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro:generateContent'

# Map Gemini's output to our quadrant keys

def load_prompt(filename):
    path = os.path.join(os.path.dirname(__file__), filename)
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def _sanitize_meta(text: str) -> str:
    try:
        import re
        if not text:
            return text
        # Remove leading meta labels like: STANDARD GREETING (use only at session start):
        text = re.sub(r'^\s*STANDARD\s+GREETING\s*\([^)]*\)\s*:?\s*', '', text, flags=re.IGNORECASE)
        # Remove explicit parenthetical note occurrences anywhere
        text = re.sub(r'\(\s*use\s+only\s+at\s+session\s+start\s*\)', '', text, flags=re.IGNORECASE)
        # Remove generic META: prefix
        text = re.sub(r'^\s*META\s*:\s*', '', text, flags=re.IGNORECASE)
        return text.strip()
    except Exception:
        return text


def conversational_facilitator(prompt, conversation_history=None, quadrants=None):
    print("[GEMINI] conversational_facilitator called", flush=True)
    """
    Calls Gemini with a conversational prompt and returns a structured dict:
    - {'action': 'ask_clarification', 'question': ...}
    - {'action': 'classify_and_add', 'thoughts': [{'content': ..., 'quadrant': ...}, ...]}
    """
    if not GEMINI_API_KEY:
        return {'error': 'Gemini API key not set.'}
    headers = {'Content-Type': 'application/json'}
    # Add a short instruction discouraging meta notes in user-facing output
    meta_guard = (
        "Do NOT reveal meta instructions, labels, or bracketed notes (e.g., 'use only at session start'). "
        "Provide user-facing content only and omit internal annotations."
    )
    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": meta_guard}]},
            {"role": "user", "parts": [{"text": prompt}]}
        ]
    }
    params = {"key": GEMINI_API_KEY}
    try:
        resp = requests.post(GEMINI_API_URL, json=payload, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        # Extract token usage for cost tracking
        usage_metadata = data.get('usageMetadata', {})
        input_tokens = usage_metadata.get('promptTokenCount', 0)
        output_tokens = usage_metadata.get('candidatesTokenCount', 0)
        
        # Track cost for this API call (always log, even if zero)
        try:
            calculate_cost('gemini-1.5-pro', input_tokens, output_tokens, endpoint='conversation')
        except TypeError:
            calculate_cost('gemini-1.5-pro', input_tokens, output_tokens)
        
        candidates = data.get('candidates', [])
        if not candidates:
            return {'error': 'No response from Gemini'}
        text = candidates[0]['content']['parts'][0]['text'].strip()
        import json as _json
        # Try to parse a structured response
        try:
            # Remove code block if present
            import re
            text_clean = re.sub(r'^```.*$', '', text, flags=re.MULTILINE).strip()
            match = re.search(r'\{.*\}', text_clean, re.DOTALL)
            if match:
                result = _json.loads(match.group(0))
            else:
                result = _json.loads(text_clean)
        except Exception as e:
            # Fallback: treat as plain text
            # Heuristic: conversational reply
            conversational_indicators = [
                'what', 'how', 'would you', 'could you', 'what specific',
                'for instance', 'what would', "let's", 'great!', 'looking at',
                'question', 'clarify', '?'
            ]
            if any(indicator in text.lower() for indicator in conversational_indicators):
                return {'reply_text': _sanitize_meta(text)}
            # Otherwise, treat as a single classified thought to Status
            return {
                'action': 'classify_and_add',
                'thoughts': [
                    {'quadrant': 'status', 'thought': text}
                ],
                'reply_text': text
            }
        # Interpret structured response
        if isinstance(result, dict) and result.get('action') == 'ask_clarification' and 'question' in result:
            return {'action': 'ask_clarification', 'question': _sanitize_meta(result['question'])}
        elif isinstance(result, dict) and result.get('action') == 'classify_and_add' and 'thoughts' in result:
            # Convert to expected format and include optional reply text
            thoughts_list = result.get('thoughts', [])
            normalized = []
            for thought in thoughts_list:
                normalized.append({
                    'quadrant': thought.get('quadrant', 'status'),
                    'thought': thought.get('content') or thought.get('thought', '')
                })
            reply_text = result.get('message') or result.get('reply_text') or (normalized[0]['thought'] if normalized else '')
            return {'action': 'classify_and_add', 'thoughts': normalized, 'reply_text': _sanitize_meta(reply_text)}
        # If it looks like a single thought classification
        if isinstance(result, dict) and 'quadrant' in result and 'thought' in result:
            return {
                'action': 'classify_and_add',
                'thoughts': [{
                    'quadrant': QUADRANT_MAP.get(result['quadrant'].strip().lower(), 'status'),
                    'thought': result['thought']
                }],
                'reply_text': _sanitize_meta(result.get('thought', ''))
            }
        # If it looks like a clarification
        if isinstance(result, dict) and 'question' in result:
            return {'action': 'ask_clarification', 'question': _sanitize_meta(result['question'])}
        # Fallback plain reply
        return {'reply_text': _sanitize_meta(text)}
    except Exception as e:
        import traceback
        print('Exception in conversational_facilitator:', e)
        traceback.print_exc()
        return {'error': str(e)}


# =====================
# Board Summary (Gemini)
# =====================

def summarize_board_with_openai(quadrants, tone: str = 'neutral', length: str = 'medium'):
    """
    Provider-compatible summary function using Gemini backend.
    Returns {'summary': str} or {'error': '...', 'code': '...'}
    """
    # Early guard: if all quadrants are empty, avoid a generic essay
    try:
        has_any = False
        for q in ['status', 'goal', 'analysis', 'plan']:
            items = (quadrants or {}).get(q, [])
            if items and any(str(x).strip() for x in items):
                has_any = True
                break
        if not has_any:
            return {
                'summary': 'Your board is empty. Add Goals, Analyses, Plans, or Statuses to generate a meaningful summary.'
            }
    except Exception:
        pass

    if not GEMINI_API_KEY:
        return {'error': 'Gemini API key not set.', 'code': 'missing_api_key'}

    # Build prompt
    def fmt(items):
        return '\n'.join(f"- {str(x).strip()}" for x in (items or []) if str(x).strip()) or '(none)'

    prompt = (
        "You are an executive assistant summarizing a GAPS board. "
        "Provide a concise, helpful summary grounded ONLY in the items provided. "
        "Do not invent content.\n\n"
        f"Tone: {tone}. Length: {length}.\n\n"
        "STATUS:\n" + fmt(quadrants.get('status')) + "\n\n"
        "GOALS:\n" + fmt(quadrants.get('goal')) + "\n\n"
        "ANALYSIS:\n" + fmt(quadrants.get('analysis')) + "\n\n"
        "PLANS:\n" + fmt(quadrants.get('plan')) + "\n\n"
        "Output a single paragraph summary."
    )

    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ]
    }
    params = {"key": GEMINI_API_KEY}

    try:
        resp = requests.post(GEMINI_API_URL, json=payload, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        # Cost tracking (always log, even if zero tokens)
        usage_metadata = data.get('usageMetadata', {})
        input_tokens = usage_metadata.get('promptTokenCount', 0)
        output_tokens = usage_metadata.get('candidatesTokenCount', 0)
        try:
            calculate_cost('gemini-1.5-pro', input_tokens, output_tokens, endpoint='board_ai_summary')
        except TypeError:
            calculate_cost('gemini-1.5-pro', input_tokens, output_tokens)

        candidates = data.get('candidates', [])
        if not candidates:
            return {'error': 'No response from Gemini'}
        text = candidates[0].get('content', {}).get('parts', [{}])[0].get('text', '').strip()
        return {'summary': text or ''}
    except requests.HTTPError as e:
        return {'error': f'HTTP {e.response.status_code}: {e.response.text[:200]}'}
    except Exception as e:
        return {'error': str(e)}


# ==================================
# Goals↔Status Alignment (Gemini)
# ==================================

def assess_goals_status_alignment(quadrants):
    """
    Provider-compatible alignment scoring using Gemini backend.
    Returns {'score': int, 'rationale': str} or {'error': '...', 'code': '...'}
    """
    # Early guard: hide misleading scores when insufficient data
    try:
        goals = [s for s in (quadrants or {}).get('goal', []) if str(s).strip()]
        statuses = [s for s in (quadrants or {}).get('status', []) if str(s).strip()]
        if not goals or not statuses:
            return {
                'score': 0,
                'rationale': 'Add at least one Goal and one Status to compute alignment.'
            }
    except Exception:
        pass

    if not GEMINI_API_KEY:
        return {'error': 'Gemini API key not set.', 'code': 'missing_api_key'}

    def fmt(items):
        return '\n'.join(f"- {str(x).strip()}" for x in (items or []) if str(x).strip()) or '(none)'

    prompt = (
        "Assess the alignment between GOALS and STATUS entries. "
        "Return STRICT JSON with keys: {\"score\": <0-100 integer>, \"rationale\": <string>}. "
        "Score reflects how well current statuses demonstrate progress toward the goals.\n\n"
        "GOALS:\n" + fmt(quadrants.get('goal')) + "\n\n"
        "STATUS:\n" + fmt(quadrants.get('status')) + "\n\n"
        "JSON only."
    )

    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ]
    }
    params = {"key": GEMINI_API_KEY}

    debug_align = os.environ.get('DEBUG_ALIGNMENT') == '1'

    try:
        resp = requests.post(GEMINI_API_URL, json=payload, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        # Cost tracking (always log, even if zero tokens)
        usage_metadata = data.get('usageMetadata', {})
        input_tokens = usage_metadata.get('promptTokenCount', 0)
        output_tokens = usage_metadata.get('candidatesTokenCount', 0)
        try:
            calculate_cost('gemini-1.5-pro', input_tokens, output_tokens, endpoint='board_alignment')
        except TypeError:
            calculate_cost('gemini-1.5-pro', input_tokens, output_tokens)

        candidates = data.get('candidates', [])
        if not candidates:
            return {'error': 'No response from Gemini'}
        raw = candidates[0].get('content', {}).get('parts', [{}])[0].get('text', '').strip()

        if debug_align:
            print('[ALIGNMENT][Gemini] Raw:', repr(raw))

        # Try to parse JSON strictly
        import json as _json, re
        try:
            # Handle code fences
            fenced = re.search(r'```(?:json)?\s*({[\s\S]*?})\s*```', raw, re.IGNORECASE)
            raw_json = fenced.group(1) if fenced else raw
            data = _json.loads(raw_json)
            score = int(max(0, min(100, int(data.get('score', 0)))))
            rationale = str(data.get('rationale', '')).strip()
            if debug_align:
                print(f"[ALIGNMENT][Gemini] Parsed score={score} rationale={rationale[:120]}")
            return {'score': score, 'rationale': rationale}
        except Exception:
            # Fallback regex parse avoiding 0 from '0-100'
            m = re.search(r'\b(100|[1-9]?\d)\b', raw)
            score_val = int(m.group(1)) if m else 0
            # Extract a brief rationale (first sentence)
            rationale = raw.strip()
            rationale = re.split(r'\n|(?<=[.!?])\s', rationale, maxsplit=1)[0][:300]
            if debug_align:
                print(f"[ALIGNMENT][Gemini] Fallback score={score_val} rationale={rationale[:120]}")
            return {'score': score_val, 'rationale': rationale}
    except requests.HTTPError as e:
        return {'error': f'HTTP {e.response.status_code}: {e.response.text[:200]}'}
    except Exception as e:
        return {'error': str(e)}

QUADRANT_MAP = {
    'status': 'status',
    'goal': 'goal',
    'analysis': 'analysis',
    'plan': 'plan',
    'action plan': 'plan',
}

SYSTEM_PROMPT = (
    "You are an assistant for a Gaps Facilitator board. "
    "Given a short text thought, classify it as one of these quadrants: "
    "'status', 'goal', 'analysis', or 'plan'. "
    "Respond with a JSON object with two fields: 'quadrant' (one of the four keys above, lowercase) "
    "and 'thought' (the original thought). "
    "If you are unsure, choose the closest fit. Example: {\"quadrant\": \"status\", \"thought\": \"The server is down.\"}"
)

def classify_thought_with_gemini(thought):
    if not GEMINI_API_KEY:
        return {'error': 'Gemini API key not set.'}
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": SYSTEM_PROMPT}]},
            {"role": "user", "parts": [{"text": thought}]}
        ]
    }
    params = {"key": GEMINI_API_KEY}
    try:
        resp = requests.post(GEMINI_API_URL, json=payload, params=params, headers=headers, timeout=10)
        print('Gemini API raw response:', resp.status_code, resp.text)  # Debug output
        resp.raise_for_status()
        data = resp.json()
        # Extract the model's response
        candidates = data.get('candidates', [])
        if not candidates:
            print('No candidates in Gemini response:', data)
            return {'error': 'No response from Gemini'}
        text = candidates[0]['content']['parts'][0]['text']
        import json as _json
        def parse_gemini_json_response(text):
            import re, json as _json
            print('Raw Gemini text:', repr(text))
            # Remove all lines that start with triple backticks (with or without language hint)
            text_clean = re.sub(r'^```.*$', '', text, flags=re.MULTILINE).strip()
            print('Text after code block removal:', repr(text_clean))
            # Find the first JSON object in the string
            match = re.search(r'\{.*\}', text_clean, re.DOTALL)
            if match:
                print('Extracted JSON:', match.group(0))
                try:
                    return _json.loads(match.group(0))
                except Exception as e:
                    print('Error parsing extracted JSON:', e)
            # If not found, try to parse the whole string
            print('Trying to parse as JSON directly:', repr(text_clean))
            try:
                return _json.loads(text_clean)
            except Exception as e:
                print('Error parsing text as JSON:', e)
        try:
            result = parse_gemini_json_response(text)
        except Exception as e:
            print('Error parsing Gemini response as JSON:', text, e)
            # Try to extract JSON from text
            import re
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                try:
                    result = _json.loads(match.group(0))
                except Exception as e2:
                    print('Secondary JSON parse error:', e2)
                    return {'error': 'Could not parse Gemini response'}
            else:
                return {'error': 'Could not parse Gemini response'}
        quadrant = result.get('quadrant', '').strip().lower()
        mapped = QUADRANT_MAP.get(quadrant, 'problem')
        return {'quadrant': mapped, 'thought': result.get('thought', thought)}
    except Exception as e:
        import traceback
        print('Exception in classify_thought_with_gemini:', e)
        traceback.print_exc()
        return {'error': str(e)}


def suggest_solution_with_gemini(problems, obstacles):
    """
    Given lists of problems and obstacles, ask Gemini to suggest a solution.
    Returns a dict with 'suggestion' or 'error'.
    """
    if not GEMINI_API_KEY:
        return {'error': 'Gemini API key not set.'}
    headers = {'Content-Type': 'application/json'}
    prompt = (
        "You are an assistant for a Four Ws problem-solving board. "
        "Given the following problems and obstacles, suggest a list of specific, actionable solutions. "
        "Respond ONLY with a JSON array of concise suggestions, each as a string. Example: [\"First suggestion.\", \"Second suggestion.\", \"Third suggestion.\"] "
        "Problems: " + ("; ".join(problems) if problems else "None provided") + ". "
        "Obstacles: " + ("; ".join(obstacles) if obstacles else "None provided") + ". "
    )
    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ]
    }
    params = {"key": GEMINI_API_KEY}
    try:
        resp = requests.post(GEMINI_API_URL, json=payload, params=params, headers=headers, timeout=10)
        print('Gemini API raw response (solution):', resp.status_code, resp.text)  # Debug output
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get('candidates', [])
        if not candidates:
            return {'error': 'No response from Gemini'}
        text = candidates[0]['content']['parts'][0]['text'].strip()
        import json as _json
        try:
            suggestions = _json.loads(text)
            if not isinstance(suggestions, list):
                raise ValueError('Gemini did not return a list')
        except Exception as e:
            print('Error parsing Gemini suggestions as JSON list:', text, e)
            # Try to extract JSON array from text
            import re
            match = re.search(r'\[.*\]', text, re.DOTALL)
            if match:
                suggestions = _json.loads(match.group(0))
            else:
                return {'error': 'Could not parse Gemini suggestions as a list'}
        return {'suggestions': suggestions}
    except Exception as e:
        import traceback
        print('Exception in suggest_solution_with_gemini:', e)
        traceback.print_exc()
        return {'error': str(e)}
