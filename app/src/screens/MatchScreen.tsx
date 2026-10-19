import { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { useAuth } from '../auth/context';
import {
  DEFAULT_FILTERS,
  DRINK_TYPES,
  type Filters,
  getStoredFilters,
  LANGUAGES,
  setStoredFilters,
} from '../call/filters';
import { type MatchResult, useMatching } from '../call/useMatching';
import { colors } from '../theme';
import { CallEndedScreen } from './CallEndedScreen';
import { CallScreen } from './CallScreen';

type MatchScreenProps = {
  apiBaseUrl: string;
  sessionToken: string;
  userId: string;
};

type OptionRowProps<T extends string> = {
  label: string;
  testIDPrefix: string;
  options: { value: T; label: string }[];
  selected: T;
  onSelect: (value: T) => void;
};

function OptionRow<T extends string>({
  label,
  testIDPrefix,
  options,
  selected,
  onSelect,
}: OptionRowProps<T>) {
  return (
    <View style={styles.optionGroup}>
      <Text style={styles.optionLabel}>{label}</Text>
      <View style={styles.optionRow}>
        {options.map((option) => {
          const isSelected = option.value === selected;
          return (
            <Pressable
              key={option.value}
              testID={`${testIDPrefix}-${option.value}`}
              accessibilityRole="radio"
              accessibilityState={{ selected: isSelected }}
              style={[styles.option, isSelected && styles.optionSelected]}
              onPress={() => onSelect(option.value)}
            >
              <Text style={[styles.optionText, isSelected && styles.optionTextSelected]}>
                {option.label}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

export function MatchScreen({ apiBaseUrl, sessionToken, userId }: MatchScreenProps) {
  const { status, match, join, widenSearch, leave } = useMatching(apiBaseUrl, sessionToken, userId);
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [endedMatch, setEndedMatch] = useState<MatchResult | null>(null);
  const { signOut } = useAuth();

  useEffect(() => {
    getStoredFilters()
      .then(setFilters)
      .catch(() => {});
  }, []);

  // The session expired or was revoked: back to the login screen.
  useEffect(() => {
    if (status === 'unauthenticated') signOut();
  }, [status, signOut]);

  const updateFilters = (next: Filters) => {
    setFilters(next);
    setStoredFilters(next).catch(() => {});
  };

  if (status === 'suspended') {
    return (
      <View style={styles.container}>
        <Text style={styles.status}>
          Your account is temporarily suspended pending review. Try again later.
        </Text>
      </View>
    );
  }

  if (endedMatch) {
    return (
      <CallEndedScreen
        partnerId={endedMatch.partnerId}
        callId={endedMatch.callId}
        onContinue={() => {
          setEndedMatch(null);
          join(filters);
        }}
        onBack={() => {
          setEndedMatch(null);
          // Without leave(), status stays 'matched' and the call re-renders.
          leave();
        }}
      />
    );
  }

  if (status === 'matched' && match) {
    return (
      <CallScreen
        apiBaseUrl={apiBaseUrl}
        sessionToken={sessionToken}
        callId={match.callId}
        partnerId={match.partnerId}
        isInitiator={match.isInitiator}
        videoEligible={match.videoEligible}
        drinkType={filters.drink_type}
        language={filters.language}
        onSkip={() => join(filters)}
        onCallEnded={() => setEndedMatch(match)}
      />
    );
  }

  return (
    <View style={styles.container} testID="match-screen">
      {status === 'idle' ? (
        <>
          <OptionRow
            label="Language"
            testIDPrefix="match-language"
            options={LANGUAGES}
            selected={filters.language}
            onSelect={(language) => updateFilters({ ...filters, language })}
          />
          <OptionRow
            label="What's in your glass?"
            testIDPrefix="match-drink"
            options={DRINK_TYPES}
            selected={filters.drink_type}
            onSelect={(drink_type) => updateFilters({ ...filters, drink_type })}
          />
          <Pressable
            testID="match-find-button"
            style={[styles.button, styles.findButton]}
            onPress={() => join(filters)}
          >
            <Text style={styles.buttonText}>Find a match</Text>
          </Pressable>
        </>
      ) : status === 'widen_prompt' ? (
        <>
          <Text style={styles.status}>
            No one found yet. Match with people who speak any language?
          </Text>
          <Pressable
            testID="match-widen-search-button"
            style={styles.button}
            onPress={() => widenSearch(filters)}
          >
            <Text style={styles.buttonText}>Any language</Text>
          </Pressable>
          <Pressable
            testID="match-keep-waiting-button"
            style={styles.secondaryButton}
            onPress={() => join(filters)}
          >
            <Text style={styles.secondaryButtonText}>Keep waiting</Text>
          </Pressable>
          <Pressable testID="match-cancel-button" style={styles.secondaryButton} onPress={leave}>
            <Text style={styles.secondaryButtonText}>Cancel</Text>
          </Pressable>
        </>
      ) : (
        <>
          <ActivityIndicator color={colors.textMuted} />
          <Text style={styles.status}>Looking for a match…</Text>
          <Pressable testID="match-cancel-button" style={styles.secondaryButton} onPress={leave}>
            <Text style={styles.secondaryButtonText}>Cancel</Text>
          </Pressable>
        </>
      )}
      <Pressable testID="match-sign-out-button" style={styles.signOut} onPress={signOut}>
        <Text style={styles.signOutText}>Sign out</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
  },
  status: {
    color: colors.text,
    textAlign: 'center',
    paddingHorizontal: 24,
  },
  optionGroup: {
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
  },
  optionLabel: {
    color: colors.textMuted,
  },
  optionRow: {
    flexDirection: 'row',
    gap: 8,
  },
  option: {
    backgroundColor: colors.surface,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.surface,
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  optionSelected: {
    borderColor: colors.primary,
    backgroundColor: colors.surfaceSelected,
  },
  button: {
    backgroundColor: colors.primary,
    borderRadius: 8,
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  findButton: {
    marginTop: 12,
  },
  secondaryButton: {
    backgroundColor: colors.surface,
    borderRadius: 8,
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  buttonText: {
    color: colors.onPrimary,
    fontWeight: '600',
  },
  secondaryButtonText: {
    color: colors.text,
    fontWeight: '600',
  },
  optionText: {
    color: colors.text,
    fontWeight: '600',
  },
  optionTextSelected: {
    color: colors.primary,
  },
  signOut: {
    position: 'absolute',
    bottom: 48,
    padding: 12,
  },
  signOutText: {
    color: colors.textMuted,
  },
});
