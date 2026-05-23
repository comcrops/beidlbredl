from flask import Blueprint
from extensions import socketio

bp = Blueprint('hello_world', __name__)

_state = {'message': 'Servus Welt!'}


@socketio.on('hello_world:update_message', namespace='/apps')
def handle_update_message(data):
    message = data.get('message', '').strip()
    if message:
        _state['message'] = message
        socketio.emit('hello_world:message_updated', {'message': message}, namespace='/apps')
