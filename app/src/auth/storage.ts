import * as SecureStore from 'expo-secure-store';

const SESSION_KEY = 'session';

type StoredSession = { sessionToken: string; userId: string };

async function getStoredSession(): Promise<StoredSession | null> {
  const raw = await SecureStore.getItemAsync(SESSION_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    if (typeof parsed?.sessionToken === 'string' && typeof parsed?.userId === 'string') {
      return parsed;
    }
    return null;
  } catch {
    return null;
  }
}

export async function getStoredSessionToken(): Promise<string | null> {
  const session = await getStoredSession();
  return session?.sessionToken ?? null;
}

export async function getStoredUserId(): Promise<string | null> {
  const session = await getStoredSession();
  return session?.userId ?? null;
}

export async function setStoredSession(sessionToken: string, userId: string): Promise<void> {
  await SecureStore.setItemAsync(SESSION_KEY, JSON.stringify({ sessionToken, userId }));
}

export async function clearStoredSessionToken(): Promise<void> {
  await SecureStore.deleteItemAsync(SESSION_KEY);
}
