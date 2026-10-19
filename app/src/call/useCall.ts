import { useCallback, useEffect, useRef, useState } from 'react';
import {
  MediaStream,
  type MediaStreamTrack,
  mediaDevices,
  RTCIceCandidate,
  RTCPeerConnection,
  type RTCRtpTransceiver,
  RTCSessionDescription,
} from 'react-native-webrtc';
import { ICE_BREAKERS } from '../content/iceBreakers';
import {
  type GamePrompt,
  type GameType,
  type IceServer,
  type OutgoingMessage,
  SignalingClient,
  signalingWsUrl,
} from './signaling';

export type CallStatus = 'connecting' | 'waiting_for_peer' | 'in_call' | 'ended' | 'failed';

/** Whether peer-to-peer media (audio/video) is flowing; chat works regardless. */
export type MediaState = 'connecting' | 'connected' | 'failed';

type TrackKind = 'audio' | 'video';

/** Why turning the mic/camera on didn't happen, so the UI can say what to do. */
export type ToggleResult = 'ok' | 'not_eligible' | 'blocked' | 'not_ready';

// The partner never reaching the signaling socket (app killed, crashed after
// the match) would otherwise leave this side on "Connecting…" forever.
const PEER_JOIN_TIMEOUT_MS = 20000;

// react-native-webrtc only emits a remote video track's first mute/unmute
// after ~3s of watching for frames, so its initial `muted` can't be trusted.
const REMOTE_VIDEO_SETTLE_MS = 3500;

async function getTrack(kind: TrackKind): Promise<MediaStreamTrack | null> {
  try {
    const stream = await mediaDevices.getUserMedia({
      audio: kind === 'audio',
      video: kind === 'video',
    });
    return stream.getTracks()[0] ?? null;
  } catch {
    // Permission denied or no device: that medium stays off, the call goes on.
    return null;
  }
}

