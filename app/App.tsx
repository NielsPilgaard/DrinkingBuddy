import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { resolveApiUrl } from './src/api/baseUrl';
import { configureApiClient } from './src/api/setup';
import { AuthProvider, useAuth } from './src/auth/context';
import { LoginScreen } from './src/screens/LoginScreen';
import { MatchScreen } from './src/screens/MatchScreen';
import { colors } from './src/theme';

const API_URL = resolveApiUrl();
configureApiClient(API_URL);

const queryClient = new QueryClient();

function Root() {
  const auth = useAuth();

  if (auth.status === 'loading' || auth.status === 'verifying') {
    return (
      <View style={styles.container}>
        <ActivityIndicator color={colors.textMuted} />
      </View>
    );
  }

  if (auth.status === 'verify-suspended') {
    return (
      <View style={styles.container}>
        <Text style={styles.error}>
          Your account is temporarily suspended pending review. Try again later.
        </Text>
      </View>
    );
  }

  if (auth.status === 'locked') {
    return (
      <View style={styles.container} testID="app-locked-screen">
        <Text style={styles.title}>Unlock to continue</Text>
        <Pressable style={styles.button} onPress={auth.retryUnlock}>
          <Text style={styles.buttonText}>Try again</Text>
        </Pressable>
      </View>
    );
  }

  if (auth.status === 'signed-out' || auth.status === 'verify-failed') {
    return (
      <View style={styles.container}>
        {auth.status === 'verify-failed' && (
          <Text style={styles.error}>Sign-in link was invalid or expired. Try again.</Text>
        )}
        <LoginScreen />
      </View>
    );
  }

  return <MatchScreen apiBaseUrl={API_URL} sessionToken={auth.sessionToken} userId={auth.userId} />;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Root />
      </AuthProvider>
    </QueryClientProvider>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  error: {
    color: colors.danger,
    textAlign: 'center',
    paddingHorizontal: 24,
  },
  title: {
    color: colors.text,
    fontSize: 20,
    fontWeight: 'bold',
  },
  button: {
    backgroundColor: colors.primary,
    borderRadius: 8,
    paddingVertical: 12,
    paddingHorizontal: 24,
  },
  buttonText: {
    color: colors.onPrimary,
    fontWeight: '600',
  },
});
