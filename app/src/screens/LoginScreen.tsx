import { useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { requestLinkEndpointAuthRequestLinkPost } from '../api/generated/sdk.gen';
import { useAuth } from '../auth/context';
import { colors } from '../theme';

function isValidBirthdate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const [year, month, day] = value.split('-').map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  return (
    date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day
  );
}

/** Digits only, dashes inserted as you type: "19900101" -> "1990-01-01". */
function formatBirthdate(value: string): string {
  const digits = value.replace(/\D/g, '').slice(0, 8);
  return [digits.slice(0, 4), digits.slice(4, 6), digits.slice(6)].filter(Boolean).join('-');
}

export function LoginScreen() {
  const { verify } = useAuth();
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
      const { data, error: reqError } = await requestLinkEndpointAuthRequestLinkPost({
        body: {
          email: email.trim(),
          birthdate:
            birthdate.trim() && isValidBirthdate(birthdate.trim()) ? birthdate.trim() : null,
        },
        // Dev builds only: a backend with ENVIRONMENT=development echoes the
        // magic-link token back, so we sign in without opening the email.
        // Any other backend ignores the header (see backend app/routers/auth.py).
        headers: __DEV__ ? { 'x-test-mode': '1' } : undefined,
      });
      if (reqError) {
        setError(
          typeof reqError === 'object' && reqError && 'detail' in reqError
            ? String((reqError as { detail: unknown }).detail)
            : 'Something went wrong. Try again.',
        );
        return;
      }
      if (data?.debug_token) {
        await verify(data.debug_token);
        return;
      }
      setLinkSent(true);
    } finally {
      setSubmitting(false);
    }
  }

  if (linkSent) {
    return (
      <View style={styles.container} testID="login-link-sent">
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
        testID="login-email-input"
        style={styles.input}
        placeholder="Email"
        placeholderTextColor={colors.textMuted}
        keyboardAppearance="dark"
        autoCapitalize="none"
        autoComplete="email"
        keyboardType="email-address"
        value={email}
        onChangeText={setEmail}
      />
      <TextInput
        testID="login-birthdate-input"
        style={styles.input}
        placeholder="Birthdate (YYYY-MM-DD) — first time only"
        placeholderTextColor={colors.textMuted}
        keyboardAppearance="dark"
        keyboardType="number-pad"
        maxLength={10}
        value={birthdate}
        onChangeText={(value) => setBirthdate(formatBirthdate(value))}
      />
      {error && <Text style={styles.error}>{error}</Text>}
      <Pressable
        testID="login-submit-button"
        style={[styles.button, !canSubmit && styles.buttonDisabled]}
        onPress={handleSubmit}
        disabled={!canSubmit}
      >
        {submitting ? (
          <ActivityIndicator color={colors.onPrimary} />
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
    // The parent centers its children; stretch so the inputs get full width.
    alignSelf: 'stretch',
    backgroundColor: colors.background,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
    paddingHorizontal: 24,
  },
  title: {
    color: colors.text,
    fontSize: 24,
    fontWeight: 'bold',
  },
  subtitle: {
    textAlign: 'center',
    color: colors.textMuted,
  },
  input: {
    width: '100%',
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
    color: colors.text,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  button: {
    width: '100%',
    backgroundColor: colors.primary,
    borderRadius: 8,
    paddingVertical: 12,
    alignItems: 'center',
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  buttonText: {
    color: colors.onPrimary,
    fontWeight: '600',
  },
  error: {
    color: colors.danger,
    textAlign: 'center',
  },
});
