import { Platform } from 'react-native';

/**
 * Where the API lives.
 *
 * Debug builds talk to a backend on the developer's machine. The Android
 * emulator reaches the host as 10.0.2.2; the iOS simulator uses localhost.
 * On a physical device, set DEV_API_URL to the machine's LAN address.
 *
 * Release builds must use HTTPS: both platforms block plain HTTP there.
 */
const DEV_API_URL: string | null = null; // e.g. 'http://192.168.1.20:8000'
const PRODUCTION_API_URL = ''; // set before the first store build, e.g. 'https://api.example.ae'

function resolveApiUrl(): string {
  if (__DEV__) {
    return DEV_API_URL ?? Platform.select({ android: 'http://10.0.2.2:8000', default: 'http://localhost:8000' });
  }
  if (!PRODUCTION_API_URL.startsWith('https://')) {
    throw new Error('PRODUCTION_API_URL must be set to an https:// address in src/config.ts');
  }
  return PRODUCTION_API_URL;
}

export const API_BASE_URL = resolveApiUrl();
