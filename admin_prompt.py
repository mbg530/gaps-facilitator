from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
import os

admin_bp = Blueprint('admin_bp', __name__, url_prefix='/admin')
PROMPT_PATH = os.path.join(os.path.dirname(__file__), 'prompts', 'prompts_modified.txt')


# --- Restrict to admin users only ---
def is_admin():
    return current_user.is_authenticated and getattr(current_user, 'is_admin', False)

@admin_bp.route('/prompt_editor', methods=['GET'])
@login_required
def prompt_editor():
    if not is_admin():
        return "Unauthorized", 403
    return render_template('prompt_editor.html')

@admin_bp.route('/get_prompt', methods=['GET'])
@login_required
def get_prompt():
    if not is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    with open(PROMPT_PATH, 'r') as f:
        return jsonify({'prompt': f.read()})

@admin_bp.route('/set_prompt', methods=['POST'])
@login_required
def set_prompt():
    if not is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    data = request.get_json()
    new_prompt = data.get('prompt', '')
    with open(PROMPT_PATH, 'w') as f:
        f.write(new_prompt)
    return jsonify({'success': True})
