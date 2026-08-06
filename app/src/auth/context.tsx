import * as Linking from 'expo-linking';
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react';
import { verifyEndpointAuthVerifyGet } from '../api/generated/sdk.gen';
import {
  clearStoredSessionToken,
  getStoredSessionToken,
  getStoredUserId,
  setStoredSession,
} from './storage';

type AuthState =
  | { status: 'loading' }
  | { status: 'signed-out' }
  | { status: 'verifying' }
  | { status: 'verify-failed' }
  | { status: 'verify-suspended' }
  | { status: 'signed-in'; sessionToken: string; userId: string };

type AuthContextValue = AuthState & {
  signIn: (sessionToken: string, userId: string) => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function extractToken(url: string): string | null {
  const { queryParams } = Linking.parse(url);
  const token = queryParams?.token;
  return typeof token === 'string' ? token : null;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: 'loading' });
  // Tracks whether magic-link verification has started (via initial URL or a
  // 'url' event) so the storage-restore path can bail out instead of
  // clobbering 'verifying'/'signed-in' state with a stale stored session.
  const verificationStarted = useRef(false);

  async function signIn(sessionToken: string, userId: string) {
    await setStoredSession(sessionToken, userId);
    setState({ status: 'signed-in', sessionToken, userId });
  }

  async function signOut() {
    await clearStoredSessionToken();
    setState({ status: 'signed-out' });
  }

  const verify = useCallback(async (token: string) => {
    verificationStarted.current = true;
    setState({ status: 'verifying' });
    const { data, error, response } = await verifyEndpointAuthVerifyGet({ query: { token } });
    if (error || !data) {
      setState({ status: response?.status === 403 ? 'verify-suspended' : 'verify-failed' });
      return;
    }
    await setStoredSession(data.session_token, data.user_id);
    setState({ status: 'signed-in', sessionToken: data.session_token, userId: data.user_id });
  }, []);

  useEffect(() => {
    async function restore() {
      const initialUrl = await Linking.getInitialURL();
      const token = initialUrl ? extractToken(initialUrl) : null;
      if (token) {
        // Cold start via magic link takes priority over any stored session —
        // await it before touching storage so a stale token can't clobber
        // the in-flight (or just-completed) verification.
        await verify(token);
        return;
      }

      const storedToken = await getStoredSessionToken();
      const storedUserId = await getStoredUserId();
      // A 'url' event may have started verification while getStoredSessionToken()
      // was in flight — don't overwrite that newer state with the stored token.
      if (verificationStarted.current) return;
      setState(
        storedToken && storedUserId
          ? { status: 'signed-in', sessionToken: storedToken, userId: storedUserId }
          : { status: 'signed-out' },
      );
    }
    restore();

    const subscription = Linking.addEventListener('url', ({ url }) => {
      const token = extractToken(url);
      if (token) verify(token);
    });

    return () => subscription.remove();
  }, [verify]);

  return (
    <AuthContext.Provider value={{ ...state, signIn, signOut }}>{children}</AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
