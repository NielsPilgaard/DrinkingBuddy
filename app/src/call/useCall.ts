import { useCallback, useEffect, useRef, useState } from 'react';
import {
  type MediaStream,
  mediaDevices,
  RTCIceCandidate,
  RTCPeerConnection,
  RTCSessionDescription,
} from 'react-native-webrtc';
import { type IceServer, type OutgoingMessage, SignalingClient, signalingWsUrl } from './signaling';

export type CallStatus = 'connecting' | 'waiting_for_peer' | 'in_call' | 'ended' | 'failed';

export type ChatEntry = { id: string; fromSelf: boolean; text: string };

let nextChatEntryId = 0;
function makeChatEntryId(): string {
  nextChatEntryId += 1;
  return `chat-${nextChatEntryId}`;
}

type UseCallOptions = {
  apiBaseUrl: string;
  sessionToken: string;
  callId: string;
  /** Whether this side should create the offer. Exactly one side must. */
  isInitiator: boolean;
  /** From the match-formed check (tasks/10-age-verification.md); video starts
   * off regardless, this only gates whether toggleVideo can ever turn it on. */
  initialVideoEligible: boolean;
};

/**
 * Wires signaling + RTCPeerConnection together for a single call. Audio
 * starts enabled; video starts disabled and can only be turned on after a
 * fresh server-side eligibility check (tasks/10-age-verification.md) both
 * at call start and on every toggle attempt - text chat always flows over
 * the signaling websocket, never a P2P datachannel, so the server can see
 * plaintext for the chat safety filters.
 */
