export interface Restaurant {
  id: string;
  name: string;
  mittagUrl: string;
}

export const RESTAURANTS: Restaurant[] = [
  { id: 'schlossrestaurant', name: 'Schlossrestaurant', mittagUrl: 'https://www.mittag.at/w/schlossrestaurant-hagenberg' },
  { id: 'caravento',         name: 'Caravento',         mittagUrl: 'https://www.mittag.at/r/caravento' },
  { id: 'salz-pfeffer',      name: 'Salz & Pfeffer',    mittagUrl: 'https://www.mittag.at/w/salz-pfeffer' },
  { id: 'vorstadt-wirt',     name: 'Vorstadt Wirt Chili', mittagUrl: 'https://www.mittag.at/w/vorstadt-wirt-chili' },
  { id: 'fleischerei-fuerst', name: 'Fleischerei Fürst', mittagUrl: 'https://www.mittag.at/w/fleischerei-fuerst' },
];
