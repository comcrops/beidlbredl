from flask_socketio import Namespace, emit
from state import kiosk_state


class GeneralNamespace(Namespace):
    def on_connect(self):
        emit('state', kiosk_state.to_dict())

    def on_open_app(self, data):
        app_id = data.get('app_id')
        if app_id and app_id not in kiosk_state.open_app_ids:
            kiosk_state.open_app_ids.append(app_id)
        kiosk_state.active_app_id = app_id
        self._broadcast_state()

    def on_close_app(self, data):
        app_id = data.get('app_id')
        if app_id in kiosk_state.open_app_ids:
            kiosk_state.open_app_ids.remove(app_id)
        if kiosk_state.active_app_id == app_id:
            kiosk_state.active_app_id = kiosk_state.open_app_ids[-1] if kiosk_state.open_app_ids else None
        self._broadcast_state()

    def on_carousel_next(self):
        self._carousel_step(1)

    def on_carousel_prev(self):
        self._carousel_step(-1)

    def _carousel_step(self, direction: int):
        if not kiosk_state.open_app_ids:
            return
        ids = kiosk_state.open_app_ids
        try:
            idx = ids.index(kiosk_state.active_app_id)
        except ValueError:
            idx = 0
        kiosk_state.active_app_id = ids[(idx + direction) % len(ids)]
        self._broadcast_state()

    def _broadcast_state(self):
        emit('state', kiosk_state.to_dict(), broadcast=True, namespace='/general')
