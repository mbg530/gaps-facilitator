from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, render_template_string
from admin_prompt import admin_bp
from templates.gaps_kb_endpoint import kb_blueprint
from models import db, Board, Thought, MeetingMinute, User
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf import CSRFProtect
import os
import uuid
import time
import glob
import google.generativeai as genai
from flask import send_from_directory

# Version detection based on file modification times
def get_app_version():
    """Generate app version based on modification time of key files"""
    try:
        # Key files that indicate app changes
        files_to_check = [
            'app.py',
            'templates/index.html', 
            'static/js/interactive-mode.js',
            'prompts/prompts_modified.txt'
        ]
        
        latest_mtime = 0
        for file_path in files_to_check:
            if os.path.exists(file_path):
                file_mtime = os.path.getmtime(file_path)
                latest_mtime = max(latest_mtime, file_mtime)
        
        # Return timestamp as version string
        return str(int(latest_mtime))
    except Exception as e:
        # Fallback version if file checking fails
        return str(int(time.time()))

# ... other imports ...

# (app = Flask(__name__) and all setup code comes here)

# --- Serve files from /prompts for download ---
# Place this after app = Flask(__name__)


import gemini_api
import openai_api

# Maximum number of conversation turns to send to the LLM for context
MAX_HISTORY_TURNS = 12
import board_store
import openai_api
import gemini_api

from sqlalchemy import event
from sqlalchemy.engine import Engine

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# AI Provider Setup
AI_PROVIDER = os.environ.get("AI_PROVIDER", "openai").lower()  # Default to OpenAI, set to 'gemini' to use Gemini
if AI_PROVIDER == "openai":
    ai_api = openai_api
else:
    ai_api = gemini_api

# Helper function to generate version string with AI provider
def get_version_with_provider():
    version = os.environ.get('APP_VERSION', 'dev')
    provider = AI_PROVIDER.upper()
    return f"{version} ({provider})"

# Debug storage for prompt engineering
debug_entries = []
MAX_DEBUG_ENTRIES = 50  # Keep last 50 entries

def add_debug_entry(user_input, prompt, ai_response, clean_message, suggestions):
    """Store debug information for web-based debug console"""
    from datetime import datetime
    
    entry = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'user_input': user_input,
        'prompt': prompt,
        'ai_response': ai_response,
        'clean_message': clean_message,
        'suggestions': suggestions or []
    }
    
    debug_entries.append(entry)
    
    # Keep only the last MAX_DEBUG_ENTRIES
    if len(debug_entries) > MAX_DEBUG_ENTRIES:
        debug_entries.pop(0)
    
    print(f"[DEBUG STORAGE] Added entry #{len(debug_entries)}: {user_input[:50]}...", flush=True)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

csrf = CSRFProtect(app)

# Register admin prompt editor blueprint
app.register_blueprint(admin_bp)

# --- Serve files from /prompts for download ---
@app.route('/prompts/<path:filename>')
def download_prompt_file(filename):
    import os
    prompts_dir = os.path.join(os.path.dirname(__file__), 'prompts')
    return send_from_directory(prompts_dir, filename, as_attachment=True)


app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Make app version available to all templates
@app.context_processor
def inject_app_version():
    return {'app_version': get_app_version()}

# Register knowledge base endpoint
app.register_blueprint(kb_blueprint)

# Register CSRF token refresh endpoint
from get_csrf_token import csrf_token_api
app.register_blueprint(csrf_token_api)

# Increase CSRF token lifetime to 1 hour (3600 seconds)
app.config['WTF_CSRF_TIME_LIMIT'] = 3600

# --- CSRF Protection (DISABLED FOR EXPERIMENTAL ENVIRONMENT) ---
# csrf = CSRFProtect(app)  # Temporarily disabled to fix API route issues
print("[WARNING] CSRF protection is disabled in experimental environment", flush=True)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

db.init_app(app)

# --- Flask-Migrate setup ---
from flask_migrate import Migrate
migrate = Migrate(app, db)

# Helper: get all boards for the current user
def get_boards():
    if current_user.is_authenticated:
        return Board.query.filter_by(user_id=current_user.id).order_by(Board.title).all()
    return []

# Helper: get current board (by id in query param, or first board)
def get_current_board():
    board_id = request.args.get('board_id')  # Remove type=int to handle UUID strings
    boards = get_boards()
    if not boards:
        return None
    if board_id:
        # Convert board_id to appropriate type for comparison
        for b in boards:
            if str(b.id) == str(board_id):  # Compare as strings to handle both int and UUID
                return b
    return boards[0]

import re

@app.route('/', methods=['GET'])
def landing():
    return render_template('landing.html')

@app.route('/facilitator', methods=['GET', 'POST'])
@login_required
def facilitator():
    if request.method == 'POST':
        # Create new board (database only)
        print('POST /facilitator form:', request.form)
        title = request.form.get('new_board_title', '').strip()
        print('Parsed title:', title)
        if title:
            # Only create a board if the user doesn't already have one with this title
            if not Board.query.filter_by(title=title, user_id=current_user.id).first():
                new_board = Board(title=title, user_id=current_user.id)
                db.session.add(new_board)
                db.session.commit()
            # Redirect to the board for this user
            return redirect(url_for('facilitator', board_id=Board.query.filter_by(title=title, user_id=current_user.id).first().id))

    board_id = request.args.get('board_id')
    uuid_re = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
    # If board_id is a UUID, load from JSON
    if board_id and uuid_re.match(str(board_id)):
        # Load boards from JSON
        boards = board_store.list_boards()
        board = board_store.get_board(board_id)
        if not board:
            return render_template('index.html', boards=boards, board=None, quadrants={}, thoughts={}, version=get_version_with_provider())
        # Prepare thoughts dict
        thoughts = {q: [] for q in ['status', 'goal', 'analysis', 'plan']}
        for t in board.get('thoughts', []):
            q = t.get('quadrant')
            if q in thoughts:
                thoughts[q].append(t)
        return render_template('index.html', boards=boards, board=board, quadrants=None, thoughts=thoughts, version=get_version_with_provider())
    else:
        # Default: use database
        board = get_current_board()
        boards = get_boards()
        if not board and boards:
            board = boards[0]  # fallback to first available board
        
        # DEBUG: Log board data being passed to template
        print(f"=== BOARD DATA DEBUG ===")
        print(f"Board object: {board}")
        print(f"Board type: {type(board)}")
        if board:
            print(f"Board attributes: {dir(board)}")
            if hasattr(board, 'title'):
                print(f"Board title: {board.title}")
            if hasattr(board, 'name'):
                print(f"Board name: {board.name}")
            if hasattr(board, 'id'):
                print(f"Board id: {board.id}")
        print(f"========================")
        
        if not board:
            return render_template('index.html', boards=[], board=None, quadrants={}, thoughts={}, version=get_version_with_provider())
        
        # DEBUG: Log thoughts retrieval
        print(f"[DEBUG] Retrieving thoughts for board {board.id}...")
        print(f"[DEBUG] Board.thoughts count: {len(board.thoughts)}")
        
        thoughts = {q: [] for q in ['status', 'goal', 'analysis', 'plan']}
        for i, t in enumerate(board.thoughts):
            print(f"[DEBUG] Thought {i+1}: '{t.content}' in {t.quadrant} quadrant (id: {t.id})")
            thoughts[t.quadrant].append(t)
        
        print(f"[DEBUG] Final thoughts dict: {[(k, len(v)) for k, v in thoughts.items()]}")
        return render_template('index.html', boards=boards, board=board, quadrants=None, thoughts=thoughts, version=get_version_with_provider())


from flask_wtf.csrf import validate_csrf