export type ChatEntry = {
  id: string;
  fromSelf: boolean;
  text: string;
  kind: 'chat' | 'ice_breaker';
};

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
 * starts enabled if the mic is available (it's optional, like video); video
 * starts disabled and can only be turned on after a
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
  const [remoteVideoActive, setRemoteVideoActive] = useState(false);
  const [mediaState, setMediaState] = useState<MediaState>('connecting');
  const [videoEnabled, setVideoEnabled] = useState(false);
  const [videoEligible, setVideoEligible] = useState(initialVideoEligible);
  const [audioEnabled, setAudioEnabled] = useState(true);
  const [chatLog, setChatLog] = useState<ChatEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [gameInvite, setGameInvite] = useState<{ gameType: GameType; fromSelf: boolean } | null>(
    null,
  );
  const [activeGame, setActiveGame] = useState<{
    gameType: GameType;
    prompt: GamePrompt;
    revealed: boolean;
  } | null>(null);

  const signalingRef = useRef<SignalingClient | null>(null);
  const peerConnectionRef = useRef<RTCPeerConnection | null>(null);
  const pendingCandidatesRef = useRef<RTCIceCandidate[]>([]);
  const remoteDescriptionSetRef = useRef(false);
  const localStreamRef = useRef<MediaStream | null>(null);
  const remoteStreamRef = useRef<MediaStream | null>(null);
  // One sendrecv transceiver per kind, negotiated up front so turning the mic or
  // camera on later is a replaceTrack (no renegotiation, so no offer glare).
  const transceiversRef = useRef<Partial<Record<TrackKind, RTCRtpTransceiver>>>({});
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
    setChatLog((log) => [...log, { id: makeChatEntryId(), fromSelf: true, text, kind: 'chat' }]);
  }, []);

  // Shown-prompt dedup for the current call only (tasks/ice-breaker.md) -
  // resets every new match since this hook is torn down with CallScreen.
  const shownIceBreakersRef = useRef<Set<string>>(new Set());

  const sendIceBreaker = useCallback(() => {
    if (!signalingRef.current) return;
    let pool: readonly string[] = ICE_BREAKERS.filter(
      (prompt) => !shownIceBreakersRef.current.has(prompt),
    );
    if (pool.length === 0) {
      shownIceBreakersRef.current.clear();
      pool = ICE_BREAKERS;
    }
    const text = pool[Math.floor(Math.random() * pool.length)];
    if (!text) return;
    shownIceBreakersRef.current.add(text);

    const message: OutgoingMessage = { type: 'ice_breaker', text };
    signalingRef.current.send(message);
    setChatLog((log) => [
      ...log,
      { id: makeChatEntryId(), fromSelf: true, text, kind: 'ice_breaker' },
    ]);
  }, []);

  const startGame = useCallback((gameType: GameType) => {
    if (!signalingRef.current) return;
    signalingRef.current.send({ type: 'game_start', game_type: gameType });
    setGameInvite({ gameType, fromSelf: true });
  }, []);

  const acceptGame = useCallback(() => {
    if (!signalingRef.current) return;
    signalingRef.current.send({ type: 'game_accept' });
    setGameInvite(null);
  }, []);

  const declineGame = useCallback(() => {
    if (!signalingRef.current) return;
    signalingRef.current.send({ type: 'game_decline' });
    setGameInvite(null);
  }, []);

  const nextGamePrompt = useCallback(() => {
    signalingRef.current?.send({ type: 'game_next' });
  }, []);

  const revealGamePrompt = useCallback(() => {
    signalingRef.current?.send({ type: 'game_reveal' });
  }, []);

  const closeGame = useCallback(() => {
    signalingRef.current?.send({ type: 'game_close' });
    setActiveGame(null);
    setGameInvite(null);
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

  /** Returns the outcome (fresh eligibility, camera permission) so callers can
   * react immediately, without depending on state that may not have re-rendered yet. */
  const toggleVideo = useCallback(async (): Promise<ToggleResult> => {
    const stream = localStreamRef.current;
    const sender = transceiversRef.current.video?.sender;
    if (videoEnabled) {
      // Stop the camera, not just disable the track: the partner's side sees
      // the track go quiet, and the camera indicator turns off.
      setVideoEnabled(false);
      await sender?.replaceTrack(null);
      stream?.getVideoTracks().forEach((track) => {
        track.stop();
        stream.removeTrack(track);
      });
      return 'ok';
    }

    let eligible: boolean;
    try {
      eligible = await requestFreshVideoEligibility();
    } catch {
      return 'not_eligible';
    }
    setVideoEligible(eligible);
    if (!eligible) return 'not_eligible';
    // Media not negotiated yet (tapped right as the call connects).
    if (!stream || !sender) return 'not_ready';

    const videoTrack = await getTrack('video');
    if (!videoTrack) return 'blocked';
    await sender.replaceTrack(videoTrack);
    stream.addTrack(videoTrack);
    setVideoEnabled(true);
    return 'ok';
  }, [videoEnabled, requestFreshVideoEligibility]);

  const toggleAudio = useCallback(async (): Promise<ToggleResult> => {
    const stream = localStreamRef.current;
    const [existing] = stream?.getAudioTracks() ?? [];
    if (existing) {
      existing.enabled = !existing.enabled;
      setAudioEnabled(existing.enabled);
      return 'ok';
    }
    // No mic yet (denied at call start): ask again.
    const sender = transceiversRef.current.audio?.sender;
    if (!stream || !sender) return 'not_ready';
    const audioTrack = await getTrack('audio');
    if (!audioTrack) return 'blocked';
    await sender.replaceTrack(audioTrack);
    stream.addTrack(audioTrack);
    setAudioEnabled(true);
    return 'ok';
  }, []);

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
    remoteStreamRef.current = null;
    transceiversRef.current = {};
    setRemoteStream(null);
    setRemoteVideoActive(false);
    setGameInvite(null);
    setActiveGame(null);
    setStatus('ended');
  }, [settleVideoStatusRequest]);

  useEffect(() => {
    let cancelled = false;
    let stream: MediaStream | null = null;
    let signaling: SignalingClient | null = null;
    let peerJoinTimer: ReturnType<typeof setTimeout> | null = null;

    async function setup() {
      try {
        // Audio-only initial capture - video is never requested from the OS
        // until toggleVideo clears a fresh server-side eligibility check. No
        // mic (denied) still joins the call: chat, and hearing the partner.
        const audioTrack = await getTrack('audio');
        stream = new MediaStream(audioTrack ? [audioTrack] : undefined);
        if (!audioTrack) setAudioEnabled(false);
        if (cancelled) {
          stream.getTracks().forEach((track) => {
            track.stop();
          });
          return;
        }
        localStreamRef.current = stream;
        setLocalStream(stream);

        signaling = new SignalingClient(signalingWsUrl(apiBaseUrl, callId), sessionToken);
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

        if (isInitiator) {
          // The answerer adopts these transceivers when it applies the offer.
          const [audioTrack] = activeStream.getAudioTracks();
          const init = { direction: 'sendrecv', streams: [activeStream] };
          transceiversRef.current = {
            audio: pc.addTransceiver(audioTrack ?? 'audio', init),
            video: pc.addTransceiver('video', init),
          };
        }

        pc.oniceconnectionstatechange = () => {
          const state = pc.iceConnectionState;
          if (state === 'connected' || state === 'completed') setMediaState('connected');
          else if (state === 'failed') setMediaState('failed');
        };

        pc.ontrack = (event: { track: MediaStreamTrack | null; streams: MediaStream[] }) => {
          const { track } = event;
          if (!track) return;
          // Tracks on the answerer's adopted transceivers arrive without a
          // stream, so collect everything into one remote stream.
          const remote = remoteStreamRef.current ?? event.streams[0] ?? new MediaStream();
          remoteStreamRef.current = remote;
          if (!remote.getTracks().some((t) => t.id === track.id)) remote.addTrack(track);
          setRemoteStream(remote);

          if (track.kind === 'video') {
            const update = () => setRemoteVideoActive(!track.muted);
            track.onmute = update;
            track.onunmute = update;
            setTimeout(() => {
              if (remoteStreamRef.current === remote) update();
            }, REMOTE_VIDEO_SETTLE_MS);
          }
        };

        pc.onicecandidate = (event: { candidate: RTCIceCandidate | null }) => {
          if (event.candidate) {
            activeSignaling.send({ type: 'ice_candidate', candidate: event.candidate.toJSON() });
          }
        };
      };

      activeSignaling.onPeerJoined = async () => {
        if (peerJoinTimer) clearTimeout(peerJoinTimer);
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

      activeSignaling.onGameEvent = (event) => {
        if (event.type === 'game_invite') {
          setGameInvite({ gameType: event.game_type, fromSelf: false });
        } else if (event.type === 'game_declined') {
          setGameInvite(null);
        } else if (event.type === 'game_started') {
          setGameInvite(null);
          setActiveGame({
            gameType: event.game_type,
            prompt: { ...event.prompt, correct_option: null },
            revealed: false,
          });
        } else if (event.type === 'game_prompt') {
          setActiveGame((current) =>
            current
              ? {
                  ...current,
                  prompt: { ...event.prompt, correct_option: null },
                  revealed: event.revealed,
                }
              : current,
          );
        } else if (event.type === 'game_revealed') {
          setActiveGame((current) =>
            current
              ? {
                  ...current,
                  revealed: true,
                  prompt: { ...current.prompt, correct_option: event.correct_option },
                }
              : current,
          );
        } else if (event.type === 'game_closed') {
          setActiveGame(null);
          setGameInvite(null);
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
          if (!transceiversRef.current.audio) {
            // Adopt the initiator's audio/video transceivers as sendrecv, so
            // this side can send on them later without renegotiating.
            const adopted: Partial<Record<TrackKind, RTCRtpTransceiver>> = {};
            for (const transceiver of pc.getTransceivers()) {
              const kind = transceiver.receiver.track?.kind;
              if (kind !== 'audio' && kind !== 'video') continue;
              transceiver.direction = 'sendrecv';
              adopted[kind] = transceiver;
            }
            transceiversRef.current = adopted;
            const [audioTrack] = activeStream.getAudioTracks();
            if (audioTrack) await adopted.audio?.sender.replaceTrack(audioTrack);
          }
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
            { id: makeChatEntryId(), fromSelf: false, text: message.text, kind: 'chat' },
          ]);
        } else if (message.type === 'ice_breaker') {
          setChatLog((log) => [
            ...log,
            { id: makeChatEntryId(), fromSelf: false, text: message.text, kind: 'ice_breaker' },
          ]);
        }
      };

      setStatus('waiting_for_peer');
      peerJoinTimer = setTimeout(() => {
        if (signalingRef.current === activeSignaling) {
          endCall();
          setStatus('failed');
        }
      }, PEER_JOIN_TIMEOUT_MS);
    }

    setup();

    return () => {
      cancelled = true;
      if (peerJoinTimer) clearTimeout(peerJoinTimer);
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
    remoteVideoActive,
    mediaState,
    videoEnabled,
    videoEligible,
    audioEnabled,
    chatLog,
    sendChat,
    sendIceBreaker,
    gameInvite,
    activeGame,
    startGame,
    acceptGame,
    declineGame,
    nextGamePrompt,
    revealGamePrompt,
    closeGame,
    toggleVideo,
    toggleAudio,
    endCall,
  };
}
