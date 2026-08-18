export type IceServer = {
  urls: string[];
  username?: string | null;
  credential?: string | null;
};

export type TurnCredentialsMessage = {
  ice_servers: IceServer[];
};

export type OfferMessage = { type: 'offer'; sdp: string };
export type AnswerMessage = { type: 'answer'; sdp: string };
export type IceCandidateMessage = { type: 'ice_candidate'; candidate: RTCIceCandidateInit };
export type ChatMessage = { type: 'chat'; text: string };
export type IceBreakerMessage = { type: 'ice_breaker'; text: string };
export type VideoStatusRequestMessage = { type: 'video_status_request' };
export type PeerJoinedEvent = { type: 'peer_joined' };
export type PeerLeftEvent = { type: 'peer_left' };
export type VideoStatusEvent = { type: 'video_status'; video_eligible: boolean };
export type ErrorEvent = { type: 'error'; detail: string };

export type RelayedMessage =
  | OfferMessage
  | AnswerMessage
  | IceCandidateMessage
  | ChatMessage
  | IceBreakerMessage;

// --- Mini-games (tasks/mini-games.md) - structured control data relayed
// over this same always-on channel, but handled server-side (session state,
// prompt picking) rather than blindly relayed like RelayedMessage. ---

export type GameType = 'trivia' | 'would_you_rather' | 'never_have_i_ever';

export type GamePrompt = {
  id: string;
  game_type: GameType;
  text: string;
  options: string[] | null;
  // Trivia's answer. Absent on the wire until reveal (server omits it from
  // GameStartedEvent/GamePromptEvent) - populated client-side from
  // GameRevealedEvent's correct_option once the round is revealed.
  correct_option: string | null;
};

type WirePrompt = Omit<GamePrompt, 'correct_option'>;

export type GameStartMessage = { type: 'game_start'; game_type: GameType };
export type GameAcceptMessage = { type: 'game_accept' };
export type GameDeclineMessage = { type: 'game_decline' };
export type GameNextMessage = { type: 'game_next' };
export type GameRevealMessage = { type: 'game_reveal' };
export type GameCloseMessage = { type: 'game_close' };

export type OutgoingGameMessage =
  | GameStartMessage
  | GameAcceptMessage
  | GameDeclineMessage
  | GameNextMessage
  | GameRevealMessage
  | GameCloseMessage;

export type GameInviteEvent = { type: 'game_invite'; game_type: GameType; from_user_id: string };
export type GameDeclinedEvent = { type: 'game_declined' };
export type GameStartedEvent = {
  type: 'game_started';
  game_type: GameType;
  prompt: WirePrompt;
};
export type GamePromptEvent = { type: 'game_prompt'; prompt: WirePrompt; revealed: boolean };
export type GameRevealedEvent = { type: 'game_revealed'; correct_option: string | null };
export type GameClosedEvent = { type: 'game_closed' };

export type IncomingGameEvent =
  | GameInviteEvent
  | GameDeclinedEvent
  | GameStartedEvent
  | GamePromptEvent
  | GameRevealedEvent
  | GameClosedEvent;

export type OutgoingMessage = RelayedMessage | VideoStatusRequestMessage | OutgoingGameMessage;

export type RelayEnvelope = {
  from_user_id: string;
  message: RelayedMessage;
};

export type IncomingMessage =
  | TurnCredentialsMessage
  | PeerJoinedEvent
  | PeerLeftEvent
  | VideoStatusEvent
  | ErrorEvent
  | RelayEnvelope
  | IncomingGameEvent;

const GAME_EVENT_TYPES = new Set<string>([
  'game_invite',
  'game_declined',
  'game_started',
  'game_prompt',
  'game_revealed',
  'game_closed',
]);

function isGameEvent(msg: unknown): msg is IncomingGameEvent {
  return (
    typeof msg === 'object' &&
    msg !== null &&
    typeof (msg as { type?: unknown }).type === 'string' &&
    GAME_EVENT_TYPES.has((msg as { type: string }).type)
  );
}

