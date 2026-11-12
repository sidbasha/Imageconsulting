import { useCallback, useEffect, useState, type ReactNode } from 'react';

import { ApiError } from './api';
import { useI18n } from './i18n';

/** Load data for a page; `reload` after a change. */
export function useData<T>(load: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(load, deps);
  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await run());
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }, [run]);
  useEffect(() => {
    reload();
  }, [reload]);
  return { data, error, loading, reload, setData };
}

/** Runs an action, remembering its error and whether it is busy. */
export function useAction() {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [done, setDone] = useState<string | null>(null);
  const run = async (key: string, action: () => Promise<unknown>, message?: string) => {
    setBusy(key);
    setError(null);
    setDone(null);
    try {
      await action();
      if (message) {
        setDone(message);
      }
      return true;
    } catch (e) {
      setError(e);
      return false;
    } finally {
      setBusy(null);
    }
  };
  return { busy, error, done, run };
}

export function ErrorNote({ error }: { error: unknown }) {
  if (!error) {
    return null;
  }
  const text = error instanceof ApiError ? error.message : String(error);
  const detail = error instanceof ApiError && error.detail && error.code !== 'validation_error' ? JSON.stringify(error.detail) : null;
  return (
    <p className="error" role="alert">
      {text}
      {detail ? <code> {detail}</code> : null}
    </p>
  );
}

export function Page({ title, intro, actions, children }: { title: string; intro?: string; actions?: ReactNode; children: ReactNode }) {
  const { t } = useI18n();
  return (
    <section>
      <header className="page-head">
        <h1>{t(title)}</h1>
        {actions}
      </header>
      {intro ? <p className="muted">{intro}</p> : null}
      {children}
    </section>
  );
}

export function Loading({ loading, empty }: { loading: boolean; empty?: boolean }) {
  const { t } = useI18n();
  if (loading) {
    return <p className="muted">{t('Loading')}…</p>;
  }
  return empty ? <p className="muted">{t('Nothing here.')}</p> : null;
}

/** An {en, ar} text pair. */
export function Bilingual<T extends Record<string, string>>({ value, onChange, label }: { value: T; onChange: (v: T) => void; label: string }) {
  const { t } = useI18n();
  return (
    <fieldset className="pair">
      <legend>{label}</legend>
      <label>
        {t('English')}
        <input value={value.en ?? ''} onChange={e => onChange({ ...value, en: e.target.value })} dir="ltr" />
      </label>
      <label>
        {t('Arabic')}
        <input value={value.ar ?? ''} onChange={e => onChange({ ...value, ar: e.target.value })} dir="rtl" />
      </label>
    </fieldset>
  );
}

export const text = (v: Record<string, string> | null | undefined, language: string) => (v ? v[language] ?? v.en ?? '' : '');
