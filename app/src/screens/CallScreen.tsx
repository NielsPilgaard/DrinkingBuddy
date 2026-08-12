import { useCallback, useEffect, useRef, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { RTCView } from 'react-native-webrtc';
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
  onCallEnded: () => void;
};

export function CallScreen({
  apiBaseUrl,
  sessionToken,
  callId,
  partnerId,
  isInitiator,
  videoEligible,
  onCallEnded,
}: CallScreenProps) {
  const {
    status,
    localStream,
    remoteStream,
    videoEnabled,
    audioEnabled,
    chatLog,
    sendChat,
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
  const [reportOpen, setReportOpen] = useState(false);
  const [verifyPromptOpen, setVerifyPromptOpen] = useState(false);
  const [draft, setDraft] = useState('');
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
    const eligible = await toggleVideo();
    if (!videoEnabled && !eligible) {
      setVerifyPromptOpen(true);
    }
  }

  useEffect(() => {
    if (verification.state.kind === 'verified') {
      setVerifyPromptOpen(false);
    }
  }, [verification.state]);

  return (
    <View style={styles.container}>
      {remoteStream ? (
        <RTCView streamURL={remoteStream.toURL()} style={styles.remoteVideo} objectFit="cover" />
      ) : (
        <View style={[styles.remoteVideo, styles.placeholder]}>
          <Text style={styles.placeholderText}>
            {status === 'waiting_for_peer' ? 'Connecting…' : 'Waiting for video…'}
          </Text>
        </View>
      )}

      {localStream && videoEnabled && (
        <RTCView streamURL={localStream.toURL()} style={styles.localVideo} objectFit="cover" />
      )}

      {chatOpen && (
        <View style={styles.chatDrawer}>
          <ScrollView style={styles.chatLog}>
            {chatLog.map((entry) => (
              <Text key={entry.id} style={entry.fromSelf ? styles.chatSelf : styles.chatPeer}>
                {entry.text}
              </Text>
            ))}
          </ScrollView>
          <View style={styles.chatInputRow}>
            <TextInput
              style={styles.chatInput}
              value={draft}
              onChangeText={setDraft}
              placeholder="Message…"
              placeholderTextColor="#8a8a96"
              onSubmitEditing={handleSend}
            />
            <Pressable style={styles.sendButton} onPress={handleSend}>
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
        <View style={styles.verifySheet}>
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

      <View style={styles.controls}>
        <Pressable style={styles.controlButton} onPress={toggleAudio}>
          <Text style={styles.controlText}>{audioEnabled ? 'Mute' : 'Unmute'}</Text>
        </Pressable>
        <Pressable style={styles.controlButton} onPress={handleToggleVideo}>
          <Text style={styles.controlText}>{videoEnabled ? 'Stop video' : 'Start video'}</Text>
        </Pressable>
        <Pressable style={styles.controlButton} onPress={() => setChatOpen((v) => !v)}>
          <Text style={styles.controlText}>Chat</Text>
        </Pressable>
        <Pressable style={styles.controlButton} onPress={() => setReportOpen(true)}>
          <Text style={styles.controlText}>Report</Text>
        </Pressable>
        <Pressable style={[styles.controlButton, styles.endButton]} onPress={handleEndCall}>
          <Text style={styles.controlText}>End</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#050506',
  },
  remoteVideo: {
    flex: 1,
  },
  placeholder: {
    alignItems: 'center',
    justifyContent: 'center',
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
  chatInputRow: {
    flexDirection: 'row',
    marginTop: 8,
    gap: 8,
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
    justifyContent: 'space-evenly',
    paddingVertical: 16,
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
