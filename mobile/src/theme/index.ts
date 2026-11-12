import { Platform } from 'react-native';

/**
 * Visual language: blush and cream grounds, a berry-rose to plum accent, a
 * touch of champagne gold, an elegant serif for titles. Gradients and soft
 * shadows use React Native's built-in CSS-style `backgroundImage` and
 * `boxShadow` (no extra native libraries).
 */
export const colors = {
  background: '#FBF5F3',
  backgroundDeep: '#F6E7E7',
  surface: '#FFFFFF',
  surfaceTint: '#FFF8F7',
  text: '#2E1F27',
  muted: '#86717B',
  primary: '#A23E66',
  primaryDeep: '#6B2346',
  primarySoft: '#F7E1E8',
  onPrimary: '#FFFFFF',
  gold: '#C29A6B',
  goldSoft: '#F5EBDD',
  lilac: '#EDE3F4',
  sage: '#E3EEE8',
  peach: '#FBE6DA',
  border: '#EFE2E2',
  danger: '#B3261E',
  dangerSoft: '#FCEBEA',
  badge: '#F6E9EC',
};

export const gradients = {
  primary: 'linear-gradient(135deg, #C2557F 0%, #A23E66 45%, #6B2346 100%)',
  hero: 'linear-gradient(150deg, #F3C9D5 0%, #D98BA8 38%, #A23E66 72%, #6B2346 100%)',
  screen: 'linear-gradient(180deg, #F9E9EA 0%, #FBF5F3 38%, #FBF5F3 100%)',
  gold: 'linear-gradient(135deg, #E9D3B4 0%, #C29A6B 100%)',
  card: 'linear-gradient(160deg, #FFFFFF 0%, #FFF7F6 100%)',
};

export const shadows = {
  soft: '0px 8px 24px rgba(162, 62, 102, 0.10)',
  lifted: '0px 14px 32px rgba(107, 35, 70, 0.22)',
  button: '0px 10px 22px rgba(162, 62, 102, 0.32)',
};

export const spacing = { xs: 4, sm: 8, md: 16, lg: 24, xl: 32 };

export const radius = { sm: 10, md: 16, lg: 24, xl: 32, pill: 999 };

export const fonts = {
  // Fashion-magazine serif for titles in Latin script. Arabic falls back to the system font.
  display: Platform.select({ ios: 'Didot', android: 'serif', default: undefined }),
};

export const type = {
  title: { fontSize: 30, fontWeight: '700' as const, lineHeight: 38, letterSpacing: 0.2 },
  heading: { fontSize: 18, fontWeight: '600' as const, lineHeight: 26 },
  body: { fontSize: 16, lineHeight: 24 },
  small: { fontSize: 13, lineHeight: 18 },
};