@app.route('/interactive_gaps', methods=['POST'])
@csrf.exempt
def interactive_gaps():
    print("Entered /interactive_gaps endpoint", flush=True)
    """
    Route for interactive GAPS AI. Uses GAPS-Coach logic for structured, hybrid conversational output.
    """
    try:
        from models import ConversationTurn, db
        from flask_login import current_user
        conversational_facilitator = ai_api.conversational_facilitator
        data = request.get_json(force=True)
        board_id = data.get('board_id')
        user_input = data.get('user_input', '')
        print(f"[DEBUG] Parsed user_input: {user_input}", flush=True)
        if not board_id:
            return jsonify({'error': 'Missing board_id'}), 400
        # If user_input is empty, check if this is initial conversation setup
        if not user_input or not user_input.strip():
            # Check if this is a fresh start (no conversation history and empty quadrants)
            from models import ConversationTurn
            history_turns = ConversationTurn.query.filter_by(board_id=board_id).order_by(ConversationTurn.id.asc()).all()
            
            if not history_turns:  # Fresh conversation start
                # Check if quadrants have content to determine appropriate response
                has_quadrant_content = False
                from models import Board
                board = Board.query.get(board_id)
                if board:
                    # Check if board has any thoughts in any quadrant
                    if board.thoughts:
                        has_quadrant_content = True
                
                if has_quadrant_content and not user_input:
                    # Quadrants have content but conversation is reset - ask for contextual guidance
                    # Use a system-style instruction that won't be categorized as user content
                    user_input = "SYSTEM: Provide a contextual greeting acknowledging the existing quadrant content and ask what the user would like to work on next. Do not categorize this instruction."
                else:
                    # Truly fresh start with empty quadrants - use standard greeting
                    user_input = "" if not user_input else user_input
            else:
                # Existing conversation, use system prompt
                user_input = ("Please summarize the current quadrant state and provide recommendations for how to proceed. "
                               "If you have new thoughts for any quadrant, output them as a JSON object at the start of your reply, "
                               "using the 'add_to_quadrant' key.")
        # Fetch full conversation history for context (all turns) - may have been fetched above
        if 'history_turns' not in locals():
            from models import ConversationTurn
            history_turns = ConversationTurn.query.filter_by(board_id=board_id).order_by(ConversationTurn.id.asc()).all()
        conversation_history = []
        for t in history_turns:
            conversation_history.append({"role": t.role, "content": t.content})
        print(f"[DEBUG] Loaded conversation_history: {conversation_history}", flush=True)

        # Backend safeguard: Flexible onboarding/intro detection and knowledge base integration
        from utils.knowledge_base import get_kb_section
        intro_triggers = [
            "tell me more about gaps",
            "how does the process work",
            "can you give me a quick overview",
            "can you give me an overview",
            "explain gaps",
            "how does gaps work",
            "what is gaps",
            "what's gaps",
            "what is the gaps process",
            "how does the gaps process work",
            "give me a quick overview of gaps"
        ]

        # Conversational onboarding: if user says 'yes' or similar after onboarding offer, serve intro
        onboarding_offer = "welcome! i use the gaps model to help clarify and solve problems. would you like a quick intro to how it works, or are you already familiar with gaps?"
        yes_triggers = ["yes", "sure", "okay", "ok", "please", "sounds good", "let's do it", "let's go", "go ahead", "alright", "absolutely", "yep", "yeah"]

        # Fetch last assistant message for this board
        last_turn = ConversationTurn.query.filter_by(board_id=board_id, role='assistant').order_by(ConversationTurn.id.desc()).first()
        # if last_turn and last_turn.content and onboarding_offer in last_turn.content.lower():
        #     if user_input and user_input.strip().lower() in yes_triggers:
        #         section = get_kb_section('Overview')
        #         defs = get_kb_section('Quadrant Definitions')
        #         process = get_kb_section('Step-by-Step GAPS Process')
        #         kb_parts = [part for part in [section, defs, process] if part]
        #         intro_msg = "Great! Here's a quick introduction to the GAPS model.\n\n" + "\n\n".join(kb_parts) + "\n\nWould you like to hear more about any part, or are you ready to get started?"
        #         db.session.add(ConversationTurn(
        #             board_id=board_id,
        #             user_id=current_user.id if hasattr(current_user, 'id') else None,
        #             role='user',
        #             content=user_input
        #         ))
        #         db.session.add(ConversationTurn(
        #             board_id=board_id,
        #             user_id=None,
        #             role='assistant',
        #             content=intro_msg
        #         ))
        #         db.session.commit()
        #         return jsonify({"reply": intro_msg})

        # Map quadrant-related requests to KB sections
        quadrant_triggers = {
            "goals": "Quadrant Definitions",
            "statuses": "Quadrant Definitions",
            "analyses": "Quadrant Definitions",
            "plans": "Quadrant Definitions",
            "step-by-step": "Step-by-Step GAPS Process",
            "process": "Step-by-Step GAPS Process"
        }
        user_input_lc = user_input.lower() if user_input else ""
        # Fuzzy/flexible onboarding/intro detection
        unfamiliar_phrases = [
            "not familiar",
            "new to",
            "don't know",
            "never heard of",
            "unfamiliar",
            "first time",
            "never used",
            "never tried"
        ]
        ask_intro_phrases = [
            "please tell me more",
            "tell me more",
            "can you explain",
            "explain",
            "overview",
            "how does it work",
            "what is gaps",
            "what's gaps",
            "how does the gaps process work"
        ]
        # If user signals unfamiliarity with GAPS and/or asks for more info, serve the intro
        # if user_input:
        #     # Only intercept onboarding/intro requests
        #     serve_intro = False
        #     if any(trigger in user_input_lc for trigger in intro_triggers):
        #         serve_intro = True
        #     elif any(phrase in user_input_lc for phrase in unfamiliar_phrases) and "gaps" in user_input_lc:
        #         serve_intro = True
        #     elif any(phrase in user_input_lc for phrase in ask_intro_phrases) and "gaps" in user_input_lc:
        #         serve_intro = True
        #     elif (any(phrase in user_input_lc for phrase in unfamiliar_phrases) and any(phrase in user_input_lc for phrase in ask_intro_phrases)):
        #         serve_intro = True
        #     # Only serve intro if onboarding/intro is triggered
        #     if serve_intro:
        #         section = get_kb_section('Overview')
        #         defs = get_kb_section('Quadrant Definitions')
        #         process = get_kb_section('Step-by-Step GAPS Process')
        #         kb_parts = [part for part in [section, defs, process] if part]
        #         msg = "\n\n".join(kb_parts)
        #         if msg:
        #             msg += "\n\nWould you like to start by describing a challenge you're facing, or is there a specific goal you have in mind?"
        #         else:
        #             msg = "Sorry, I couldn't retrieve the GAPS explanation right now. Please try again or contact support."
        #         db.session.add(ConversationTurn(
        #             board_id=board_id,
        #             user_id=current_user.id if hasattr(current_user, 'id') else None,
        #             role='user',
        #             content=user_input
        #         ))
        #         db.session.add(ConversationTurn(
        #             board_id=board_id,
        #             user_id=None,
        #             role='assistant',
        #             content=msg
        #         ))
        #         db.session.commit()
        #         return jsonify({"reply": msg})
                    # content=user_input
                # ))
                # db.session.add(ConversationTurn(
                #     board_id=board_id,
                #     user_id=None,
                #     role='assistant',
                #     content=onboarding_msg
                # ))
                # db.session.commit()
                # return jsonify({"reply": onboarding_msg})

        # Otherwise, allow the LLM to answer naturally (for relevant non-GAPS queries, etc.)
        # Serve quadrant or process explanations
        for key, section in quadrant_triggers.items():
            # Only match if user is explicitly asking for a definition
            definition_phrases = [
                f"what is {key}",
                f"define {key}",
                f"what does {key} mean",
                f"explain {key}",
                f"meaning of {key}"
            ]
            if any(phrase in user_input_lc for phrase in definition_phrases):
                print(f"[DEBUG] Triggered quadrant explanation for key: {key}", flush=True)
                kb_text = get_kb_section(section)
                if kb_text:
                    db.session.add(ConversationTurn(
                        board_id=board_id,
                        user_id=current_user.id if hasattr(current_user, 'id') else None,
                        role='user',
                        content=user_input
                    ))
                    db.session.add(ConversationTurn(
                        board_id=board_id,
                        user_id=None,
                        role='assistant',
                        content=kb_text
                    ))
                    db.session.commit()
                    print(f"[DEBUG] Returning quadrant explanation: {kb_text}", flush=True)
                    return jsonify({"reply": kb_text})

        # Use quadrants from POST data if present, otherwise fall back to DB
        quadrants = data.get('quadrants')
        if not quadrants:
            quadrants = {q: [] for q in ['status', 'goal', 'analysis', 'plan']}
            from models import Thought
            thoughts = Thought.query.filter_by(board_id=board_id).all()
            for t in thoughts:
                if t.quadrant in quadrants:
                    quadrants[t.quadrant].append(t.content)
            # If using board_store (UUID boards), try that as fallback
            if not thoughts:
                import board_store
                board = board_store.get_board(board_id)
                if board and 'thoughts' in board:
                    for t in board['thoughts']:
                        q = t.get('quadrant')
                        if q in quadrants:
                            quadrants[q].append(t.get('content', ''))
        print("[DEBUG] Quadrants being used for LLM (from POST data if present):", quadrants, flush=True)
        
        # === HYBRID RULE-BASED + AI CATEGORIZATION ===
        # Import debug logger
        from debug_logger import debug_logger
        
        # Get configurable confidence threshold from environment
        RULE_CONFIDENCE_THRESHOLD = float(os.environ.get('RULE_CONFIDENCE_THRESHOLD', '0.7'))
        print(f"[DEBUG] Rule confidence threshold: {RULE_CONFIDENCE_THRESHOLD}", flush=True)
        debug_logger.log('system', f'Interactive Mode started with threshold: {RULE_CONFIDENCE_THRESHOLD}', {'user_input': user_input[:100]})
        
        # Step 1: Check if input is a question (skip categorization for questions)
        def is_question(text):
            text_lower = text.lower().strip()
            # Direct question words
            question_words = ['what', 'how', 'why', 'when', 'where', 'who', 'which', 'can', 'could', 'would', 'should', 'do', 'does', 'did', 'is', 'are', 'was', 'were']
            # Question patterns
            if text.strip().endswith('?'):
                return True
            if any(text_lower.startswith(word + ' ') for word in question_words):
                return True
            if any(phrase in text_lower for phrase in ['what do you', 'how do you', 'can you', 'could you', 'would you']):
                return True
            return False
        
        is_user_question = is_question(user_input)
        print(f"[DEBUG] Is question: {is_user_question} ('{user_input[:50]}...')")
        
        # Step 2: Try rule-based categorization (skip for questions)
        rule_based_suggestion = None
        
        if is_question(user_input):
            print(f"[DEBUG] Is question: True ('{user_input[:50]}...')")
            print("[DEBUG] Skipping rule-based categorization - user asked a question", flush=True)
            debug_logger.log('question_detection', 'Skipped rule-based categorization', {
                'input': user_input[:100],
                'reason': 'User asked a question'
            })
        else:
            print(f"[DEBUG] Is question: False ('{user_input[:50]}...')")
            debug_logger.log('question_detection', 'Proceeding with categorization', {
                'input': user_input[:100],
                'reason': 'Not a question'
            })
            # Try rule-based categorization
            try:
                from rule_based_categorizer import RuleBasedCategorizer
                categorizer = RuleBasedCategorizer()
                start_time = time.time()
                rule_result = categorizer.categorize(user_input)
                processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                
                print(f"[DEBUG] Rule-based result: {rule_result['quadrant']} (confidence: {rule_result['confidence']:.2f}, {processing_time:.1f}ms)", flush=True)
                debug_logger.log('rule_based', f"Categorized as {rule_result['quadrant']}", {
                    'input': user_input[:100],
                    'quadrant': rule_result['quadrant'],
                    'confidence': rule_result['confidence'],
                    'processing_time_ms': round(processing_time, 1),
                    'reasoning': rule_result.get('reasoning', 'N/A')
                })
                
                # Check if confidence is high enough to use rule-based result
                if rule_result['confidence'] >= RULE_CONFIDENCE_THRESHOLD:
                    print(f"[DEBUG] High confidence ({rule_result['confidence']:.2f} >= {RULE_CONFIDENCE_THRESHOLD}) - using rule-based categorization", flush=True)
                    debug_logger.log('hybrid_decision', 'Using rule-based categorization', {
                        'confidence': rule_result['confidence'],
                        'threshold': RULE_CONFIDENCE_THRESHOLD,
                        'quadrant': rule_result['quadrant']
                    })
                    rule_based_suggestion = {
                        'thought': user_input,
                        'quadrant': rule_result['quadrant']
                    }
                else:
                    print(f"[DEBUG] Low confidence ({rule_result['confidence']:.2f} < {RULE_CONFIDENCE_THRESHOLD}) - involving AI for categorization", flush=True)
                    debug_logger.log('hybrid_decision', 'Involving AI for categorization', {
                        'confidence': rule_result['confidence'],
                        'threshold': RULE_CONFIDENCE_THRESHOLD,
                        'reason': 'Low confidence'
                    })
            except Exception as e:
                print(f"[DEBUG] Rule-based categorization failed: {e}", flush=True)
                debug_logger.log('error', 'Rule-based categorization failed', {
                    'error': str(e),
                    'input': user_input[:100]
                })
        
        # Limit conversation history to the last MAX_HISTORY_TURNS for prompt context
        history_window = conversation_history[-MAX_HISTORY_TURNS:] if len(conversation_history) > MAX_HISTORY_TURNS else conversation_history
        
        # Step 3: Build AI prompt based on rule-based result
        from app import build_conversational_prompt
        
        # Rule-based prompt modification disabled - LLM always handles both conversation and categorization
        # if rule_based_suggestion:
        #     # High confidence rule-based result - AI focuses on conversation only
        #     enhanced_prompt = build_conversational_prompt(history_window + [{"role": "user", "content": user_input}], quadrants)
        #     enhanced_prompt += f"\n\nNOTE: Rule-based system has already categorized this input as '{rule_based_suggestion['quadrant'].upper()}' with high confidence. Focus on providing conversational response and strategic advice. Do not re-categorize - the categorization is already handled."
        #     prompt = enhanced_prompt
        # else:
        #     # Low confidence or no rule result - AI handles both conversation and categorization
        base_prompt = build_conversational_prompt(history_window + [{"role": "user", "content": user_input}], quadrants)
        prompt = base_prompt
        
        # DEBUG: Print the full prompt being sent to the AI
        print("=== AI PROMPT SENT (interactive_gaps) ===", flush=True)
        print(prompt, flush=True)
        print("[DEBUG] Quadrants being sent to LLM:", quadrants, flush=True)
        print("[DEBUG] User input being processed:", repr(user_input), flush=True)
        print("[DEBUG] AI Provider:", AI_PROVIDER, flush=True)
        print("=========================================")
        
        # Call the LLM and capture the raw response
        ai_result = conversational_facilitator(prompt, quadrants=quadrants)
        
        # DEBUG: Print the raw AI response
        print("\n=== RAW AI RESPONSE ===", flush=True)
        print("AI Result type:", type(ai_result), flush=True)
        print("AI Result content:", repr(ai_result), flush=True)
        print("========================\n", flush=True)
        # Always use the full reply_text (JSON + follow-up) if present
        if isinstance(ai_result, dict) and 'reply_text' in ai_result:
            reply_text = ai_result['reply_text']
        elif isinstance(ai_result, dict) and 'question' in ai_result:
            reply_text = ai_result['question']
        else:
            reply_text = str(ai_result)
        # Robustly clean leading/trailing stray characters and extract user-facing message
        import re
        import json
        def extract_json_and_message(reply_text):
            import json
            import re
            reply_text = reply_text.lstrip()
            
            # Handle markdown-wrapped JSON (e.g., ```json {...} ```)
            markdown_match = re.search(r'```(?:json)?\s*({.*?})\s*```', reply_text, re.DOTALL)
            if markdown_match:
                json_part = markdown_match.group(1)
                # Get text before and after the markdown block
                before_json = reply_text[:markdown_match.start()].strip()
                after_json = reply_text[markdown_match.end():].strip()
                message_part = (before_json + ' ' + after_json).strip()
                try:
                    parsed_json = json.loads(json_part)
                    return parsed_json, message_part
                except Exception as e:
                    print(f"[DEBUG] Failed to parse markdown-wrapped JSON: {e}", flush=True)
                    # Fall through to regular processing
            
            # Handle regular JSON at start of text
            if reply_text.startswith('{') or reply_text.startswith('['):
                stack = []
                end = None
                for i, c in enumerate(reply_text):
                    if c in '{[':
                        stack.append(c)
                    elif c in '}]':
                        if stack:
                            open_c = stack.pop()
                            # Check for matching pairs
                            if (open_c == '{' and c != '}') or (open_c == '[' and c != ']'):
                                break
                        if not stack:
                            end = i + 1
                            break
                if end:
                    json_part = reply_text[:end]
                    # More careful message extraction - only strip leading whitespace and newlines
                    message_part = reply_text[end:].lstrip(' \n\t')
                    try:
                        parsed_json = json.loads(json_part)
                        # If there's no conversational message after JSON, provide a default response
                        if not message_part.strip():
                            message_part = "I'd suggest reviewing the categorizations above. Does that placement work for you?"
                    except Exception as e:
                        print(f"[DEBUG] Failed to parse JSON from AI reply: {e}", flush=True)
                        parsed_json = None
                    return parsed_json, message_part.strip()
            # If no JSON at the start, just return the message
            return None, reply_text.strip()
        suggestions, reply_text_clean = extract_json_and_message(reply_text)
        
        # === PROMPT ENGINEERING DEBUG: JSON EXTRACTION ===
        print(f"\n🔍 JSON EXTRACTION RESULTS:", flush=True)
        print(f"   📊 Extracted JSON: {suggestions}", flush=True)
        print(f"   💬 Clean Message: '{reply_text_clean}'", flush=True)
        
        # === HYBRID INTEGRATION: DISABLED ===
        # Rule-based suggestion injection has been disabled to allow LLM full control
        # over both conversational flow and categorization, matching prompt testing tool behavior
        # if rule_based_suggestion:
        #     # High confidence rule-based categorization - inject the result
        #     debug_logger.log('hybrid_integration', 'Injecting rule-based suggestion', {
        #         'suggestion': rule_based_suggestion['thought'][:100],
        #         'quadrant': rule_based_suggestion['quadrant']
        #     })
        #     
        #     # Create or enhance suggestions with rule-based result
        #     if not suggestions:
        #         suggestions = {'add_to_quadrant': [rule_based_suggestion]}
        #     elif 'add_to_quadrant' not in suggestions:
        #         suggestions['add_to_quadrant'] = [rule_based_suggestion]
        #     else:
        #         # Prepend rule-based suggestion to any AI suggestions
        #         suggestions['add_to_quadrant'].insert(0, rule_based_suggestion)
        #     
        #     print(f"[DEBUG] Injected rule-based suggestion: {rule_based_suggestion}", flush=True)
        
        # Filter out meta-conversational suggestions and duplicates from JSON
        if suggestions and 'add_to_quadrant' in suggestions:
            meta_filters = [
                'quadrants are currently empty',
                'quadrants are empty', 
                'user requested a summary',
                'user requested recommendations',
                'provide recommendations for how to proceed',
                'need recommendations',
                'should start with goals',
                'should start with',
                'recommendations for how to proceed',
                # Greeting and conversational content filters
                'i can help you solve problems',
                'what gap is on your mind',
                'what problem are you hoping to solve',
                'tell me about your goals',
                'which area would you like to start',
                'anything more for goals',
                'anything else you want to add',
                'ok? anything more',
                'want to move or edit it',
                'edit wording or move it',
                'how do you think this might be impacting',
                'what do you think about',
                'does that sound right',
                'make sense?',
                'sound good?',
                'i see you have a goal',
                'what would you like to work on next',
                'goals, status, analysis, or plans',
                'which quadrant should we work on',
                'what should we focus on'
            ]
            
            # Build list of existing quadrant items for duplicate detection
            existing_items = set()
            for quadrant_name, items in quadrants.items():
                for item in items:
                    # Normalize for comparison (lowercase, strip whitespace)
                    normalized_item = item.lower().strip()
                    existing_items.add(normalized_item)
            
            print(f"[DEBUG] Existing quadrant items for duplicate check: {len(existing_items)} items", flush=True)
            debug_logger.log('filtering', f'Starting suggestion filtering', {
                'total_suggestions': len(suggestions['add_to_quadrant']),
                'existing_items_count': len(existing_items)
            })
            
            filtered_suggestions = []
            seen_suggestions = set()  # Track suggestions to avoid rule-based + AI duplicates
            
            for suggestion in suggestions['add_to_quadrant']:
                thought_text = suggestion.get('thought', '').lower().strip()
                
                # Check for meta-conversational content
                is_meta = any(meta_phrase in thought_text for meta_phrase in meta_filters)
                if is_meta:
                    print(f"[DEBUG] Filtered out meta-suggestion: {suggestion['thought']}", flush=True)
                    debug_logger.log('filtering', 'Filtered meta-suggestion', {
                        'suggestion': suggestion['thought'][:100],
                        'reason': 'Meta-conversational content'
                    })
                    continue
                
                # Check for duplicates against existing quadrant items
                is_duplicate = thought_text in existing_items
                if is_duplicate:
                    print(f"[DEBUG] Filtered out duplicate suggestion: {suggestion['thought']}", flush=True)
                    debug_logger.log('filtering', 'Filtered duplicate suggestion', {
                        'suggestion': suggestion['thought'][:100],
                        'reason': 'Already exists in quadrants'
                    })
                    continue
                
                # Check for semantic duplicates between rule-based and AI suggestions
                # Create a normalized version for comparison
                normalized_text = ' '.join(thought_text.split())  # Remove extra whitespace
                # Remove common prefixes/suffixes that might differ
                for prefix in ['i want to ', 'we need to ', 'goal is to ', 'plan to ']:
                    if normalized_text.startswith(prefix):
                        normalized_text = normalized_text[len(prefix):]
                        break
                
                # Check if we've seen a similar suggestion already
                is_semantic_duplicate = False
                for seen_text in seen_suggestions:
                    # Simple similarity check - if 80% of words overlap, consider duplicate
                    seen_words = set(seen_text.split())
                    current_words = set(normalized_text.split())
                    if len(current_words) > 0 and len(seen_words) > 0:
                        overlap = len(seen_words.intersection(current_words))
                        similarity = overlap / max(len(seen_words), len(current_words))
                        if similarity >= 0.8:  # 80% similarity threshold
                            is_semantic_duplicate = True
                            print(f"[DEBUG] Filtered out semantic duplicate: '{suggestion['thought']}' (similar to previous suggestion)", flush=True)
                            debug_logger.log('filtering', 'Filtered semantic duplicate', {
                                'suggestion': suggestion['thought'][:100],
                                'similarity': round(similarity, 2),
                                'reason': 'Similar to previous suggestion'
                            })
                            break
                
                if is_semantic_duplicate:
                    continue
                
                # Keep non-meta, non-duplicate suggestions
                seen_suggestions.add(normalized_text)
                filtered_suggestions.append(suggestion)
                debug_logger.log('filtering', 'Kept suggestion', {
                    'suggestion': suggestion['thought'][:100],
                    'quadrant': suggestion.get('quadrant', 'unknown')
                })
            
            suggestions['add_to_quadrant'] = filtered_suggestions
            print(f"[DEBUG] After filtering: {len(filtered_suggestions)} suggestions remain", flush=True)
            debug_logger.log('filtering', 'Filtering complete', {
                'final_suggestions_count': len(filtered_suggestions),
                'filtered_out_count': len(suggestions_before_filter) - len(filtered_suggestions) if 'suggestions_before_filter' in locals() else 'unknown'
            })
        
        print(f"[DEBUG] Final reply_text (raw): {reply_text}", flush=True)
        print(f"[DEBUG] Final reply_text (cleaned): {reply_text_clean}", flush=True)
        print(f"[DEBUG] Suggestions parsed (after filtering): {suggestions}", flush=True)
        # Save conversation turn for context continuity (just the message)
        db.session.add(ConversationTurn(
            board_id=board_id,
            user_id=None,
            role='assistant',
            content=reply_text
        ))
        db.session.commit()
        # Backend JSON patch: If reply_text does not contain the required JSON but confirms an addition, patch it
        import re, json as pyjson
        patched = False
        if 'add_to_quadrant' not in reply_text:
            # Look for conversational confirmation pattern, expanded for more phrasings
            confirmation_patterns = [
                r"['\"](.+?)['\"] has been added to the (\w+) quadrant",
                r"['\"](.+?)['\"] was added to the (\w+) quadrant",
                r"['\"](.+?)['\"] has been added as (?:a|an)? ?(\w+)",
                r"['\"](.+?)['\"] was added as (?:a|an)? ?(\w+)",
                r"Added ['\"](.+?)['\"] to the (\w+) quadrant",
                r"Added ['\"](.+?)['\"] as (?:a|an)? ?(\w+)",
                r"The (goal|status|analysis|plan) has been added[\.]?",
                r"(Goal|Status|Analysis|Plan) has been added[\.]?"
            ]
            match = None
            for pat in confirmation_patterns:
                match = re.search(pat, reply_text, re.IGNORECASE)
                if match:
                    break
            valid_quadrants = {'goal', 'status', 'analysis', 'plan'}
            if match:
                if len(match.groups()) == 2:
                    thought = match.group(1)
                    quadrant = match.group(2).lower()
                elif len(match.groups()) == 1:
                    quadrant = match.group(1).lower()
                    # Use the user's last message as the thought
                    if conversation_history:
                        # Find the last user turn
                        for turn in reversed(conversation_history):
                            if turn['role'] == 'user':
                                thought = turn['content'].strip()
                                break
                        else:
                            thought = ''
                    else:
                        thought = ''
                else:
                    thought = ''
                    quadrant = ''
                if quadrant.endswith('s'):
                    quadrant = quadrant[:-1]  # e.g., 'status' -> 'statu', fix below
                for q in valid_quadrants:
                    if quadrant.startswith(q):
                        quadrant = q
                        break
                if quadrant in valid_quadrants and thought:
                    json_obj = {"add_to_quadrant": [{"quadrant": quadrant, "thought": thought}]}
                    json_str = pyjson.dumps(json_obj, ensure_ascii=False)
                    reply_text = f"{json_str}\n\n" + reply_text
                    patched = True
        if patched:
            print("[BACKEND PATCH] Prepended missing JSON to AI reply:", reply_text, flush=True)

        # === PROMPT ENGINEERING DEBUG: FINAL OUTPUT ===
        print(f"\n🎆 FINAL OUTPUT TO USER:", flush=True)
        print(f"   💬 Message to User: '{reply_text_clean}'", flush=True)
        # Safe handling of suggestions that might be None
        suggestions_list = suggestions.get('add_to_quadrant', []) if suggestions else []
        print(f"   📊 Suggestions Count: {len(suggestions_list)}", flush=True)
        if suggestions_list:
            for i, suggestion in enumerate(suggestions_list):
                print(f"   📝 Suggestion {i+1}: {suggestion.get('quadrant', 'unknown').upper()} - '{suggestion.get('thought', 'unknown')}'", flush=True)
        print("="*80 + "\n", flush=True)
        
        # Store debug information for web-based console
        suggestions_for_debug = []
        if suggestions_list:
            for suggestion in suggestions_list:
                suggestions_for_debug.append({
                    'quadrant': suggestion.get('quadrant', 'unknown'),
                    'thought': suggestion.get('thought', 'unknown')
                })
        
        add_debug_entry(
            user_input=user_input,
            prompt=prompt,
            ai_response=reply_text,
            clean_message=reply_text_clean,
            suggestions=suggestions_for_debug
        )
        
        # Return AI response to frontend
        # Defensive: always return both keys
        if not isinstance(suggestions, dict) or 'add_to_quadrant' not in suggestions:
            suggestions = {"add_to_quadrant": []}
        return jsonify({"reply": reply_text_clean, "suggestions": suggestions})
    except Exception as e:
        print(f"[DEBUG] Exception caught in /interactive_gaps: {e}", flush=True)
        return jsonify({"error": str(e)}), 500

