import { useState, type ReactElement } from 'react';
import { Pressable, StyleSheet, Text, TextInput } from 'react-native';
import { useRouter, type Href } from 'expo-router';
import { ApiContractUnavailableError } from '@/api/hooks';
import { Screen } from '@/components';
import { useTranslation } from '@/i18n/useTranslation';
import { spacing, typography, useThemeColors } from '@/theme/tokens';
import { useAuth } from './AuthProvider';

interface AuthFormProps {
  mode: 'sign-in' | 'sign-up';
}

export function AuthForm({ mode }: AuthFormProps): ReactElement {
  const { t } = useTranslation();
  const colors = useThemeColors();
  const router = useRouter();
  const { signIn, signUp, isReady } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const signingUp = mode === 'sign-up';

  async function submit(): Promise<void> {
    if (!isReady) return;
    setError('');
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      setError(t('auth.invalid_email'));
      return;
    }
    if (password.length < 8) {
      setError(t('auth.password_required'));
      return;
    }
    if (signingUp && !displayName.trim()) {
      setError(t('auth.name_required'));
      return;
    }
    setBusy(true);
    try {
      if (signingUp) await signUp(email, password, displayName);
      else await signIn(email, password);
      router.replace('/' as Href);
    } catch (cause) {
      const status =
        typeof cause === 'object' && cause !== null && 'status' in cause ? cause.status : undefined;
      if (status === 409) setError(t('auth.duplicate_email'));
      else if (status === 401) setError(t('auth.invalid_credentials'));
      else if (cause instanceof ApiContractUnavailableError)
        setError(t('auth.contract_unavailable'));
      else setError(t('errors.generic_description'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen contentContainerStyle={styles.screen}>
      <Text accessibilityRole="header" style={[styles.heading, { color: colors.text }]}>
        {t(signingUp ? 'auth.sign_up' : 'auth.sign_in')}
      </Text>
      {signingUp ? (
        <TextInput
          accessibilityLabel={t('auth.display_name')}
          autoCapitalize="words"
          value={displayName}
          onChangeText={setDisplayName}
          placeholder={t('auth.display_name')}
          style={[
            styles.input,
            { backgroundColor: colors.surface, color: colors.text, borderColor: colors.border },
          ]}
        />
      ) : null}
      <TextInput
        accessibilityLabel={t('auth.email')}
        autoCapitalize="none"
        autoComplete="email"
        keyboardType="email-address"
        value={email}
        onChangeText={setEmail}
        placeholder={t('auth.email')}
        style={[
          styles.input,
          { backgroundColor: colors.surface, color: colors.text, borderColor: colors.border },
        ]}
      />
      <TextInput
        accessibilityLabel={t('auth.password')}
        autoComplete={signingUp ? 'new-password' : 'password'}
        secureTextEntry
        value={password}
        onChangeText={setPassword}
        placeholder={t('auth.password')}
        style={[
          styles.input,
          { backgroundColor: colors.surface, color: colors.text, borderColor: colors.border },
        ]}
      />
      {error ? (
        <Text accessibilityRole="alert" style={{ color: colors.high }}>
          {error}
        </Text>
      ) : null}
      <Pressable
        accessibilityRole="button"
        accessibilityState={{ disabled: busy || !isReady }}
        disabled={busy || !isReady}
        onPress={() => void submit()}
        style={[styles.button, { backgroundColor: colors.primary, opacity: busy ? 0.65 : 1 }]}
      >
        <Text style={[styles.buttonText, { color: colors.onPrimary }]}>
          {t(signingUp ? 'auth.submit_sign_up' : 'auth.submit_sign_in')}
        </Text>
      </Pressable>
      <Pressable
        accessibilityRole="link"
        onPress={() =>
          router.replace((signingUp ? '/auth/sign-in' : '/auth/sign-up') as unknown as Href)
        }
        style={styles.switch}
      >
        <Text style={[styles.switchText, { color: colors.primary }]}>
          {t(signingUp ? 'auth.switch_sign_in' : 'auth.switch_sign_up')}
        </Text>
      </Pressable>
    </Screen>
  );
}

const styles = StyleSheet.create({
  screen: { flexGrow: 1, justifyContent: 'center', gap: spacing.lg, padding: spacing.xl },
  heading: {
    fontSize: typography.size.xl,
    lineHeight: typography.lineHeight.xl,
    fontWeight: typography.weight.bold,
  },
  input: {
    minHeight: 48,
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: spacing.md,
    fontSize: typography.size.md,
  },
  button: {
    minHeight: 48,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.lg,
    borderRadius: 12,
  },
  buttonText: { fontSize: typography.size.md, fontWeight: typography.weight.semibold },
  switch: { minHeight: 44, justifyContent: 'center' },
  switchText: { fontSize: typography.size.md },
});
