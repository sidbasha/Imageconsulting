/**
 * Who the signed-in person is for the purpose of navigation. Each audience
 * gets its own tabs, menu and account items; the API enforces the same
 * boundaries independently (permissions and feature switches).
 *
 * - staff: any admin permission (Super Admin, Admin, the manager roles)
 * - stylist: an approved stylist (role "stylist" / permission "stylist.practice")
 * - customer: everyone else
 */
import type { User } from '../api/client';
import type { IconName } from '../components/Icon';
import { isStaff } from '../screens/admin/common';

export type Audience = 'customer' | 'stylist' | 'staff';

export function audienceOf(user: User | null): Audience {
  const permissions = user?.permissions ?? [];
  if (isStaff(permissions)) {
    return 'staff';
  }
  if (user?.role === 'stylist' || permissions.includes('stylist.practice')) {
    return 'stylist';
  }
  return 'customer';
}

/** A stylist's tools, each shown when its feature is in the active release. */
export const STYLIST_LINKS: { key: string; icon: IconName; feature: string; screen: string; params?: object }[] = [
  { key: 'bookings', icon: 'calendar', feature: 'phase2.stylist_discovery', screen: 'Practice' },
  { key: 'services', icon: 'scissors', feature: 'phase2.stylist_discovery', screen: 'StylistServices' },
  { key: 'messages', icon: 'mail', feature: 'phase2.messaging', screen: 'Messages' },
  { key: 'featured', icon: 'megaphone', feature: 'phase2.paid_promotion', screen: 'Featured' },
  { key: 'membership', icon: 'crown', feature: 'phase2.consultant_subscriptions', screen: 'Plans', params: { audience: 'consultant' } },
  { key: 'profile', icon: 'badge', feature: 'phase2.stylist_onboarding', screen: 'StylistApplication' },
];