@app.route('/get_quadrants')
def get_quadrants():
    board_id = request.args.get('board_id')
    quadrants = {q: [] for q in ['status', 'goal', 'analysis', 'plan']}
    from models import Thought
    thoughts = Thought.query.filter_by(board_id=board_id).all()
    for t in thoughts:
        if t.quadrant in quadrants:
            quadrants[t.quadrant].append(t.content)
    return jsonify(quadrants)

@app.route('/export_conversation', methods=['POST'])
@login_required
def export_conversation():
    # ...
    from flask import send_file
    import io, json
    from models import ConversationTurn, Board
    data = request.get_json(force=True)
    board_id = data.get('board_id')
    if not board_id:
        return jsonify({'error': 'Missing board_id'}), 400
    board = Board.query.get(board_id)
    if not board or board.user_id != current_user.id:
        return jsonify({'error': 'Not authorized'}), 403
    turns = ConversationTurn.query.filter_by(board_id=board_id).order_by(ConversationTurn.timestamp).all()
    out = [
        {
            'id': t.id,
            'role': t.role,
            'content': t.content,
            'timestamp': t.timestamp.isoformat() if t.timestamp else None
        } for t in turns
    ]
    buf = io.BytesIO()
    buf.write(json.dumps(out, indent=2).encode('utf-8'))
    buf.seek(0)
    filename = f'conversation_log_board_{board_id}.json'
    return send_file(
        buf,
        mimetype='application/json',
        as_attachment=True,
        download_name=filename
    )

