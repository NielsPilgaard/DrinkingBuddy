import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Alert,
  BackHandler,
  KeyboardAvoidingView,
  LayoutAnimation,
  Linking,
  Platform,
  Pressable,
  StatusBar,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { RTCView } from 'react-native-webrtc';
import { CallSheet } from '../call/CallSheet';
import { ChatSheet } from '../call/ChatSheet';
import { DRINK_ICONS, type DrinkType } from '../call/DrinkCounter';
import type { Language } from '../call/filters';
import { GameSheet } from '../call/GameSheet';
import { MenuSheet } from '../call/MenuSheet';
import { blockUser } from '../call/moderation';
import { ReportBlockSheet } from '../call/ReportBlockSheet';
import { useCall } from '../call/useCall';
import { colors } from '../theme';
import { useVerification } from '../verification/useVerification';

type CallScreenProps = {
  apiBaseUrl: string;
  sessionToken: string;
  callId: string;
  partnerId: string;
  isInitiator: boolean;
  videoEligible: boolean;
  drinkType: DrinkType;
  language: Language;
  /** Partner left, call failed, or the user hung up via "Leave call". */
  onCallEnded: () => void;
  /** User tapped Skip: the call is already ended, requeue straight away (PRD §4.3). */
  onSkip: () => void;
};

type Sheet = 'chat' | 'menu' | 'games' | 'verify';

// No safe-area library in the app: Android is edge-to-edge (SDK 57) and reports
// its status bar height; iOS notch devices sit around 47-59pt.
const TOP_INSET = Platform.OS === 'android' ? (StatusBar.currentHeight ?? 24) + 8 : 54;
// Video height below the status bar while a sheet is open (mockup: 200px incl. top bar).
const COLLAPSED_STAGE = 170;

// ~2dp per band keeps each opacity step under ~1%, too small to read as a stripe.
const SCRIM_BAND_HEIGHT = 2;
const SCRIM_MAX_OPACITY = 0.55;

/**
 * Top-down dark fade so the status bar and pills stay legible over bright video
 * (mockup .scrim-top). Stacked translucent bands stand in for a gradient: no
 * expo-linear-gradient, which is a native module and would need a new dev build.
 */
function TopScrim({ height }: { height: number }) {
  const bands = Math.ceil(height / SCRIM_BAND_HEIGHT);
  return (
    <View pointerEvents="none" style={[styles.scrim, { height }]}>
      {Array.from({ length: bands }, (_, i) => {
        // Ease-out (quadratic) so the fade has no visible hard edge at the bottom.
        const t = 1 - i / bands;
        return (
          <View
            // biome-ignore lint/suspicious/noArrayIndexKey: fixed-length static list
            key={i}
            style={{
              height: SCRIM_BAND_HEIGHT,
              backgroundColor: `rgba(0,0,0,${(SCRIM_MAX_OPACITY * t * t).toFixed(3)})`,
            }}
          />
        );
      })}
    </View>
  );
}

