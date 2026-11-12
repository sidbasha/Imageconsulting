import { useState } from 'react';

import { api, day } from '../api';
import { useI18n } from '../i18n';
import { ErrorNote, Loading, Page, useAction, useData } from '../ui';

type Violation = { id: string; user: { id: string; name: string; email: string }; kinds: string[]; message: string; message_status: string; created_at: string; user_violations: number };
type Restriction = { user_id: string; warned_at: string | null; suspended_until: string | null; banned_at: string | null; note: string | null };
type Testimonial = { id: string; stylist: string; rating: number; text: string; status: string; created_at: string };

/** Flagged messages, suspensions and testimonials (rows 31-33, 45, 58). */
export function Moderation() {
  const { t } = useI18n();
  const violations = useData(() => api<Violation[]>('GET', '/admin/moderation/violations'));
  const restrictions = useData(() => api<Restriction[]>('GET', '/admin/moderation/restrictions'));
  const testimonials = useData(() => api<Testimonial[]>('GET', '/admin/stylists/testimonials'));
  const [note, setNote] = useState('Reviewed by moderator');
  const action = useAction();

  const review = (v: Violation, uphold: boolean) =>
    action.run(v.id, async () => {
      await api('POST', `/admin/moderation/violations/${v.id}`, { uphold });
      await violations.reload();
    });
  const lift = (userId: string) =>
    action.run(userId, async () => {
      await api('POST', `/admin/moderation/users/${userId}/lift`, { note });
      await restrictions.reload();
    });
  const setTestimonial = (tm: Testimonial, status: string) =>
    action.run(tm.id, async () => {
      await api('PATCH', `/admin/stylists/testimonials/${tm.id}`, { status });
      await testimonials.reload();
    });

  return (
    <Page title="Moderation" intro="Dismissing a violation delivers the message after all and stops it counting. Thresholds are in Settings (moderation.*).">
      <ErrorNote error={violations.error ?? action.error} />
      <h2>Flagged messages</h2>
      <Loading loading={violations.loading} empty={violations.data?.length === 0} />
      {violations.data?.length ? (
        <table>
          <thead><tr><th>Sender</th><th>Message</th><th>Found</th><th>Count</th><th /></tr></thead>
          <tbody>
            {violations.data.map(v => (
              <tr key={v.id}>
                <td>{v.user.name}<br /><span className="muted">{v.user.email}</span></td>
                <td>{v.message}<br /><span className="muted">{day(v.created_at)} · {v.message_status}</span></td>
                <td>{v.kinds.join(', ')}</td>
                <td>{v.user_violations}</td>
                <td className="row">
                  <button onClick={() => review(v, true)} data-testid={`uphold-${v.id}`}>Uphold</button>
                  <button className="link" onClick={() => review(v, false)} data-testid={`dismiss-${v.id}`}>Dismiss (false positive)</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}

      <h2>Suspended and closed accounts</h2>
      <label style={{ maxWidth: 420 }}>{t('Note')}<input value={note} onChange={e => setNote(e.target.value)} /></label>
      <Loading loading={restrictions.loading} empty={restrictions.data?.length === 0} />
      {restrictions.data?.map(r => (
        <div key={r.user_id} className="card row">
          <code>{r.user_id}</code>
          <span>{r.banned_at ? `closed ${day(r.banned_at)}` : `suspended until ${day(r.suspended_until)}`}</span>
          <button onClick={() => lift(r.user_id)}>Lift</button>
        </div>
      ))}

      <h2>{t('Testimonials')}</h2>
      <Loading loading={testimonials.loading} empty={testimonials.data?.length === 0} />
      {testimonials.data?.length ? (
        <table>
          <thead><tr><th>Stylist</th><th>Rating</th><th>Text</th><th>{t('Status')}</th><th /></tr></thead>
          <tbody>
            {testimonials.data.map(tm => (
              <tr key={tm.id}>
                <td>{tm.stylist}</td><td>{'★'.repeat(tm.rating)}</td><td>{tm.text}</td><td>{tm.status}</td>
                <td><button className="link" onClick={() => setTestimonial(tm, tm.status === 'published' ? 'hidden' : 'published')}>{tm.status === 'published' ? 'Hide' : 'Publish'}</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </Page>
  );
}
