import { useRef, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { colors } from '../theme';
import { CallSheet } from './CallSheet';
import type { ChatEntry } from './useCall';

type ChatSheetProps = {
  chatLog: ChatEntry[];
  onSend: (text: string) => void;
  onIceBreaker: () => void;
  onClose: () => void;
};

export function ChatSheet({ chatLog, onSend, onIceBreaker, onClose }: ChatSheetProps) {
  const [draft, setDraft] = useState('');
  const scrollRef = useRef<ScrollView>(null);

  function handleSend() {
    if (!draft.trim()) return;
    onSend(draft.trim());
    setDraft('');
  }

  return (
    <CallSheet title="💬 Chat" onClose={onClose} testID="call-chat-drawer">
      <ScrollView
        ref={scrollRef}
        style={styles.log}
        contentContainerStyle={styles.logContent}
        onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: true })}
        keyboardShouldPersistTaps="handled"
      >
        {chatLog.length === 0 && (
          <Text style={styles.empty}>Say hi, or tap 🎲 for a conversation starter.</Text>
        )}
        {chatLog.map((entry) =>
          entry.kind === 'ice_breaker' ? (
            <View key={entry.id} style={styles.iceBreaker}>
              <Text style={styles.iceBreakerText}>🎲 {entry.text}</Text>
            </View>
          ) : (
            <View
              key={entry.id}
              style={[styles.bubble, entry.fromSelf ? styles.bubbleSelf : styles.bubblePeer]}
            >
              <Text
                testID={entry.fromSelf ? 'call-chat-message-self' : 'call-chat-message-peer'}
                style={entry.fromSelf ? styles.textSelf : styles.textPeer}
              >
                {entry.text}
              </Text>
            </View>
          ),
        )}
      </ScrollView>
      <View style={styles.inputRow}>
        <Pressable
          style={styles.iceBreakerButton}
          onPress={onIceBreaker}
          accessibilityLabel="Send an icebreaker"
        >
          <Text style={styles.iconText}>🎲</Text>
        </Pressable>
        <TextInput
          testID="call-chat-input"
          style={styles.input}
          value={draft}
          onChangeText={setDraft}
          placeholder="Message…"
          placeholderTextColor={colors.textMuted}
          keyboardAppearance="dark"
          returnKeyType="send"
          onSubmitEditing={handleSend}
        />
        <Pressable
          testID="call-chat-send-button"
          style={[styles.sendButton, !draft.trim() && styles.sendButtonIdle]}
          onPress={handleSend}
          accessibilityLabel="Send"
        >
          <Text style={styles.sendText}>➤</Text>
        </Pressable>
      </View>
    </CallSheet>
  );
}

const styles = StyleSheet.create({
  log: {
    flex: 1,
  },
  logContent: {
    padding: 14,
    gap: 10,
  },
  empty: {
    color: colors.textMuted,
    textAlign: 'center',
    marginTop: 24,
  },
  bubble: {
    maxWidth: '78%',
    paddingHorizontal: 13,
    paddingVertical: 9,
  },
  bubblePeer: {
    alignSelf: 'flex-start',
    backgroundColor: colors.surface,
    borderRadius: 16,
    borderBottomLeftRadius: 4,
  },
  bubbleSelf: {
    alignSelf: 'flex-end',
    backgroundColor: colors.primary,
    borderRadius: 16,
    borderBottomRightRadius: 4,
  },
  textPeer: {
    color: colors.text,
    fontSize: 14,
    lineHeight: 19,
  },
  textSelf: {
    color: colors.onPrimary,
    fontSize: 14,
    lineHeight: 19,
    fontWeight: '500',
  },
  iceBreaker: {
    alignSelf: 'center',
    maxWidth: '90%',
    backgroundColor: colors.surfaceSelected,
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  iceBreakerText: {
    color: colors.primary,
    textAlign: 'center',
    fontSize: 13,
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 14,
    paddingTop: 10,
    paddingBottom: 24,
    borderTopWidth: 1,
    borderTopColor: '#26262f',
  },
  iceBreakerButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.surface,
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconText: {
    fontSize: 16,
  },
  input: {
    flex: 1,
    minWidth: 0,
    color: colors.text,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: '#2f2f3a',
    borderRadius: 999,
    paddingHorizontal: 15,
    paddingVertical: 9,
    fontSize: 14,
  },
  sendButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendButtonIdle: {
    opacity: 0.5,
  },
  sendText: {
    color: colors.onPrimary,
    fontSize: 15,
  },
});
