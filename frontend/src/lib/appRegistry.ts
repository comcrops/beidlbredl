import type { Component } from 'svelte';
import HelloWorldDisplay from '../apps/hello-world/Display.svelte';
import HelloWorldMobileControls from '../apps/hello-world/MobileControls.svelte';
import RotAppDisplay from '../apps/rot-app/Display.svelte';
import BlauAppDisplay from '../apps/blau-app/Display.svelte';

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
  {
    id: 'rot-app',
    name: 'Rote App',
    icon: '🔴',
    hasMobileControls: false,
    display: RotAppDisplay,
  },
  {
    id: 'blau-app',
    name: 'Blaue App',
    icon: '🔵',
    hasMobileControls: false,
    display: BlauAppDisplay,
  },
];

export function getApp(id: string): AppDefinition | undefined {
  return apps.find((app) => app.id === id);
}
