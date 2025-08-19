from flask import Blueprint, jsonify
from flask_wtf.csrf import generate_csrf

csrf_token_api = Blueprint('csrf_token_api', __name__)

@csrf_token_api.route('/get_csrf_token')
def get_csrf_token():
    return jsonify({'csrf_token': generate_csrf()})
