from flask import Blueprint
from extensions import socketio

bp = Blueprint('hagenberg_mittag', __name__)


@socketio.on('hagenberg_mittag:focus', namespace='/apps')
def handle_focus(data):
    socketio.emit('hagenberg_mittag:focus', data, namespace='/apps')


@socketio.on('hagenberg_mittag:set_week_mode', namespace='/apps')
def handle_set_week_mode(data):
    socketio.emit('hagenberg_mittag:set_week_mode', data, namespace='/apps')
