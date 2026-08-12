import { startVerification as startDiditVerification } from '@didit-protocol/sdk-react-native';
import { useCallback, useState } from 'react';
import {
  startVerificationEndpointVerifyStartPost,
  verificationStatusEndpointVerifyStatusGet,
} from '../api/generated/sdk.gen';

export type VerificationState =
  | { kind: 'unverified' }
  | { kind: 'checking' }
  | { kind: 'waitlisted' }
  | { kind: 'verified' };

/**
 * Drives the age-verification flow: kicks off a Didit session server-side,
 * hands the session_token to the Didit SDK's native flow, then re-checks
 * server status once the SDK reports completion. The server is always the
 * source of truth for "verified" - the SDK's own completion event only
 * tells us the user finished the flow, not that Didit's webhook has landed
 * yet, so a short poll follows a "completed" result.
 */
export function useVerification() {
  const [state, setState] = useState<VerificationState>({ kind: 'unverified' });
  const [error, setError] = useState<string | null>(null);

  /** Returns 'verified', 'failed' (explicit terminal non-verified result), or
   * 'pending' (still processing, or the status request itself failed - both
   * cases the caller should keep retrying rather than giving up). */
  const refreshStatus = useCallback(async (): Promise<'verified' | 'failed' | 'pending'> => {
    const { data, error: statusError } = await verificationStatusEndpointVerifyStatusGet();
    if (statusError || !data) return 'pending';
    if (data.status === 'verified') {
      setState({ kind: 'verified' });
      return 'verified';
    }
    if (data.status === 'failed' || data.status === 'revoked') {
      return 'failed';
    }
    return 'pending';
  }, []);

  const startVerification = useCallback(async () => {
    setError(null);
    setState({ kind: 'checking' });

    const { data, error: startError } = await startVerificationEndpointVerifyStartPost({
      body: { method: 'age_estimation' },
    });

    if (startError || !data) {
      setError('Could not start verification. Try again.');
      setState({ kind: 'unverified' });
      return;
    }

    if (data.status === 'waitlisted') {
      setState({ kind: 'waitlisted' });
      return;
    }

    if (!data.session_token) {
      setError('Could not start verification. Try again.');
      setState({ kind: 'unverified' });
      return;
    }

    const result = await startDiditVerification(data.session_token, {
      showCloseButton: true,
    });

    if (result.type !== 'completed') {
      setState({ kind: 'unverified' });
      return;
    }

    // Didit's webhook may not have landed yet: the SDK completing only means
    // the user finished the flow, not that the server has a terminal result.
    // Poll with backoff and only give up (unverified) on an explicit failed/
    // revoked result - a still-pending or transiently-failing status check
    // keeps the UI in 'checking' rather than dropping the user back to start.
    const retryDelaysMs = [1000, 2000, 4000, 8000, 8000];
    for (const delayMs of retryDelaysMs) {
      const outcome = await refreshStatus();
      if (outcome === 'verified') return;
      if (outcome === 'failed') {
        setState({ kind: 'unverified' });
        return;
      }
      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }
    // Still pending after all retries - leave state as 'checking' rather
    // than misreporting 'unverified'; refreshStatus can be called again
    // (e.g. on screen focus) to keep polling for the eventual result.
  }, [refreshStatus]);

  return { state, error, startVerification, refreshStatus };
}
