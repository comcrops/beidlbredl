import { writable } from 'svelte/store';

export interface KioskState {
  activeAppId: string | null;
  openAppIds: string[];
  locked: boolean;
}

export const kioskState = writable<KioskState>({
  activeAppId: null,
  openAppIds: [],
  locked: false,
});
