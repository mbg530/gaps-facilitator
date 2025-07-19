from flask import Blueprint, jsonify
import os

kb_blueprint = Blueprint('kb_blueprint', __name__)

@kb_blueprint.route('/gaps_kb', methods=['GET'])
def serve_gaps_kb():
    kb_path = os.path.join(os.path.dirname(__file__), '../prompts/gaps_knowledge_base.md')
    try:
        with open(kb_path, 'r', encoding='utf-8') as f:
            kb_content = f.read()
        return jsonify({'content': kb_content})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
