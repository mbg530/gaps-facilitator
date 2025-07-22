import os
from openai import OpenAI

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable not set.")
client = OpenAI(api_key=OPENAI_API_KEY)

# Helper to load prompt from file

import os

def load_prompt(filename):
    """
    Load a prompt file from the prompts/ directory. Use this for all AI prompt templates.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(base_dir, filename) if not os.path.isabs(filename) else filename
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()

def load_and_fill_prompt(filename, **kwargs):
    """
    Load a prompt and fill in placeholders using kwargs.
    Example: load_and_fill_prompt('prompts/suggest_solution.txt', PROBLEMS='...', OBSTACLES='...')
    """
    prompt = load_prompt(filename)
    for key, value in kwargs.items():
        prompt = prompt.replace(f'<{key.upper()}>', value)
    return prompt

# --- Example: Classify Thought ---

import os
SHOW_JSON_WARNING = os.environ.get('SHOW_JSON_WARNING', 'true').lower() == 'true'

OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4-turbo")

def conversational_facilitator(prompt, conversation_history=None, quadrants=None):
    print("[OPENAI] conversational_facilitator called", flush=True)
    """
    Calls OpenAI with a conversational prompt and returns a structured dict:
    - {'action': 'ask_clarification', 'question': ...}
    - {'action': 'classify_and_add', 'thoughts': [{'content': ..., 'quadrant': ...}, ...]}
    """
    
    # Removed hardcoded initial greeting logic - now always uses prompt file
    
    # Let AI handle all categorization - removed broken force categorization logic
    # that was always defaulting to 'status' quadrant regardless of context
    # Load onboarding-rich system prompt
    system_prompt = load_prompt('prompts/prompts_modified.txt')
    messages = [{"role": "system", "content": system_prompt}]
    if conversation_history:
        messages.extend(conversation_history)
    # Prepend formatted quadrant state if provided
    if quadrants:
        def format_items(items):
            return "\n".join(f"- {item}" for item in items) if items else "(none)"
        quadrant_text = (
            f"Current Quadrant State:\n"
            f"Goals:\n{format_items(quadrants.get('goal', []))}\n\n"
            f"Analyses:\n{format_items(quadrants.get('analysis', []))}\n\n"
            f"Plans:\n{format_items(quadrants.get('plan', []))}\n\n"
            f"Statuses:\n{format_items(quadrants.get('status', []))}"
        )
        messages.append({"role": "user", "content": quadrant_text})
    messages.append({"role": "user", "content": prompt})
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.3,
        max_tokens=300
    )
    import json
    reply = response.choices[0].message.content.strip()
    import re
    try:
        # Remove code block if present
        if reply.startswith("```json"):
            reply = reply.split("```json",1)[1].split("```",1)[0].strip()
        # Robustly extract ONLY the JSON object with add_to_quadrant (not code block)
        # If code block is present, strip it
        code_block_match = re.search(r'```(?:json)?\s*({[\s\S]*?})\s*```', reply, re.IGNORECASE)
        if code_block_match:
            json_str = code_block_match.group(1)
            try:
                result = json.loads(json_str)
            except Exception:
                result = None
            after_json = reply.split(code_block_match.group(0), 1)[1].strip()
            warning = "\nWarning: AI did not output a valid JSON object. Please rephrase or try again." if SHOW_JSON_WARNING else ""
            return {
                'action': 'classify_and_add',
                'thoughts': result['add_to_quadrant'] if result else [],
                'reply_text': f"{json_str}\n{after_json}{warning}".strip()
            }
        # Otherwise, try to find inline JSON
        json_match = re.search(r'(\{\s*"add_to_quadrant"\s*:\s*\[.*?\]\s*\})', reply, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            try:
                result = json.loads(json_str)
            except Exception:
                result = None
            after_json = reply.split(json_str, 1)[1].strip()
            warning = "\nWarning: AI did not output a valid JSON object. Please rephrase or try again." if SHOW_JSON_WARNING else ""
            return {
                'action': 'classify_and_add',
                'thoughts': result['add_to_quadrant'] if result else [],
                'reply_text': f"{json_str}\n{after_json}{warning}".strip()
            }
        # Fallback: If lines like 'Goal: ...', 'Plan: ...', etc. are present, build JSON
        quadrant_map = {'goal': 'goal', 'plan': 'plan', 'status': 'status', 'analysis': 'analysis'}
        thoughts = []
        lines = reply.splitlines()
        for line in lines:
            m = re.match(r'\s*(Goal|Plan|Status|Analysis)\s*:\s*(.+)', line, re.IGNORECASE)
            if m:
                quadrant = quadrant_map[m.group(1).lower()]
                thought = m.group(2).strip().strip('.')
                if thought:
                    thoughts.append({'quadrant': quadrant, 'thought': thought})
        # Filter out meta-conversational suggestions before processing
        meta_filters = [
            'quadrants are currently empty',
            'quadrants are empty', 
            'provide recommendations for how to proceed',
            'need recommendations',
            'should start with goals',
            'should start with',
            'recommendations for how to proceed'
        ]
        
        filtered_thoughts = []
        for thought_data in thoughts:
            thought_text = thought_data['thought'].lower()
            is_meta = any(meta_phrase in thought_text for meta_phrase in meta_filters)
            if not is_meta:
                filtered_thoughts.append(thought_data)
            else:
                print(f"[DEBUG] Filtered out meta-suggestion: {thought_data['thought']}")
        
        # If we found any valid (non-meta) thoughts, build JSON and extract the first question after those lines
        if filtered_thoughts:
            # Find the first line after the last matched quadrant line that looks like a question
            last_idx = max(i for i, line in enumerate(lines) if re.match(r'\s*(Goal|Plan|Status|Analysis)\s*:', line, re.IGNORECASE))
            question_text = ''
            for line in lines[last_idx+1:]:
                if '?' in line:
                    question_text = line.strip()
            warning = "\n\n⚠️ Warning: The AI did not output a valid JSON object for quadrant assignments. Please rephrase your request or try again." if SHOW_JSON_WARNING else ""
            return {
                'action': 'classify_and_add',
                'thoughts': filtered_thoughts,
                'reply_text': reply.strip() + warning
            }
        # SMART BACKEND CATEGORIZATION: If AI fails to provide JSON, analyze the original user input
        # Extract the original user input from the prompt for intelligent categorization
        user_input = ""
        if "Latest User Input:" in prompt:
            lines = prompt.split("\n")
            for i, line in enumerate(lines):
                if "Latest User Input:" in line and i + 1 < len(lines):
                    user_input = lines[i + 1].strip()
                    break
        
        if user_input and not '?' in user_input:
            # Skip categorization for internal system prompts
            system_prompt_indicators = [
                'please summarize the current quadrant state',
                'provide recommendations for how to proceed',
                'output them as a json object',
                'using the add_to_quadrant key',
                'if you have new thoughts for any quadrant'
            ]
            
            input_lower = user_input.lower()
            
            # Don't categorize internal system prompts
            if any(indicator in input_lower for indicator in system_prompt_indicators):
                # This is an internal system prompt, not a user input - don't categorize
                pass
            else:
                # This is a real user input - proceed with intelligent categorization
            
                # PLAN indicators: need to, should, must, implement, develop, create, train, provide, etc.
                plan_keywords = ['need to', 'should', 'must', 'implement', 'develop', 'create', 'train', 'provide', 'establish', 'build', 'design', 'plan to', 'going to', 'will']
                
                # GOAL indicators: want to, goal is, aim to, objective, target, improve, achieve, etc.
                goal_keywords = ['want to', 'goal is', 'aim to', 'objective', 'target', 'improve', 'achieve', 'desire', 'hope to', 'aspire', 'increase', 'enhance', 'better', 'responsible for', 'need to develop', 'development of', 'working on', 'tasked with']
                
                # STATUS indicators: currently, now, is/are (present state), morale is, satisfaction is, etc.
                status_keywords = ['currently', 'right now', ' is ', ' are ', 'morale is', 'satisfaction is', 'performance is', 'revenue is', 'status is']
                
                # ANALYSIS indicators: because, due to, caused by, reason, factor, reluctant, hesitant, etc.
                analysis_keywords = ['because', 'due to', 'caused by', 'reason', 'factor', 'reluctant', 'hesitant', 'challenge', 'problem', 'issue', 'barrier']
                
                # Check for patterns (order matters - most specific first)
                if any(keyword in input_lower for keyword in plan_keywords):
                    quadrant = 'plan'
                elif any(keyword in input_lower for keyword in goal_keywords):
                    quadrant = 'goal'
                elif any(keyword in input_lower for keyword in analysis_keywords):
                    quadrant = 'analysis'
                elif any(keyword in input_lower for keyword in status_keywords):
                    quadrant = 'status'
                else:
                    # Default heuristic: if it sounds actionable, it's probably a plan
                    if any(word in input_lower for word in ['education', 'training', 'teaching', 'learning', 'preparation']):
                        quadrant = 'plan'
                    else:
                        quadrant = 'status'  # Safe default
                
                thoughts = [{'quadrant': quadrant, 'thought': user_input}]
                print(f"[BACKEND] Smart categorization: '{user_input}' → {quadrant} quadrant")
                return {
                    'action': 'classify_and_add',
                    'thoughts': thoughts,
                    'reply_text': f'I\'ve categorized your input as a {quadrant.title()}: "{user_input}". What would you like to explore next?'
                }
        # If no user input found or it's a question, treat as clarification
        return {'action': 'ask_clarification', 'question': reply.strip()}
    except Exception as e:
        # Fallback: treat as plain text question
        return {'action': 'ask_clarification', 'question': reply.strip()}

def classify_thought_with_openai(content):
    """
    Calls OpenAI GPT model to classify a thought into a quadrant and optionally rewrite the thought.
    Returns a dict: {"quadrant": ..., "thought": ...}
    Now also supports flagging thoughts that do not belong on the board.
    """
    system_prompt = load_prompt('prompts/classify_thought.txt')

    user_prompt = f"Input: {content}\nRespond with valid JSON only."
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2,
        max_tokens=300
    )
    # Extract and parse the JSON from the response
    import json
    reply = response.choices[0].message.content
    try:
        # Remove code block if present
        if reply.strip().startswith("```json"):
            reply = reply.strip().split("```json",1)[1].split("```",1)[0].strip()
        result = json.loads(reply)
        # If the result is a dict (old style), wrap in list for backward compatibility
        if isinstance(result, dict):
            result = [result]
        # Return a list of dicts, each with quadrant and thought
        return [
            {
                "quadrant": item.get("quadrant", "status").lower(),
                "thought": item.get("thought", "")
            }
            for item in result if item.get("thought")
        ]
    except Exception as e:
        raise RuntimeError(f"OpenAI response could not be parsed as JSON: {reply}\nError: {e}")


# --- Suggest Solution ---
def suggest_solution_with_openai(problems, obstacles):
    """
    Given lists of problems and obstacles, ask OpenAI to suggest a solution.
    Returns a dict with 'suggestions' or 'error'.
    Now also supports flagging items that do not belong on the board.
    """
    system_prompt = load_and_fill_prompt(
        'prompts/suggest_solution.txt',
        PROBLEMS='; '.join(problems) if problems else 'None provided',
        OBSTACLES='; '.join(obstacles) if obstacles else 'None provided'
    )

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Please provide your response as a JSON array only."}
        ],
        temperature=0.3,
        max_tokens=512
    )
    import json
    reply = response.choices[0].message.content
    try:
        # Remove code block if present
        if reply.strip().startswith("```json"):
            reply = reply.strip().split("```json",1)[1].split("```",1)[0].strip()
        suggestions = json.loads(reply)
        if not isinstance(suggestions, list):
            raise ValueError('OpenAI did not return a list')
        # Ensure each suggestion is a dict with content and quadrant
        normalized = []
        for s in suggestions:
            if isinstance(s, dict) and 'content' in s and 'quadrant' in s:
                normalized.append({'content': s['content'], 'quadrant': s['quadrant']})
            elif isinstance(s, str):
                normalized.append({'content': s, 'quadrant': 'status'})
        return {'suggestions': normalized}
    except Exception as e:
        import logging
        logging.error(f"OpenAI classify_thought_with_openai JSON parse error: {e}\nAI reply: {reply}")
        return {'error': 'Sorry, the AI response could not be understood. Please try again or rephrase your input.'}


# --- Brainstorm ---
def brainstorm_with_openai(topic):
    """
    Given a topic, brainstorm three creative and practical solutions. Returns a list of suggestions.
    """
    system_prompt = (
        "You are an assistant for a Four Ws (GAPS) board. "
        "Brainstorm three creative and practical solutions for the following issue. "
        "Respond as a numbered list."
    )
    user_prompt = f"'{topic}'"
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.5,
        max_tokens=256
    )
    text = response.choices[0].message.content
    # Parse ideas from numbered list
    ideas = [line.lstrip("1234567890. ").strip() for line in text.split('\n') if line.strip() and any(c.isalpha() for c in line)]
    if len(ideas) > 3:
        ideas = ideas[:3]
    return {'suggestions': ideas}

# --- Meeting Minutes ---
def meeting_minutes_with_openai(summary):
    """
    Rewrite a meeting summary as clear, concise meeting minutes. Returns a string.
    """
    system_prompt = (
        "You are an assistant for a Four Ws (GAPS) board. "
        "Rewrite the following meeting summary as clear, concise meeting minutes."
    )
    user_prompt = f"Summary: '{summary}'\n\nMeeting Minutes:"
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2,
        max_tokens=256
    )
    text = response.choices[0].message.content.strip()
    return {'result': text}

def rewrite_thought_with_openai(thought):
    system_prompt = "You are an assistant that rewrites thoughts to be clearer, more positive, or more actionable. Respond with 1-3 improved versions as a numbered or bulleted list."
    user_prompt = f"Rewrite the following thought to be clearer, more positive, or more actionable.\n\nThought: '{thought}'\n\nRewritten Thought:"
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.5,
        max_tokens=256
    )
    text = response.choices[0].message.content.strip()
    # Parse for multiple suggestions (numbered or bulleted)
    lines = [line.strip("1234567890.-• \t") for line in text.split('\n') if line.strip()]
    filtered = [l for l in lines if l and not l.lower().startswith("here are") and not l.lower().startswith("depending on")]
    if not filtered:
        filtered = [text]
    return {'suggestions': filtered}

