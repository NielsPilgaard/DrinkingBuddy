import { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { useAuth } from '../auth/context';
import { type Filters, type MatchResult, useMatching } from '../call/useMatching';
import { CallEndedScreen } from './CallEndedScreen';
import { CallScreen } from './CallScreen';

type MatchScreenProps = {
  apiBaseUrl: string;
  sessionToken: string;
  userId: string;
};

const DEFAULT_FILTERS: Filters = {
  language: 'en',
  drink_type: 'alcoholic',
  location: 'dk',
};

export function MatchScreen({ apiBaseUrl, sessionToken, userId }: MatchScreenProps) {
  const { status, match, join, widenSearch, leave } = useMatching(apiBaseUrl, sessionToken, userId);
  const [endedMatch, setEndedMatch] = useState<MatchResult | null>(null);
  const { signOut } = useAuth();

  useEffect(() => {
    join(DEFAULT_FILTERS);
    return () => leave();
  }, [join, leave]);

  // The session expired or was revoked: back to the login screen.
  useEffect(() => {
    if (status === 'unauthenticated') signOut();
  }, [status, signOut]);

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
          join(DEFAULT_FILTERS);
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
        drinkType={DEFAULT_FILTERS.drink_type}
        onCallEnded={() => setEndedMatch(match)}
      />
    );
  }

  return (
    <View style={styles.container} testID="match-screen">
      {status === 'widen_prompt' ? (
        <>
          <Text style={styles.status}>No one found nearby. Search all regions instead?</Text>
          <Pressable
            testID="match-widen-search-button"
            style={styles.button}
            onPress={() => widenSearch(DEFAULT_FILTERS)}
          >
            <Text style={styles.buttonText}>Widen search</Text>
          </Pressable>
          <Pressable
            testID="match-keep-waiting-button"
            style={styles.secondaryButton}
            onPress={() => join(DEFAULT_FILTERS)}
          >
            <Text style={styles.buttonText}>Keep waiting</Text>
          </Pressable>
        </>
      ) : (
        <>
          <ActivityIndicator />
          <Text style={styles.status}>Looking for a match…</Text>
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
    backgroundColor: '#050506',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
  },
  status: {
    color: '#f2f2f5',
  },
  button: {
    backgroundColor: '#2563eb',
    borderRadius: 8,
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  secondaryButton: {
    backgroundColor: '#1f1f28',
    borderRadius: 8,
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  buttonText: {
    color: '#fff',
    fontWeight: '600',
  },
  signOut: {
    position: 'absolute',
    bottom: 48,
    padding: 12,
  },
  signOutText: {
    color: '#8a8a96',
  },
});
