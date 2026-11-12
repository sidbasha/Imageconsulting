import { useEffect, useState, type FormEvent } from 'react';
import { BrowserRouter, MemoryRouter, NavLink, Navigate, Route, Routes } from 'react-router-dom';

import { api, configure, login, logout, tokens } from './api';
import { I18nProvider, useI18n } from './i18n';
import { CatalogueProducts, CataloguePlans } from './pages/Catalogue';
import { Moderation } from './pages/Moderation';
import { Orders } from './pages/Orders';
import { Promotions } from './pages/Promotions';
import { Releases } from './pages/Releases';
import { ReportTemplates } from './pages/ReportTemplates';
import { Retail } from './pages/Retail';
import { Rewards } from './pages/Rewards';
import { Settings } from './pages/Settings';
import { Stylists } from './pages/Stylists';
import { TryOnLibrary } from './pages/TryOnLibrary';
import { Users } from './pages/Users';
import { ErrorNote } from './ui';
import './styles.css';

type Me = { full_name: string; email: string; role: string; permissions: string[] };

/** Every section, the permission that opens it (Feature List rows 53-60 and release control). */
export const SECTIONS = [
  { path: 'releases', label: 'Releases', permission: 'release.view', element: <Releases /> },
  { path: 'users', label: 'Users', permission: 'users.review', element: <Users /> },
  { path: 'stylists', label: 'Stylists', permission: 'stylists.review', element: <Stylists /> },
  { path: 'products', label: 'Products', permission: 'content.manage', element: <CatalogueProducts /> },
  { path: 'plans', label: 'Plans', permission: 'pricing.manage', element: <CataloguePlans /> },
  { path: 'orders', label: 'Orders', permission: 'orders.manage', element: <Orders /> },
  { path: 'retail', label: 'Retail links', permission: 'content.manage', element: <Retail /> },
  { path: 'templates', label: 'Report templates', permission: 'content.manage', element: <ReportTemplates /> },
  { path: 'try-on', label: 'Try-on library', permission: 'content.manage', element: <TryOnLibrary /> },
  { path: 'moderation', label: 'Moderation', permission: 'moderation.manage', element: <Moderation /> },
  { path: 'rewards', label: 'Rewards', permission: 'rewards.manage', element: <Rewards /> },
  { path: 'promotions', label: 'Promotions', permission: 'promotions.manage', element: <Promotions /> },
  { path: 'settings', label: 'Settings', permission: 'settings.manage', element: <Settings /> },
];

function Shell() {
  const { t, language, setLanguage } = useI18n();
  const [me, setMe] = useState<Me | null>(null);
  const [checking, setChecking] = useState(!!tokens.load());

  useEffect(() => {
    configure({ onExpired: () => setMe(null) });
    if (tokens.load()) {
      api<Me>('GET', '/users/me').then(setMe).catch(() => tokens.clear()).finally(() => setChecking(false));
    }
  }, []);

  const languageSwitch = (
    <button className="link" onClick={() => setLanguage(language === 'en' ? 'ar' : 'en')} data-testid="language">
      {language === 'en' ? 'العربية' : 'English'}
    </button>
  );
  if (checking) {
    return null;
  }
  if (!me) {
    return <SignIn onSignedIn={setMe} languageSwitch={languageSwitch} />;
  }
  const mine = SECTIONS.filter(s => me.permissions.includes(s.permission));
  return (
    <div className="layout">
      <nav>
        <strong>{t('Image Consulting admin')}</strong>
        {mine.map(s => (
          <NavLink key={s.path} to={`/${s.path}`}>
            {t(s.label)}
          </NavLink>
        ))}
        <div className="nav-foot">
          <span className="muted">{me.full_name}</span>
          {languageSwitch}
          <button className="link" onClick={async () => { await logout(); setMe(null); }} data-testid="sign-out">
            {t('Sign out')}
          </button>
        </div>
      </nav>
      <main>
        {mine.length === 0 ? <p className="error">{t('This account has no admin access.')}</p> : null}
        <Routes>
          {mine.map(s => <Route key={s.path} path={`/${s.path}`} element={s.element} />)}
          <Route path="*" element={mine[0] ? <Navigate to={`/${mine[0].path}`} replace /> : null} />
        </Routes>
      </main>
    </div>
  );
}

function SignIn({ onSignedIn, languageSwitch }: { onSignedIn: (me: Me) => void; languageSwitch: React.ReactNode }) {
  const { t } = useI18n();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
      onSignedIn(await api<Me>('GET', '/users/me'));
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };
  return (
    <form className="signin" onSubmit={submit}>
      <h1>{t('Image Consulting admin')}</h1>
      <label>
        {t('Email')}
        <input type="email" value={email} onChange={e => setEmail(e.target.value)} autoComplete="username" required />
      </label>
      <label>
        {t('Password')}
        <input type="password" value={password} onChange={e => setPassword(e.target.value)} autoComplete="current-password" required />
      </label>
      <ErrorNote error={error} />
      <button type="submit" disabled={busy}>{t('Sign in')}</button>
      {languageSwitch}
    </form>
  );
}

export default function App({ initialPath }: { initialPath?: string }) {
  const Router = initialPath ? MemoryRouter : BrowserRouter;
  return (
    <I18nProvider>
      <Router {...(initialPath ? { initialEntries: [initialPath] } : {})}>
        <Shell />
      </Router>
    </I18nProvider>
  );
}