export function useCall({
  apiBaseUrl,
  sessionToken,
  callId,
  isInitiator,
  initialVideoEligible,
}: UseCallOptions) {
  const [status, setStatus] = useState<CallStatus>('connecting');
  const [localStream, setLocalStream] = useState<MediaStream | null>(null);
  const [remoteStream, setRemoteStream] = useState<MediaStream | null>(null);
  const [videoEnabled, setVideoEnabled] = useState(false);
  const [videoEligible, setVideoEligible] = useState(initialVideoEligible);
  const [audioEnabled, setAudioEnabled] = useState(true);
  const [chatLog, setChatLog] = useState<ChatEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  const signalingRef = useRef<SignalingClient | null>(null);
  const peerConnectionRef = useRef<RTCPeerConnection | null>(null);
  const pendingCandidatesRef = useRef<RTCIceCandidate[]>([]);
  const remoteDescriptionSetRef = useRef(false);
  const localStreamRef = useRef<MediaStream | null>(null);
  const videoStatusRequestRef = useRef<{
    resolve: (eligible: boolean) => void;
    reject: (err: Error) => void;
    timeoutId: ReturnType<typeof setTimeout>;
  } | null>(null);

  const VIDEO_STATUS_REQUEST_TIMEOUT_MS = 8000;

  const settleVideoStatusRequest = useCallback((eligible: boolean | null, err?: Error) => {
    const pending = videoStatusRequestRef.current;
    if (!pending) return;
    videoStatusRequestRef.current = null;
    clearTimeout(pending.timeoutId);
    if (err) {
      pending.reject(err);
    } else {
      pending.resolve(eligible ?? false);
    }
  }, []);

  const sendChat = useCallback((text: string) => {
    if (!signalingRef.current) return;
    const message: OutgoingMessage = { type: 'chat', text };
    signalingRef.current.send(message);
    setChatLog((log) => [...log, { id: makeChatEntryId(), fromSelf: true, text }]);
  }, []);

  const requestFreshVideoEligibility = useCallback((): Promise<boolean> => {
    const signaling = signalingRef.current;
    if (!signaling) return Promise.resolve(false);
    if (videoStatusRequestRef.current) {
      return Promise.reject(new Error('A video eligibility request is already in flight'));
    }
    return new Promise((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        settleVideoStatusRequest(null, new Error('video eligibility request timed out'));
      }, VIDEO_STATUS_REQUEST_TIMEOUT_MS);
      videoStatusRequestRef.current = { resolve, reject, timeoutId };
      signaling.send({ type: 'video_status_request' });
    });
  }, [settleVideoStatusRequest]);

  /** Returns the fresh eligibility result so callers can react immediately,
   * without depending on state that may not have re-rendered yet. */
  const toggleVideo = useCallback(async (): Promise<boolean> => {
    if (videoEnabled) {
      setVideoEnabled(false);
      localStream?.getVideoTracks().forEach((track) => {
        track.enabled = false;
      });
      return true;
    }

    let eligible: boolean;
    try {
      eligible = await requestFreshVideoEligibility();
    } catch {
      return false;
    }
    setVideoEligible(eligible);
    if (!eligible) return false;

    const stream = localStreamRef.current;
    if (!stream) return false;
    if (stream.getVideoTracks().length === 0) {
      const videoStream = await mediaDevices.getUserMedia({ audio: false, video: true });
      const [videoTrack] = videoStream.getVideoTracks();
      if (videoTrack) {
        stream.addTrack(videoTrack);
        peerConnectionRef.current?.addTrack(videoTrack, stream);
      }
    }
    stream.getVideoTracks().forEach((track) => {
      track.enabled = true;
    });
    setVideoEnabled(true);
    return true;
  }, [videoEnabled, localStream, requestFreshVideoEligibility]);

  const toggleAudio = useCallback(() => {
    setAudioEnabled((enabled) => {
      const next = !enabled;
      localStream?.getAudioTracks().forEach((track) => {
        track.enabled = next;
      });
      return next;
    });
  }, [localStream]);

  const endCall = useCallback(() => {
    settleVideoStatusRequest(null, new Error('call ended'));
    peerConnectionRef.current?.close();
    peerConnectionRef.current = null;
    signalingRef.current?.close();
    signalingRef.current = null;
    localStreamRef.current?.getTracks().forEach((track) => {
      track.stop();
    });
    localStreamRef.current = null;
    setLocalStream(null);
    setRemoteStream(null);
    setStatus('ended');
  }, [settleVideoStatusRequest]);

  useEffect(() => {
    let cancelled = false;
    let stream: MediaStream | null = null;
    let signaling: SignalingClient | null = null;

    async function setup() {
      try {
        // Audio-only initial capture - video is never requested from the OS
        // until toggleVideo clears a fresh server-side eligibility check.
        stream = await mediaDevices.getUserMedia({ audio: true, video: false });
        if (cancelled) {
          stream.getTracks().forEach((track) => {
            track.stop();
          });
          return;
        }
        localStreamRef.current = stream;
        setLocalStream(stream);

        signaling = new SignalingClient(signalingWsUrl(apiBaseUrl, sessionToken, callId));
        signalingRef.current = signaling;
        await signaling.waitUntilOpen();
        if (cancelled) return;
      } catch (err) {
        stream?.getTracks().forEach((track) => {
          track.stop();
        });
        if (stream === localStreamRef.current) localStreamRef.current = null;
        signaling?.close();
        if (signaling === signalingRef.current) signalingRef.current = null;
        if (!cancelled) {
          setLocalStream(null);
          setError(err instanceof Error ? err.message : 'Failed to start call');
          setStatus('failed');
        }
        return;
      }

      const activeStream = stream;
      const activeSignaling = signaling;

      activeSignaling.onTurnCredentials = (creds) => {
        const iceServers = creds.ice_servers.map((server: IceServer) => ({
          urls: server.urls,
          username: server.username ?? undefined,
          credential: server.credential ?? undefined,
        }));
        const pc = new RTCPeerConnection({ iceServers });
        peerConnectionRef.current = pc;

        activeStream.getTracks().forEach((track) => {
          pc.addTrack(track, activeStream);
        });

        pc.ontrack = (event: { streams: MediaStream[] }) => {
          setRemoteStream(event.streams[0] ?? null);
        };

        pc.onicecandidate = (event: { candidate: RTCIceCandidate | null }) => {
          if (event.candidate) {
            activeSignaling.send({ type: 'ice_candidate', candidate: event.candidate.toJSON() });
          }
        };
      };

      activeSignaling.onPeerJoined = async () => {
        setStatus('in_call');
        const pc = peerConnectionRef.current;
        if (!pc || !isInitiator) return;
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);
        activeSignaling.send({ type: 'offer', sdp: offer.sdp ?? '' });
      };

      activeSignaling.onPeerLeft = () => {
        endCall();
      };

      activeSignaling.onClose = () => {
        if (signalingRef.current !== activeSignaling) return;
        endCall();
        setStatus('failed');
      };

      activeSignaling.onVideoStatus = (eligible) => {
        if (videoStatusRequestRef.current) {
          settleVideoStatusRequest(eligible);
        } else {
          // Unsolicited status push (none today, but harmless to reflect).
          setVideoEligible(eligible);
        }
      };

      activeSignaling.onRelayed = async (_from, message) => {
        const pc = peerConnectionRef.current;
        if (!pc) return;

        if (message.type === 'offer') {
          await pc.setRemoteDescription(
            new RTCSessionDescription({ type: 'offer', sdp: message.sdp }),
          );
          remoteDescriptionSetRef.current = true;
          for (const candidate of pendingCandidatesRef.current.splice(0)) {
            await pc.addIceCandidate(candidate);
          }
          const answer = await pc.createAnswer();
          await pc.setLocalDescription(answer);
          activeSignaling.send({ type: 'answer', sdp: answer.sdp ?? '' });
        } else if (message.type === 'answer') {
          await pc.setRemoteDescription(
            new RTCSessionDescription({ type: 'answer', sdp: message.sdp }),
          );
          remoteDescriptionSetRef.current = true;
          for (const candidate of pendingCandidatesRef.current.splice(0)) {
            await pc.addIceCandidate(candidate);
          }
        } else if (message.type === 'ice_candidate') {
          const candidate = new RTCIceCandidate(message.candidate);
          if (remoteDescriptionSetRef.current) {
            await pc.addIceCandidate(candidate);
          } else {
            pendingCandidatesRef.current.push(candidate);
          }
        } else if (message.type === 'chat') {
          setChatLog((log) => [
            ...log,
            { id: makeChatEntryId(), fromSelf: false, text: message.text },
          ]);
        }
      };

      setStatus('waiting_for_peer');
    }

    setup();

    return () => {
      cancelled = true;
      peerConnectionRef.current?.close();
      peerConnectionRef.current = null;
      signalingRef.current?.close();
      signalingRef.current = null;
      localStreamRef.current?.getTracks().forEach((track) => {
        track.stop();
      });
      localStreamRef.current = null;
    };
  }, [apiBaseUrl, sessionToken, callId, isInitiator, endCall, settleVideoStatusRequest]);

  return {
    status,
    error,
    localStream,
    remoteStream,
    videoEnabled,
    videoEligible,
    audioEnabled,
    chatLog,
    sendChat,
    toggleVideo,
    toggleAudio,
    endCall,
  };
}
