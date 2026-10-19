import type { ReactNode } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { colors } from '../theme';

type CallSheetProps = {
  title: string;
  onClose: () => void;
  testID?: string;
  children: ReactNode;
};

/**
 * Drawer chrome shared by the in-call sheets (chat, menu, games, verify): handle,
 * title row, collapse button. CallScreen lays it out in-flow below the shrunken
 * video, per docs/mockups/prototype-match-screen.html; only one is open at a time.
 */
export function CallSheet({ title, onClose, testID, children }: CallSheetProps) {
  return (
    <View style={styles.sheet} testID={testID}>
      <View style={styles.header}>
        <View style={styles.handle} />
        <View style={styles.titleRow}>
          <Text style={styles.title}>{title}</Text>
          <Pressable
            onPress={onClose}
            hitSlop={12}
            accessibilityRole="button"
            accessibilityLabel="Close"
            testID="call-sheet-close-button"
          >
            <Text style={styles.close}>︿</Text>
          </Pressable>
        </View>
      </View>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  sheet: {
    flex: 1,
    backgroundColor: colors.panel,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    borderTopWidth: 1,
    borderColor: colors.border,
    overflow: 'hidden',
  },
  header: {
    paddingHorizontal: 14,
    paddingTop: 10,
    paddingBottom: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#26262f',
  },
  handle: {
    alignSelf: 'center',
    width: 36,
    height: 4,
    borderRadius: 999,
    backgroundColor: '#3a3a45',
    marginBottom: 10,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  title: {
    color: colors.textMuted,
    fontSize: 13,
  },
  close: {
    color: colors.textMuted,
    fontSize: 20,
    paddingHorizontal: 8,
  },
});
