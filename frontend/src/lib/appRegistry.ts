import type { Component } from 'svelte';
import HelloWorldDisplay from '../apps/hello-world/Display.svelte';
import HelloWorldMobileControls from '../apps/hello-world/MobileControls.svelte';

export interface AppDefinition {
  id: string;
  name: string;
  icon: string;
  hasMobileControls: boolean;
  display: Component;
  mobileControls?: Component;
}

export const apps: AppDefinition[] = [
  {
    id: 'hello-world',
    name: 'Hallo Welt',
    icon: '👋',
    hasMobileControls: true,
    display: HelloWorldDisplay,
    mobileControls: HelloWorldMobileControls,
  },
];

export function getApp(id: string): AppDefinition | undefined {
  return apps.find((app) => app.id === id);
}
