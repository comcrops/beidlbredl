from flask import Blueprint, g, jsonify, request
from auth import require_auth
import users

bp = Blueprint('users', __name__)


def _user_response(user: dict) -> dict:
    return {'username': user['username'], 'avatar_url': users.avatar_url(user)}


@bp.route('/api/users/me', methods=['GET'])
@require_auth
def get_me():
    user = users.get_user(g.user_sub)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(_user_response(user))


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
        return jsonify(_user_response(user)), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/users/me', methods=['PUT'])
@require_auth
def update_me():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    if len(username) < 3 or len(username) > 20:
        return jsonify({'error': 'Username must be 3-20 characters'}), 400
    if not all(c.isalnum() or c == '_' for c in username):
        return jsonify({'error': 'Username: letters, numbers, underscores only'}), 400
    try:
        user = users.update_user(g.user_sub, username)
        return jsonify(_user_response(user))
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/users/avatars', methods=['GET'])
def get_avatars():
    raw = request.args.get('usernames', '')
    usernames = [u.strip() for u in raw.split(',') if u.strip()]
    avatar_map = users.get_avatars_by_usernames(usernames)
    return jsonify(avatar_map)


@bp.route('/api/users/me/avatar', methods=['POST'])
@require_auth
def upload_avatar():
    if 'avatar' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    f = request.files['avatar']
    if not f.content_type or not f.content_type.startswith('image/'):
        return jsonify({'error': 'File must be an image'}), 400
    try:
        user = users.update_avatar(g.user_sub, f.stream, f.filename or 'avatar', f.content_type)
        return jsonify(_user_response(user))
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
