import fs from 'fs';
import path from 'path';

import ar from '../src/localization/ar/translation.json';
import en from '../src/localization/en/translation.json';
import { ENTRIES, GROUP_ORDER, visibleSections } from '../src/navigation/registry';

const flatten = (value: object, prefix = ''): string[] =>
  Object.entries(value).flatMap(([key, v]) =>
    typeof v === 'object' ? flatten(v as object, `${prefix}${key}.`) : [`${prefix}${key}`],
  );

test('English and Arabic define exactly the same keys, none empty', () => {
  expect(flatten(ar).sort()).toEqual(flatten(en).sort());
  const values = (o: object): string[] => Object.values(o).flatMap(v => (typeof v === 'object' ? values(v) : [v]));
  expect(values(en).every(Boolean) && values(ar).every(Boolean)).toBe(true);
});

test('Arabic strings are actually Arabic (not copied English)', () => {
  const arabic = /[؀-ۿ]/;
  const untranslated = flatten(ar).filter(key => {
    const text = key.split('.').reduce((o: any, k) => o[k], ar) as string;
    return !arabic.test(text) && key !== 'language.en';
  });
  expect(untranslated).toEqual([]);
});

test('every entry and group has a label in both languages', () => {
  for (const entry of ENTRIES) {
    expect((en.entries as Record<string, string>)[entry.id]).toBeTruthy();
    expect((ar.entries as Record<string, string>)[entry.id]).toBeTruthy();
  }
  expect(Object.keys(en.entries).sort()).toEqual(ENTRIES.map(e => e.id).sort());
  expect(Object.keys(en.groups).sort()).toEqual([...GROUP_ORDER].sort());
});

test('every feature key used by the app exists in the backend catalog', () => {
  const catalog = fs.readFileSync(
    path.join(__dirname, '../../backend/app/modules/phase_management/catalog.py'),
    'utf8',
  );
  const known = new Set([...catalog.matchAll(/"(phase\d\.[a-z_]+)"/g)].map(m => m[1]));
  expect(known.size).toBe(52);
  expect(ENTRIES.map(e => e.feature).filter(key => !known.has(key))).toEqual([]);
  expect(new Set(ENTRIES.map(e => e.id)).size).toBe(ENTRIES.length);
});

test('only enabled features are shown, and empty groups disappear', () => {
  expect(visibleSections([])).toEqual([]);
  const sections = visibleSections(['phase1.face_shape', 'phase2.booking', 'phase9.unknown']);
  expect(sections.map(s => [s.group, s.entries.map(e => e.id)])).toEqual([
    ['assessment', ['faceShape']],
    ['experts', ['bookings']],
  ]);
});
