import os
import openai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize OpenAI client with error handling
client = None
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if OPENAI_API_KEY:
    try:
        openai.api_key = OPENAI_API_KEY
        client = openai  # In 0.28, we use the module directly
        print("OpenAI client initialized successfully")
    except Exception as e:
        print(f"Warning: Failed to initialize OpenAI client: {e}")
        client = None
else:
    raise ValueError("OPENAI_API_KEY environment variable not set.")

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

OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5-nano")

# Cost tracking for different models (per 1K tokens)
MODEL_COSTS = {
    "gpt-5": {"input": 1.25, "output": 10.0},
    "gpt-5-mini": {"input": 0.25, "output": 2.0},
    "gpt-5-nano": {"input": 0.05, "output": 0.40},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002}
}

def calculate_cost(model, input_tokens, output_tokens):
    """Calculate cost for API call based on token usage"""
    if model not in MODEL_COSTS:
        print(f"Warning: Unknown model {model} for cost calculation")
        return 0.0
    
    costs = MODEL_COSTS[model]
    input_cost = (input_tokens / 1000) * costs["input"]
    output_cost = (output_tokens / 1000) * costs["output"]
    total_cost = input_cost + output_cost
    
    print(f"💰 COST: {model} | In:{input_tokens}tok(${input_cost:.4f}) Out:{output_tokens}tok(${output_cost:.4f}) Total:${total_cost:.4f}")
    
    # Also log to dedicated cost tracking file
    log_cost_to_file(model, input_tokens, output_tokens, input_cost, output_cost, total_cost)
    
    return total_cost

def log_cost_to_file(model, input_tokens, output_tokens, input_cost, output_cost, total_cost):
    """Log cost information to a dedicated file for easy tracking and comparison"""
    import os
    from datetime import datetime
    
    # Create costs directory if it doesn't exist
    cost_dir = "costs"
    if not os.path.exists(cost_dir):
        os.makedirs(cost_dir)
    
    # Generate filename with current date
    today = datetime.now().strftime("%Y-%m-%d")
    cost_file = os.path.join(cost_dir, f"llm_costs_{today}.txt")
    
    # Format timestamp
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    # Create log entry
    log_entry = f"{timestamp} | {model:<12} | In:{input_tokens:>5}tok(${input_cost:>7.4f}) | Out:{output_tokens:>4}tok(${output_cost:>7.4f}) | Total:${total_cost:>7.4f}\n"
    
    # Append to file (create header if new file)
    try:
        # Check if file exists to add header
        file_exists = os.path.exists(cost_file)
        
        with open(cost_file, "a", encoding="utf-8") as f:
            # Add header if this is a new file
            if not file_exists:
                f.write("=== LLM COST TRACKING ===\n")
                f.write("Time     | Model        | Input Tokens (Cost)   | Output Tokens (Cost) | Total Cost\n")
                f.write("-" * 85 + "\n")
            
            f.write(log_entry)
    except Exception as e:
        print(f"Warning: Could not write to cost file: {e}")

def conversational_facilitator(prompt, conversation_history=None, quadrants=None):
    # Removed verbose logging to keep Flask log clean for cost tracking
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
    response = client.ChatCompletion.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=0.7,
        max_tokens=1500
    )
    
    # Track cost for this API call
    if hasattr(response, 'usage'):
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        calculate_cost(OPENAI_MODEL, input_tokens, output_tokens)
    
    # TRUST THE LLM: Just like the prompt testing tool, let the LLM handle everything
    # No backend interference, no forced categorization, no JSON extraction
    reply = response.choices[0].message.content.strip()
    
    # Simple approach: Just return the LLM's response as-is
    # The LLM will handle conversation vs JSON based on the prompt instructions
    return {'action': 'ask_clarification', 'question': reply}

def classify_thought_with_openai(content):
    """
    Calls OpenAI GPT model to classify a thought into a quadrant and optionally rewrite the thought.
    Returns a dict: {"quadrant": ..., "thought": ...}
    Now also supports flagging thoughts that do not belong on the board.
    """
    system_prompt = load_prompt('prompts/classify_thought.txt')

    user_prompt = f"Input: {content}\nRespond with valid JSON only."
    response = client.ChatCompletion.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2,
        max_tokens=300
    )
    
    # Track cost for this API call
    if hasattr(response, 'usage'):
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        calculate_cost(OPENAI_MODEL, input_tokens, output_tokens)
    
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

    response = client.ChatCompletion.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Please provide your response as a JSON array only."}
        ],
        temperature=0.3,
        max_tokens=512
    )
    
    # Track cost for this API call
    if hasattr(response, 'usage'):
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        calculate_cost(OPENAI_MODEL, input_tokens, output_tokens)
    
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
    response = client.ChatCompletion.create(
        model=OPENAI_MODEL,
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
    response = client.ChatCompletion.create(
        model=OPENAI_MODEL,
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
    response = client.ChatCompletion.create(
        model=OPENAI_MODEL,
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

