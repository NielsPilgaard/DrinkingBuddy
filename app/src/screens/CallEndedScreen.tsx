import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { ReportBlockSheet } from '../call/ReportBlockSheet';
import { colors } from '../theme';

type CallEndedScreenProps = {
  partnerId: string;
  callId: string;
  onContinue: () => void;
  onBack: () => void;
};

export function CallEndedScreen({ partnerId, callId, onContinue, onBack }: CallEndedScreenProps) {
  const [reportOpen, setReportOpen] = useState(false);

  return (
    <View style={styles.container} testID="call-ended-screen">
      <View style={styles.avatar}>
        <Text style={styles.avatarText}>🧑</Text>
      </View>
      <Text style={styles.title}>Call ended</Text>
      <Text style={styles.subtitle}>Ready for the next one?</Text>

      <View style={styles.actions}>
        <Pressable
          testID="call-ended-find-next-button"
          style={styles.primaryButton}
          onPress={onContinue}
        >
          <Text style={styles.primaryText}>Find next match</Text>
        </Pressable>

        <Pressable
          testID="call-ended-report-button"
          style={styles.secondaryButton}
          onPress={() => setReportOpen(true)}
        >
          <Text style={styles.dangerText}>Report or block</Text>
        </Pressable>

        <Pressable testID="call-ended-back-button" style={styles.linkButton} onPress={onBack}>
          <Text style={styles.linkText}>Back to filters</Text>
        </Pressable>
      </View>

      {reportOpen && (
        <ReportBlockSheet
          partnerId={partnerId}
          callId={callId}
          onClose={() => setReportOpen(false)}
          onDone={() => {
            setReportOpen(false);
            onContinue();
          }}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  avatar: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: colors.avatar,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 20,
  },
  avatarText: {
    fontSize: 44,
  },
  title: {
    color: colors.text,
    fontSize: 22,
    fontWeight: '700',
  },
  subtitle: {
    color: colors.textMuted,
    marginTop: 6,
  },
  actions: {
    alignSelf: 'stretch',
    gap: 12,
    marginTop: 32,
  },
  primaryButton: {
    backgroundColor: colors.primary,
    borderRadius: 999,
    paddingVertical: 14,
    alignItems: 'center',
  },
  primaryText: {
    color: colors.onPrimary,
    fontWeight: '700',
  },
  secondaryButton: {
    backgroundColor: colors.surface,
    borderRadius: 999,
    paddingVertical: 14,
    alignItems: 'center',
  },
  dangerText: {
    color: colors.danger,
    fontWeight: '600',
  },
  linkButton: {
    alignItems: 'center',
    padding: 8,
  },
  linkText: {
    color: colors.textMuted,
  },
});
