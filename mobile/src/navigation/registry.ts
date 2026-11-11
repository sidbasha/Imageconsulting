/**
 * Every customer-facing entry point and the feature key that unlocks it.
 *
 * The home screen is built from this list filtered by what the API reports as
 * enabled, so releasing a phase in the admin panel changes the app without a
 * new build. Feature keys match backend/app/modules/phase_management/catalog.py
 * (a test fails if one does not exist there).
 *
 * `screen` is the route to open. It is undefined until that feature's screens
 * are built; such entries render as "In development" and cannot be opened.
 */
export type Group = 'assessment' | 'recommendations' | 'experts' | 'library' | 'shop' | 'account';

export type Entry = { id: string; feature: string; group: Group; screen?: string };

export const GROUP_ORDER: Group[] = ['assessment', 'recommendations', 'experts', 'library', 'shop', 'account'];

export const ENTRIES: Entry[] = [
  { id: 'onboardingQuiz', feature: 'phase1.onboarding_quiz', group: 'assessment' },
  { id: 'styleAssessment', feature: 'phase1.style_assessment', group: 'assessment' },
  { id: 'photoAssessment', feature: 'phase1.photo_assessment', group: 'assessment' },
  { id: 'faceShape', feature: 'phase1.face_shape', group: 'assessment' },
  { id: 'bodyShape', feature: 'phase1.body_shape', group: 'assessment' },
  { id: 'seasonalColor', feature: 'phase1.seasonal_color', group: 'assessment' },

  { id: 'outfits', feature: 'phase1.outfit_recommendations', group: 'recommendations' },
  { id: 'tryOn', feature: 'phase1.virtual_tryon', group: 'recommendations' },
  { id: 'hair', feature: 'phase1.hair_preview', group: 'recommendations' },
  { id: 'eyewear', feature: 'phase1.eyewear', group: 'recommendations' },
  { id: 'shopping', feature: 'phase1.retail_links', group: 'recommendations' },
  { id: 'makeupPreview', feature: 'phase3.pmu_preview', group: 'recommendations' },

  { id: 'findStylist', feature: 'phase2.stylist_discovery', group: 'experts' },
  { id: 'bookings', feature: 'phase2.booking', group: 'experts' },
  { id: 'consultations', feature: 'phase2.consultations', group: 'experts' },
  { id: 'messages', feature: 'phase2.messaging', group: 'experts' },
  { id: 'occasionAudit', feature: 'phase2.occasion_audit', group: 'experts' },
  { id: 'wardrobeAudit', feature: 'phase2.wardrobe_audit', group: 'experts' },
  { id: 'makeupAudit', feature: 'phase2.makeup_audit', group: 'experts' },
  { id: 'expertColor', feature: 'phase2.expert_color_analysis', group: 'experts' },
  { id: 'personalShopper', feature: 'phase3.personal_shopper', group: 'experts' },
  { id: 'nearbyStylists', feature: 'phase3.location_discovery', group: 'experts' },

  { id: 'guides', feature: 'phase1.digital_guides', group: 'library' },
  { id: 'reports', feature: 'phase1.paid_reports', group: 'library' },

  { id: 'shop', feature: 'phase3.physical_products', group: 'shop' },
  { id: 'offers', feature: 'phase3.geo_promotions', group: 'shop' },
  { id: 'vouchers', feature: 'phase3.vouchers', group: 'shop' },

  { id: 'subscription', feature: 'phase1.customer_subscriptions', group: 'account' },
  { id: 'rewards', feature: 'phase1.loyalty_points', group: 'account' },
  { id: 'redeem', feature: 'phase2.reward_redemption', group: 'account' },
];

export type Section = { group: Group; entries: Entry[] };

/** Sections to show for a set of enabled feature keys. Empty groups are dropped. */
export function visibleSections(enabled: readonly string[]): Section[] {
  const on = new Set(enabled);
  return GROUP_ORDER.map(group => ({
    group,
    entries: ENTRIES.filter(entry => entry.group === group && on.has(entry.feature)),
  })).filter(section => section.entries.length > 0);
}