@app.route('/summarize_conversation', methods=['POST'])
@login_required
def summarize_conversation_route():
    try:
        from summarize_utils import summarize_conversation
        from models import Board
        data = request.get_json(force=True)
        board_id = data.get('board_id')
        if not board_id:
            return jsonify({'error': 'Missing board_id'}), 400
        board = Board.query.get(board_id)
        if not board or board.user_id != current_user.id:
            return jsonify({'error': 'Not authorized'}), 403
        summary = summarize_conversation(board_id)
        if summary:
            return jsonify({'success': True, 'summary': summary})
        else:
            return jsonify({'success': False, 'error': 'Nothing to summarize yet - a longer conversation is needed'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/reset_conversation', methods=['POST'])
@login_required
def reset_conversation():
    try:
        from models import ConversationTurn, Board, db
        data = request.get_json(force=True)
        board_id = data.get('board_id')
        if not board_id:
            return jsonify({'error': 'Missing board_id'}), 400
        board = Board.query.get(board_id)
        if not board or board.user_id != current_user.id:
            return jsonify({'error': 'Not authorized'}), 403
        ConversationTurn.query.filter_by(board_id=board_id).delete()
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('landing'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        if not username or not email or not password:
            flash('All fields are required.')
            return render_template('register.html')
        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            flash('Username or email already exists.')
            return render_template('register.html')
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        # Auto-create a default board for new user
        default_board = Board(title='My First Board', user_id=user.id)
        db.session.add(default_board)
        db.session.commit()
        return redirect(url_for('facilitator'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('landing'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('facilitator'))
        flash('Invalid username or password.')
        return render_template('login.html')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/add_thought', methods=['POST'])
@login_required
def add_thought():
    print("=== ENTERED ADD_THOUGHT ROUTE ===")
    data = request.get_json()
    print("/add_thought received data:", data)
    content = data.get('content', '').strip()
    quadrant = data.get('quadrant', '')
    board_id = data.get('board_id')
    uuid_re = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
    # Normalize quadrant names to singular
    quadrant_map = {
        'statuses': 'status',
        'status': 'status',
        'goals': 'goal',
        'goal': 'goal',
        'analyses': 'analysis',
        'analysis': 'analysis',
        'plans': 'plan',
        'plan': 'plan',
    }
    quadrant = quadrant_map.get(quadrant.lower(), 'status')
    # Accept 'auto' as quadrant (let AI decide), fallback to 'status' for now
    if quadrant == 'auto' or not quadrant:
        quadrant = 'status'
    if not (content and board_id):
        print("Returning error: Missing content or board_id")
        return jsonify({'success': False, 'error': 'Missing content or board_id'}), 400
    if uuid_re.match(str(board_id)):
        # JSON board
        try:
            board = board_store.get_board(board_id)
            print("DEBUG: Looking for board_id:", board_id)
            if hasattr(board_store, 'list_board_ids'):
                print("DEBUG: All board IDs:", board_store.list_board_ids())
            else:
                print("DEBUG: board_store has no 'list_board_ids' method.")
            if not board:
                print("Returning error: Board not found")
                return jsonify({'success': False, 'error': 'Board not found'}), 404
            thoughts = board.get('thoughts', [])
            new_id = str(uuid.uuid4())
            new_thought = {'id': new_id, 'content': content, 'quadrant': quadrant}
            thoughts.append(new_thought)
            board['thoughts'] = thoughts
            board_store.save_board(board)
            print("Returning success: JSON board thought added")
            return jsonify({'success': True, 'thought': new_thought})
        except Exception as e:
            import traceback
            print('IN JSON BOARD EXCEPTION HANDLER')
            print('ADD_THOUGHT ERROR (JSON board):', e)
            traceback.print_exc()
            print("Returning error: Exception in JSON board flow")
            return jsonify({'success': False, 'error': str(e)}), 500
    # DB board
    if quadrant not in ['status', 'goal', 'analysis', 'plan']:
        quadrant = 'status'
    try:
        # Prevent duplicate: same content, quadrant, and board_id
        existing = Thought.query.filter_by(content=content, quadrant=quadrant, board_id=board_id).first()
        if existing:
            print("Duplicate thought detected; not adding.")
            return jsonify({'success': False, 'error': 'Duplicate thought: this thought already exists in this quadrant.'}), 409
        thought = Thought(content=content, quadrant=quadrant, board_id=board_id)
        db.session.add(thought)
        db.session.commit()
        minute = MeetingMinute(board_id=board_id, action='add', detail=f"Added thought: '{content}' to '{quadrant}'")
        db.session.add(minute)
        db.session.commit()
        print("Returning success: DB board thought added")
        return jsonify({'success': True, 'thought': {'id': thought.id, 'content': thought.content, 'quadrant': thought.quadrant}})
    except Exception as e:
        print('IN DB BOARD EXCEPTION HANDLER')
        print('ADD_THOUGHT ERROR (DB board):', e)
        import traceback
        traceback.print_exc()
        print("Returning error: Exception in DB board flow")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/move_thought', methods=['POST'])
def move_thought():
    print("=== ENTERED MOVE_THOUGHT ROUTE ===")
    # ... existing code ...
    import re
    data = request.get_json()
    thought_id = data.get('thought_id')
    new_quadrant = data.get('quadrant')
    board_id = data.get('board_id')
    uuid_re = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
    if not (thought_id and new_quadrant and board_id):
        return jsonify({'success': False, 'error': 'Missing data'}), 400
    if uuid_re.match(str(board_id)):
        # JSON board
        board = board_store.get_board(board_id)
        if not board:
            return jsonify({'success': False, 'error': 'Board not found'}), 404
        found = False
        for t in board.get('thoughts', []):
            if str(t.get('id')) == str(thought_id):
                t['quadrant'] = new_quadrant
                found = True
                break
        if found:
            board_store.save_board(board)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Thought not found'}), 404
    else:
        # DB board
        thought = Thought.query.get(thought_id)
        if thought and new_quadrant in ['status', 'goal', 'analysis', 'plan']:
            old_quadrant = thought.quadrant
            thought.quadrant = new_quadrant
            db.session.commit()
            # Log meeting minute
            minute = MeetingMinute(board_id=board_id, action='move', detail=f"Moved thought ID {thought_id} from '{old_quadrant}' to '{new_quadrant}'")
            db.session.add(minute)
            db.session.commit()
            return jsonify({'success': True})
    return jsonify({'success': False}), 400

@app.route('/delete_thought', methods=['POST'])
def delete_thought():
    print("=== ENTERED DELETE_THOUGHT ROUTE ===", flush=True)
    data = request.get_json()
    print(f"[DEBUG] Delete thought received data: {data}", flush=True)
    thought_id = data.get('thought_id')
    print(f"[DEBUG] Looking for thought_id: {thought_id}", flush=True)
    
    if not thought_id:
        print("[DEBUG] No thought_id provided", flush=True)
        return jsonify({'success': False, 'error': 'No thought_id provided'}), 400
    
    thought = Thought.query.get(thought_id)
    print(f"[DEBUG] Found thought: {thought}", flush=True)
    
    if thought:
        board_id = thought.board_id
        print(f"[DEBUG] Deleting thought {thought_id} from board {board_id}", flush=True)
        db.session.delete(thought)
        db.session.commit()
        # Log meeting minute
        minute = MeetingMinute(board_id=board_id, action='delete', detail=f"Deleted thought ID {thought_id}")
        db.session.add(minute)
        db.session.commit()
        print(f"[DEBUG] Successfully deleted thought {thought_id}", flush=True)
        return jsonify({'success': True})
    
    print(f"[DEBUG] Thought {thought_id} not found in database", flush=True)
    return jsonify({'success': False, 'error': f'Thought {thought_id} not found'}), 400

@app.route('/update_thought', methods=['POST'])
def update_thought():
    # ... existing code ...
    data = request.get_json()
    thought_id = data.get('thought_id')
    content = data.get('content', '').strip()
    thought = Thought.query.get(thought_id)
    if thought and content:
        old_content = thought.content
        thought.content = content
        db.session.commit()
        # Log meeting minute
        minute = MeetingMinute(board_id=thought.board_id, action='edit', detail=f"Edited thought ID {thought_id}: '{old_content}' → '{content}'")
        db.session.add(minute)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False}), 400

@app.route('/export_board')
def export_board():
    board_id = request.args.get('board_id')
    if not board_id:
        return jsonify({'success': False, 'error': 'No board_id provided'}), 400
    
    # Check if it's a UUID (JSON board) or integer (DB board)
    import re
    import json
    from flask import Response
    uuid_re = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
    
    if uuid_re.match(str(board_id)):
        # JSON board
        board = board_store.get_board(board_id)
        if not board:
            return jsonify({'success': False, 'error': 'Board not found'}), 404
        board_data = board
        filename = f"{board.get('title', 'board')}_{board_id[:8]}.json"
    else:
        # DB board
        try:
            board_id_int = int(board_id)
            board = Board.query.get(board_id_int)
            if not board:
                return jsonify({'success': False, 'error': 'Board not found'}), 404
            thoughts = [
                {'id': t.id, 'content': t.content, 'quadrant': t.quadrant}
                for t in board.thoughts
            ]
            board_data = {'success': True, 'title': board.title, 'thoughts': thoughts}
            filename = f"{board.title.replace(' ', '_')}_{board_id}.json"
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid board_id format'}), 400
    
    # Create downloadable JSON response
    json_output = json.dumps(board_data, indent=2, ensure_ascii=False)
    
    response = Response(
        json_output,
        mimetype='application/json',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Type': 'application/json; charset=utf-8'
        }
    )
    
    return response

@app.route('/import_board', methods=['POST'])
def import_board():
    try:
        data = request.get_json()
        title = data.get('title', '').strip()
        thoughts = data.get('thoughts', [])
        if not title or not isinstance(thoughts, list):
            return jsonify({'success': False, 'error': 'Invalid data'}), 400
        # Create new board with unique title
        orig_title = title
        i = 1
        while Board.query.filter_by(title=title).first():
            title = f"{orig_title} ({i})"
            i += 1
        # Ensure user is authenticated
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'User not logged in'}), 401
        board = Board(title=title, user_id=current_user.id)
        db.session.add(board)
        db.session.commit()
        for t in thoughts:
            if t.get('content') and t.get('quadrant') in ['status', 'goal', 'analysis', 'plan']:
                thought = Thought(content=t['content'], quadrant=t['quadrant'], board_id=board.id)
                db.session.add(thought)
        db.session.commit()
        return jsonify({'success': True, 'board_id': board.id, 'title': board.title})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/classify_thought', methods=['POST'])
