import React, { useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';

import { AppText, Button, ErrorBanner, LanguageSwitch, Screen, TextField } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import type { AuthStackParams } from '../navigation/RootNavigator';
import { spacing } from '../theme';
import { errorMessage } from './errorMessage';

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MIN_PASSWORD = 10; // matches the API's rule

type Errors = Partial<Record<'email' | 'password' | 'fullName', string>>;

function Layout({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <Screen>
      <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
          <LanguageSwitch />
          <View style={styles.heading}>
            <AppText variant="title" accessibilityRole="header">
              {title}
            </AppText>
            <AppText muted>{subtitle}</AppText>
          </View>
          {children}
        </ScrollView>
      </KeyboardAvoidingView>
    </Screen>
  );
}

export function LoginScreen({ navigation }: NativeStackScreenProps<AuthStackParams, 'Login'>) {
  const { t } = useTranslation();
  const { signIn, notice } = useApp();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState<Errors>({});
  const [failure, setFailure] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    const found: Errors = {};
    if (!email.trim()) {
      found.email = 'validation.emailRequired';
    } else if (!EMAIL.test(email.trim())) {
      found.email = 'validation.emailInvalid';
    }
    if (!password) {
      found.password = 'validation.passwordRequired';
    }
    setErrors(found);
    if (Object.keys(found).length) {
      return;
    }
    setBusy(true);
    setFailure(null);
    try {
      await signIn(email.trim(), password);
    } catch (error) {
      setFailure(error);
      setBusy(false);
    }
  };

  // Stored as keys and translated on render, so a visible error follows a language switch.
  const banner = failure ? errorMessage(failure, t) : notice ? t(`errors.${notice}`) : null;

  return (
    <Layout title={t('auth.signInTitle')} subtitle={t('auth.signInSubtitle')}>
      <ErrorBanner message={banner} />
      <TextField
        label={t('auth.email')}
        value={email}
        onChangeText={setEmail}
        error={errors.email && t(errors.email)}
        autoCapitalize="none"
        autoCorrect={false}
        keyboardType="email-address"
        textContentType="username"
        autoComplete="email"
        testID="email"
      />
      <TextField
        label={t('auth.password')}
        value={password}
        onChangeText={setPassword}
        error={errors.password && t(errors.password)}
        secureTextEntry
        textContentType="password"
        autoComplete="current-password"
        onSubmitEditing={submit}
        testID="password"
      />
      <Button label={t('auth.signIn')} onPress={submit} loading={busy} testID="submit" />
      <Button kind="link" label={t('auth.noAccount')} onPress={() => navigation.navigate('Register')} testID="go-register" />
    </Layout>
  );
}

export function RegisterScreen({ navigation }: NativeStackScreenProps<AuthStackParams, 'Register'>) {
  const { t } = useTranslation();
  const { register } = useApp();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState<Errors>({});
  const [failure, setFailure] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    const found: Errors = {};
    if (!fullName.trim()) {
      found.fullName = 'validation.nameRequired';
    }
    if (!email.trim()) {
      found.email = 'validation.emailRequired';
    } else if (!EMAIL.test(email.trim())) {
      found.email = 'validation.emailInvalid';
    }
    if (password.length < MIN_PASSWORD) {
      found.password = 'validation.passwordShort';
    }
    setErrors(found);
    if (Object.keys(found).length) {
      return;
    }
    setBusy(true);
    setFailure(null);
    try {
      await register({ email: email.trim(), password, fullName: fullName.trim() });
    } catch (error) {
      setFailure(error);
      setBusy(false);
    }
  };

  return (
    <Layout title={t('auth.registerTitle')} subtitle={t('auth.registerSubtitle')}>
      <ErrorBanner message={failure ? errorMessage(failure, t) : null} />
      <TextField
        label={t('auth.fullName')}
        value={fullName}
        onChangeText={setFullName}
        error={errors.fullName && t(errors.fullName)}
        textContentType="name"
        autoComplete="name"
        testID="full-name"
      />
      <TextField
        label={t('auth.email')}
        value={email}
        onChangeText={setEmail}
        error={errors.email && t(errors.email)}
        autoCapitalize="none"
        autoCorrect={false}
        keyboardType="email-address"
        textContentType="username"
        autoComplete="email"
        testID="email"
      />
      <TextField
        label={t('auth.password')}
        value={password}
        onChangeText={setPassword}
        error={errors.password && t(errors.password)}
        hint={t('auth.passwordHint')}
        secureTextEntry
        textContentType="newPassword"
        autoComplete="new-password"
        onSubmitEditing={submit}
        testID="password"
      />
      <Button label={t('auth.register')} onPress={submit} loading={busy} testID="submit" />
      <Button kind="link" label={t('auth.haveAccount')} onPress={() => navigation.goBack()} testID="go-login" />
    </Layout>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  content: { padding: spacing.lg, gap: spacing.md },
  heading: { gap: spacing.xs, marginTop: spacing.lg, marginBottom: spacing.sm },
});
