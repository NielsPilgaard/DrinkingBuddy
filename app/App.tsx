import { StatusBar } from 'expo-status-bar';
import { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000';

type Status = { state: 'loading' } | { state: 'ok'; body: string } | { state: 'error'; message: string };

export default function App() {
  const [status, setStatus] = useState<Status>({ state: 'loading' });

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then(async (res) => {
        const body = await res.text();
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        setStatus({ state: 'ok', body });
      })
      .catch((err) => setStatus({ state: 'error', message: String(err) }));
  }, []);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>DrinkingBuddy</Text>
      <Text>API: {API_URL}</Text>
      {status.state === 'loading' && <Text>Checking backend...</Text>}
      {status.state === 'ok' && <Text style={styles.ok}>Backend healthy: {status.body}</Text>}
      {status.state === 'error' && <Text style={styles.error}>Backend unreachable: {status.message}</Text>}
      <StatusBar style="auto" />
    </View>
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
