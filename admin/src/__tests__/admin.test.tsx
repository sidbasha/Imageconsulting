import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import App from '../App';
import { tokens } from '../api';

type Handler = (body: any) => [number, unknown];
let routes: Record<string, Handler> = {};
let calls: { method: string; path: string; body: any }[] = [];

function serve(extra: Record<string, Handler>, permissions: string[]) {
  routes = {
    'POST /auth/login': () => [200, { access_token: 'a1', refresh_token: 'r1' }],
    'GET /users/me': () => [200, { full_name: 'Owner', email: 'o@x', role: 'super_admin', permissions }],
    ...extra,
  };
}

beforeEach(() => {
  calls = [];
  sessionStorage.clear();
  localStorage.clear();
  vi.stubGlobal('fetch', vi.fn(async (url: string, init: RequestInit = {}) => {
    const path = url.replace(/^.*\/api\/v1/, '');
    const method = init.method ?? 'GET';
    const body = init.body instanceof FormData ? init.body : init.body ? JSON.parse(String(init.body)) : undefined;
    calls.push({ method, path, body });
    const handler = routes[`${method} ${path}`];
    const [status, payload] = handler ? handler(body) : [404, { error: { code: 'not_found', message: `no route ${method} ${path}` } }];
    if (payload instanceof Blob) {
      return new Response(payload, { status });
    }
    return new Response(status === 204 ? null : JSON.stringify(payload), { status, headers: { 'Content-Type': 'application/json' } });
  }));
  vi.stubGlobal('URL', Object.assign(URL, { createObjectURL: () => 'blob:x' }));
});

async function signIn() {
  const user = userEvent.setup();
  render(<App initialPath="/" />);
  await user.type(await screen.findByLabelText('Email'), 'o@x.com');
  await user.type(screen.getByLabelText('Password'), 'secret-password');
  await user.click(screen.getByRole('button', { name: 'Sign in' }));
  return user;
}

test('sections follow the signed-in role; a client admin never sees release control', async () => {
  serve({ 'GET /admin/eligibility?status_filter=pending_review': () => [200, []], 'GET /admin/identity/pending': () => [200, []] },
    ['users.review', 'stylists.review', 'orders.manage']);
  await signIn();
  const nav = await screen.findByRole('navigation');
  expect(within(nav).getByRole('link', { name: 'Users' })).toBeInTheDocument();
  expect(within(nav).getByRole('link', { name: 'Orders' })).toBeInTheDocument();
  expect(within(nav).queryByRole('link', { name: 'Releases' })).toBeNull();
  expect(within(nav).queryByRole('link', { name: 'Settings' })).toBeNull();
  expect(tokens.load()).toEqual({ access: 'a1', refresh: 'r1' });
});

test('a customer account is told it has no admin access', async () => {
  serve({}, []);
  await signIn();
  expect(await screen.findByText('This account has no admin access.')).toBeInTheDocument();
});

test('release control: stage, check against dependencies, release with a note, restore an older one', async () => {
  const state = {
    release_version: 3,
    phases: [{ key: 'phase1', name: 'Phase 1', enabled: true }, { key: 'phase2', name: 'Phase 2', enabled: false }],
    features: [{ key: 'phase1.eyewear', name: 'Eyewear recommendations', phase: 'phase1', switch_on: true, available: true, is_enhancement: true,
      source_row: 13, source_phase_label: '', requires: ['phase1.face_shape'] }],
  };
  serve({
    'GET /admin/phase-management/state': () => [200, state],
    'GET /admin/phase-management/releases': () => [200, [
      { id: 'r3', version: 3, status: 'active', note: 'now', activate_at: null, activated_at: '2026-11-10T00:00:00Z', created_at: '' },
      { id: 'r2', version: 2, status: 'superseded', note: 'before', activate_at: null, activated_at: '2026-11-01T00:00:00Z', created_at: '' }]],
    'POST /admin/phase-management/releases/validate': () => [200, { violations: [], would_enable: ['phase2.booking'], would_disable: [] }],
    'POST /admin/phase-management/releases': () => [201, { id: 'r4' }],
    'POST /admin/phase-management/releases/r2/rollback': () => [201, { id: 'r5' }],
  }, ['release.view', 'release.manage']);
  const user = await signIn();
  await user.click(await screen.findByTestId('phase-phase2'));
  await user.click(screen.getByTestId('validate'));
  expect(await screen.findByText('Turns on: phase2.booking')).toBeInTheDocument();
  expect(screen.getByTestId('apply')).toBeDisabled(); // a note is required
  await user.type(screen.getByTestId('release-note'), 'Phase 2 delivered');
  await user.click(screen.getByTestId('apply'));
  await waitFor(() => expect(calls.find(c => c.method === 'POST' && c.path === '/admin/phase-management/releases')?.body)
    .toEqual({ phases: { phase2: true }, features: {}, note: 'Phase 2 delivered' }));
  await user.click(screen.getByTestId('restore-2'));
  await waitFor(() => expect(calls.some(c => c.path === '/admin/phase-management/releases/r2/rollback')).toBe(true));
});

