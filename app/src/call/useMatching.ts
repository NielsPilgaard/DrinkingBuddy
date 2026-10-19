import { useCallback, useEffect, useRef, useState } from 'react';
import type { Filters } from './filters';
import { authedWebSocket } from './signaling';

export type MatchingStatus =
  | 'idle'
  | 'waiting'
  | 'widen_prompt'
  | 'matched'
  | 'suspended'
  | 'unauthenticated';

const UNAUTHENTICATED_CLOSE_CODE = 4401;
const SUSPENDED_CLOSE_CODE = 4403;

export type MatchResult = {
  partnerId: string;
  callId: string;
  isInitiator: boolean;
  videoEligible: boolean;
};

function matchingWsUrl(apiBaseUrl: string): string {
  return `${apiBaseUrl.replace(/^http/, 'ws')}/matching/ws`;
}

/**
 * Drives the matching queue websocket up to the point of a match, then hands
 * off (call_id, partner_id) for useCall to take over signaling. Whichever
 * user id sorts first is the offer initiator — both sides derive this the
 * same way the backend derives call_id, so no extra round trip is needed.
 */
export function useMatching(apiBaseUrl: string, sessionToken: string, userId: string) {
  const [status, setStatus] = useState<MatchingStatus>('idle');
  const [match, setMatch] = useState<MatchResult | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  // What we're queued with, so a dropped socket (API restart, network blip) can
  // rejoin. Null when not queued: idle, or matched and in a call.
  const queuedRef = useRef<{ filters: Filters; widen: boolean } | null>(null);
  const retryRef = useRef<{ attempt: number; timer: ReturnType<typeof setTimeout> | null }>({
    attempt: 0,
    timer: null,
  });

  const connect = useCallback(
    (filters: Filters, widen: boolean) => {
      if (retryRef.current.timer) clearTimeout(retryRef.current.timer);
      retryRef.current.timer = null;
      queuedRef.current = { filters, widen };
      // Drop the previous match now: left in place until the server's 'waiting'
      // arrives, it re-renders the old call and reopens its signaling socket.
      setMatch(null);
      setStatus('waiting');
      const previous = wsRef.current;
      wsRef.current = null;
      previous?.close();

      const ws = authedWebSocket(matchingWsUrl(apiBaseUrl), sessionToken);
      wsRef.current = ws;
      ws.onopen = () => {
        ws.send(JSON.stringify({ type: 'join', filters, widen_search: widen }));
      };
      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === 'waiting') {
          retryRef.current.attempt = 0;
          setStatus('waiting');
        } else if (msg.type === 'widen_search_prompt') {
          setStatus('widen_prompt');
        } else if (msg.type === 'matched') {
          queuedRef.current = null;
          setStatus('matched');
          setMatch({
            partnerId: msg.partner_id,
            callId: msg.call_id,
            isInitiator: userId < msg.partner_id,
            videoEligible: msg.video_eligible,
          });
        }
      };
      ws.onclose = (event) => {
        if (wsRef.current !== ws) return;
        wsRef.current = null;
        if (event.code === SUSPENDED_CLOSE_CODE || event.code === UNAUTHENTICATED_CLOSE_CODE) {
          queuedRef.current = null;
          setStatus(event.code === SUSPENDED_CLOSE_CODE ? 'suspended' : 'unauthenticated');
          return;
        }
        const queued = queuedRef.current;
        if (!queued) return;
        // Dropped while queueing: rejoin with backoff instead of showing
        // "Looking for a match…" forever.
        const delay = Math.min(1000 * 2 ** retryRef.current.attempt, 15000);
        retryRef.current.attempt += 1;
        retryRef.current.timer = setTimeout(() => connect(queued.filters, queued.widen), delay);
      };
    },
    [apiBaseUrl, sessionToken, userId],
  );

  const join = useCallback((filters: Filters) => connect(filters, false), [connect]);

  const widenSearch = useCallback(
    (filters: Filters) => {
      const ws = wsRef.current;
      if (ws?.readyState === WebSocket.OPEN) {
        queuedRef.current = { filters, widen: true };
        ws.send(JSON.stringify({ type: 'join', filters, widen_search: true }));
      } else {
        connect(filters, true);
      }
      setStatus('waiting');
    },
    [connect],
  );

  const skip = useCallback(() => {
    wsRef.current?.send(JSON.stringify({ type: 'skip' }));
    setStatus('waiting');
    setMatch(null);
  }, []);

  const leave = useCallback(() => {
    queuedRef.current = null;
    if (retryRef.current.timer) clearTimeout(retryRef.current.timer);
    retryRef.current.timer = null;
    const ws = wsRef.current;
    wsRef.current = null;
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'leave' }));
    }
    ws?.close();
    setStatus('idle');
    setMatch(null);
  }, []);

  useEffect(() => leave, [leave]);

  return { status, match, join, widenSearch, skip, leave };
}
