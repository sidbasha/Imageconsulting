/**
 * Every customer-facing entry point and the feature key that unlocks it.
 *
 * The home screen is built from this list filtered by what the API reports as
 * enabled, so releasing a phase in the admin panel changes the app without a
 * new build. Feature keys match backend/app/modules/phase_management/catalog.py
 * (a test fails if one does not exist there).
 *
 * `target` is the screen to open. It is undefined until that feature's screens
 * are built; such entries render as "In development" and cannot be opened.
 */
export type Group = 'assessment' | 'recommendations' | 'experts' | 'library' | 'shop' | 'account';

export type Target =
  | { screen: 'Assessment'; params: { key: string } }
  | { screen: 'Recommendations'; params: { category: 'outfits' | 'eyewear' | 'hair' } }
  | { screen: 'PhotoAnalysis'; params: { kind: 'face_shape' | 'body_shape' | 'seasonal_color' } }
  | { screen: 'Preview'; params: { kind: 'hair-colour' | 'outfit-colour' | 'makeup' } }
  | { screen: 'Library'; params?: { kind: 'guide' | 'report' } }
  | { screen: 'Plans'; params?: { audience: 'customer' | 'consultant' } }
  | { screen: 'Offers'; params?: { show: 'offers' | 'vouchers' } }
  | { screen: 'Stylists'; params?: { kind: string } }
  | {
      screen: 'Photos' | 'Retail' | 'Rewards' | 'Profile' | 'Shop' | 'Bookings' | 'Messages' | 'StylistApplication' | 'Practice';
      params?: undefined;
    };

export type Entry = { id: string; feature: string; group: Group; target?: Target };

export const GROUP_ORDER: Group[] = ['assessment', 'recommendations', 'experts', 'library', 'shop', 'account'];

export const ENTRIES: Entry[] = [
  { id: 'onboardingQuiz', feature: 'phase1.onboarding_quiz', group: 'assessment', target: { screen: 'Assessment', params: { key: 'onboarding_quiz' } } },
  { id: 'styleAssessment', feature: 'phase1.style_assessment', group: 'assessment', target: { screen: 'Assessment', params: { key: 'style' } } },
  { id: 'photoAssessment', feature: 'phase1.photo_assessment', group: 'assessment', target: { screen: 'Photos' } },
  { id: 'faceShape', feature: 'phase1.face_shape', group: 'assessment', target: { screen: 'Assessment', params: { key: 'face_shape' } } },
  { id: 'bodyShape', feature: 'phase1.body_shape', group: 'assessment', target: { screen: 'Assessment', params: { key: 'body_shape' } } },
  { id: 'seasonalColor', feature: 'phase1.seasonal_color', group: 'assessment', target: { screen: 'Assessment', params: { key: 'seasonal_color' } } },

  { id: 'outfits', feature: 'phase1.outfit_recommendations', group: 'recommendations', target: { screen: 'Recommendations', params: { category: 'outfits' } } },
  { id: 'tryOn', feature: 'phase1.virtual_tryon', group: 'recommendations', target: { screen: 'Preview', params: { kind: 'outfit-colour' } } },
  { id: 'hair', feature: 'phase1.hair_preview', group: 'recommendations', target: { screen: 'Recommendations', params: { category: 'hair' } } },
  { id: 'hairColour', feature: 'phase1.hair_preview', group: 'recommendations', target: { screen: 'Preview', params: { kind: 'hair-colour' } } },
  { id: 'eyewear', feature: 'phase1.eyewear', group: 'recommendations', target: { screen: 'Recommendations', params: { category: 'eyewear' } } },
  { id: 'shopping', feature: 'phase1.retail_links', group: 'recommendations', target: { screen: 'Retail' } },
  { id: 'makeupPreview', feature: 'phase3.pmu_preview', group: 'recommendations', target: { screen: 'Preview', params: { kind: 'makeup' } } },

  { id: 'findStylist', feature: 'phase2.stylist_discovery', group: 'experts', target: { screen: 'Stylists' } },
  { id: 'bookings', feature: 'phase2.booking', group: 'experts', target: { screen: 'Bookings' } },
  { id: 'consultations', feature: 'phase2.consultations', group: 'experts', target: { screen: 'Bookings' } },
  { id: 'messages', feature: 'phase2.messaging', group: 'experts', target: { screen: 'Messages' } },
  { id: 'occasionAudit', feature: 'phase2.occasion_audit', group: 'experts', target: { screen: 'Stylists', params: { kind: 'occasion_audit' } } },
  { id: 'wardrobeAudit', feature: 'phase2.wardrobe_audit', group: 'experts', target: { screen: 'Stylists', params: { kind: 'wardrobe_audit' } } },
  { id: 'makeupAudit', feature: 'phase2.makeup_audit', group: 'experts', target: { screen: 'Stylists', params: { kind: 'makeup_audit' } } },
  { id: 'expertColor', feature: 'phase2.expert_color_analysis', group: 'experts', target: { screen: 'Stylists', params: { kind: 'expert_color' } } },
  { id: 'personalShopper', feature: 'phase3.personal_shopper', group: 'experts', target: { screen: 'Stylists', params: { kind: 'personal_shopper_day' } } },
  // Location search needs the device's position (a geolocation library, not added yet); until then this lists by city.
  { id: 'nearbyStylists', feature: 'phase3.location_discovery', group: 'experts', target: { screen: 'Stylists' } },

  { id: 'guides', feature: 'phase1.digital_guides', group: 'library', target: { screen: 'Library', params: { kind: 'guide' } } },
  { id: 'reports', feature: 'phase1.paid_reports', group: 'library', target: { screen: 'Library', params: { kind: 'report' } } },

  { id: 'shop', feature: 'phase3.physical_products', group: 'shop', target: { screen: 'Shop' } },
  { id: 'offers', feature: 'phase3.brand_advertising', group: 'shop', target: { screen: 'Offers', params: { show: 'offers' } } },
  { id: 'vouchers', feature: 'phase3.vouchers', group: 'shop', target: { screen: 'Offers', params: { show: 'vouchers' } } },

  { id: 'profile', feature: 'phase1.eligibility_verification', group: 'account', target: { screen: 'Profile' } },
  { id: 'subscription', feature: 'phase1.customer_subscriptions', group: 'account', target: { screen: 'Plans' } },
  { id: 'rewards', feature: 'phase1.loyalty_points', group: 'account', target: { screen: 'Rewards' } },
  { id: 'redeem', feature: 'phase2.reward_redemption', group: 'account', target: { screen: 'Rewards' } },
  { id: 'becomeStylist', feature: 'phase2.stylist_onboarding', group: 'account', target: { screen: 'StylistApplication' } },
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
