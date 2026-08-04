import { useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { requestLinkEndpointAuthRequestLinkPost } from '../api/generated/sdk.gen';

function isValidBirthdate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const [year, month, day] = value.split('-').map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  return (
    date.getUTCFullYear() === year &&
    date.getUTCMonth() === month - 1 &&
    date.getUTCDate() === day
  );
}

export function LoginScreen() {
  const [email, setEmail] = useState('');
  const [birthdate, setBirthdate] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [linkSent, setLinkSent] = useState(false);

  const canSubmit = email.trim().length > 0 && !submitting;

  async function handleSubmit() {
    setError(null);
    setSubmitting(true);
    try {
      const { error: reqError } = await requestLinkEndpointAuthRequestLinkPost({
        body: {
          email: email.trim(),
          birthdate:
            birthdate.trim() && isValidBirthdate(birthdate.trim()) ? birthdate.trim() : null,
        },
      });
      if (reqError) {
        setError(
          typeof reqError === 'object' && reqError && 'detail' in reqError
            ? String((reqError as { detail: unknown }).detail)
            : 'Something went wrong. Try again.',
        );
        return;
      }
      setLinkSent(true);
    } finally {
      setSubmitting(false);
    }
  }

  if (linkSent) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>Check your email</Text>
        <Text style={styles.subtitle}>
          We sent a sign-in link to {email.trim()}. Open it on this device to continue.
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>DrinkingBuddy</Text>
      <TextInput
        style={styles.input}
        placeholder="Email"
        autoCapitalize="none"
        autoComplete="email"
        keyboardType="email-address"
        value={email}
        onChangeText={setEmail}
      />
      <TextInput
        style={styles.input}
        placeholder="Birthdate (YYYY-MM-DD) — first time only"
        autoCapitalize="none"
        value={birthdate}
        onChangeText={setBirthdate}
      />
      {error && <Text style={styles.error}>{error}</Text>}
      <Pressable
        style={[styles.button, !canSubmit && styles.buttonDisabled]}
        onPress={handleSubmit}
        disabled={!canSubmit}
      >
        {submitting ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.buttonText}>Send sign-in link</Text>
        )}
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
    paddingHorizontal: 24,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
  },
  subtitle: {
    textAlign: 'center',
    color: '#444',
  },
  input: {
    width: '100%',
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  button: {
    width: '100%',
    backgroundColor: '#2563eb',
    borderRadius: 8,
    paddingVertical: 12,
    alignItems: 'center',
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  buttonText: {
    color: '#fff',
    fontWeight: '600',
  },
  error: {
    color: 'red',
    textAlign: 'center',
  },
});
