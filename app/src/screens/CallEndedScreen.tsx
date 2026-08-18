import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { ReportBlockSheet } from '../call/ReportBlockSheet';

type CallEndedScreenProps = {
  partnerId: string;
  callId: string;
  onContinue: () => void;
};

export function CallEndedScreen({ partnerId, callId, onContinue }: CallEndedScreenProps) {
  const [reportOpen, setReportOpen] = useState(false);

  return (
    <View style={styles.container} testID="call-ended-screen">
      <Text style={styles.title}>Call ended</Text>

      <Pressable
        testID="call-ended-report-button"
        style={styles.reportButton}
        onPress={() => setReportOpen(true)}
      >
        <Text style={styles.reportButtonText}>Report or block this person</Text>
      </Pressable>

      <Pressable
        testID="call-ended-find-next-button"
        style={styles.continueButton}
        onPress={onContinue}
      >
        <Text style={styles.continueButtonText}>Find next match</Text>
      </Pressable>

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
    backgroundColor: '#050506',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 16,
    padding: 24,
  },
  title: {
    color: '#f2f2f5',
    fontSize: 18,
    fontWeight: '700',
  },
  reportButton: {
    backgroundColor: '#1f1f28',
    borderRadius: 8,
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  reportButtonText: {
    color: '#ff6b6b',
    fontWeight: '600',
  },
  continueButton: {
    backgroundColor: '#2563eb',
    borderRadius: 8,
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  continueButtonText: {
    color: '#fff',
    fontWeight: '600',
  },
});
