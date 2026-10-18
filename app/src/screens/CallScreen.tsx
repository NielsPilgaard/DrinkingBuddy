import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Alert,
  BackHandler,
  KeyboardAvoidingView,
  Linking,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { RTCView } from 'react-native-webrtc';
import { DrinkCounter } from '../call/DrinkCounter';
import { GameDrawer } from '../call/GameDrawer';
import { ReportBlockSheet } from '../call/ReportBlockSheet';
import { useCall } from '../call/useCall';
import { useVerification } from '../verification/useVerification';

type CallScreenProps = {
  apiBaseUrl: string;
  sessionToken: string;
  callId: string;
  partnerId: string;
  isInitiator: boolean;
  videoEligible: boolean;
  drinkType: 'alcoholic' | 'non_alcoholic';
  onCallEnded: () => void;
};

export function CallScreen({
  apiBaseUrl,
  sessionToken,
  callId,
  partnerId,
  isInitiator,
  videoEligible,
  drinkType,
  onCallEnded,
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

  const [chatOpen, setChatOpen] = useState(false);
  const [gameOpen, setGameOpen] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);
  const [verifyPromptOpen, setVerifyPromptOpen] = useState(false);
  const [draft, setDraft] = useState('');
  const [controlsHeight, setControlsHeight] = useState(96);
  const callEndedRef = useRef(false);
  const onCallEndedRef = useRef(onCallEnded);
  onCallEndedRef.current = onCallEnded;

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

  function handleReportBlockDone() {
    setReportOpen(false);
    endCall();
    notifyCallEnded();
  }

  useEffect(() => {
    if (status === 'ended' || status === 'failed') {
      notifyCallEnded();
    }
  }, [status, notifyCallEnded]);

  function handleSend() {
    if (!draft.trim()) return;
    sendChat(draft.trim());
    setDraft('');
  }

  async function handleToggleVideo() {
    const result = await toggleVideo();
    if (result === 'not_eligible') setVerifyPromptOpen(true);
    else if (result === 'blocked') showBlockedAlert('Camera');
  }

  async function handleToggleAudio() {
    if ((await toggleAudio()) === 'blocked') showBlockedAlert('Microphone');
  }

  // Android back: close whatever drawer/sheet is open; with none open, confirm
  // before ending the call instead of letting back close the app mid-call.
  useEffect(() => {
    const subscription = BackHandler.addEventListener('hardwareBackPress', () => {
      if (chatOpen || gameOpen || reportOpen || verifyPromptOpen) {
        setChatOpen(false);
        setGameOpen(false);
        setReportOpen(false);
        setVerifyPromptOpen(false);
        return true;
      }
      Alert.alert('End this call?', undefined, [
        { text: 'Stay', style: 'cancel' },
        { text: 'End call', style: 'destructive', onPress: handleEndCallRef.current },
      ]);
      return true;
    });
    return () => subscription.remove();
  }, [chatOpen, gameOpen, reportOpen, verifyPromptOpen]);

  useEffect(() => {
    if (verification.state.kind === 'verified') {
      setVerifyPromptOpen(false);
    }
  }, [verification.state]);

  // Auto-open the game drawer for the receiving party's accept/decline
  // prompt, and keep it open through the synced round - tasks/mini-games.md
  // requires the invite to surface without the receiver having tapped
  // anything first.
  useEffect(() => {
    if (gameInvite || activeGame) {
      setGameOpen(true);
    }
  }, [gameInvite, activeGame]);

  return (
    // Android is edge-to-edge (SDK 57), so the window no longer resizes for the keyboard:
    // without this the chat input sits under it.
    <KeyboardAvoidingView style={styles.keyboardAvoider} behavior="padding">
      <View style={styles.container} testID="call-screen">
        {remoteStream && remoteVideoActive ? (
          <RTCView streamURL={remoteStream.toURL()} style={styles.remoteVideo} objectFit="cover" />
        ) : (
          <View style={[styles.remoteVideo, styles.placeholder]} testID="call-remote-placeholder">
            <Text style={styles.placeholderText}>
              {status === 'waiting_for_peer'
                ? 'Connecting…'
                : mediaState === 'failed'
                  ? "Couldn't connect audio. Chat still works."
                  : mediaState === 'connecting'
                    ? 'Connecting audio…'
                    : 'Connected · camera off'}
            </Text>
          </View>
        )}

        {localStream && videoEnabled && (
          // zOrder: on Android both RTCViews are SurfaceViews, and without it the
          // remote video draws over this preview.
          <RTCView
            streamURL={localStream.toURL()}
            style={styles.localVideo}
            objectFit="cover"
            mirror
            zOrder={1}
          />
        )}

        <DrinkCounter drinkType={drinkType} />

        {gameOpen && (
          <GameDrawer
            style={{ bottom: controlsHeight }}
            gameInvite={gameInvite}
            activeGame={activeGame}
            onStartGame={startGame}
            onAcceptGame={acceptGame}
            onDeclineGame={declineGame}
            onNextPrompt={nextGamePrompt}
            onRevealPrompt={revealGamePrompt}
            onCloseGame={() => {
              closeGame();
              setGameOpen(false);
            }}
            onClose={() => setGameOpen(false)}
          />
        )}

        {chatOpen && !gameOpen && (
          <View style={[styles.chatDrawer, { bottom: controlsHeight }]} testID="call-chat-drawer">
            <ScrollView style={styles.chatLog}>
              {chatLog.map((entry) => (
                <Text
                  key={entry.id}
                  testID={entry.fromSelf ? 'call-chat-message-self' : 'call-chat-message-peer'}
                  style={[
                    entry.fromSelf ? styles.chatSelf : styles.chatPeer,
                    entry.kind === 'ice_breaker' && styles.chatIceBreaker,
                  ]}
                >
                  {entry.kind === 'ice_breaker' ? `🎲 ${entry.text}` : entry.text}
                </Text>
              ))}
            </ScrollView>
            <View style={styles.chatInputRow}>
              <Pressable style={styles.iceBreakerButton} onPress={sendIceBreaker}>
                <Text style={styles.iceBreakerButtonText}>🎲</Text>
              </Pressable>
              <TextInput
                testID="call-chat-input"
                style={styles.chatInput}
                value={draft}
                onChangeText={setDraft}
                placeholder="Message…"
                placeholderTextColor="#8a8a96"
                onSubmitEditing={handleSend}
              />
              <Pressable
                testID="call-chat-send-button"
                style={styles.sendButton}
                onPress={handleSend}
              >
                <Text style={styles.sendButtonText}>Send</Text>
              </Pressable>
            </View>
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

        {verifyPromptOpen && (
          <View style={[styles.verifySheet, { bottom: controlsHeight }]}>
            {verification.state.kind === 'waitlisted' ? (
              <Text style={styles.verifyText}>You're on the list, we'll email you.</Text>
            ) : (
              <Text style={styles.verifyText}>Verify your age to enable video</Text>
            )}
            {verification.error && <Text style={styles.verifyError}>{verification.error}</Text>}
            <View style={styles.verifyActions}>
              <Pressable
                style={styles.controlButton}
                onPress={() => verification.startVerification()}
                disabled={verification.state.kind === 'checking'}
              >
                <Text style={styles.controlText}>
                  {verification.state.kind === 'checking' ? 'Verifying…' : 'Verify now'}
                </Text>
              </Pressable>
              <Pressable style={styles.controlButton} onPress={() => setVerifyPromptOpen(false)}>
                <Text style={styles.controlText}>Not now</Text>
              </Pressable>
            </View>
          </View>
        )}

        <View
          style={styles.controls}
          onLayout={(e) => setControlsHeight(e.nativeEvent.layout.height)}
        >
          <Pressable
            testID="call-mute-button"
            style={styles.controlButton}
            onPress={handleToggleAudio}
          >
            <Text style={styles.controlText}>{audioEnabled ? 'Mute' : 'Unmute'}</Text>
          </Pressable>
          <Pressable
            testID="call-video-button"
            style={styles.controlButton}
            onPress={handleToggleVideo}
          >
            <Text style={styles.controlText}>{videoEnabled ? 'Stop video' : 'Start video'}</Text>
          </Pressable>
          <Pressable
            testID="call-chat-toggle-button"
            style={styles.controlButton}
            onPress={() => {
              setGameOpen(false);
              setChatOpen((v) => !v);
            }}
          >
            <Text style={styles.controlText}>Chat</Text>
          </Pressable>
          <Pressable
            testID="call-games-toggle-button"
            style={styles.controlButton}
            onPress={() => {
              setChatOpen(false);
              setGameOpen((v) => !v);
            }}
          >
            <Text style={styles.controlText}>Games</Text>
          </Pressable>
          <Pressable
            testID="call-report-button"
            style={styles.controlButton}
            onPress={() => setReportOpen(true)}
          >
            <Text style={styles.controlText}>Report</Text>
          </Pressable>
          <Pressable
            testID="call-end-button"
            style={[styles.controlButton, styles.endButton]}
            onPress={handleEndCall}
          >
            <Text style={styles.controlText}>End</Text>
          </Pressable>
        </View>
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
    backgroundColor: '#050506',
  },
  remoteVideo: {
    flex: 1,
  },
  placeholder: {
    alignItems: 'center',
    // Upper third, so the chat/game drawers don't cover the status text.
    paddingTop: '60%',
  },
  placeholderText: {
    color: '#8a8a96',
  },
  localVideo: {
    position: 'absolute',
    top: 48,
    right: 16,
    width: 100,
    height: 150,
    borderRadius: 12,
    backgroundColor: '#111',
  },
  verifySheet: {
    position: 'absolute',
    bottom: 96,
    left: 12,
    right: 12,
    backgroundColor: 'rgba(23,23,29,0.95)',
    borderRadius: 12,
    padding: 16,
    gap: 12,
  },
  verifyText: {
    color: '#f2f2f5',
    fontWeight: '600',
  },
  verifyError: {
    color: '#ff6b6b',
  },
  verifyActions: {
    flexDirection: 'row',
    gap: 8,
  },
  chatDrawer: {
    position: 'absolute',
    bottom: 96,
    left: 12,
    right: 12,
    maxHeight: 240,
    backgroundColor: 'rgba(23,23,29,0.95)',
    borderRadius: 12,
    padding: 8,
  },
  chatLog: {
    maxHeight: 180,
  },
  chatSelf: {
    color: '#ffb020',
    textAlign: 'right',
    paddingVertical: 2,
  },
  chatPeer: {
    color: '#f2f2f5',
    textAlign: 'left',
    paddingVertical: 2,
  },
  chatIceBreaker: {
    color: '#8a8a96',
    fontStyle: 'italic',
    textAlign: 'center',
  },
  chatInputRow: {
    flexDirection: 'row',
    marginTop: 8,
    gap: 8,
  },
  iceBreakerButton: {
    backgroundColor: '#1f1f28',
    borderRadius: 8,
    paddingHorizontal: 10,
    justifyContent: 'center',
  },
  iceBreakerButtonText: {
    fontSize: 16,
  },
  chatInput: {
    flex: 1,
    color: '#f2f2f5',
    backgroundColor: '#1f1f28',
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  sendButton: {
    backgroundColor: '#2563eb',
    borderRadius: 8,
    paddingHorizontal: 12,
    justifyContent: 'center',
  },
  sendButtonText: {
    color: '#fff',
    fontWeight: '600',
  },
  controls: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-evenly',
    gap: 8,
    paddingVertical: 16,
    paddingHorizontal: 12,
    paddingBottom: 32,
    backgroundColor: '#0e0e12',
  },
  controlButton: {
    backgroundColor: '#1f1f28',
    borderRadius: 999,
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  endButton: {
    backgroundColor: '#ff6b6b',
  },
  controlText: {
    color: '#f2f2f5',
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