function isRelayedMessage(msg: unknown): msg is RelayedMessage {
  if (typeof msg !== 'object' || msg === null) return false;
  const candidate = msg as Partial<RelayedMessage>;
  switch (candidate.type) {
    case 'offer':
    case 'answer':
      return typeof (candidate as OfferMessage | AnswerMessage).sdp === 'string';
    case 'ice_candidate':
      return (
        typeof (candidate as IceCandidateMessage).candidate === 'object' &&
        (candidate as IceCandidateMessage).candidate !== null
      );
    case 'chat':
      return typeof (candidate as ChatMessage).text === 'string';
    case 'ice_breaker':
      return typeof (candidate as IceBreakerMessage).text === 'string';
    default:
      return false;
  }
}

function isRelayEnvelope(msg: unknown): msg is RelayEnvelope {
  return (
    typeof msg === 'object' &&
    msg !== null &&
    'message' in msg &&
    'from_user_id' in msg &&
    typeof (msg as RelayEnvelope).from_user_id === 'string' &&
    isRelayedMessage((msg as RelayEnvelope).message)
  );
}

function isTurnCredentials(msg: unknown): msg is TurnCredentialsMessage {
  return (
    typeof msg === 'object' &&
    msg !== null &&
    Array.isArray((msg as TurnCredentialsMessage).ice_servers)
  );
}

export { isRelayEnvelope, isTurnCredentials };

export function signalingWsUrl(baseUrl: string, sessionToken: string, callId: string): string {
  const wsBase = baseUrl.replace(/^http/, 'ws');
  return `${wsBase}/signaling/ws?token=${encodeURIComponent(sessionToken)}&call_id=${encodeURIComponent(callId)}`;
}

export class SignalingClient {
  private ws: WebSocket;

  onTurnCredentials: ((creds: TurnCredentialsMessage) => void) | null = null;
  onPeerJoined: (() => void) | null = null;
  onPeerLeft: (() => void) | null = null;
  onRelayed: ((from: string, message: RelayedMessage) => void) | null = null;
  onVideoStatus: ((videoEligible: boolean) => void) | null = null;
  onGameEvent: ((event: IncomingGameEvent) => void) | null = null;
  onError: ((detail: string) => void) | null = null;
  onClose: (() => void) | null = null;

  constructor(url: string) {
    this.ws = new WebSocket(url);
    this.ws.onmessage = (event) => this.handleMessage(event.data);
    this.ws.onclose = () => this.onClose?.();
  }

  private handleMessage(raw: string) {
    let msg: unknown;
    try {
      msg = JSON.parse(raw);
    } catch {
      return;
    }
    if (typeof msg !== 'object' || msg === null) return;

    if (isTurnCredentials(msg)) {
      this.onTurnCredentials?.(msg);
      return;
    }
    if (isRelayEnvelope(msg)) {
      this.onRelayed?.(msg.from_user_id, msg.message);
      return;
    }
    const typed = msg as IncomingMessage & { type?: string; detail?: string };
    if (typed.type === 'peer_joined') {
      this.onPeerJoined?.();
      return;
    }
    if (typed.type === 'peer_left') {
      this.onPeerLeft?.();
      return;
    }
    if (
      typed.type === 'video_status' &&
      typeof (typed as VideoStatusEvent).video_eligible === 'boolean'
    ) {
      this.onVideoStatus?.((typed as VideoStatusEvent).video_eligible);
      return;
    }
    if (isGameEvent(msg)) {
      this.onGameEvent?.(msg);
      return;
    }
    if (typed.type === 'error' && typeof typed.detail === 'string') {
      this.onError?.(typed.detail);
    }
  }

  waitUntilOpen(): Promise<void> {
    if (this.ws.readyState === WebSocket.OPEN) return Promise.resolve();
    if (this.ws.readyState === WebSocket.CLOSING || this.ws.readyState === WebSocket.CLOSED) {
      return Promise.reject(new Error('signaling connection closed'));
    }
    return new Promise((resolve, reject) => {
      this.ws.addEventListener('open', () => resolve(), { once: true });
      this.ws.addEventListener('error', () => reject(new Error('signaling connection failed')), {
        once: true,
      });
      this.ws.addEventListener('close', () => reject(new Error('signaling connection closed')), {
        once: true,
      });
    });
  }

  send(message: OutgoingMessage): void {
    this.ws.send(JSON.stringify(message));
  }

  close(): void {
    this.ws.close();
  }
}
