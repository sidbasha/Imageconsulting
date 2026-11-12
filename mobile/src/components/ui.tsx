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
import { colors, fonts, gradients, radius, shadows, spacing, type } from '../theme';

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
  const { text, rtl } = useDirection();
  // Titles use the display serif in Latin script; Arabic keeps the system face, which has the glyphs.
  const display = variant === 'title' && !rtl && fonts.display ? { fontFamily: fonts.display, fontWeight: '700' as const } : null;
  return <Text {...rest} style={[type[variant], { color: muted ? colors.muted : colors.text }, display, text, style]} />;
}

export function Screen({ children, testID }: { children: React.ReactNode; testID?: string }) {
  const { rtl } = useDirection();
  return (
    <SafeAreaView style={[styles.screen, { backgroundImage: gradients.screen }]} testID={testID} accessibilityLanguage={rtl ? 'ar' : 'en'}>
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
  /** primary: gradient pill; soft: tinted pill; link: text only. */
  kind?: 'primary' | 'soft' | 'link';
  testID?: string;
};

export function Button({ label, onPress, loading, kind = 'primary', testID }: ButtonProps) {
  const primary = kind === 'primary';
  const base = kind === 'primary' ? styles.button : kind === 'soft' ? styles.soft : styles.link;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled: !!loading, busy: !!loading }}
      disabled={loading}
      onPress={onPress}
      testID={testID}
      style={({ pressed }) => [base, primary && { backgroundImage: gradients.primary, boxShadow: shadows.button },
        pressed && styles.pressed, loading && styles.dimmed]}>
      {loading ? (
        <ActivityIndicator color={primary ? colors.onPrimary : colors.primary} />
      ) : (
        <Text style={primary ? styles.buttonLabel : styles.linkLabel}>{label}</Text>
      )}
    </Pressable>
  );
}

type FieldProps = TextInputProps & { label: string; error?: string | null; hint?: string };

