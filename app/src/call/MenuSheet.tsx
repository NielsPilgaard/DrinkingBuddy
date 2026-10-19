import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { colors } from '../theme';
import { CallSheet } from './CallSheet';
import { DrinkCounter, type DrinkType } from './DrinkCounter';

type MenuSheetProps = {
  drinkType: DrinkType;
  drinkCount: number;
  onDrink: () => void;
  onGames: () => void;
  onIceBreaker: () => void;
  onReport: () => void;
  onBlock: () => void;
  onLeave: () => void;
  onClose: () => void;
};

type MenuItemProps = {
  icon: string;
  title: string;
  subtitle: string;
  onPress: () => void;
  testID?: string;
  destructive?: boolean;
};

function MenuItem({ icon, title, subtitle, onPress, testID, destructive }: MenuItemProps) {
  return (
    <Pressable
      testID={testID}
      style={({ pressed }) => [styles.item, pressed && styles.itemPressed]}
      onPress={onPress}
      accessibilityRole="button"
    >
      <View style={[styles.icon, destructive && styles.iconDestructive]}>
        <Text style={styles.iconText}>{icon}</Text>
      </View>
      <View style={styles.body}>
        <Text style={[styles.title, destructive && styles.titleDestructive]}>{title}</Text>
        <Text style={styles.subtitle}>{subtitle}</Text>
      </View>
      <Text style={styles.chevron}>›</Text>
    </Pressable>
  );
}

export function MenuSheet({
  drinkType,
  drinkCount,
  onDrink,
  onGames,
  onIceBreaker,
  onReport,
  onBlock,
  onLeave,
  onClose,
}: MenuSheetProps) {
  return (
    <CallSheet title="☰ Menu" onClose={onClose} testID="call-menu-sheet">
      <ScrollView contentContainerStyle={styles.list}>
        <DrinkCounter drinkType={drinkType} count={drinkCount} onIncrement={onDrink} />
        <MenuItem
          testID="call-games-toggle-button"
          icon="🎮"
          title="Mini games"
          subtitle="Trivia, Would You Rather, Never Have I Ever"
          onPress={onGames}
        />
        <MenuItem
          testID="call-icebreaker-button"
          icon="🎲"
          title="Icebreaker"
          subtitle="Drop a random conversation starter in the chat"
          onPress={onIceBreaker}
        />
        <MenuItem
          testID="call-report-button"
          icon="🚩"
          title="Report"
          subtitle="Flag this person to our moderators"
          onPress={onReport}
        />
        <MenuItem
          testID="call-block-button"
          icon="🚫"
          title="Block"
          subtitle="Never match with this person again"
          onPress={onBlock}
        />
        <MenuItem
          testID="call-end-button"
          icon="👋"
          title="Leave call"
          subtitle="Hang up and go back to your filters"
          onPress={onLeave}
          destructive
        />
      </ScrollView>
    </CallSheet>
  );
}

const styles = StyleSheet.create({
  list: {
    padding: 14,
    gap: 10,
    paddingBottom: 28,
  },
  item: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 16,
    padding: 14,
  },
  itemPressed: {
    backgroundColor: colors.surfaceRaised,
  },
  icon: {
    width: 42,
    height: 42,
    borderRadius: 12,
    backgroundColor: colors.surfaceRaised,
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconDestructive: {
    backgroundColor: colors.dangerSoft,
  },
  iconText: {
    fontSize: 20,
  },
  body: {
    flex: 1,
  },
  title: {
    color: colors.text,
    fontSize: 14,
    fontWeight: '600',
  },
  titleDestructive: {
    color: colors.onDangerSoft,
  },
  subtitle: {
    color: colors.textMuted,
    fontSize: 12,
    marginTop: 2,
  },
  chevron: {
    color: colors.textMuted,
    fontSize: 20,
  },
});
