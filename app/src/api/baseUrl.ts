import Constants from 'expo-constants';

const API_PORT = 8000;

/**
 * Backend URL. `EXPO_PUBLIC_API_URL` wins when set. Otherwise, in a dev build,
 * reuse the host the JS bundle was loaded from (the laptop running Metro) so a
 * phone on the same wifi finds the backend without editing app/.env.
 */
export function resolveApiUrl(): string {
  const fromEnv = process.env.EXPO_PUBLIC_API_URL;
  if (fromEnv) return fromEnv;

  const metroHost = __DEV__ ? Constants.expoConfig?.hostUri?.split(':')[0] : undefined;
  return `http://${metroHost || 'localhost'}:${API_PORT}`;
}
