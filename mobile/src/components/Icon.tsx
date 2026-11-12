/**
 * Fine-line icons (Lucide, drawn with react-native-svg) and the line-art
 * flourish used on feature cards.
 */
import React from 'react';
import { StyleSheet, View } from 'react-native';
import Svg, { Circle, Path } from 'react-native-svg';
import {
  ArrowUpLeft, ArrowUpRight, BadgePercent, BookOpen, Brush, CalendarHeart, Camera, Crown, FileText, Flower2, Gem, Gift, Glasses,
  Handbag, Heart, House, Layers, Mail, MapPin, MessagesSquare, Palette, PersonStanding, ScanFace, Scissors, Search, Settings,
  Shirt, ShoppingBag, ShoppingCart, Sparkle, Sparkles, Star, SwatchBook, Tag, Ticket, UserRound, UserSearch, WandSparkles, Wine,
  ShieldCheck, IdCard, BadgeCheck, Receipt, Flag, Package, Megaphone, SlidersHorizontal, Images, Link,
} from 'lucide-react-native';

const ICONS = {
  'arrow-up-left': ArrowUpLeft, 'arrow-up-right': ArrowUpRight, house: House, search: Search, settings: Settings, star: Star,
  'map-pin': MapPin, sparkles: Sparkles, flower: Flower2, bag: ShoppingBag, user: UserRound, palette: Palette, shirt: Shirt,
  'user-search': UserSearch, book: BookOpen, file: FileText, brush: Brush,
  shield: ShieldCheck, 'id-card': IdCard, badge: BadgeCheck, receipt: Receipt, flag: Flag, package: Package,
  megaphone: Megaphone, sliders: SlidersHorizontal, images: Images, link: Link, gem: Gem, crown: Crown, ticket: Ticket,
};
export type IconName = keyof typeof ICONS;

const ENTRY = {
  onboardingQuiz: Sparkles, styleAssessment: Shirt, photoAssessment: Camera, faceShape: ScanFace, bodyShape: PersonStanding,
  seasonalColor: Palette, outfits: WandSparkles, tryOn: ShoppingBag, outfitColour: SwatchBook, hair: Scissors, hairStyles: Sparkle,
  hairColour: Brush, eyewear: Glasses, shopping: ShoppingCart, makeupPreview: Heart, findStylist: UserSearch, bookings: CalendarHeart,
  consultations: MessagesSquare, messages: Mail, occasionAudit: Wine, wardrobeAudit: Layers, makeupAudit: Brush, expertColor: Flower2,
  personalShopper: Handbag, nearbyStylists: MapPin, guides: BookOpen, reports: FileText, shop: Gift, offers: Tag, vouchers: Ticket,
  profile: UserRound, subscription: Crown, rewards: Gem, redeem: BadgePercent, becomeStylist: WandSparkles,
} as Record<string, typeof Sparkles>;

type Props = { size?: number; color?: string; strokeWidth?: number };

export function Icon({ name, size = 22, color = '#2E1F27', strokeWidth = 1.6 }: Props & { name: IconName }) {
  const Glyph = ICONS[name];
  return <Glyph size={size} color={color} strokeWidth={strokeWidth} />;
}

/** The icon for a service (registry entry id). */
export function EntryIcon({ id, size = 22, color = '#2E1F27', strokeWidth = 1.6 }: Props & { id: string }) {
  const Glyph = ENTRY[id] ?? Sparkle;
  return <Glyph size={size} color={color} strokeWidth={strokeWidth} />;
}

/** Decorative line art for gradient cards: rings and a botanical sprig, in translucent white. */
export function Flourish({ size = 220 }: { size?: number }) {
  const stroke = 'rgba(255,255,255,0.38)';
  return (
    <View pointerEvents="none" style={[styles.flourish, { width: size, height: size }]}>
      <Svg width={size} height={size} viewBox="0 0 220 220" fill="none">
        <Circle cx="150" cy="70" r="92" stroke="rgba(255,255,255,0.16)" strokeWidth="1" />
        <Circle cx="150" cy="70" r="66" stroke="rgba(255,255,255,0.22)" strokeWidth="1" />
        <Circle cx="150" cy="70" r="40" stroke="rgba(255,255,255,0.30)" strokeWidth="1" />
        {/* stem */}
        <Path d="M96 196 C 112 150, 134 112, 178 76" stroke={stroke} strokeWidth="1.4" strokeLinecap="round" />
        {/* leaves */}
        <Path d="M112 160 C 96 150, 88 132, 92 116 C 108 122, 118 140, 112 160 Z" stroke={stroke} strokeWidth="1.2" />
        <Path d="M128 134 C 148 136, 164 150, 168 168 C 150 166, 134 154, 128 134 Z" stroke={stroke} strokeWidth="1.2" />
        <Path d="M146 108 C 132 96, 128 78, 134 62 C 148 72, 154 90, 146 108 Z" stroke={stroke} strokeWidth="1.2" />
        <Path d="M162 90 C 180 94, 194 106, 198 122 C 182 120, 168 108, 162 90 Z" stroke={stroke} strokeWidth="1.2" />
      </Svg>
    </View>
  );
}

const styles = StyleSheet.create({ flourish: { position: 'absolute', top: -10, right: -20 } });
