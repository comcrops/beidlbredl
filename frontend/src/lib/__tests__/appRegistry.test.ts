import { describe, it, expect } from 'vitest';
import { apps, getApp } from '../appRegistry';

describe('appRegistry', () => {
  it('contains hello-world', () => {
    const ids = apps.map((a) => a.id);
    expect(ids).toContain('hello-world');
  });

  it('hello-world has required fields', () => {
    const app = getApp('hello-world');
    expect(app).toBeDefined();
    expect(app?.name).toBeTruthy();
    expect(app?.icon).toBeTruthy();
    expect(app?.hasMobileControls).toBe(true);
    expect(app?.display).toBeDefined();
    expect(app?.mobileControls).toBeDefined();
  });

  it('getApp returns undefined for unknown id', () => {
    expect(getApp('does-not-exist')).toBeUndefined();
  });
});
