from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file
from admin_prompt import admin_bp
from templates.gaps_kb_endpoint import kb_blueprint
from models import db, Board, Thought, MeetingMinute, User
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf import CSRFProtect
import os
import uuid
import google.generativeai as genai
from flask import send_from_directory

# ... other imports ...

# (app = Flask(__name__) and all setup code comes here)

# --- Serve files from /prompts for download ---
# Place this after app = Flask(__name__)


import gemini_api
import openai_api

# Maximum number of conversation turns to send to the LLM for context
MAX_HISTORY_TURNS = 12
import board_store

from sqlalchemy import event
from sqlalchemy.engine import Engine

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

AI_PROVIDER = os.environ.get("AI_PROVIDER", "gemini").lower()  # Set to 'openai' to use OpenAI
if AI_PROVIDER == "openai":
    ai_api = openai_api
else:
    ai_api = gemini_api

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////home/mel/CascadeProjects/gaps_facilitator/fourws.db'

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

# Register knowledge base endpoint
app.register_blueprint(kb_blueprint)

# Register CSRF token refresh endpoint
from get_csrf_token import csrf_token_api
app.register_blueprint(csrf_token_api)

# Increase CSRF token lifetime to 1 hour (3600 seconds)
app.config['WTF_CSRF_TIME_LIMIT'] = 3600

# --- CSRF Protection ---
csrf = CSRFProtect(app)

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
    board_id = request.args.get('board_id', type=int)
    boards = get_boards()
    if not boards:
        return None
    if board_id:
        for b in boards:
            if b.id == board_id:
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
            return render_template('index.html', boards=boards, board=None, quadrants={}, thoughts={}, version=os.environ.get('VERSION', 'dev'))
        # Prepare thoughts dict
        thoughts = {q: [] for q in ['status', 'goal', 'analysis', 'plan']}
        for t in board.get('thoughts', []):
            q = t.get('quadrant')
            if q in thoughts:
                thoughts[q].append(t)
        return render_template('index.html', boards=boards, board=board, quadrants=None, thoughts=thoughts, version=os.environ.get('VERSION', 'dev'))
    else:
        # Default: use database
        board = get_current_board()
        boards = get_boards()
        if not board and boards:
            board = boards[0]  # fallback to first available board
        if not board:
            return render_template('index.html', boards=[], board=None, quadrants={}, thoughts={}, version=os.environ.get('VERSION', 'dev'))
        thoughts = {q: [] for q in ['status', 'goal', 'analysis', 'plan']}
        for t in board.thoughts:
            thoughts[t.quadrant].append(t)
        return render_template('index.html', boards=boards, board=board, quadrants=None, thoughts=thoughts, version=os.environ.get('VERSION', 'dev'))


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
        # If user_input is empty, send a kickoff prompt to ensure quadrant-aware summary and JSON
        if not user_input or not user_input.strip():
            user_input = ("Please summarize the current quadrant state and provide recommendations for how to proceed. "
                           "If you have new thoughts for any quadrant, output them as a JSON object at the start of your reply, "
                           "using the 'add_to_quadrant' key.")
        # Fetch full conversation history for context (all turns)
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
        # Limit conversation history to the last MAX_HISTORY_TURNS for prompt context
        history_window = conversation_history[-MAX_HISTORY_TURNS:] if len(conversation_history) > MAX_HISTORY_TURNS else conversation_history
        # Call GAPS-Coach logic
        from app import build_conversational_prompt
        prompt = build_conversational_prompt(history_window + [{"role": "user", "content": user_input}], quadrants)
        # DEBUG: Print the full prompt being sent to the AI
        print("=== AI PROMPT SENT (interactive_gaps) ===", flush=True)
        print(prompt, flush=True)
        print("[DEBUG] Quadrants being sent to LLM:", quadrants, flush=True)
        print("=========================================")
        ai_result = conversational_facilitator(prompt, quadrants=quadrants)
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
            reply_text = reply_text.lstrip()
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
                    message_part = reply_text[end:].lstrip(' \n,]}')
                    try:
                        parsed_json = json.loads(json_part)
                    except Exception as e:
                        print(f"[DEBUG] Failed to parse JSON from AI reply: {e}", flush=True)
                        parsed_json = None
                    return parsed_json, message_part.strip()
            # If no JSON at the start, just return the message
            return None, reply_text.strip()
        suggestions, reply_text_clean = extract_json_and_message(reply_text)
        print(f"[DEBUG] Final reply_text (raw): {reply_text}", flush=True)
        print(f"[DEBUG] Final reply_text (cleaned): {reply_text_clean}", flush=True)
        print(f"[DEBUG] Suggestions parsed: {suggestions}", flush=True)
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
    # ... existing code ...
    data = request.get_json()
    thought_id = data.get('thought_id')
    thought = Thought.query.get(thought_id)
    if thought:
        board_id = thought.board_id
        db.session.delete(thought)
        db.session.commit()
        # Log meeting minute
        minute = MeetingMinute(board_id=board_id, action='delete', detail=f"Deleted thought ID {thought_id}")
        db.session.add(minute)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False}), 400

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
    board_id = request.args.get('board_id', type=int)
    board = Board.query.get(board_id)
    if not board:
        return jsonify({'success': False, 'error': 'Board not found'}), 404
    thoughts = [
        {'id': t.id, 'content': t.content, 'quadrant': t.quadrant}
        for t in board.thoughts
    ]
    return jsonify({'success': True, 'title': board.title, 'thoughts': thoughts})

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
def create_board_json():
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'success': False, 'error': 'No name provided'}), 400
    board_id = board_store.create_board(name)
    return jsonify({'success': True, 'board_id': board_id})

@app.route('/export_board')
def export_board_json():
    board_id = request.args.get('board_id')
    if not board_id:
        return jsonify({'success': False, 'error': 'No board_id provided'}), 400
    board = board_store.get_board(board_id)
    if not board:
        return jsonify({'success': False, 'error': 'Board not found'}), 404
    return jsonify(board)

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
    state = session.get('conversation_state', 'awaiting_initial')
    history = session.get('conversation_history', [])
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

    # Call your AI (Gemini or OpenAI)
    try:
        ai_result = conversational_facilitator(prompt)
    except Exception as e:
        return jsonify({'success': False, 'error': f'AI error: {str(e)}'}), 500

    # Parse AI response for intent
    if ai_result.get('action') == 'ask_clarification':
        session['conversation_state'] = 'awaiting_clarification'
        history.append({'role': 'ai', 'content': ai_result['question']})
        session['conversation_history'] = history
        return jsonify({'success': True, 'followup': ai_result['question']})

    elif ai_result.get('action') == 'classify_and_add':
        # Add thoughts to quadrants as directed by AI
        for thought in ai_result['thoughts']:
            t = Thought(content=thought['content'], quadrant=thought['quadrant'], board_id=board_id)
            db.session.add(t)
        db.session.commit()
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
        return jsonify({"reply": "Sorry, something went wrong while contacting the AI.", "suggestions": {"add_to_quadrant": []}}), 200


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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print('Registered routes:')
    for rule in app.url_map.iter_rules():
        print(rule)
    app.run(debug=True)