def classify_thought():
    import traceback
    print("=== classify_thought route called ===")
    data = request.get_json()
    content = data.get('content', '').strip()
    print(f"Received content: {content}")
    if not content:
        print("No content provided to classify_thought")
        return jsonify({'success': False, 'error': 'No content provided'}), 400
    try:
        print(f"AI_PROVIDER: {AI_PROVIDER}")
        # Use the pluggable AI backend
        if AI_PROVIDER == 'gemini':
            result = ai_api.classify_thought_with_gemini(content)
        else:
            result = ai_api.classify_thought_with_openai(content)
        print(f"AI result: {result}")
        if isinstance(result, list):
            # Multiple thoughts returned
            print(f"Returning multiple thoughts: {result}")
            return jsonify({'success': True, 'thoughts': result})
        else:
            quadrant = result.get('quadrant')
            thought = result.get('thought', content)
            if quadrant in ['status', 'goal', 'analysis', 'plan']:
                print(f"Returning: quadrant={quadrant}, thought={thought}")
                return jsonify({'success': True, 'quadrant': quadrant, 'thought': thought})
            else:
                print("AI did not return a valid quadrant")
                return jsonify({'success': False, 'error': 'AI did not return a valid quadrant'}), 200
    except Exception as e:
        print("ERROR in classify_thought:", e)
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# --- Board Menu JSON API Endpoints ---
@app.route('/list_boards', methods=['GET'])
@login_required
def list_boards_json():
    db_boards = Board.query.filter_by(user_id=current_user.id).order_by(Board.title).all()
    boards = []
    for b in db_boards:
        boards.append({
            'id': b.id,
            'title': b.title,
            'name': getattr(b, 'name', None) or b.title,  # for compatibility
            'created_at': b.created_at.isoformat() if hasattr(b, 'created_at') and b.created_at else None,
        })
    return jsonify({'boards': boards})

# Debug endpoint to list all DB boards
@app.route('/debug_list_boards', methods=['GET'])
def debug_list_boards():
    boards = Board.query.all()
    return jsonify([
        {'id': str(b.id), 'title': b.title if hasattr(b, 'title') else None} for b in boards
    ])

@app.route('/create_board', methods=['POST'])
@login_required
def create_board_json():
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'success': False, 'error': 'No name provided'}), 400
    
    # Check if board with this name already exists for this user
    existing_board = Board.query.filter_by(title=name, user_id=current_user.id).first()
    if existing_board:
        return jsonify({'success': False, 'error': 'A board with this name already exists'}), 400
    
    # Create new board in database
    new_board = Board(title=name, user_id=current_user.id)
    db.session.add(new_board)
    db.session.commit()
    
    return jsonify({'success': True, 'board_id': new_board.id})

# Duplicate route removed - consolidated into single export_board route above

@app.route('/import_board', methods=['POST'])
def import_board_json():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    board_id = board_store.import_board(data)
    return jsonify({'success': True, 'board_id': board_id})

@app.route('/delete_board', methods=['POST'])
def delete_board():
    import re
    data = request.get_json()
    board_id = data.get('board_id')
    uuid_re = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
    if not board_id:
        return jsonify({'success': False, 'error': 'No board_id provided'}), 400
    if uuid_re.match(str(board_id)):
        # JSON board
        try:
            board_store.delete_board(board_id)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    else:
        # DB board
        board = Board.query.get(board_id)
        if not board:
            return jsonify({'success': False, 'error': 'Board not found'}), 404
        db.session.delete(board)
        db.session.commit()
        return jsonify({'success': True})

# --- Conversational AI endpoint for guided thought addition ---
from flask import session

@app.route('/ai_conversation', methods=['POST'])
@login_required
def ai_conversation():
    user_input = request.json.get('content', '').strip()
    board_id = request.json.get('board_id')
    # RESET conversation state to force fresh categorization
    state = 'awaiting_initial'  # Always start fresh
    history = []  # Clear history for fresh start
    session['conversation_state'] = state
    session['conversation_history'] = history
    if not board_id:
        return jsonify({'success': False, 'error': 'Missing board_id'}), 400

    # Add user input to history
    history.append({'role': 'user', 'content': user_input})

    # Compose prompt for the AI
    prompt = build_conversational_prompt(history, state)

    # DEBUG: Log the full prompt sent to OpenAI
    print("=== AI PROMPT SENT ===")
    print(prompt)
    print("======================")

    # === PROMPT ENGINEERING DEBUG LOGGING ===
    print("\n" + "="*80, flush=True)
    print(" PROMPT ENGINEERING DEBUG - COMPLETE FLOW", flush=True)
    print("="*80, flush=True)
    print(f" USER INPUT: {user_input}", flush=True)
    print(f" AI PROVIDER: {os.environ.get('AI_PROVIDER', 'openai')}", flush=True)
    print(f" CURRENT QUADRANTS: {quadrants}", flush=True)
    print("\n FULL PROMPT BEING SENT TO AI:", flush=True)
    print("-" * 60, flush=True)
    print(prompt, flush=True)
    print("-" * 60, flush=True)

    # Call your AI (Gemini or OpenAI)
    try:
        conversational_facilitator = ai_api.conversational_facilitator
        ai_result = conversational_facilitator(prompt)
        
        # DEBUG: Log the AI response
        print(f"\n RAW AI RESPONSE:", flush=True)
        print("-" * 60, flush=True)
        print(ai_result, flush=True)
        print("-" * 60, flush=True)
        print(f"AI Result Type: {type(ai_result)}")
        print(f"AI Result: {ai_result}")
        print(f"AI Action: {ai_result.get('action')}")
        print(f"AI Thoughts Count: {len(ai_result.get('thoughts', []))}")
        print("==================")
        
    except Exception as e:
        print(f"AI ERROR: {str(e)}")
        return jsonify({'success': False, 'error': f'AI error: {str(e)}'}), 500

    # Parse AI response for intent
    if ai_result.get('action') == 'ask_clarification':
        session['conversation_state'] = 'awaiting_clarification'
        history.append({'role': 'ai', 'content': ai_result['question']})
        session['conversation_history'] = history
        return jsonify({'success': True, 'followup': ai_result['question']})

    elif ai_result.get('action') == 'classify_and_add':
        # Add thoughts to quadrants as directed by AI
        print(f"[DEBUG] Adding {len(ai_result['thoughts'])} thoughts to database...")
        for i, thought in enumerate(ai_result['thoughts']):
            print(f"[DEBUG] Thought {i+1}: '{thought['thought']}' -> {thought['quadrant']} quadrant (board_id: {board_id})")
            t = Thought(content=thought['thought'], quadrant=thought['quadrant'], board_id=board_id)
            db.session.add(t)
            print(f"[DEBUG] Added thought to session: {t}")
        
        print("[DEBUG] Committing to database...")
        db.session.commit()
        print("[DEBUG] Database commit successful!")
        
        session['conversation_state'] = 'awaiting_initial'
        # Do NOT reset session['conversation_history'] here; preserve full history for context
        return jsonify({'success': True, 'message': 'Thought(s) added!', 'thoughts': ai_result['thoughts']})

    else:
        # Always return something useful to the frontend
        ai_text = ai_result.get('reply_text') or ai_result.get('question') or ai_result.get('message') or str(ai_result)
        if ai_text:
            # Keep conversation state/history for continued flow
            history.append({'role': 'ai', 'content': ai_text})
            session['conversation_history'] = history
            return jsonify({'success': True, 'reply': ai_text})
        else:
            # Last resort fallback
            session['conversation_history'] = history
            return jsonify({'success': True, 'reply': "I'm here, but I didn't quite understand. Could you rephrase or ask another way?"})

import os

def build_conversational_prompt(history, state, latest_user_message=None):
    import json
    print("STATE TYPE:", type(state), "VALUE:", state)
    # Ensure state is a dict
    if isinstance(state, str):
        try:
            state = json.loads(state)
        except Exception:
            state = {}
    # Load the conversational facilitator prompt from file
    prompt_path = os.path.join(os.path.dirname(__file__), 'prompts', 'prompts_modified.txt')
    with open(prompt_path, 'r', encoding='utf-8') as f:
        template = f.read()
    # Build the conversation history string, matching the example: 'User:' and 'AI:'
    role_map = {'user': 'User', 'ai': 'AI', 'assistant': 'AI'}
    conversation_history = ""
    for turn in history:
        role = role_map.get(turn['role'].lower(), turn['role'].capitalize())
        conversation_history += f"{role}: {turn['content']}\n"
    # Format quadrant state
    if state:
        quadrant_lines = []
        for q in ['status', 'goal', 'analysis', 'plan']:
            items = state.get(q, [])
            quadrant_lines.append(f"{q.capitalize()}:")
            if items:
                for item in items:
                    quadrant_lines.append(f"  - {item}")
            else:
                quadrant_lines.append("  (empty)")
        quadrant_state = "\n".join(quadrant_lines)
    else:
        quadrant_state = "(No quadrant data provided)"
    # Fill in placeholders
    prompt = template.replace('{conversation_history}', conversation_history.strip())
    prompt = prompt.replace('{quadrant_state}', quadrant_state.strip())
    if latest_user_message is None and history:
        # Default to last user turn
        for turn in reversed(history):
            if turn['role'].lower() == 'user':
                latest_user_message = turn['content']
                break
    prompt = prompt.replace('{latest_user_message}', (latest_user_message or '').strip())
    return prompt


