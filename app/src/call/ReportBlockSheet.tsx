import { useState } from 'react';
import { Modal, Pressable, StyleSheet, Text, View } from 'react-native';
import { colors } from '../theme';
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
      animationType="slide"
      onRequestClose={onClose}
      testID="report-block-sheet"
    >
      <Pressable style={styles.overlay} onPress={submitting ? undefined : onClose}>
        {/* Swallow taps on the sheet itself so only the backdrop closes it. */}
        <Pressable style={styles.sheet} onPress={() => {}}>
          <View style={styles.handle} />
          <Text style={styles.title}>Report this person?</Text>
          <Text style={styles.subtitle}>
            Pick a reason. Reports go to our moderators, and they won't know it was you.
          </Text>
          <View style={styles.reasons}>
            {REPORT_REASONS.map((r) => {
              const selected = reason === r.value;
              return (
                <Pressable
                  key={r.value}
                  testID={`report-reason-${r.value}`}
                  style={[styles.reasonRow, selected && styles.reasonRowSelected]}
                  onPress={() => setReason(r.value)}
                  accessibilityRole="radio"
                  accessibilityState={{ selected }}
                >
                  <View style={[styles.radio, selected && styles.radioSelected]}>
                    {selected && <View style={styles.radioDot} />}
                  </View>
                  <Text style={styles.reasonText}>{r.label}</Text>
                </Pressable>
              );
            })}
          </View>

          {error && <Text style={styles.errorText}>{error}</Text>}

          <Pressable
            testID="report-and-block-button"
            style={[styles.reportButton, !reason && styles.actionDisabled]}
            onPress={() => handleReport(true)}
            disabled={!reason || submitting}
          >
            <Text style={styles.reportText}>{submitting ? 'Sending…' : 'Report & block'}</Text>
          </Pressable>
          <View style={styles.secondaryRow}>
            <Pressable
              testID="report-cancel-button"
              style={styles.secondaryButton}
              onPress={onClose}
              disabled={submitting}
            >
              <Text style={styles.cancelText}>Cancel</Text>
            </Pressable>
            <Pressable
              testID="report-block-only-button"
              style={styles.secondaryButton}
              onPress={handleBlockOnly}
              disabled={submitting}
            >
              <Text style={styles.blockText}>Block only</Text>
            </Pressable>
          </View>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent: 'flex-end',
  },
  sheet: {
    backgroundColor: colors.panel,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    borderTopWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: 16,
    paddingTop: 10,
    paddingBottom: 32,
    gap: 10,
  },
  handle: {
    alignSelf: 'center',
    width: 36,
    height: 4,
    borderRadius: 999,
    backgroundColor: '#3a3a45',
    marginBottom: 6,
  },
  title: {
    color: colors.text,
    fontWeight: '700',
    fontSize: 18,
  },
  subtitle: {
    color: colors.textMuted,
    fontSize: 13,
    lineHeight: 18,
  },
  reasons: {
    gap: 8,
    marginVertical: 4,
  },
  reasonRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 13,
    paddingHorizontal: 14,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  reasonRowSelected: {
    borderColor: colors.danger,
    backgroundColor: colors.dangerSoft,
  },
  radio: {
    width: 18,
    height: 18,
    borderRadius: 9,
    borderWidth: 2,
    borderColor: colors.textMuted,
    alignItems: 'center',
    justifyContent: 'center',
  },
  radioSelected: {
    borderColor: colors.danger,
  },
  radioDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.danger,
  },
  reasonText: {
    color: colors.text,
    fontSize: 15,
  },
  errorText: {
    color: colors.danger,
  },
  reportButton: {
    backgroundColor: colors.danger,
    borderRadius: 999,
    paddingVertical: 13,
    alignItems: 'center',
    marginTop: 4,
  },
  reportText: {
    color: '#1f0505',
    fontWeight: '700',
    fontSize: 15,
  },
  actionDisabled: {
    opacity: 0.4,
  },
  secondaryRow: {
    flexDirection: 'row',
    gap: 10,
  },
  secondaryButton: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: 999,
    paddingVertical: 12,
    alignItems: 'center',
  },
  cancelText: {
    color: colors.textMuted,
    fontWeight: '600',
  },
  blockText: {
    color: colors.onDangerSoft,
    fontWeight: '600',
  },
});