test('stylist vetting: accept a credential, then approve', async () => {
  let accepted = false;
  serve({
    'GET /admin/stylists?status_filter=submitted': () => [200, [{ id: 'p1', display_name: 'Amal', bio: 'Colour', city: 'Dubai', years_experience: 6,
      business_license_no: null, status: 'submitted', review_note: null,
      credentials: [{ id: 'c1', kind: 'certification', title: 'AICI', status: accepted ? 'accepted' : 'pending', note: null }] }]],
    'POST /admin/stylists/credentials/c1/review': () => { accepted = true; return [200, {}]; },
    'POST /admin/stylists/p1/decision': () => [200, {}],
  }, ['stylists.review']);
  const user = await signIn();
  await user.click(await screen.findByTestId('accept-c1'));
  expect(await screen.findByText('accepted')).toBeInTheDocument();
  await user.type(screen.getByPlaceholderText('Shown to the applicant'), 'Welcome');
  await user.click(screen.getByTestId('approve-Amal'));
  await waitFor(() => expect(calls.find(c => c.path === '/admin/stylists/p1/decision')?.body).toEqual({ approve: true, note: 'Welcome' }));
});

test('try-on library: upload a reference photo, see the cut-out, approve it', async () => {
  const items: any[] = [];
  serve({
    'GET /admin/tryon-items': () => [200, items],
    'POST /admin/tryon-items': (form: FormData) => {
      expect(form.get('kind')).toBe('hairstyle');
      expect(form.get('licence')).toBe('Salon lookbook 2026');
      items.push({ id: 't1', kind: 'hairstyle', title: { en: 'Soft bob', ar: 'بوب' }, category: null, tags: {}, licence: 'Salon lookbook 2026',
        content_status: 'draft', is_active: true, created_at: '2026-11-12T00:00:00Z' });
      return [201, items[0]];
    },
    'GET /admin/tryon-items/t1/image': () => [200, new Blob(['png'])],
    'PATCH /admin/tryon-items/t1': body => { items[0].content_status = body.content_status ?? items[0].content_status; items[0].tags = body.tags ?? items[0].tags; return [200, items[0]]; },
  }, ['content.manage']);
  const user = await signIn();
  await user.click(await screen.findByRole('link', { name: 'Try-on library' }));
  await user.selectOptions(await screen.findByTestId('tryon-kind'), 'hairstyle');
  await user.type(screen.getByTestId('tryon-title-en'), 'Soft bob');
  await user.type(screen.getByTestId('tryon-title-ar'), 'بوب');
  await user.type(screen.getByTestId('tryon-licence'), 'Salon lookbook 2026');
  await user.upload(screen.getByTestId('tryon-file'), new File(['jpg'], 'ref.jpg', { type: 'image/jpeg' }));
  await user.click(screen.getByTestId('tryon-upload'));
  expect(await screen.findByText('Cut out. Check it below and approve it.')).toBeInTheDocument();
  expect(await screen.findByAltText('Soft bob')).toBeInTheDocument();
  await user.type(screen.getByPlaceholderText('face_shape: oval, round'), 'face_shape: oval');
  await user.click(screen.getByTestId('approve-Soft bob'));
  await waitFor(() => expect(calls.find(c => c.method === 'PATCH')?.body).toEqual({ content_status: 'approved', tags: { face_shape: ['oval'] } }));
});

test('refunds ask for confirmation first', async () => {
  serve({
    'GET /admin/orders': () => [200, [{ id: 'o1', kind: 'product', status: 'paid', amount_minor: 2900, currency: 'AED', items: [{ title: 'Pear guide', quantity: 1 }],
      created_at: '2026-11-12T00:00:00Z', paid_at: null, fulfilment_status: null, shipping: null, user_id: 'u1', points_used: 0 }]],
    'POST /admin/orders/o1/refund': () => [200, {}],
  }, ['orders.manage']);
  const user = await signIn();
  await user.click(await screen.findByRole('link', { name: 'Orders' }));
  const confirm = vi.spyOn(window, 'confirm').mockReturnValueOnce(false).mockReturnValueOnce(true);
  await user.click(await screen.findByTestId('refund-o1'));
  expect(calls.some(c => c.path === '/admin/orders/o1/refund')).toBe(false);
  await user.click(screen.getByTestId('refund-o1'));
  await waitFor(() => expect(calls.some(c => c.path === '/admin/orders/o1/refund')).toBe(true));
  expect(confirm).toHaveBeenCalledWith('Refund AED 29.00? Anything the order gave is taken back.');
});

test('Arabic switches the panel to right-to-left', async () => {
  serve({ 'GET /admin/settings': () => [200, []], 'GET /countries': () => [200, []] }, ['settings.manage']);
  const user = await signIn();
  await user.click(await screen.findByTestId('language'));
  expect(document.documentElement.dir).toBe('rtl');
  expect(await screen.findByRole('link', { name: 'الإعدادات' })).toBeInTheDocument();
});
