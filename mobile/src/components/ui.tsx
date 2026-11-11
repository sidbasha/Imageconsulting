/**
 * Shared building blocks. Every one of them takes its direction from the
 * selected language (useDirection), so switching between English and Arabic
 * re-lays-out the screen immediately, with no app restart.
 */
import React from 'react';
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
  type StyleProp,
  type TextInputProps,
  type TextProps,
  type TextStyle,
  type ViewStyle,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useTranslation } from 'react-i18next';

import { useApp } from '../contexts/AppContext';
import { LANGUAGES } from '../localization';
import { colors, radius, spacing, type } from '../theme';

export function useDirection() {
  const { rtl } = useApp();
  return {
    rtl,
    row: (rtl ? 'row-reverse' : 'row') as 'row' | 'row-reverse',
    text: { textAlign: rtl ? 'right' : 'left', writingDirection: rtl ? 'rtl' : 'ltr' } as TextStyle,
  };
}

type Variant = 'title' | 'heading' | 'body' | 'small';

export function AppText({ variant = 'body', muted, style, ...rest }: TextProps & { variant?: Variant; muted?: boolean }) {
  const { text } = useDirection();
  return <Text {...rest} style={[type[variant], { color: muted ? colors.muted : colors.text }, text, style]} />;
}

export function Screen({ children, testID }: { children: React.ReactNode; testID?: string }) {
  const { rtl } = useDirection();
  return (
    <SafeAreaView style={styles.screen} testID={testID} accessibilityLanguage={rtl ? 'ar' : 'en'}>
      {children}
    </SafeAreaView>
  );
}

/** A horizontal line of items that starts on the reading side. */
export function Row({ children, style }: { children: React.ReactNode; style?: StyleProp<ViewStyle> }) {
  const { row } = useDirection();
  return <View style={[styles.row, { flexDirection: row }, style]}>{children}</View>;
}

type ButtonProps = {
  label: string;
  onPress: () => void;
  loading?: boolean;
  kind?: 'primary' | 'link';
  testID?: string;
};

export function Button({ label, onPress, loading, kind = 'primary', testID }: ButtonProps) {
  const primary = kind === 'primary';
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled: !!loading, busy: !!loading }}
      disabled={loading}
      onPress={onPress}
      testID={testID}
      style={({ pressed }) => [primary ? styles.button : styles.link, (pressed || loading) && styles.dimmed]}>
      {loading ? (
        <ActivityIndicator color={primary ? colors.onPrimary : colors.primary} />
      ) : (
        <Text style={primary ? styles.buttonLabel : styles.linkLabel}>{label}</Text>
      )}
    </Pressable>
  );
}

type FieldProps = TextInputProps & { label: string; error?: string | null; hint?: string };

export function TextField({ label, error, hint, style, ...rest }: FieldProps) {
  const { text } = useDirection();
  return (
    <View style={styles.field}>
      <AppText variant="small" muted>
        {label}
      </AppText>
      <TextInput
        accessibilityLabel={label}
        placeholderTextColor={colors.muted}
        {...rest}
        style={[styles.input, text, !!error && styles.inputError, style]}
      />
      {error ? (
        <AppText variant="small" style={styles.error} accessibilityRole="alert">
          {error}
        </AppText>
      ) : hint ? (
        <AppText variant="small" muted>
          {hint}
        </AppText>
      ) : null}
    </View>
  );
}

export function ErrorBanner({ message }: { message: string | null }) {
  if (!message) {
    return null;
  }
  return (
    <View style={styles.banner} accessibilityRole="alert" testID="error-banner">
      <AppText variant="small" style={styles.error}>
        {message}
      </AppText>
    </View>
  );
}

/** English / العربية. Each option is written in its own language so it can always be found. */
export function LanguageSwitch() {
  const { language, setLanguage } = useApp();
  const { t } = useTranslation();
  return (
    <Row style={styles.switch}>
      {LANGUAGES.map(code => {
        const selected = code === language;
        return (
          <Pressable
            key={code}
            accessibilityRole="button"
            accessibilityState={{ selected }}
            accessibilityLabel={t(`language.${code}`)}
            testID={`language-${code}`}
            onPress={() => setLanguage(code)}
            style={[styles.chip, selected && styles.chipSelected]}>
            <Text style={[styles.chipLabel, selected && styles.chipLabelSelected]}>{t(`language.${code}`)}</Text>
          </Pressable>
        );
      })}
    </Row>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  row: { alignItems: 'center' },
  button: {
    backgroundColor: colors.primary,
    borderRadius: radius.md,
    minHeight: 52,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.lg,
  },
  buttonLabel: { ...type.body, color: colors.onPrimary, fontWeight: '600' },
  link: { minHeight: 44, alignItems: 'center', justifyContent: 'center' },
  linkLabel: { ...type.body, color: colors.primary, fontWeight: '600' },
  dimmed: { opacity: 0.6 },
  field: { gap: spacing.xs },
  input: {
    ...type.body,
    color: colors.text,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    minHeight: 52,
    paddingHorizontal: spacing.md,
  },
  inputError: { borderColor: colors.danger },
  error: { color: colors.danger },
  banner: {
    borderWidth: 1,
    borderColor: colors.danger,
    borderRadius: radius.md,
    padding: spacing.md,
    backgroundColor: colors.surface,
  },
  switch: { gap: spacing.sm },
  chip: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 999,
    paddingHorizontal: spacing.md,
    minHeight: 40,
    justifyContent: 'center',
    backgroundColor: colors.surface,
  },
  chipSelected: { backgroundColor: colors.primary, borderColor: colors.primary },
  chipLabel: { ...type.small, color: colors.text, fontWeight: '600' },
  chipLabelSelected: { color: colors.onPrimary },
});
