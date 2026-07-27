import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { StatusBar } from 'expo-status-bar';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';
import { healthHealthGetOptions } from './src/api/generated/@tanstack/react-query.gen';
import { configureApiClient } from './src/api/setup';
import { AuthProvider, useAuth } from './src/auth/context';
import { LoginScreen } from './src/screens/LoginScreen';

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000';
configureApiClient(API_URL);

const queryClient = new QueryClient();

function HealthCheck() {
  const { data, error, isLoading } = useQuery(healthHealthGetOptions());

  return (
    <View style={styles.container}>
      <Text style={styles.title}>DrinkingBuddy</Text>
      <Text>API: {API_URL}</Text>
      {isLoading && <Text>Checking backend...</Text>}
      {data && <Text style={styles.ok}>Backend healthy: {JSON.stringify(data)}</Text>}
      {error && <Text style={styles.error}>Backend unreachable: {String(error)}</Text>}
      <StatusBar style="auto" />
    </View>
  );
}

function Root() {
  const auth = useAuth();

  if (auth.status === 'loading' || auth.status === 'verifying') {
    return (
      <View style={styles.container}>
        <ActivityIndicator />
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

  return (
    <>
      <HealthCheck />
      <StatusBar style="auto" />
    </>
  );
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
    backgroundColor: '#fff',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
  },
  ok: {
    color: 'green',
  },
  error: {
    color: 'red',
    textAlign: 'center',
    paddingHorizontal: 24,
  },
});
