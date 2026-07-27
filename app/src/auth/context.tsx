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
import { clearStoredSessionToken, getStoredSessionToken, setStoredSessionToken } from './storage';

type AuthState =
  | { status: 'loading' }
  | { status: 'signed-out' }
  | { status: 'verifying' }
  | { status: 'verify-failed' }
  | { status: 'signed-in'; sessionToken: string };

type AuthContextValue = AuthState & {
  signIn: (sessionToken: string) => Promise<void>;
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

  async function signIn(sessionToken: string) {
    await setStoredSessionToken(sessionToken);
    setState({ status: 'signed-in', sessionToken });
  }

  async function signOut() {
    await clearStoredSessionToken();
    setState({ status: 'signed-out' });
  }

  const verify = useCallback(async (token: string) => {
    verificationStarted.current = true;
    setState({ status: 'verifying' });
    const { data, error } = await verifyEndpointAuthVerifyGet({ query: { token } });
    if (error || !data) {
      setState({ status: 'verify-failed' });
      return;
    }
    await setStoredSessionToken(data.session_token);
    setState({ status: 'signed-in', sessionToken: data.session_token });
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
      // A 'url' event may have started verification while getStoredSessionToken()
      // was in flight — don't overwrite that newer state with the stored token.
      if (verificationStarted.current) return;
      setState(
        storedToken ? { status: 'signed-in', sessionToken: storedToken } : { status: 'signed-out' },
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
