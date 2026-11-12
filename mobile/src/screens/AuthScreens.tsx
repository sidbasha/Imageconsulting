import React, { useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';

import type { Gender } from '../api/client';
import { AppText, Button, Chips, ErrorBanner, LanguageSwitch, Screen, TextField } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import type { AuthStackParams } from '../navigation/RootNavigator';
import { colors, fonts, gradients, radius, shadows, spacing } from '../theme';
import { errorMessage } from './errorMessage';

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MIN_PASSWORD = 10; // matches the API's rule

type Errors = Partial<Record<'email' | 'password' | 'fullName' | 'dateOfBirth' | 'gender', string>>;
const DATE = /^\d{4}-\d{2}-\d{2}$/;

function Layout({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  const { t } = useTranslation();
  return (
    <Screen>
      <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
          <View style={[styles.hero, { backgroundImage: gradients.hero, boxShadow: shadows.lifted }]}>
            <View style={styles.orbLarge} />
            <View style={styles.orbSmall} />
            <LanguageSwitch />
            <View style={styles.monogram}>
              <Text style={styles.monogramText}>IC</Text>
            </View>
            <Text style={styles.brand}>{t('auth.brand')}</Text>
          </View>
          <View style={[styles.sheet, { boxShadow: shadows.soft }]}>
            <View style={styles.heading}>
              <AppText variant="title" accessibilityRole="header">
                {title}
              </AppText>
              <AppText muted>{subtitle}</AppText>
            </View>
            {children}
          </View>
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
  const [dateOfBirth, setDateOfBirth] = useState('');
  const [gender, setGender] = useState<Gender | null>(null);
  const [errors, setErrors] = useState<Errors>({});
  const [failure, setFailure] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    const found: Errors = {};
    if (!DATE.test(dateOfBirth.trim()) || Number.isNaN(Date.parse(dateOfBirth.trim()))) {
      found.dateOfBirth = 'validation.dateInvalid';
    }
    if (!gender) {
      found.gender = 'validation.genderRequired';
    }
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
      // The UAE is the only market at launch (Feature List row 3); more appear in the profile later.
      await register({
        email: email.trim(), password, fullName: fullName.trim(),
        dateOfBirth: dateOfBirth.trim(), gender: gender ?? undefined, countryCode: 'AE',
      });
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
      <TextField
        label={t('profile.dob')}
        hint={t('profile.dobHint')}
        value={dateOfBirth}
        onChangeText={setDateOfBirth}
        error={errors.dateOfBirth && t(errors.dateOfBirth)}
        keyboardType="numbers-and-punctuation"
        testID="dob"
      />
      <Chips
        label={t('profile.gender')}
        value={gender}
        onChange={setGender}
        testID="gender"
        options={[{ value: 'female', label: t('profile.female') }, { value: 'male', label: t('profile.male') }]}
      />
      {errors.gender ? <ErrorBanner message={t(errors.gender)} /> : null}
      <AppText variant="small" muted>
        {t('auth.eligibilityNote')}
      </AppText>
      <Button label={t('auth.register')} onPress={submit} loading={busy} testID="submit" />
      <Button kind="link" label={t('auth.haveAccount')} onPress={() => navigation.goBack()} testID="go-login" />
    </Layout>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  content: { padding: spacing.md, gap: 0, paddingBottom: spacing.xl * 2 },
  hero: { borderRadius: radius.xl, padding: spacing.lg, paddingBottom: spacing.xl * 2, alignItems: 'center', gap: spacing.md, overflow: 'hidden' },
  orbLarge: { position: 'absolute', width: 240, height: 240, borderRadius: 120, backgroundColor: 'rgba(255,255,255,0.12)', top: -80, right: -70 },
  orbSmall: { position: 'absolute', width: 140, height: 140, borderRadius: 70, backgroundColor: 'rgba(255,255,255,0.10)', bottom: -30, left: -40 },
  monogram: {
    width: 76, height: 76, borderRadius: 38, marginTop: spacing.md, alignItems: 'center', justifyContent: 'center',
    borderWidth: 1.5, borderColor: 'rgba(255,255,255,0.75)', backgroundColor: 'rgba(255,255,255,0.14)',
  },
  monogramText: { fontFamily: fonts.display, fontSize: 30, color: colors.onPrimary, letterSpacing: 2 },
  brand: { color: colors.onPrimary, fontSize: 13, letterSpacing: 3, textTransform: 'uppercase', fontWeight: '600' },
  sheet: {
    backgroundColor: colors.surface, borderRadius: radius.xl, padding: spacing.lg, gap: spacing.md,
    marginTop: -spacing.xl, marginHorizontal: spacing.xs,
  },
  heading: { gap: spacing.xs, marginBottom: spacing.xs },
});
