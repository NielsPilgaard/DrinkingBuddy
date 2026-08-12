import * as Linking from 'expo-linking';
import * as LocalAuthentication from 'expo-local-authentication';
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
  | { status: 'locked'; sessionToken: string; userId: string }
  | { status: 'signed-in'; sessionToken: string; userId: string };

type AuthContextValue = AuthState & {
  signIn: (sessionToken: string, userId: string) => Promise<void>;
  signOut: () => Promise<void>;
  retryUnlock: () => Promise<void>;
};

// When true, biometric unlock is mandatory and the OS passcode/PIN fallback
// is disabled; when false, the device fallback stays available.
const REQUIRE_BIOMETRIC_UNLOCK = false;

async function deviceCanGate(): Promise<boolean> {
  const [hasHardware, isEnrolled] = await Promise.all([
    LocalAuthentication.hasHardwareAsync(),
    LocalAuthentication.isEnrolledAsync(),
  ]);
  return hasHardware && isEnrolled;
}

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

  const unlock = useCallback(async (sessionToken: string, userId: string) => {
    const canGate = await deviceCanGate();
    // Magic-link verification may have started (or finished) while the
    // above await was in flight — a stale stored-session unlock must not
    // clobber that newer state.
    if (verificationStarted.current) return;
    if (!canGate) {
      setState({ status: 'signed-in', sessionToken, userId });
      return;
    }
    const result = await LocalAuthentication.authenticateAsync({
      disableDeviceFallback: REQUIRE_BIOMETRIC_UNLOCK,
    });
    if (verificationStarted.current) return;
    if (result.success) {
      setState({ status: 'signed-in', sessionToken, userId });
    } else {
      setState({ status: 'locked', sessionToken, userId });
    }
  }, []);

  async function retryUnlock() {
    if (state.status !== 'locked') return;
    await unlock(state.sessionToken, state.userId);
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
      if (storedToken && storedUserId) {
        await unlock(storedToken, storedUserId);
      } else {
        setState({ status: 'signed-out' });
      }
    }
    restore();

    const subscription = Linking.addEventListener('url', ({ url }) => {
      const token = extractToken(url);
      if (token) verify(token);
    });

    return () => subscription.remove();
  }, [verify, unlock]);

  return (
    <AuthContext.Provider value={{ ...state, signIn, signOut, retryUnlock }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