export function TextField({ label, error, hint, style, onFocus, onBlur, ...rest }: FieldProps) {
  const { text } = useDirection();
  const [focused, setFocused] = React.useState(false);
  return (
    <View style={styles.field}>
      <AppText variant="small" muted>
        {label}
      </AppText>
      <TextInput
        accessibilityLabel={label}
        placeholderTextColor={colors.muted}
        {...rest}
        onFocus={e => {
          setFocused(true);
          onFocus?.(e);
        }}
        onBlur={e => {
          setFocused(false);
          onBlur?.(e);
        }}
        style={[styles.input, text, focused && styles.inputFocused, !!error && styles.inputError, style]}
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

/** Title row with a back control that sits on, and points to, the reading-start side. */
export function ScreenHeader({ title, onBack }: { title: string; onBack: () => void }) {
  const { rtl } = useDirection();
  const { t } = useTranslation();
  return (
    <View style={styles.header}>
      <Row>
        <Pressable accessibilityRole="button" accessibilityLabel={`${rtl ? '›' : '‹'} ${t('common.back')}`} onPress={onBack} testID="back"
          style={({ pressed }) => [styles.back, { boxShadow: shadows.soft }, pressed && styles.pressed]}>
          <Text style={styles.backArrow}>{rtl ? '›' : '‹'}</Text>
        </Pressable>
      </Row>
      <AppText variant="title" accessibilityRole="header">
        {title}
      </AppText>
    </View>
  );
}

export function Card({ children, style }: { children: React.ReactNode; style?: StyleProp<ViewStyle> }) {
  return <View style={[styles.card, { boxShadow: shadows.soft, backgroundImage: gradients.card }, style]}>{children}</View>;
}

/** A list of short advice lines with a leading mark on the reading-start side. */
export function Bullets({ items }: { items: string[] }) {
  return (
    <View style={styles.bullets}>
      {items.map(item => (
        <Row key={item} style={styles.bullet}>
          <View style={styles.dot} />
          <AppText style={styles.flex}>{item}</AppText>
        </Row>
      ))}
    </View>
  );
}

export function Palette({ colors: swatches }: { colors: string[] }) {
  return (
    <Row style={styles.palette}>
      {swatches.map(hex => (
        <View key={hex} style={[styles.swatch, { backgroundColor: hex }]} accessibilityLabel={hex} testID={`swatch-${hex}`} />
      ))}
    </Row>
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

/** A single-choice row of pill buttons. */
export function Chips<T extends string>({ options, value, onChange, label, testID }: {
  options: { value: T; label: string }[];
  value: T | null;
  onChange: (value: T) => void;
  label?: string;
  testID?: string;
}) {
  return (
    <View style={styles.field}>
      {label ? (
        <AppText variant="small" muted>
          {label}
        </AppText>
      ) : null}
      <Row style={styles.chips}>
        {options.map(option => {
          const selected = option.value === value;
          return (
            <Pressable
              key={option.value}
              accessibilityRole="radio"
              accessibilityState={{ selected }}
              accessibilityLabel={option.label}
              testID={`${testID ?? 'chip'}-${option.value}`}
              onPress={() => onChange(option.value)}
              style={[styles.chip, selected && styles.chipSelected]}>
              <Text style={[styles.chipLabel, selected && styles.chipLabelSelected]}>{option.label}</Text>
            </Pressable>
          );
        })}
      </Row>
    </View>
  );
}

/** Amount in minor units shown with its currency, e.g. "AED 49.00". */
export function money(minor: number, currency: string): string {
  return `${currency} ${(minor / 100).toFixed(2)}`;
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
  chips: { gap: spacing.sm, flexWrap: 'wrap' },
  screen: { flex: 1, backgroundColor: colors.background },
  flex: { flex: 1 },
  header: { gap: spacing.md, marginBottom: spacing.xs },
  back: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: colors.surface,
    alignItems: 'center',
    justifyContent: 'center',
  },
  backArrow: { fontSize: 28, lineHeight: 30, color: colors.primary, fontWeight: '300', marginTop: -2 },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: 'rgba(239, 226, 226, 0.7)',
    padding: spacing.md + 2,
    gap: spacing.sm,
  },
  bullets: { gap: spacing.sm },
  bullet: { gap: spacing.sm + 2, alignItems: 'flex-start' },
  dot: { width: 7, height: 7, borderRadius: 4, backgroundColor: colors.gold, marginTop: 9 },
  palette: { gap: spacing.sm, flexWrap: 'wrap' },
  swatch: { width: 40, height: 40, borderRadius: 20, borderWidth: 3, borderColor: colors.surface, boxShadow: '0px 3px 8px rgba(46, 31, 39, 0.18)' },
  row: { alignItems: 'center' },
  button: {
    backgroundColor: colors.primary,
    borderRadius: radius.pill,
    minHeight: 54,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.lg,
  },
  soft: {
    backgroundColor: colors.primarySoft,
    borderRadius: radius.pill,
    minHeight: 48,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.lg,
  },
  buttonLabel: { ...type.body, color: colors.onPrimary, fontWeight: '700', letterSpacing: 0.4 },
  link: { minHeight: 44, alignItems: 'center', justifyContent: 'center', paddingHorizontal: spacing.xs },
  linkLabel: { ...type.body, color: colors.primary, fontWeight: '600' },
  pressed: { transform: [{ scale: 0.98 }], opacity: 0.92 },
  dimmed: { opacity: 0.6 },
  field: { gap: spacing.xs + 2 },
  input: {
    ...type.body,
    color: colors.text,
    backgroundColor: colors.surfaceTint,
    borderWidth: 1.5,
    borderColor: colors.border,
    borderRadius: radius.md,
    minHeight: 54,
    paddingHorizontal: spacing.md,
  },
  inputFocused: { borderColor: colors.primary, backgroundColor: colors.surface, boxShadow: '0px 0px 0px 4px rgba(162, 62, 102, 0.12)' },
  inputError: { borderColor: colors.danger },
  error: { color: colors.danger },
  banner: {
    borderRadius: radius.md,
    padding: spacing.md,
    backgroundColor: colors.dangerSoft,
    borderWidth: 1,
    borderColor: 'rgba(179, 38, 30, 0.25)',
  },
  switch: { gap: 4, padding: 4, borderRadius: radius.pill, backgroundColor: colors.surface, alignSelf: 'flex-start', boxShadow: shadows.soft },
  chip: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.pill,
    paddingHorizontal: spacing.md,
    minHeight: 40,
    justifyContent: 'center',
    backgroundColor: colors.surface,
  },
  chipSelected: { backgroundColor: colors.primary, borderColor: colors.primary, backgroundImage: gradients.primary },
  chipLabel: { ...type.small, color: colors.text, fontWeight: '600' },
  chipLabelSelected: { color: colors.onPrimary },
});
