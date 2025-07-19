import os
import requests

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro:generateContent'

# Map Gemini's output to our quadrant keys

def load_prompt(filename):
    path = os.path.join(os.path.dirname(__file__), filename)
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def conversational_facilitator(prompt):
    print("[GEMINI] conversational_facilitator called", flush=True)
    """
    Calls Gemini with a conversational prompt and returns a structured dict:
    - {'action': 'ask_clarification', 'question': ...}
    - {'action': 'classify_and_add', 'thoughts': [{'content': ..., 'quadrant': ...}, ...]}
    """
    if not GEMINI_API_KEY:
        return {'error': 'Gemini API key not set.'}
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
            if 'clarify' in text.lower() or 'question' in text.lower():
                return {'action': 'ask_clarification', 'question': text}
            # Otherwise treat as a single thought
            return {'action': 'classify_and_add', 'thoughts': [{'content': text, 'quadrant': 'status'}]}
        # Interpret structured response
        if result.get('action') == 'ask_clarification' and 'question' in result:
            return {'action': 'ask_clarification', 'question': result['question']}
        elif result.get('action') == 'classify_and_add' and 'thoughts' in result:
            return {'action': 'classify_and_add', 'thoughts': result['thoughts']}
        # If it looks like a single thought classification
        if 'quadrant' in result and 'thought' in result:
            return {
                'action': 'classify_and_add',
                'thoughts': [{
                    'content': result['thought'],
                    'quadrant': QUADRANT_MAP.get(result['quadrant'].strip().lower(), 'status')
                }]
            }
        # If it looks like a clarification
        if 'question' in result:
            return {'action': 'ask_clarification', 'question': result['question']}
        # Fallback
        return {'action': 'ask_clarification', 'question': text}
    except Exception as e:
        import traceback
        print('Exception in conversational_facilitator:', e)
        traceback.print_exc()
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
