import { io } from 'socket.io-client';
import { kioskState } from './stores/kiosk';

const BASE_URL = import.meta.env.VITE_BACKEND_URL ?? '';

export const generalSocket = io(`${BASE_URL}/general`, { autoConnect: false });
export const appsSocket = io(`${BASE_URL}/apps`, { autoConnect: false });

generalSocket.on(
  'state',
  (state: { active_app_id: string | null; open_app_ids: string[]; locked: boolean }) => {
    kioskState.set({
      activeAppId: state.active_app_id,
      openAppIds: state.open_app_ids,
      locked: state.locked,
    });
  }
);

export function connectSockets(): void {
  generalSocket.connect();
  appsSocket.connect();
}
