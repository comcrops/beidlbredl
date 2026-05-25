from flask import Blueprint
from extensions import socketio

bp = Blueprint('hagenberg_mittag', __name__)

# in-memory state (survives until Flask restarts)
_state = {}
