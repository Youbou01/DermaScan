import { useRouter, type Href } from 'expo-router';
import { useState, type ReactElement } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { Screen } from '@/components';
import { useTranslation } from '@/i18n/useTranslation';
import { radii, spacing, typography, useThemeColors } from '@/theme/tokens';
import { AuthActionError, useAuth } from './AuthContext';

export interface AuthScreenProps {
  readonly initialMode?: 'login' | 'register';
}

const EMAIL_REGEX = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export function AuthScreen({ initialMode = 'login' }: AuthScreenProps): ReactElement {
  const router = useRouter();
  const colors = useThemeColors();
  const { t } = useTranslation();
  const { signIn, register } = useAuth();

  const [mode, setMode] = useState<'login' | 'register'>(initialMode);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isRegister = mode === 'register';

  const handleSubmit = async (): Promise<void> => {
    const trimmedEmail = email.trim();
    if (!EMAIL_REGEX.test(trimmedEmail) || password.length < 8) {
      setErrorMessage(t('auth.validation_error'));
      return;
    }
    if (isRegister && !displayName.trim()) {
      setErrorMessage(t('auth.name_required_error'));
      return;
    }

    setErrorMessage(null);
    setIsSubmitting(true);
    try {
      if (isRegister) {
        await register(trimmedEmail, password, displayName);
      } else {
        await signIn(trimmedEmail, password);
      }
      router.replace('/profile' as unknown as Href);
    } catch (err) {
      if (err instanceof AuthActionError && err.code === 'email-already-registered') {
        setErrorMessage(t('auth.email_taken'));
      } else {
        setErrorMessage(t('auth.invalid_credentials'));
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Screen contentContainerStyle={styles.content}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={t('auth.back_home')}
        onPress={() => router.push('/' as unknown as Href)}
        style={[styles.backButton, { borderColor: colors.border }]}
      >
        <Text style={[styles.backText, { color: colors.primary }]}>‹ {t('auth.back_home')}</Text>
      </Pressable>

      <Text accessibilityRole="header" style={[styles.title, { color: colors.text }]}>
        {isRegister ? t('auth.register_title') : t('auth.sign_in_title')}
      </Text>
      <Text style={[styles.subtitle, { color: colors.textMuted }]}>{t('auth.subtitle')}</Text>

      {isRegister ? (
        <View style={styles.fieldGroup}>
          <Text style={[styles.label, { color: colors.text }]}>{t('auth.display_name_label')}</Text>
          <TextInput
            accessibilityLabel={t('auth.display_name_label')}
            autoCapitalize="words"
            onChangeText={(val) => {
              setDisplayName(val);
              setErrorMessage(null);
            }}
            placeholder={t('auth.display_name_placeholder')}
            placeholderTextColor={colors.textMuted}
            style={[
              styles.input,
              {
                color: colors.text,
                backgroundColor: colors.surface,
                borderColor: colors.border,
              },
            ]}
            value={displayName}
          />
        </View>
      ) : null}

      <View style={styles.fieldGroup}>
        <Text style={[styles.label, { color: colors.text }]}>{t('auth.email_label')}</Text>
        <TextInput
          accessibilityLabel={t('auth.email_label')}
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="email-address"
          onChangeText={(val) => {
            setEmail(val);
            setErrorMessage(null);
          }}
          placeholder={t('auth.email_placeholder')}
          placeholderTextColor={colors.textMuted}
          style={[
            styles.input,
            {
              color: colors.text,
              backgroundColor: colors.surface,
              borderColor: colors.border,
            },
          ]}
          value={email}
        />
      </View>

      <View style={styles.fieldGroup}>
        <Text style={[styles.label, { color: colors.text }]}>{t('auth.password_label')}</Text>
        <TextInput
          accessibilityLabel={t('auth.password_label')}
          autoCapitalize="none"
          onChangeText={(val) => {
            setPassword(val);
            setErrorMessage(null);
          }}
          placeholder={t('auth.password_placeholder')}
          placeholderTextColor={colors.textMuted}
          secureTextEntry
          style={[
            styles.input,
            {
              color: colors.text,
              backgroundColor: colors.surface,
              borderColor: colors.border,
            },
          ]}
          value={password}
        />
      </View>

      {errorMessage ? (
        <Text accessibilityRole="alert" style={[styles.errorText, { color: colors.high }]}>
          {errorMessage}
        </Text>
      ) : null}

      <Pressable
        accessibilityRole="button"
        accessibilityLabel={isRegister ? t('auth.register_button') : t('auth.sign_in_button')}
        disabled={isSubmitting}
        onPress={() => {
          void handleSubmit();
        }}
        style={({ pressed }) => [
          styles.primaryButton,
          {
            backgroundColor: colors.primary,
            opacity: pressed || isSubmitting ? 0.75 : 1,
          },
        ]}
      >
        <Text style={[styles.primaryButtonText, { color: colors.onPrimary }]}>
          {isRegister ? t('auth.register_button') : t('auth.sign_in_button')}
        </Text>
      </Pressable>

      <Pressable
        accessibilityRole="button"
        accessibilityLabel={isRegister ? t('auth.switch_to_sign_in') : t('auth.switch_to_register')}
        onPress={() => {
          setMode(isRegister ? 'login' : 'register');
          setErrorMessage(null);
        }}
        style={[styles.secondaryButton, { borderColor: colors.border }]}
      >
        <Text style={[styles.secondaryButtonText, { color: colors.primary }]}>
          {isRegister ? t('auth.switch_to_sign_in') : t('auth.switch_to_register')}
        </Text>
      </Pressable>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, gap: spacing.md, paddingBottom: spacing.xxxl },
  backButton: {
    minHeight: 44,
    alignSelf: 'flex-start',
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  backText: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
  title: {
    fontSize: typography.size.xl,
    lineHeight: typography.lineHeight.xl,
    fontWeight: typography.weight.bold,
  },
  subtitle: {
    fontSize: typography.size.sm,
    lineHeight: typography.lineHeight.sm,
  },
  fieldGroup: {
    gap: spacing.xs,
  },
  label: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
  input: {
    minHeight: 48,
    borderWidth: 1,
    borderRadius: radii.md,
    paddingHorizontal: spacing.md,
    fontSize: typography.size.md,
  },
  errorText: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.medium,
  },
  primaryButton: {
    minHeight: 48,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.md,
    paddingHorizontal: spacing.lg,
    marginTop: spacing.xs,
  },
  primaryButtonText: {
    fontSize: typography.size.md,
    fontWeight: typography.weight.semibold,
  },
  secondaryButton: {
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderRadius: radii.md,
    paddingHorizontal: spacing.md,
  },
  secondaryButtonText: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
});
