import { useRef, useState } from 'react';
import { Animated, Pressable, StyleSheet, Text } from 'react-native';

type DrinkCounterProps = {
  drinkType: 'alcoholic' | 'non_alcoholic';
};

const ICONS: Record<DrinkCounterProps['drinkType'], string> = {
  alcoholic: '🍺',
  non_alcoholic: '🥤',
};

export function DrinkCounter({ drinkType }: DrinkCounterProps) {
  const [count, setCount] = useState(0);
  const scale = useRef(new Animated.Value(1)).current;
  const floatAnim = useRef(new Animated.Value(0)).current;
  const [floatKey, setFloatKey] = useState(0);
  const [floating, setFloating] = useState(false);

  function handlePress() {
    setCount((c) => c + 1);

    scale.setValue(1);
    Animated.sequence([
      Animated.timing(scale, { toValue: 1.25, duration: 100, useNativeDriver: true }),
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
    outputRange: [0, -32],
  });
  const floatOpacity = floatAnim.interpolate({
    inputRange: [0, 0.7, 1],
    outputRange: [1, 1, 0],
  });

  return (
    <Pressable style={styles.wrapper} onPress={handlePress}>
      <Animated.View style={[styles.badge, { transform: [{ scale }] }]}>
        <Text style={styles.badgeText}>
          {ICONS[drinkType]} {count}
        </Text>
      </Animated.View>
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
    </Pressable>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    position: 'absolute',
    top: 48,
    left: 16,
  },
  badge: {
    backgroundColor: 'rgba(23,23,29,0.85)',
    borderRadius: 999,
    paddingHorizontal: 14,
    paddingVertical: 8,
  },
  badgeText: {
    color: '#f2f2f5',
    fontWeight: '700',
    fontSize: 16,
  },
  plusOne: {
    position: 'absolute',
    top: -4,
    right: -8,
    color: '#ffb020',
    fontWeight: '700',
    fontSize: 14,
  },
});