function formatDuration(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

export function CallScreen({
  apiBaseUrl,
  sessionToken,
  callId,
  partnerId,
  isInitiator,
  videoEligible,
  drinkType,
  language,
  onCallEnded,
  onSkip,
}: CallScreenProps) {
  const {
    status,
    localStream,
    remoteStream,
    remoteVideoActive,
    mediaState,
    videoEnabled,
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
  } = useCall({
    apiBaseUrl,
    sessionToken,
    callId,
    isInitiator,
    initialVideoEligible: videoEligible,
  });
  const verification = useVerification();

  const [sheet, setSheetState] = useState<Sheet | null>(null);
  const [reportOpen, setReportOpen] = useState(false);
  const [drinkCount, setDrinkCount] = useState(0);
  const [seenChatCount, setSeenChatCount] = useState(0);
  const [connectedAt, setConnectedAt] = useState<number | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const callEndedRef = useRef(false);
  const onCallEndedRef = useRef(onCallEnded);
  onCallEndedRef.current = onCallEnded;

  const setSheet = useCallback((next: Sheet | null) => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setSheetState(next);
  }, []);

  const notifyCallEnded = useCallback(() => {
    if (callEndedRef.current) return;
    callEndedRef.current = true;
    onCallEndedRef.current();
  }, []);

  function handleEndCall() {
    endCall();
    notifyCallEnded();
  }
  const handleEndCallRef = useRef(handleEndCall);
  handleEndCallRef.current = handleEndCall;

  function handleSkip() {
    if (callEndedRef.current) return;
    // Mark ended first so the status effect below doesn't also route to the
    // call-ended screen once useCall reports 'ended'.
    callEndedRef.current = true;
    endCall();
    onSkip();
  }

  function handleReportBlockDone() {
    setReportOpen(false);
    endCall();
    notifyCallEnded();
  }

  function handleBlock() {
    Alert.alert('Block this person?', "You won't be matched with them again.", [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Block',
        style: 'destructive',
        onPress: async () => {
          try {
            await blockUser(partnerId);
            handleReportBlockDone();
          } catch {
            Alert.alert('Something went wrong', 'Try again.');
          }
        },
      },
    ]);
  }

  useEffect(() => {
    if (status === 'ended' || status === 'failed') {
      notifyCallEnded();
    }
  }, [status, notifyCallEnded]);

  useEffect(() => {
    if (status === 'in_call' && connectedAt === null) setConnectedAt(Date.now());
  }, [status, connectedAt]);

  useEffect(() => {
    if (connectedAt === null) return;
    const interval = setInterval(
      () => setElapsed(Math.floor((Date.now() - connectedAt) / 1000)),
      1000,
    );
    return () => clearInterval(interval);
  }, [connectedAt]);

  // Everything in the log counts as read while the chat sheet is open.
  useEffect(() => {
    if (sheet === 'chat') setSeenChatCount(chatLog.length);
  }, [sheet, chatLog.length]);
  const hasUnread = chatLog.slice(seenChatCount).some((entry) => !entry.fromSelf);

  async function handleToggleVideo() {
    const result = await toggleVideo();
    if (result === 'not_eligible') setSheet('verify');
    else if (result === 'blocked') showBlockedAlert('Camera');
  }

  async function handleToggleAudio() {
    if ((await toggleAudio()) === 'blocked') showBlockedAlert('Microphone');
  }

  // Android back: close whatever sheet is open; with none open, confirm before
  // ending the call instead of letting back close the app mid-call.
  useEffect(() => {
    const subscription = BackHandler.addEventListener('hardwareBackPress', () => {
      if (reportOpen) {
        setReportOpen(false);
        return true;
      }
      if (sheet) {
        setSheet(null);
        return true;
      }
      Alert.alert('Leave this call?', undefined, [
        { text: 'Stay', style: 'cancel' },
        { text: 'Leave', style: 'destructive', onPress: handleEndCallRef.current },
      ]);
      return true;
    });
    return () => subscription.remove();
  }, [sheet, reportOpen, setSheet]);

  useEffect(() => {
    if (verification.state.kind === 'verified' && sheet === 'verify') {
      setSheet(null);
    }
  }, [verification.state, sheet, setSheet]);

  // Auto-open the game sheet for the receiving party's accept/decline prompt,
  // and keep it open through the synced round - tasks/completed/mini-games.md
  // requires the invite to surface without the receiver having tapped anything.
  useEffect(() => {
    if (gameInvite || activeGame) {
      setSheet('games');
    }
  }, [gameInvite, activeGame, setSheet]);

  const connected = status === 'in_call';
  const sheetOpen = sheet !== null;
  const placeholderCaption =
    status === 'connecting' || status === 'waiting_for_peer'
      ? 'Waiting for them to join…'
      : mediaState === 'failed'
        ? "Couldn't connect audio. Chat still works."
        : mediaState === 'connecting'
          ? 'Connecting audio…'
          : 'Camera off';

  return (
    // Android is edge-to-edge (SDK 57), so the window no longer resizes for the keyboard:
    // without this the chat input sits under it.
    <KeyboardAvoidingView style={styles.keyboardAvoider} behavior="padding">
      <View style={styles.container} testID="call-screen">
        <View style={[styles.stage, sheetOpen && { flex: 0, height: TOP_INSET + COLLAPSED_STAGE }]}>
          {remoteStream && remoteVideoActive ? (
            <RTCView
              streamURL={remoteStream.toURL()}
              style={StyleSheet.absoluteFill}
              objectFit="cover"
            />
          ) : (
            <View
              // Collapsed, the stage is barely taller than the top bar: sit below it.
              style={[styles.placeholder, sheetOpen && { paddingTop: TOP_INSET + 44 }]}
              testID="call-remote-placeholder"
            >
              <View style={[styles.avatar, sheetOpen && styles.avatarSmall]}>
                <Text style={[styles.avatarText, sheetOpen && styles.avatarTextSmall]}>🧑</Text>
              </View>
              <Text style={styles.placeholderText}>{placeholderCaption}</Text>
            </View>
          )}

          {remoteStream && remoteVideoActive && <TopScrim height={TOP_INSET + 80} />}

          <View style={[styles.topBar, { top: TOP_INSET }]}>
            <View style={styles.topBarLeft}>
              <View style={styles.pill} testID="call-status-pill">
                <View style={[styles.dot, !connected && styles.dotPending]} />
                <Text style={styles.pillText}>
                  {connected ? `Connected · ${formatDuration(elapsed)}` : 'Connecting…'}
                </Text>
              </View>
              <View style={styles.pill}>
                <Text style={styles.pillText}>
                  🌐 {language.toUpperCase()} · {DRINK_ICONS[drinkType]}
                </Text>
              </View>
            </View>
            <Pressable
              testID="call-menu-button"
              style={styles.menuButton}
              onPress={() => setSheet(sheet === 'menu' ? null : 'menu')}
              accessibilityLabel="Menu"
            >
              <Text style={styles.menuIcon}>☰</Text>
              {drinkCount > 0 && (
                <View style={styles.drinkBadge}>
                  <Text style={styles.drinkBadgeText}>{drinkCount}</Text>
                </View>
              )}
            </Pressable>
          </View>

          {!sheetOpen && (
            <View style={[styles.selfPip, { top: TOP_INSET + 54 }]}>
              {localStream && videoEnabled ? (
                // zOrder: on Android both RTCViews are SurfaceViews, and without it the
                // remote video draws over this preview.
                <RTCView
                  streamURL={localStream.toURL()}
                  style={StyleSheet.absoluteFill}
                  objectFit="cover"
                  mirror
                  zOrder={1}
                />
              ) : (
                <Text style={styles.selfPipText}>🙂</Text>
              )}
            </View>
          )}
        </View>

        {sheet === 'chat' && (
          <ChatSheet
            chatLog={chatLog}
            onSend={sendChat}
            onIceBreaker={sendIceBreaker}
            onClose={() => setSheet(null)}
          />
        )}

        {sheet === 'menu' && (
          <MenuSheet
            drinkType={drinkType}
            drinkCount={drinkCount}
            onDrink={() => setDrinkCount((c) => c + 1)}
            onGames={() => setSheet('games')}
            onIceBreaker={() => {
              sendIceBreaker();
              setSheet('chat');
            }}
            onReport={() => setReportOpen(true)}
            onBlock={handleBlock}
            onLeave={handleEndCall}
            onClose={() => setSheet(null)}
          />
        )}

        {sheet === 'games' && (
          <GameSheet
            gameInvite={gameInvite}
            activeGame={activeGame}
            onStartGame={startGame}
            onAcceptGame={acceptGame}
            onDeclineGame={declineGame}
            onNextPrompt={nextGamePrompt}
            onRevealPrompt={revealGamePrompt}
            onCloseGame={() => {
              closeGame();
              setSheet(null);
            }}
            onClose={() => setSheet(null)}
          />
        )}

        {sheet === 'verify' && (
          <CallSheet title="📷 Video" onClose={() => setSheet(null)} testID="call-verify-sheet">
            <View style={styles.verifyBody}>
              <Text style={styles.verifyIcon}>🪪</Text>
              {verification.state.kind === 'waitlisted' ? (
                <>
                  <Text style={styles.verifyTitle}>You're on the list</Text>
                  <Text style={styles.verifyText}>
                    We'll email you when verification opens up again. Audio and chat work in the
                    meantime.
                  </Text>
                </>
              ) : (
                <>
                  <Text style={styles.verifyTitle}>Verify your age to turn on video</Text>
                  <Text style={styles.verifyText}>
                    A quick selfie check, once. Audio and chat work either way.
                  </Text>
                </>
              )}
              {verification.error && <Text style={styles.verifyError}>{verification.error}</Text>}
            </View>
            <View style={styles.sheetFooter}>
              <Pressable style={styles.secondaryButton} onPress={() => setSheet(null)}>
                <Text style={styles.secondaryText}>Not now</Text>
              </Pressable>
              {verification.state.kind !== 'waitlisted' && (
                <Pressable
                  style={styles.primaryButton}
                  onPress={() => verification.startVerification()}
                  disabled={verification.state.kind === 'checking'}
                >
                  <Text style={styles.primaryText}>
                    {verification.state.kind === 'checking' ? 'Verifying…' : 'Verify now'}
                  </Text>
                </Pressable>
              )}
            </View>
          </CallSheet>
        )}

        {!sheetOpen && (
          <View style={styles.bottomBar}>
            <Pressable
              testID="call-mute-button"
              style={[styles.ctrlButton, !audioEnabled && styles.ctrlButtonOff]}
              onPress={handleToggleAudio}
              accessibilityLabel={audioEnabled ? 'Mute microphone' : 'Unmute microphone'}
            >
              <Text style={styles.ctrlIcon}>{audioEnabled ? '🎤' : '🔇'}</Text>
            </Pressable>
            <Pressable
              testID="call-video-button"
              style={[styles.ctrlButton, !videoEnabled && styles.ctrlButtonOff]}
              onPress={handleToggleVideo}
              accessibilityLabel={videoEnabled ? 'Stop video' : 'Start video'}
            >
              <Text style={styles.ctrlIcon}>📷</Text>
              {!videoEnabled && <View style={styles.ctrlSlash} />}
            </Pressable>
            <Pressable
              testID="call-chat-toggle-button"
              style={styles.ctrlButton}
              onPress={() => setSheet('chat')}
              accessibilityLabel="Chat"
            >
              <Text style={styles.ctrlIcon}>💬</Text>
              {hasUnread && <View style={styles.unreadDot} />}
            </Pressable>
            <Pressable testID="call-skip-button" style={styles.skipButton} onPress={handleSkip}>
              <Text style={styles.skipText}>Skip ⏭</Text>
            </Pressable>
          </View>
        )}

        {reportOpen && (
          <ReportBlockSheet
            partnerId={partnerId}
            callId={callId}
            onClose={() => setReportOpen(false)}
            onDone={handleReportBlockDone}
          />
        )}
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  keyboardAvoider: {
    flex: 1,
  },
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  stage: {
    flex: 1,
    backgroundColor: '#1d1729',
    overflow: 'hidden',
  },
  placeholder: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 14,
  },
  avatar: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: colors.avatar,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarSmall: {
    width: 56,
    height: 56,
    borderRadius: 28,
  },
  avatarText: {
    fontSize: 40,
  },
  avatarTextSmall: {
    fontSize: 24,
  },
  placeholderText: {
    color: colors.textMuted,
    fontSize: 13,
  },
  scrim: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    overflow: 'hidden',
  },
  topBar: {
    position: 'absolute',
    left: 16,
    right: 16,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  topBarLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  pill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: colors.scrim,
    borderRadius: 999,
    paddingHorizontal: 13,
    paddingVertical: 7,
  },
  pillText: {
    color: colors.text,
    fontSize: 12,
    fontVariant: ['tabular-nums'],
  },
  dot: {
    width: 7,
    height: 7,
    borderRadius: 4,
    backgroundColor: colors.success,
  },
  dotPending: {
    backgroundColor: colors.primary,
  },
  menuButton: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: colors.scrim,
    alignItems: 'center',
    justifyContent: 'center',
  },
  menuIcon: {
    color: colors.text,
    fontSize: 16,
  },
  drinkBadge: {
    position: 'absolute',
    bottom: -6,
    right: -8,
    backgroundColor: colors.primary,
    borderRadius: 999,
    borderWidth: 2,
    borderColor: colors.background,
    paddingHorizontal: 5,
    minWidth: 20,
    alignItems: 'center',
  },
  drinkBadgeText: {
    color: colors.onPrimary,
    fontSize: 10,
    fontWeight: '700',
  },
  selfPip: {
    position: 'absolute',
    right: 16,
    width: 78,
    height: 112,
    borderRadius: 16,
    borderWidth: 2,
    borderColor: 'rgba(255,255,255,0.18)',
    backgroundColor: '#26203a',
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
  selfPipText: {
    fontSize: 22,
  },
  bottomBar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: colors.bar,
    borderTopWidth: 1,
    borderTopColor: '#1c1c22',
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 28,
  },
  ctrlButton: {
    width: 46,
    height: 46,
    borderRadius: 23,
    backgroundColor: colors.surface,
    alignItems: 'center',
    justifyContent: 'center',
  },
  ctrlButtonOff: {
    backgroundColor: colors.dangerSoft,
  },
  ctrlIcon: {
    fontSize: 18,
  },
  ctrlSlash: {
    position: 'absolute',
    width: 26,
    height: 2,
    borderRadius: 1,
    backgroundColor: colors.onDangerSoft,
    transform: [{ rotate: '-45deg' }],
  },
  unreadDot: {
    position: 'absolute',
    top: 0,
    right: 0,
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: colors.danger,
    borderWidth: 2,
    borderColor: colors.bar,
  },
  skipButton: {
    flex: 1,
    backgroundColor: colors.primary,
    borderRadius: 999,
    paddingVertical: 13,
    alignItems: 'center',
    shadowColor: colors.primary,
    shadowOpacity: 0.3,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 6 },
    elevation: 4,
  },
  skipText: {
    color: colors.onPrimary,
    fontWeight: '700',
    fontSize: 15,
  },
  verifyBody: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 28,
    gap: 8,
  },
  verifyIcon: {
    fontSize: 40,
    marginBottom: 4,
  },
  verifyTitle: {
    color: colors.text,
    fontSize: 17,
    fontWeight: '700',
    textAlign: 'center',
  },
  verifyText: {
    color: colors.textMuted,
    textAlign: 'center',
    lineHeight: 20,
  },
  verifyError: {
    color: colors.danger,
    textAlign: 'center',
  },
  sheetFooter: {
    flexDirection: 'row',
    gap: 10,
    paddingHorizontal: 14,
    paddingTop: 10,
    paddingBottom: 24,
    borderTopWidth: 1,
    borderTopColor: '#26262f',
  },
  primaryButton: {
    flex: 1,
    backgroundColor: colors.primary,
    borderRadius: 999,
    paddingVertical: 12,
    alignItems: 'center',
  },
  primaryText: {
    color: colors.onPrimary,
    fontWeight: '700',
  },
  secondaryButton: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: 999,
    paddingVertical: 12,
    alignItems: 'center',
  },
  secondaryText: {
    color: colors.text,
    fontWeight: '600',
  },
});

// Once a permission is denied, Android stops prompting; only Settings can re-enable it.
function showBlockedAlert(device: 'Camera' | 'Microphone') {
  Alert.alert(
    `${device} access is off`,
    `Allow ${device.toLowerCase()} access for DrinkingBuddy in Settings. Chat works without it.`,
    [
      { text: 'Not now', style: 'cancel' },
      { text: 'Open Settings', onPress: () => Linking.openSettings() },
    ],
  );
}
