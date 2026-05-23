from flask import Blueprint, g, jsonify, request
from auth import require_auth
import users

bp = Blueprint('users', __name__)


@bp.route('/api/users/me', methods=['GET'])
@require_auth
def get_me():
    user = users.get_user(g.user_sub)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({'username': user['username']})


@bp.route('/api/users/me', methods=['POST'])
@require_auth
def create_me():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    if len(username) < 3 or len(username) > 20:
        return jsonify({'error': 'Username must be 3-20 characters'}), 400
    if not all(c.isalnum() or c == '_' for c in username):
        return jsonify({'error': 'Username: letters, numbers, underscores only'}), 400
    if users.get_user(g.user_sub):
        return jsonify({'error': 'User already exists'}), 409
    try:
        user = users.create_user(g.user_sub, username)
        return jsonify({'username': user['username']}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
