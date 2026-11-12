import React, { useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import type { ColourTypeSummary, Swatch } from '../api/client';
import { colors, fonts, gradients, radius, shadows, spacing } from '../theme';
import { AppText, Card, Tag } from './ui';

const METAL_HEX: Record<string, string> = {
  gold: '#c8a046', bronze: '#a0703a', copper: '#b8734a', silver: '#bfc3c7', platinum: '#d9dbdc', white_gold: '#e3e1da', rose_gold: '#d4a08a',
};

type Props = {
  type: ColourTypeSummary;
  /** Consultant mode: tap colours to build the client's own palette. */
  selected?: string[];
  onToggle?: (hex: string) => void;
  testID?: string;
};

/** A colour type's palette: a hero, then neutrals, colours by family, lips, hair, metals and colours to avoid. */
export function PaletteView({ type, selected, onToggle, testID }: Props) {
  const { t } = useTranslation();
  const [focus, setFocus] = useState<Swatch | null>(null);
  const families = Array.from(new Set(type.colours.map(c => c.family)));
  const tap = (s: Swatch) => (onToggle ? onToggle(s.hex) : setFocus(f => (f?.hex === s.hex ? null : s)));

  const chip = (s: Swatch, size: 'lg' | 'md' = 'md') => {
    const isOn = selected?.includes(s.hex);
    return (
      <Pressable key={s.hex + s.name} onPress={() => tap(s)} accessibilityRole={onToggle ? 'checkbox' : 'button'}
        accessibilityState={onToggle ? { checked: !!isOn } : undefined} accessibilityLabel={`${s.name} ${s.hex}`}
        testID={`palette-${s.hex}`}
        style={[size === 'lg' ? styles.swatchLg : styles.swatch, { backgroundColor: s.hex }, isOn && styles.swatchOn]} />
    );
  };

  return (
    <View style={styles.wrap} testID={testID}>
      <View style={[styles.hero, { backgroundImage: gradients.hero }]}>
        <AppText variant="small" style={styles.heroKicker}>{t(`colourTypes.season.${type.season}`)}</AppText>
        <AppText style={styles.heroTitle} testID="palette-title">{type.title}</AppText>
        <AppText style={styles.heroBody}>{type.summary}</AppText>
        <View style={styles.signature}>
          {type.signature.map(hex => <View key={hex} style={[styles.sigDot, { backgroundColor: hex }]} />)}
        </View>
      </View>

      {focus ? (
        <Card style={styles.focus}>
          <View style={[styles.focusSwatch, { backgroundColor: focus.hex }]} />
          <View style={styles.flex}>
            <AppText variant="heading">{focus.name}</AppText>
            <AppText muted>{focus.hex.toUpperCase()}</AppText>
          </View>
        </Card>
      ) : null}

      <Card>
        <AppText variant="heading">{t('palette.neutrals')}</AppText>
        <View style={styles.row}>{type.neutrals.map(s => chip(s, 'lg'))}</View>
      </Card>

      <Card>
        <AppText variant="heading">{t('palette.colours')}</AppText>
        <AppText variant="small" muted>{t('palette.coloursNote')}</AppText>
        <View style={styles.grid}>
          {families.map(family => (
            <View key={family} style={styles.family}>
              {type.colours.filter(c => c.family === family).map(s => chip(s))}
            </View>
          ))}
        </View>
      </Card>

      <Card>
        <AppText variant="heading">{t('palette.lips')}</AppText>
        <View style={styles.row}>{type.lips.map(s => chip(s))}</View>
      </Card>

      <Card>
        <AppText variant="heading">{t('palette.hair')}</AppText>
        <View style={styles.row}>
          {type.hair.map(s => (
            <View key={s.hex} style={styles.labelled}>
              {chip(s)}
              <AppText variant="small" muted style={styles.center}>{s.name}</AppText>
            </View>
          ))}
        </View>
      </Card>

      <Card>
        <AppText variant="heading">{t('palette.metals')}</AppText>
        <View style={styles.row}>
          {type.metals.map(m => (
            <View key={m} style={styles.labelled}>
              <View style={[styles.metal, { backgroundColor: METAL_HEX[m] ?? colors.gold }]} />
              <AppText variant="small" muted style={styles.center}>{t(`palette.metal.${m}`)}</AppText>
            </View>
          ))}
        </View>
      </Card>

      <Card>
        <Tag label={t('palette.avoid')} tone="lilac" />
        <AppText variant="small" muted>{t('palette.avoidNote')}</AppText>
        <View style={styles.row}>{type.avoid.map(s => chip(s))}</View>
      </Card>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: spacing.md },
  flex: { flex: 1 },
  hero: { borderRadius: radius.xl, padding: spacing.lg, gap: spacing.sm, boxShadow: shadows.lifted },
  heroKicker: { color: '#FFF3F6', letterSpacing: 1.6, textTransform: 'uppercase' },
  heroTitle: { color: '#FFFFFF', fontFamily: fonts.display, fontSize: 32, lineHeight: 40 },
  heroBody: { color: '#FFF3F6' },
  signature: { flexDirection: 'row', gap: spacing.sm, marginTop: spacing.xs },
  sigDot: { width: 28, height: 28, borderRadius: 14, borderWidth: 2, borderColor: '#FFFFFF' },
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  family: { gap: 4 },
  swatch: { width: 44, height: 44, borderRadius: radius.sm, borderWidth: 1, borderColor: 'rgba(0,0,0,0.06)' },
  swatchLg: { width: 48, height: 64, borderRadius: radius.md, borderWidth: 1, borderColor: 'rgba(0,0,0,0.06)' },
  swatchOn: { borderWidth: 3, borderColor: colors.text },
  labelled: { alignItems: 'center', gap: 4, width: 76 },
  center: { textAlign: 'center' },
  metal: { width: 44, height: 44, borderRadius: 22, boxShadow: 'inset 0px -6px 10px rgba(0,0,0,0.18)' },
  focus: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  focusSwatch: { width: 72, height: 72, borderRadius: radius.md },
});