# --- Dummy AI endpoints for frontend integration ---
@app.route('/rewrite_thought', methods=['POST'])
def rewrite_thought():
    import traceback
    data = request.get_json() or {}
    thought = data.get('thought')
    board_id = data.get('board_id')
    if not thought:
        return jsonify({'success': False, 'error': 'Missing thought'}), 400
    if not board_id:
        return jsonify({'success': False, 'error': 'Missing board_id'}), 400
    try:
        if AI_PROVIDER == 'openai':
            print("Using OpenAI for rewrite_thought")
            result = ai_api.rewrite_thought_with_openai(thought)
            return jsonify({'success': True, 'suggestions': result.get('suggestions', [])})
        else:
            api_key = os.environ.get('GEMINI_API_KEY')
            if not api_key:
                return jsonify({'success': False, 'error': 'Gemini API key not set in environment.'}), 500
            genai.configure(api_key=api_key)
            prompt = f"Rewrite the following thought to be clearer, more positive, or more actionable.\n\nThought: '{thought}'\n\nRewritten Thought:"
            model = genai.GenerativeModel('models/gemini-1.5-pro-latest')
            response = model.generate_content(prompt)
            text = response.text.strip() if hasattr(response, 'text') else str(response).strip()
            if not text:
                return jsonify({'success': False, 'error': 'Gemini returned empty output.'}), 500
            # Parse for multiple suggestions (numbered or bulleted)
            lines = [line.strip("1234567890.-• \t") for line in text.split('\n') if line.strip()]
            # Filter out generic intro lines
            filtered = [l for l in lines if l and not l.lower().startswith("here are") and not l.lower().startswith("depending on")]
            if not filtered:
                filtered = [text]
            return jsonify({'success': True, 'suggestions': filtered})
    except Exception as e:
        print("ERROR in rewrite_thought:", e)
        traceback.print_exc()
        # Use a more generic error response that could be customized via prompt if needed
        return jsonify({"reply": "An error occurred while processing your request. Please try again.", "suggestions": {"add_to_quadrant": []}}), 200


@app.route('/suggest_solution/', methods=['POST'])
def suggest_solution():
    data = request.get_json()
    print("/suggest_solution received data:", data)
    import traceback
    data = data or {}
    problems = data.get('problems', [])
    obstacles = data.get('obstacles', [])
    if not isinstance(problems, list) or not isinstance(obstacles, list):
        return jsonify({'success': False, 'error': 'Problems and obstacles must be lists.'}), 400
    try:
        if AI_PROVIDER == 'openai':
            print("Using OpenAI for suggest_solution")
            result = ai_api.suggest_solution_with_openai(problems, obstacles)
        else:
            print("Using Gemini for suggest_solution")
            result = ai_api.suggest_solution_with_gemini(problems, obstacles)
        if 'suggestions' in result:
            suggestions = result['suggestions']
            enriched = []
            for s in suggestions:
                # s is now a dict with 'content' and 'quadrant'
                if not isinstance(s, dict) or not s.get('content', '').strip():
                    continue
                # Classify each suggestion into a quadrant
                if AI_PROVIDER == 'openai':
                    classified = ai_api.classify_thought_with_openai(s)
                    # OpenAI returns a list of dicts [{quadrant, thought}]
                    if isinstance(classified, list) and classified:
                        quadrant = classified[0].get('quadrant', 'status')
                    else:
                        quadrant = 'status'
                else:
                    classified = ai_api.classify_thought_with_gemini(s)
                    quadrant = classified.get('quadrant', 'status')
                enriched.append({'content': s, 'quadrant': quadrant})
            return jsonify({'success': True, 'suggestions': enriched})
        else:
            return jsonify({'success': False, 'error': result.get('error', 'Unknown error')})
    except Exception as e:
        print("ERROR in suggest_solution:", e)
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'AI error: {str(e)}'}), 500

@app.route('/brainstorm', methods=['POST'])
def brainstorm():
    data = request.get_json() or {}
    topic = data.get('topic')
    board_id = data.get('board_id')
    if not topic or not board_id:
        return jsonify({'success': False, 'error': 'Missing data'}), 400
    if AI_PROVIDER == 'gemini':
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            return jsonify({'success': False, 'error': 'Gemini API key not set in environment.'}), 500
        genai.configure(api_key=api_key)
        prompt = f"Brainstorm three creative and practical solutions for the following issue:\n\n'{topic}'\n\nRespond as a numbered list."
        try:
            model = genai.GenerativeModel('models/gemini-1.5-pro-latest')
            response = model.generate_content(prompt)
            text = response.text if hasattr(response, 'text') else str(response)
            # Parse ideas from numbered list
            ideas = [line.lstrip("1234567890. ").strip() for line in text.split('\n') if line.strip() and any(c.isalpha() for c in line)]
            if len(ideas) > 3:
                ideas = ideas[:3]
            return jsonify({'success': True, 'suggestions': ideas})
        except Exception as e:
            return jsonify({'success': False, 'error': f'Gemini error: {str(e)}'}), 500
    else:
        try:
            result = ai_api.brainstorm_with_openai(topic)
            if 'suggestions' in result:
                return jsonify({'success': True, 'suggestions': result['suggestions']})
            else:
                return jsonify({'success': False, 'error': result.get('error', 'Unknown error')})
        except Exception as e:
            return jsonify({'success': False, 'error': f'OpenAI error: {str(e)}'}), 500

@app.route('/meeting_minutes', methods=['POST'])
def meeting_minutes():
    data = request.get_json() or {}
    summary = data.get('summary')
    board_id = data.get('board_id')
    if not board_id:
        return jsonify({'success': False, 'error': 'No board selected. Please select a board and try again.'}), 400
    import re
    uuid_re = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
    if not summary:
        transcript = []
        if uuid_re.match(str(board_id)):
            # JSON board
            board = board_store.get_board(board_id)
            if board:
                thoughts = board.get('thoughts', [])
                if thoughts:
                    transcript.append('Thoughts:')
                    for t in thoughts:
                        quadrant = t.get('quadrant', 'status')
                        content = t.get('content', '')
                        transcript.append(f"- [{quadrant}] {content}")
                events = board.get('events', []) or []
                if events:
                    transcript.append('\nSession Events:')
                    for e in events:
                        timestamp = e.get('timestamp', '')
                        action = e.get('action', '')
                        detail = e.get('detail', '')
                        transcript.append(f"- [{timestamp}] {action}: {detail}")
        else:
            # DB board
            thoughts = Thought.query.filter_by(board_id=board_id).all()
            minutes = MeetingMinute.query.filter_by(board_id=board_id).order_by(MeetingMinute.timestamp.asc()).all()
            if thoughts:
                transcript.append('Thoughts:')
                for t in thoughts:
                    transcript.append(f"- [{t.quadrant}] {t.content}")
            if minutes:
                transcript.append('\nSession Events:')
                for m in minutes:
                    transcript.append(f"- [{m.timestamp.strftime('%Y-%m-%d %H:%M')}] {m.action}: {m.detail}")
        if not transcript:
            return jsonify({'success': False, 'error': 'No data found for this board to generate meeting minutes.'}), 400
        summary = '\n'.join(transcript)

    if AI_PROVIDER == 'gemini':
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            return jsonify({'success': False, 'error': 'Gemini API key not set in environment.'}), 500
        genai.configure(api_key=api_key)
        prompt = f"Rewrite the following meeting summary as clear, concise meeting minutes.\n\nSummary: '{summary}'\n\nMeeting Minutes:"
        try:
            model = genai.GenerativeModel('models/gemini-1.5-pro-latest')
            response = model.generate_content(prompt)
            text = response.text.strip() if hasattr(response, 'text') else str(response).strip()
            return jsonify({'success': True, 'result': text})
        except Exception as e:
            return jsonify({'success': False, 'error': f'Gemini error: {str(e)}'}), 500
    else:
        try:
            result = ai_api.meeting_minutes_with_openai(summary)
            if 'result' in result:
                return jsonify({'success': True, 'result': result['result']})
            else:
                return jsonify({'success': False, 'error': result.get('error', 'Unknown error')})
        except Exception as e:
            return jsonify({'success': False, 'error': f'OpenAI error: {str(e)}'}), 500

@app.route('/get_meeting_minutes', methods=['GET'])
def get_meeting_minutes():
    board_id = request.args.get('board_id', type=int)
    if not board_id:
        return jsonify({'success': False, 'error': 'Missing board_id'}), 400
    minutes = MeetingMinute.query.filter_by(board_id=board_id).order_by(MeetingMinute.timestamp.desc()).all()
    return jsonify({'success': True, 'minutes': [
        {
            'timestamp': m.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'action': m.action,
            'detail': m.detail
        } for m in minutes
    ]})

    if not summary or not board_id:
        return jsonify({'success': False, 'error': 'Missing data'}), 400
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        return jsonify({'success': False, 'error': 'Gemini API key not set in environment.'}), 500
    genai.configure(api_key=api_key)
    prompt = f"Rewrite the following meeting summary as clear, concise meeting minutes.\n\nSummary: '{summary}'\n\nMeeting Minutes:"
    try:
        model = genai.GenerativeModel('models/gemini-1.5-pro-latest')
        response = model.generate_content(prompt)
        text = response.text.strip() if hasattr(response, 'text') else str(response).strip()
        return jsonify({'success': True, 'result': text})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Gemini error: {str(e)}'}), 500


# @app.errorhandler(500)
# def handle_500_error(e):
#     return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/api/logged_in', methods=['GET'])
def api_logged_in():
    from flask_login import current_user
    return jsonify({'logged_in': current_user.is_authenticated})

# ============================================================================
# RULE-BASED CATEGORIZATION TESTING INTERFACE
# ============================================================================

