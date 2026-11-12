import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Image, Pressable, ScrollView, StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';
import { useTranslation } from 'react-i18next';

import type { Photo } from '../api/client';
import { useApp } from '../contexts/AppContext';
import { colors, radius, shadows, spacing } from '../theme';
import { AppText } from './ui';

// Photos are private: fetched with the user's token and kept in memory only for this session.
const cache = new Map<string, string>();

/** One of the user's own photos, loaded from the API. */
export function PhotoThumb({ id, style, testID }: { id: string; style?: StyleProp<ViewStyle>; testID?: string }) {
  const { api } = useApp();
  const [uri, setUri] = useState<string | null>(cache.get(id) ?? null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (cache.has(id)) {
      setUri(cache.get(id)!);
      return;
    }
    let live = true;
    api
      .photoFile(id)
      .then(u => {
        cache.set(id, u);
        if (live) {
          setUri(u);
        }
      })
      .catch(() => live && setFailed(true));
    return () => {
      live = false;
    };
  }, [api, id]);

  return (
    <View style={[styles.frame, style]} testID={testID}>
      {uri ? (
        <Image source={{ uri }} style={StyleSheet.absoluteFill} resizeMode="cover" testID={testID ? `${testID}-image` : undefined} />
      ) : failed ? null : (
        <ActivityIndicator color={colors.primary} />
      )}
    </View>
  );
}

/** A row of the user's photos to pick from, the chosen one outlined. */
export function PhotoPicker({ photos, value, onChange, testID }: {
  photos: Photo[];
  value: string | null;
  onChange: (id: string) => void;
  testID?: string;
}) {
  const { t } = useTranslation();
  return (
    <View style={styles.picker}>
      <AppText variant="small" muted>{t('preview.photo')}</AppText>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.row}>
        {photos.map(p => {
          const selected = p.id === value;
          return (
            <Pressable key={p.id} accessibilityRole="radio" accessibilityState={{ selected }}
              accessibilityLabel={`${t(`photos.kind.${p.kind}`)} ${p.created_at.slice(0, 10)}`}
              onPress={() => onChange(p.id)} testID={testID ? `${testID}-${p.id}` : undefined}
              style={[styles.option, selected && styles.selected]}>
              <PhotoThumb id={p.id} style={styles.small} />
            </Pressable>
          );
        })}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  frame: {
    width: 84,
    height: 108,
    borderRadius: radius.md,
    overflow: 'hidden',
    backgroundColor: colors.primarySoft,
    alignItems: 'center',
    justifyContent: 'center',
  },
  picker: { gap: spacing.sm },
  row: { gap: spacing.sm, paddingVertical: spacing.xs },
  option: { borderRadius: radius.md + 3, borderWidth: 3, borderColor: 'transparent' },
  selected: { borderColor: colors.primary, boxShadow: shadows.soft },
  small: { width: 72, height: 92 },
});
