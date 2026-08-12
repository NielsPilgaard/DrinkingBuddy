import { useCallback, useEffect, useRef, useState } from 'react';

export type Filters = {
  language: string;
  drink_type: 'alcoholic' | 'non_alcoholic';
  location: string;
};

export type MatchingStatus = 'idle' | 'waiting' | 'widen_prompt' | 'matched' | 'suspended';

const SUSPENDED_CLOSE_CODE = 4403;

export type MatchResult = {
  partnerId: string;
  callId: string;
  isInitiator: boolean;
  videoEligible: boolean;
};

function matchingWsUrl(apiBaseUrl: string, sessionToken: string): string {
  const wsBase = apiBaseUrl.replace(/^http/, 'ws');
  return `${wsBase}/matching/ws?token=${encodeURIComponent(sessionToken)}`;
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

  const join = useCallback(
    (filters: Filters) => {
      wsRef.current?.close();

      const ws = new WebSocket(matchingWsUrl(apiBaseUrl, sessionToken));
      wsRef.current = ws;
      ws.onopen = () => {
        ws.send(JSON.stringify({ type: 'join', filters }));
      };
      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === 'waiting') {
          setStatus('waiting');
        } else if (msg.type === 'widen_search_prompt') {
          setStatus('widen_prompt');
        } else if (msg.type === 'matched') {
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
        if (event.code === SUSPENDED_CLOSE_CODE) {
          setStatus('suspended');
        }
      };
    },
    [apiBaseUrl, sessionToken, userId],
  );

  const widenSearch = useCallback((filters: Filters) => {
    wsRef.current?.send(JSON.stringify({ type: 'join', filters, widen_search: true }));
  }, []);

  const skip = useCallback(() => {
    wsRef.current?.send(JSON.stringify({ type: 'skip' }));
    setStatus('waiting');
    setMatch(null);
  }, []);

  const leave = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'leave' }));
    }
    wsRef.current?.close();
    wsRef.current = null;
    setStatus('idle');
    setMatch(null);
  }, []);

  useEffect(() => {
    return () => {
      wsRef.current?.close();
    };
  }, []);

  return { status, match, join, widenSearch, skip, leave };
}