# HTML Template for Rule Testing Interface
RULE_TESTER_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>🧪 Rule-Based Categorization Tester</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; background: #f8f9fa; }
        .header { text-align: center; margin-bottom: 30px; }
        .container { background: white; padding: 20px; border-radius: 8px; margin: 15px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .result { padding: 15px; border-radius: 5px; margin: 10px 0; }
        .error { background: #ffebee; color: #c62828; border-left: 4px solid #f44336; }
        .success { background: #e8f5e9; color: #2e7d32; border-left: 4px solid #4caf50; }
        .info { background: #e3f2fd; color: #1976d2; border-left: 4px solid #2196f3; }
        input[type="text"], select { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
        button { background: #4CAF50; color: white; padding: 12px 24px; border: none; border-radius: 4px; cursor: pointer; margin: 5px; font-size: 14px; }
        button:hover { background: #45a049; }
        button.secondary { background: #2196F3; }
        button.secondary:hover { background: #1976D2; }
        .quadrant { display: inline-block; margin: 3px; padding: 6px 12px; border-radius: 20px; font-weight: bold; font-size: 0.9em; }
        .goal { background: #e3f2fd; color: #1976d2; }
        .status { background: #f3e5f5; color: #7b1fa2; }
        .analysis { background: #fff3e0; color: #f57c00; }
        .plan { background: #e8f5e9; color: #388e3c; }
        .rules { background: #fafafa; padding: 15px; border-left: 4px solid #2196F3; margin: 10px 0; }
        .keyword { background: #e0e0e0; padding: 3px 8px; margin: 2px; border-radius: 12px; display: inline-block; font-size: 0.85em; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .stat-box { background: #f5f5f5; padding: 15px; border-radius: 8px; text-align: center; }
        .stat-number { font-size: 2em; font-weight: bold; color: #4CAF50; }
        .back-link { position: absolute; top: 20px; left: 20px; }
        .back-link a { color: #2196F3; text-decoration: none; font-weight: bold; }
        .back-link a:hover { text-decoration: underline; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        @media (max-width: 768px) { .grid { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="back-link">
        <a href="/">← Back to Main App</a>
    </div>
    
    <div class="header">
        <h1>🧪 Rule-Based Categorization Tester</h1>
        <p>Test and customize the rule-based quadrant categorization system</p>
    </div>
    
    <div class="grid">
        <div>
            <div class="container">
                <h3>🎯 Test Single Input</h3>
                <input type="text" id="testInput" placeholder="Enter text to categorize (e.g., 'I want to increase sales by 20%')" />
                <button onclick="testSingle()">Categorize</button>
                <div id="singleResult"></div>
            </div>
            
            <div class="container">
                <h3>📦 Quick Examples</h3>
                <button onclick="testExample('I want to increase sales by 20% this quarter')">Goal Example</button>
                <button onclick="testExample('We are currently behind on the project timeline')">Status Example</button>
                <button onclick="testExample('The main issue is poor communication between teams')">Analysis Example</button>
                <button onclick="testExample('Next step is to schedule a team meeting')">Plan Example</button>
            </div>
            
            <div class="container">
                <h3>➕ Add Custom Keyword</h3>
                <select id="quadrantSelect">
                    <option value="goal">Goal</option>
                    <option value="status">Status</option>
                    <option value="analysis">Analysis</option>
                    <option value="plan">Plan</option>
                </select>
                <input type="text" id="keywordInput" placeholder="Enter new keyword or phrase" />
                <button onclick="addKeyword()">Add Keyword</button>
                <div id="addResult"></div>
            </div>
        </div>
        
        <div>
            <div class="container">
                <h3>⚡ Performance Test</h3>
                <button onclick="performanceTest()">Run Speed Test (100 categorizations)</button>
                <div id="performanceResult"></div>
            </div>
            
            <div class="container">
                <h3>📋 Current Rules</h3>
                <button class="secondary" onclick="viewRules()">View All Rules</button>
                <div id="rulesDisplay"></div>
            </div>
        </div>
    </div>

    <script>
        function testSingle() {
            const text = document.getElementById('testInput').value;
            if (!text.trim()) {
                document.getElementById('singleResult').innerHTML = '<div class="result error">Please enter some text to test.</div>';
                return;
            }
            
            fetch('/api/rule-categorize', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({text: text})
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    document.getElementById('singleResult').innerHTML = `<div class="result error">Error: ${data.error}</div>`;
                    return;
                }
                const quadrantClass = data.category.toLowerCase();
                document.getElementById('singleResult').innerHTML = `
                    <div class="result success">
                        <strong>Text:</strong> "${data.text}"<br>
                        <strong>Category:</strong> <span class="quadrant ${quadrantClass}">${data.category.toUpperCase()}</span><br>
                        <strong>Confidence:</strong> ${data.confidence.toFixed(2)}<br>
                        <strong>Speed:</strong> ${data.processing_time_ms.toFixed(1)}ms<br>
                        ${data.matched_keywords.length > 0 ? '<strong>Matched Keywords:</strong> ' + data.matched_keywords.map(k => `<span class="keyword">${k}</span>`).join('') : ''}
                    </div>
                `;
            })
            .catch(error => {
                document.getElementById('singleResult').innerHTML = `<div class="result error">Network error: ${error}</div>`;
            });
        }
        
        function testExample(text) {
            document.getElementById('testInput').value = text;
            testSingle();
        }
        
        function performanceTest() {
            document.getElementById('performanceResult').innerHTML = '<div class="result info">Running performance test...</div>';
            
            fetch('/api/rule-performance', {method: 'POST'})
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    document.getElementById('performanceResult').innerHTML = `<div class="result error">Error: ${data.error}</div>`;
                    return;
                }
                document.getElementById('performanceResult').innerHTML = `
                    <div class="result success">
                        <div class="stats">
                            <div class="stat-box">
                                <div class="stat-number">${data.total_tests}</div>
                                <div>Tests</div>
                            </div>
                            <div class="stat-box">
                                <div class="stat-number">${data.avg_time_ms.toFixed(2)}ms</div>
                                <div>Avg Time</div>
                            </div>
                            <div class="stat-box">
                                <div class="stat-number">${data.categorizations_per_second.toFixed(0)}</div>
                                <div>Per Second</div>
                            </div>
                            <div class="stat-box">
                                <div class="stat-number">$0.00</div>
                                <div>API Cost</div>
                            </div>
                        </div>
                    </div>
                `;
            })
            .catch(error => {
                document.getElementById('performanceResult').innerHTML = `<div class="result error">Network error: ${error}</div>`;
            });
        }
        
        function addKeyword() {
            const quadrant = document.getElementById('quadrantSelect').value;
            const keyword = document.getElementById('keywordInput').value.trim();
            
            if (!keyword) {
                document.getElementById('addResult').innerHTML = '<div class="result error">Please enter a keyword.</div>';
                return;
            }
            
            fetch('/api/rule-add-keyword', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({quadrant: quadrant, keyword: keyword})
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    document.getElementById('addResult').innerHTML = `<div class="result error">Error: ${data.error}</div>`;
                    return;
                }
                document.getElementById('addResult').innerHTML = `<div class="result success">${data.message}</div>`;
                document.getElementById('keywordInput').value = '';
            })
            .catch(error => {
                document.getElementById('addResult').innerHTML = `<div class="result error">Network error: ${error}</div>`;
            });
        }
        
        function viewRules() {
            document.getElementById('rulesDisplay').innerHTML = '<div class="result info">Loading rules...</div>';
            
            fetch('/api/rule-patterns')
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    document.getElementById('rulesDisplay').innerHTML = `<div class="result error">Error: ${data.error}</div>`;
                    return;
                }
                let html = '<div class="rules">';
                
                // Add rule management header
                html += '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">';
                html += '<h4>📋 Rule Management</h4>';
                html += '<button onclick="toggleRuleMode()" id="ruleModeBtn" class="secondary">Switch to Edit Mode</button>';
                html += '</div>';
                
                for (const [quadrant, patterns] of Object.entries(data)) {
                    html += `<div class="quadrant-rules" data-quadrant="${quadrant}">`;
                    html += `<h4>🎯 ${quadrant.toUpperCase()} Quadrant</h4>`;
                    
                    // Keywords section with management
                    html += `<div class="rule-section">`;
                    html += `<strong>Keywords (${patterns.keywords.length}):</strong>`;
                    html += `<button onclick="toggleSection('keywords-${quadrant}')" class="secondary" style="margin-left: 10px; padding: 4px 8px; font-size: 12px;">Show All</button><br>`;
                    html += `<div id="keywords-${quadrant}" class="rule-items" style="display: none;">`;
                    patterns.keywords.forEach((keyword, index) => {
                        html += `<div class="rule-item" data-type="keyword" data-quadrant="${quadrant}" data-index="${index}">`;
                        html += `<span class="keyword editable" onclick="editRule('keyword', '${quadrant}', ${index}, '${keyword}')">${keyword}</span>`;
                        html += `<button onclick="deleteRule('keyword', '${quadrant}', ${index})" class="delete-btn" style="display: none; margin-left: 5px; padding: 2px 6px; background: #f44336; color: white; border: none; border-radius: 3px; font-size: 11px;">×</button>`;
                        html += `</div>`;
                    });
                    html += `</div>`;
                    
                    // Show first 10 keywords by default
                    html += `<div class="keywords-preview">`;
                    html += patterns.keywords.slice(0, 10).map((k, i) => 
                        `<span class="keyword editable" onclick="editRule('keyword', '${quadrant}', ${i}, '${k}')">${k}</span>`
                    ).join('');
                    if (patterns.keywords.length > 10) html += `<span class="keyword">...and ${patterns.keywords.length - 10} more</span>`;
                    html += `</div>`;
                    html += `</div>`;
                    
                    // Phrase patterns section with management
                    html += `<div class="rule-section">`;
                    html += `<strong>Phrase Patterns (${patterns.phrases.length}):</strong>`;
                    html += `<button onclick="toggleSection('phrases-${quadrant}')" class="secondary" style="margin-left: 10px; padding: 4px 8px; font-size: 12px;">Show All</button><br>`;
                    html += `<div id="phrases-${quadrant}" class="rule-items" style="display: none;">`;
                    patterns.phrases.forEach((phrase, index) => {
                        html += `<div class="rule-item" data-type="phrase" data-quadrant="${quadrant}" data-index="${index}">`;
                        html += `<code class="phrase-pattern editable" onclick="editRule('phrase', '${quadrant}', ${index}, '${phrase}')" style="background: #f5f5f5; padding: 4px 8px; border-radius: 4px; font-family: monospace; font-size: 0.9em;">${phrase}</code>`;
                        html += `<button onclick="deleteRule('phrase', '${quadrant}', ${index})" class="delete-btn" style="display: none; margin-left: 5px; padding: 2px 6px; background: #f44336; color: white; border: none; border-radius: 3px; font-size: 11px;">×</button>`;
                        html += `</div>`;
                    });
                    html += `</div>`;
                    html += `</div>`;
                    
                    html += `<br>`;
                    html += `</div>`;
                }
                html += '</div>';
                document.getElementById('rulesDisplay').innerHTML = html;
            })
            .catch(error => {
                document.getElementById('rulesDisplay').innerHTML = `<div class="result error">Network error: ${error}</div>`;
            });
        }
        
        let editMode = false;
        
        function toggleRuleMode() {
            editMode = !editMode;
            const btn = document.getElementById('ruleModeBtn');
            const deleteButtons = document.querySelectorAll('.delete-btn');
            
            if (editMode) {
                btn.textContent = 'Switch to View Mode';
                btn.style.background = '#f44336';
                deleteButtons.forEach(btn => btn.style.display = 'inline-block');
                document.querySelectorAll('.editable').forEach(el => {
                    el.style.cursor = 'pointer';
                    el.title = 'Click to edit';
                });
            } else {
                btn.textContent = 'Switch to Edit Mode';
                btn.style.background = '#2196F3';
                deleteButtons.forEach(btn => btn.style.display = 'none');
                document.querySelectorAll('.editable').forEach(el => {
                    el.style.cursor = 'default';
                    el.title = '';
                });
            }
        }
        
        function toggleSection(sectionId) {
            const section = document.getElementById(sectionId);
            const preview = section.parentElement.querySelector('.keywords-preview');
            if (section.style.display === 'none') {
                section.style.display = 'block';
                if (preview) preview.style.display = 'none';
                event.target.textContent = 'Hide';
            } else {
                section.style.display = 'none';
                if (preview) preview.style.display = 'block';
                event.target.textContent = 'Show All';
            }
        }
        
        function editRule(type, quadrant, index, currentValue) {
            if (!editMode) return;
            
            const newValue = prompt(`Edit ${type}:`, currentValue);
            if (newValue === null || newValue.trim() === currentValue.trim()) {
                return; // User cancelled or no change
            }
            
            fetch('/api/rule-edit', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    type: type,
                    quadrant: quadrant,
                    index: index,
                    old_value: currentValue,
                    new_value: newValue.trim()
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert(`Error: ${data.error}`);
                    return;
                }
                alert(data.message);
                viewRules(); // Refresh the display
            })
            .catch(error => {
                alert(`Network error: ${error}`);
            });
        }
        
        function deleteRule(type, quadrant, index) {
            if (!editMode) return;
            
            if (!confirm(`Are you sure you want to delete this ${type}?`)) {
                return;
            }
            
            fetch('/api/rule-delete', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    type: type,
                    quadrant: quadrant,
                    index: index
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert(`Error: ${data.error}`);
                    return;
                }
                alert(data.message);
                viewRules(); // Refresh the display
            })
            .catch(error => {
                alert(`Network error: ${error}`);
            });
        }
        
        // Auto-test on page load
        window.onload = function() {
            testExample('I want to achieve better results this quarter');
        };
    </script>
</body>
</html>
"""

@app.route('/api/test-no-csrf', methods=['POST'])
@csrf.exempt
def test_no_csrf():
    """Test route to verify CSRF exemption works"""
    return jsonify({'status': 'success', 'message': 'CSRF exemption working'})

@app.route('/rule-tester')
@login_required
def rule_tester_page():
    """Rule-based categorization testing interface"""
    return render_template_string(RULE_TESTER_TEMPLATE)

@app.route('/debug')
@login_required
def debug_page():
    """Debug page showing hybrid system processing logs"""
    return render_template('debug.html')

@app.route('/api/debug/logs')
@login_required
def get_debug_logs():
    """API endpoint to get recent debug logs"""
    from debug_logger import debug_logger
    
    limit = request.args.get('limit', 50, type=int)
    logs = debug_logger.get_logs(limit=limit)
    
    return jsonify({
        'logs': logs,
        'total_count': len(logs)
    })

@app.route('/api/debug/clear', methods=['POST'])
@login_required
@csrf.exempt  # Temporary for experimental environment
def clear_debug_logs():
    """API endpoint to clear debug logs"""
    from debug_logger import debug_logger
    
    debug_logger.clear()
    return jsonify({'status': 'success', 'message': 'Debug logs cleared'})

@app.route('/api/rule-categorize', methods=['POST'])
@csrf.exempt
def rule_categorize():
    """API endpoint for rule-based categorization"""
    try:
        print(f"[DEBUG] Rule categorize called, request content type: {request.content_type}", flush=True)
        
        # Check if request has JSON data
        if not request.is_json:
            print(f"[DEBUG] Request is not JSON, raw data: {request.get_data()}", flush=True)
            return jsonify({'error': 'Request must be JSON'}), 400
        
        data = request.get_json()
        print(f"[DEBUG] Received JSON data: {data}", flush=True)
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        text = data.get('text', '')
        print(f"[DEBUG] Extracted text: '{text}'", flush=True)
        
        if not text.strip():
            return jsonify({'error': 'No text provided'}), 400
        
        from rule_based_categorizer import RuleBasedCategorizer
        import time
        
        categorizer = RuleBasedCategorizer()
        
        # Measure processing time
        start_time = time.time()
        result = categorizer.categorize(text)
        end_time = time.time()
        processing_time_ms = (end_time - start_time) * 1000
        
        print(f"[DEBUG] Categorization result: {result}", flush=True)
        
        # Convert 'quadrant' key to 'category' for frontend compatibility
        if 'quadrant' in result:
            result['category'] = result.pop('quadrant')
        
        # Add processing time for frontend display
        result['processing_time_ms'] = round(processing_time_ms, 3)
        
        # Add input text to response for frontend display
        result['text'] = text
        
        # Add matched_keywords field for frontend display (extract from reasoning if available)
        matched_keywords = []
        if 'reasoning' in result and 'keyword:' in result['reasoning']:
            # Extract keywords from reasoning string
            import re
            keyword_matches = re.findall(r"keyword: '([^']+)'", result['reasoning'])
            matched_keywords = keyword_matches
        result['matched_keywords'] = matched_keywords
        
        return jsonify(result)
    except ImportError as e:
        print(f"[DEBUG] Import error: {str(e)}", flush=True)
        return jsonify({'error': f'Rule categorizer import failed: {str(e)}'}), 500
    except Exception as e:
        print(f"[DEBUG] Categorization exception: {str(e)}", flush=True)
        return jsonify({'error': f'Categorization failed: {str(e)}'}), 500

@app.route('/api/rule-performance', methods=['POST'])
@csrf.exempt
def rule_performance_test():
    """API endpoint for rule-based performance testing"""
    try:
        from rule_based_categorizer import RuleBasedCategorizer
        import time
        
        categorizer = RuleBasedCategorizer()
        
        test_cases = [
            "I want to achieve better results",
            "Currently working on the project", 
            "The issue is lack of resources",
            "Plan to implement new strategy"
        ] * 25  # 100 total tests
        
        start_time = time.time()
        for text in test_cases:
            categorizer.categorize(text)
        end_time = time.time()
        
        total_time_ms = (end_time - start_time) * 1000
        avg_time_ms = total_time_ms / len(test_cases)
        categorizations_per_second = len(test_cases) / (total_time_ms / 1000)
        
        return jsonify({
            'total_tests': len(test_cases),
            'total_time_ms': total_time_ms,
            'avg_time_ms': avg_time_ms,
            'categorizations_per_second': categorizations_per_second
        })
    except Exception as e:
        return jsonify({'error': f'Performance test failed: {str(e)}'}), 500

@app.route('/api/rule-patterns')
@csrf.exempt
def get_rule_patterns():
    """API endpoint to get current rule patterns"""
    try:
        from rule_based_categorizer import RuleBasedCategorizer
        categorizer = RuleBasedCategorizer()
        return jsonify(categorizer.patterns)
    except Exception as e:
        return jsonify({'error': f'Failed to get patterns: {str(e)}'}), 500

@app.route('/api/rule-add-keyword', methods=['POST'])
@csrf.exempt
def add_rule_keyword():
    """API endpoint to add new keyword to rules"""
    try:
        from rule_based_categorizer import RuleBasedCategorizer
        categorizer = RuleBasedCategorizer()
        
        data = request.json
        quadrant = data.get('quadrant', '').lower()
        keyword = data.get('keyword', '').strip()
        
        if quadrant not in categorizer.patterns:
            return jsonify({'error': 'Invalid quadrant. Choose: goal, status, analysis, plan'}), 400
        
        if not keyword:
            return jsonify({'error': 'No keyword provided'}), 400
        
        categorizer.patterns[quadrant]['keywords'].append(keyword)
        return jsonify({'success': True, 'message': f'Added "{keyword}" to {quadrant.upper()} quadrant'})
    except Exception as e:
        return jsonify({'error': f'Failed to add keyword: {str(e)}'}), 500

@app.route('/api/rule-edit', methods=['POST'])
@csrf.exempt
def edit_rule():
    """API endpoint to edit existing rule (keyword or phrase pattern)"""
    try:
        from rule_based_categorizer import RuleBasedCategorizer
        categorizer = RuleBasedCategorizer()
        
        data = request.json
        rule_type = data.get('type', '').lower()  # 'keyword' or 'phrase'
        quadrant = data.get('quadrant', '').lower()
        index = data.get('index', -1)
        old_value = data.get('old_value', '')
        new_value = data.get('new_value', '').strip()
        
        if quadrant not in categorizer.patterns:
            return jsonify({'error': 'Invalid quadrant. Choose: goal, status, analysis, plan'}), 400
        
        if rule_type not in ['keyword', 'phrase']:
            return jsonify({'error': 'Invalid rule type. Choose: keyword, phrase'}), 400
        
        if not new_value:
            return jsonify({'error': 'New value cannot be empty'}), 400
        
        # Get the appropriate list
        if rule_type == 'keyword':
            rule_list = categorizer.patterns[quadrant]['keywords']
        else:
            rule_list = categorizer.patterns[quadrant]['phrases']
        
        # Validate index
        if index < 0 or index >= len(rule_list):
            return jsonify({'error': 'Invalid rule index'}), 400
        
        # Verify old value matches (safety check)
        if rule_list[index] != old_value:
            return jsonify({'error': 'Rule has been modified by another process. Please refresh and try again.'}), 409
        
        # Update the rule
        rule_list[index] = new_value
        
        return jsonify({
            'success': True, 
            'message': f'Updated {rule_type} in {quadrant.upper()} quadrant from "{old_value}" to "{new_value}"'
        })
    except Exception as e:
        return jsonify({'error': f'Failed to edit rule: {str(e)}'}), 500

@app.route('/api/rule-delete', methods=['POST'])
@csrf.exempt
def delete_rule():
    """API endpoint to delete existing rule (keyword or phrase pattern)"""
    try:
        from rule_based_categorizer import RuleBasedCategorizer
        categorizer = RuleBasedCategorizer()
        
        data = request.json
        rule_type = data.get('type', '').lower()  # 'keyword' or 'phrase'
        quadrant = data.get('quadrant', '').lower()
        index = data.get('index', -1)
        
        if quadrant not in categorizer.patterns:
            return jsonify({'error': 'Invalid quadrant. Choose: goal, status, analysis, plan'}), 400
        
        if rule_type not in ['keyword', 'phrase']:
            return jsonify({'error': 'Invalid rule type. Choose: keyword, phrase'}), 400
        
        # Get the appropriate list
        if rule_type == 'keyword':
            rule_list = categorizer.patterns[quadrant]['keywords']
        else:
            rule_list = categorizer.patterns[quadrant]['phrases']
        
        # Validate index
        if index < 0 or index >= len(rule_list):
            return jsonify({'error': 'Invalid rule index'}), 400
        
        # Get the value being deleted for the success message
        deleted_value = rule_list[index]
        
        # Delete the rule
        del rule_list[index]
        
        return jsonify({
            'success': True, 
            'message': f'Deleted {rule_type} "{deleted_value}" from {quadrant.upper()} quadrant'
        })
    except Exception as e:
        return jsonify({'error': f'Failed to delete rule: {str(e)}'}), 500

# ============================================================================
# PROMPT DEBUG CONSOLE ROUTES
# ============================================================================

@app.route('/admin/prompt_debug')
@login_required
def prompt_debug():
    """Web-based debug console for prompt engineering"""
    if not current_user.is_admin:
        return "Unauthorized", 403
    return render_template('prompt_debug.html')

@app.route('/admin/debug_entries')
@login_required
def get_debug_entries():
    """API endpoint to get debug entries for the web console"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Return debug entries in reverse order (newest first)
    return jsonify({
        'entries': list(reversed(debug_entries)),
        'count': len(debug_entries)
    })

@app.route('/admin/clear_debug_log', methods=['POST'])
@login_required
def clear_debug_log():
    """Clear all debug entries"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    global debug_entries
    debug_entries.clear()
    print("[DEBUG STORAGE] Debug log cleared by admin", flush=True)
    
    return jsonify({'success': True, 'message': 'Debug log cleared'})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print('Registered routes:')
    for rule in app.url_map.iter_rules():
        print(rule)
    app.run(debug=True)
