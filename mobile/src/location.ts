import { PermissionsAndroid, Platform } from 'react-native';
import Geolocation from '@react-native-community/geolocation';

export type Position = { lat: number; lng: number };

/**
 * The device's approximate position, asked for only when the user taps
 * "near me". Coarse accuracy is enough and kinder to privacy; the position is
 * sent with that one request and not stored by the app or the API.
 * Resolves to null if the user declines or no fix arrives in time.
 */
export async function approximatePosition(): Promise<Position | null> {
  if (Platform.OS === 'android') {
    const granted = await PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.ACCESS_COARSE_LOCATION);
    if (granted !== PermissionsAndroid.RESULTS.GRANTED) {
      return null;
    }
  }
  return new Promise(resolve => {
    Geolocation.getCurrentPosition(
      p => resolve({ lat: p.coords.latitude, lng: p.coords.longitude }),
      () => resolve(null),
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 10 * 60 * 1000 },
    );
  });
}
