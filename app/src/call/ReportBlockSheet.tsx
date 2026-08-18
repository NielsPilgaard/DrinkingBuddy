import { useState } from 'react';
import { Modal, Pressable, StyleSheet, Text, View } from 'react-native';
import { blockUser, REPORT_REASONS, type ReportReason, reportUser } from './moderation';

type ReportBlockSheetProps = {
  partnerId: string;
  callId: string;
  onClose: () => void;
  /** Called after a report and/or block completes, so the caller can e.g. end the call. */
  onDone: () => void;
};

export function ReportBlockSheet({ partnerId, callId, onClose, onDone }: ReportBlockSheetProps) {
  const [reason, setReason] = useState<ReportReason | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleReport(alsoBlock: boolean) {
    if (!reason || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      await reportUser(partnerId, callId, reason);
      if (alsoBlock) {
        await blockUser(partnerId);
      }
      onDone();
    } catch {
      setError('Something went wrong. Try again.');
    } finally {
      setSubmitting(false);
    }
  }

  async function handleBlockOnly() {
    if (submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      await blockUser(partnerId);
      onDone();
    } catch {
      setError('Something went wrong. Try again.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal
      visible
      transparent
      animationType="fade"
      onRequestClose={onClose}
      testID="report-block-sheet"
    >
      <View style={styles.overlay}>
        <View style={styles.sheet}>
          <Text style={styles.title}>Report this person?</Text>
          {REPORT_REASONS.map((r) => (
            <Pressable
              key={r.value}
              testID={`report-reason-${r.value}`}
              style={[styles.reasonRow, reason === r.value && styles.reasonRowSelected]}
              onPress={() => setReason(r.value)}
            >
              <Text style={styles.reasonText}>{r.label}</Text>
            </Pressable>
          ))}

          {error && <Text style={styles.errorText}>{error}</Text>}

          <View style={styles.actions}>
            <Pressable
              testID="report-cancel-button"
              style={styles.cancelButton}
              onPress={onClose}
              disabled={submitting}
            >
              <Text style={styles.cancelText}>Cancel</Text>
            </Pressable>
            <Pressable
              testID="report-block-only-button"
              style={styles.blockButton}
              onPress={handleBlockOnly}
              disabled={submitting}
            >
              <Text style={styles.actionText}>Block only</Text>
            </Pressable>
            <Pressable
              testID="report-and-block-button"
              style={[styles.reportButton, !reason && styles.actionDisabled]}
              onPress={() => handleReport(true)}
              disabled={!reason || submitting}
            >
              <Text style={styles.actionText}>Report & block</Text>
            </Pressable>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.6)',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  sheet: {
    width: '100%',
    backgroundColor: '#17171d',
    borderRadius: 16,
    padding: 16,
    gap: 8,
  },
  title: {
    color: '#f2f2f5',
    fontWeight: '700',
    fontSize: 16,
    marginBottom: 4,
  },
  reasonRow: {
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 8,
    backgroundColor: '#1f1f28',
  },
  reasonRowSelected: {
    backgroundColor: '#2563eb',
  },
  reasonText: {
    color: '#f2f2f5',
  },
  errorText: {
    color: '#ff6b6b',
    marginTop: 4,
  },
  actions: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 12,
  },
  cancelButton: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: 'center',
    backgroundColor: '#1f1f28',
  },
  cancelText: {
    color: '#8a8a96',
    fontWeight: '600',
  },
  blockButton: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: 'center',
    backgroundColor: '#ff6b6b',
  },
  reportButton: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: 'center',
    backgroundColor: '#e11d48',
  },
  actionDisabled: {
    opacity: 0.5,
  },
  actionText: {
    color: '#fff',
    fontWeight: '600',
  },
});
