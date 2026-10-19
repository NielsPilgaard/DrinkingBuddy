import { useRef, useState } from 'react';
import { Animated, Pressable, StyleSheet, Text, View } from 'react-native';
import { colors } from '../theme';

export type DrinkType = 'alcoholic' | 'non_alcoholic';

export const DRINK_ICONS: Record<DrinkType, string> = {
  alcoholic: '🍺',
  non_alcoholic: '🥤',
};

type DrinkCounterProps = {
  drinkType: DrinkType;
  count: number;
  onIncrement: () => void;
};

/**
 * Drink tally row for the in-call menu sheet (tasks/completed/beer-counter.md).
 * CallScreen owns the count so the menu button can badge it. One-way
 * increment only: a tally, not a precise counter, so no decrement/undo.
 */
export function DrinkCounter({ drinkType, count, onIncrement }: DrinkCounterProps) {
  const scale = useRef(new Animated.Value(1)).current;
  const floatAnim = useRef(new Animated.Value(0)).current;
  const [floatKey, setFloatKey] = useState(0);
  const [floating, setFloating] = useState(false);

  function handlePress() {
    onIncrement();

    scale.setValue(1);
    Animated.sequence([
      Animated.timing(scale, { toValue: 1.3, duration: 100, useNativeDriver: true }),
      Animated.timing(scale, { toValue: 1, duration: 100, useNativeDriver: true }),
    ]).start();

    setFloatKey((k) => k + 1);
    setFloating(true);
    floatAnim.setValue(0);
    Animated.timing(floatAnim, {
      toValue: 1,
      duration: 700,
      useNativeDriver: true,
    }).start(() => setFloating(false));
  }

  const floatTranslateY = floatAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [0, -28],
  });
  const floatOpacity = floatAnim.interpolate({
    inputRange: [0, 0.7, 1],
    outputRange: [1, 1, 0],
  });

  return (
    <View style={styles.row} testID="call-drink-counter">
      <View style={styles.icon}>
        <Text style={styles.iconText}>{DRINK_ICONS[drinkType]}</Text>
      </View>
      <View style={styles.body}>
        <Text style={styles.title}>Drink counter</Text>
        <Text style={styles.subtitle}>Tap + every time you top up</Text>
      </View>
      <View>
        <Animated.Text style={[styles.count, { transform: [{ scale }] }]}>{count}</Animated.Text>
        {floating && (
          <Animated.Text
            key={floatKey}
            style={[
              styles.plusOne,
              { opacity: floatOpacity, transform: [{ translateY: floatTranslateY }] },
            ]}
          >
            +1
          </Animated.Text>
        )}
      </View>
      <Pressable
        testID="call-drink-increment-button"
        style={styles.plusButton}
        onPress={handlePress}
        accessibilityLabel="Add a drink"
      >
        <Text style={styles.plusText}>+</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 16,
    padding: 14,
  },
  icon: {
    width: 42,
    height: 42,
    borderRadius: 12,
    backgroundColor: colors.surfaceSelected,
    alignItems: 'center',
    justifyContent: 'center',
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
  subtitle: {
    color: colors.textMuted,
    fontSize: 12,
    marginTop: 2,
  },
  count: {
    color: colors.primary,
    fontSize: 20,
    fontWeight: '700',
    minWidth: 24,
    textAlign: 'center',
  },
  plusOne: {
    position: 'absolute',
    top: -6,
    right: -10,
    color: colors.primary,
    fontWeight: '700',
    fontSize: 13,
  },
  plusButton: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  plusText: {
    color: colors.onPrimary,
    fontSize: 18,
    fontWeight: '700',
    lineHeight: 20,
  },
});
