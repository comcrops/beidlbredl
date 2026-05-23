import { describe, it, expect } from 'vitest';
import { get } from 'svelte/store';
import { kioskState } from '../stores/kiosk';

describe('kioskState', () => {
  it('starts with null active app and empty open list', () => {
    const state = get(kioskState);
    expect(state.activeAppId).toBeNull();
    expect(state.openAppIds).toEqual([]);
  });
});
