import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';

import { configure } from './api';

/** Panel chrome in English and Arabic. Content (titles, notes) shows as stored. */
const ar: Record<string, string> = {
  'Image Consulting admin': 'لوحة إدارة الاستشارات',
  'Sign in': 'تسجيل الدخول', 'Sign out': 'تسجيل الخروج', Email: 'البريد الإلكتروني', Password: 'كلمة المرور',
  'This account has no admin access.': 'لا يملك هذا الحساب صلاحيات إدارية.',
  Releases: 'الإصدارات', Users: 'المستخدمات', Identity: 'الهوية', Stylists: 'المستشارات', Products: 'المنتجات',
  Plans: 'الخطط', Orders: 'الطلبات', 'Retail links': 'روابط المتاجر', 'Report templates': 'نماذج التقارير',
  'Try-on library': 'مكتبة التجربة', Moderation: 'الإشراف', Testimonials: 'آراء العميلات', Rewards: 'المكافآت',
  Promotions: 'الترويج', Vouchers: 'القسائم', Settings: 'الإعدادات', Countries: 'الدول',
  Save: 'حفظ', Cancel: 'إلغاء', Approve: 'موافقة', Reject: 'رفض', Refresh: 'تحديث', Create: 'إنشاء', Delete: 'حذف',
  Open: 'فتح', Status: 'الحالة', Note: 'ملاحظة', Loading: 'جارٍ التحميل', 'Nothing here.': 'لا يوجد شيء هنا.',
  Saved: 'تم الحفظ', English: 'الإنجليزية', Arabic: 'العربية',
};

type Ctx = { language: 'en' | 'ar'; setLanguage: (l: 'en' | 'ar') => void; t: (s: string) => string };
const I18n = createContext<Ctx>({ language: 'en', setLanguage: () => undefined, t: s => s });

export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<'en' | 'ar'>(() => (localStorage.getItem('ic-admin-lang') === 'ar' ? 'ar' : 'en'));
  useEffect(() => {
    document.documentElement.lang = language;
    document.documentElement.dir = language === 'ar' ? 'rtl' : 'ltr';
    localStorage.setItem('ic-admin-lang', language);
    configure({ language });
  }, [language]);
  const t = (s: string) => (language === 'ar' ? ar[s] ?? s : s);
  return <I18n.Provider value={{ language, setLanguage, t }}>{children}</I18n.Provider>;
}

export const useI18n = () => useContext(I18n);
