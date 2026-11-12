/**
 * End-to-end: the mobile app's API client and navigation registry against a
 * running backend (real HTTP, real PostgreSQL). Nothing is mocked.
 *
 * Needs: E2E_API_URL, plus a Super Admin account in E2E_ADMIN_EMAIL /
 * E2E_ADMIN_PASSWORD. `scripts/e2e.sh` at the repository root sets all of
 * this up and runs the test.
 */
import fs from 'fs';

import { createApiClient, type Language, type Tokens, type TokenStore } from '../src/api/client';
import { visibleSections } from '../src/navigation/registry';

const BASE = process.env.E2E_API_URL;
const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL;
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD;
if (!BASE || !ADMIN_EMAIL || !ADMIN_PASSWORD) {
  throw new Error('Set E2E_API_URL, E2E_ADMIN_EMAIL and E2E_ADMIN_PASSWORD (see scripts/e2e.sh)');
}

function device(language: Language = 'en') {
  let stored: Tokens | null = null;
  const state = { language, expired: 0 };
  const tokenStore: TokenStore = {
    load: async () => stored,
    save: async tokens => {
      stored = tokens;
    },
    clear: async () => {
      stored = null;
    },
  };
  const api = createApiClient({
    baseUrl: BASE!,
    tokenStore,
    getLanguage: () => state.language,
    onSessionExpired: () => (state.expired += 1),
  });
  return { api, state, tokens: () => stored, corruptAccessToken: () => (stored = { ...stored!, accessToken: 'stale' }) };
}

async function admin(method: string, path: string, body?: unknown) {
  const login = await fetch(`${BASE}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: ADMIN_EMAIL, password: ADMIN_PASSWORD }),
  });
  const { access_token } = await login.json();
  const response = await fetch(`${BASE}/api/v1/admin/phase-management${path}`, {
    method,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${access_token}` },
    body: body ? JSON.stringify(body) : undefined,
  });
  return { status: response.status, body: await response.json() };
}

const email = `e2e-${Date.now()}@example.com`;
const password = 'e2e-password-long-enough';
const groups = (features: string[]) => visibleSections(features).map(s => s.group);

describe('mobile app against the live API', () => {
  const phone = device('ar');
  let launchReleaseId: string;

  beforeAll(async () => {
    const state = await admin('GET', '/state');
    expect(state.status).toBe(200);
    launchReleaseId = state.body.release_id;
    expect(state.body.phases.map((p: any) => p.enabled)).toEqual([true, false, false]);
  });

  test('register in Arabic, then read the profile', async () => {
    const user = await phone.api.register({ email, password, full_name: 'نور', preferred_language: 'ar' });
    expect(user).toMatchObject({ email, full_name: 'نور', preferred_language: 'ar', role: 'customer' });
  });

  test('the launch release exposes Phase 1 only, and the home screen follows it', async () => {
    const enabled = await phone.api.enabledFeatures();
    expect(enabled.phases).toEqual(['phase1']);
    expect(enabled.features).toHaveLength(20);
    expect(groups(enabled.features)).toEqual(['assessment', 'recommendations', 'library', 'account']);
  });

  test('server errors arrive in the language the app is set to', async () => {
    const other = device('ar');
    const arabic = await other.api.login(email, 'wrong-password').catch(e => e);
    expect(arabic).toMatchObject({ status: 401, code: 'invalid_credentials' });
    expect(arabic.message).toMatch(/[؀-ۿ]/);
    other.state.language = 'en';
    const english = await other.api.login(email, 'wrong-password').catch(e => e);
    expect(english.message).toBe('The email or password is incorrect.');
  });

  test('language change is saved to the profile', async () => {
    phone.state.language = 'en';
    expect((await phone.api.updateMe({ preferred_language: 'en' })).preferred_language).toBe('en');
    expect((await phone.api.me()).preferred_language).toBe('en');
  });

  test('a stale access token is renewed transparently', async () => {
    const before = phone.tokens()!.refreshToken;
    phone.corruptAccessToken();
    expect((await phone.api.me()).email).toBe(email);
    expect(phone.tokens()!.refreshToken).not.toBe(before);
    expect(phone.state.expired).toBe(0);
  });

  test('releasing Phase 2 in the admin API changes what the app shows, with no new build', async () => {
    const released = await admin('POST', '/releases', { phases: { phase2: true }, note: 'e2e: release phase 2' });
    expect(released.status).toBe(201);
    const enabled = await phone.api.enabledFeatures();
    expect(enabled.phases).toEqual(['phase1', 'phase2']);
    expect(enabled.features).toHaveLength(44);
    expect(groups(enabled.features)).toContain('experts');
    expect(groups(enabled.features)).not.toContain('shop');
  });

  test('rolling back hides Phase 2 again', async () => {
    const rolled = await admin('POST', `/releases/${launchReleaseId}/rollback`, { note: 'e2e: back to launch' });
    expect(rolled.status).toBe(201);
    const enabled = await phone.api.enabledFeatures();
    expect(enabled.phases).toEqual(['phase1']);
    expect(groups(enabled.features)).not.toContain('experts');
  });

  test('a customer cannot reach release control', async () => {
    const tokens = phone.tokens()!;
    const response = await fetch(`${BASE}/api/v1/admin/phase-management/state`, {
      headers: { Authorization: `Bearer ${tokens.accessToken}` },
    });
    expect(response.status).toBe(403);
  });

  test('take the style assessment in Arabic and get advice from it', async () => {
    phone.state.language = 'ar';
    const questionnaire = await phone.api.questionnaire('style');
    expect(questionnaire.title).toBe('تقييم الأسلوب الشخصي');
    expect(questionnaire.questions.map(q => q.key)).toEqual(['line', 'shape', 'colour', 'texture', 'pattern']);
    expect(await phone.api.latestResult('style')).toBeNull();

    // Pick the third option everywhere: the "romantic" answers.
    const answers = Object.fromEntries(questionnaire.questions.map(q => [q.key, q.options[2].key]));
    const result = await phone.api.submitAnswers('style', answers);
    expect(result.profile).toMatchObject({ key: 'romantic', title: 'رومانسي' });
    expect(result.profile!.advice.outfits).toHaveLength(3);
    expect((await phone.api.latestResult('style'))!.profile!.key).toBe('romantic');

    const outfits = await phone.api.recommendations('outfits');
    expect(outfits.sections.map(s => s.source)).toEqual(['style']);
    expect(outfits.missing.map(m => m.key)).toEqual(['body_shape', 'seasonal_color']);

    phone.state.language = 'en';
    expect((await phone.api.latestResult('style'))!.profile!.title).toBe('Romantic');
    const incomplete = await phone.api.submitAnswers('style', { line: 'curved' }).catch(e => e);
    expect(incomplete).toMatchObject({ status: 422, code: 'invalid_answers' });
  });

  test('colour self-assessment returns a palette', async () => {
    const result = await phone.api.submitAnswers('seasonal_color', {
      jewellery: 'silver', veins: 'blue', depth: 'deep', clarity: 'bright',
    });
    expect(result.profile!.key).toBe('winter');
    expect(result.profile!.palette).toHaveLength(6);
  });

  test('a good photo is accepted, a blurry one is refused with reasons, and photos can be deleted', async () => {
    const photo = (name: string) => new Blob([new Uint8Array(fs.readFileSync(`${process.env.E2E_PHOTO_DIR}/${name}`)) as any], { type: 'image/jpeg' } as any);

    const refused = await phone.api.uploadPhoto(photo('good.jpg'), 'face', false).catch(e => e);
    expect(refused).toMatchObject({ status: 422, code: 'consent_required' });

    const blurry = await phone.api.uploadPhoto(photo('blurry.jpg'), 'face', true).catch(e => e);
    expect(blurry).toMatchObject({ status: 422, code: 'photo_rejected' });
    expect(blurry.detail.reasons).toEqual(['too_blurry']);

    const saved = await phone.api.uploadPhoto(photo('good.jpg'), 'face', true);
    expect(saved).toMatchObject({ kind: 'face', width: 600, height: 600 });
    expect((await phone.api.photos()).map(p => p.id)).toEqual([saved.id]);

    await phone.api.deletePhoto(saved.id);
    expect(await phone.api.photos()).toEqual([]);
  });

  test('switching one feature off blocks it for the app and keeps the result for later', async () => {
    const off = await admin('POST', '/releases', { features: { 'phase1.style_assessment': false, 'phase1.outfit_recommendations': false, 'phase1.virtual_tryon': false }, note: 'e2e: style off' });
    expect(off.status).toBe(201);
    expect(await phone.api.questionnaire('style').catch(e => e)).toMatchObject({ status: 404, code: 'feature_not_available' });
    expect((await phone.api.enabledFeatures()).features).not.toContain('phase1.style_assessment');

    const back = await admin('POST', `/releases/${launchReleaseId}/rollback`, { note: 'e2e: style back on' });
    expect(back.status).toBe(201);
    expect((await phone.api.latestResult('style'))!.profile!.key).toBe('romantic');
  });

  test('sign out ends the session on the server as well', async () => {
    const old = phone.tokens()!;
    await phone.api.logout();
    expect(phone.tokens()).toBeNull();
    const reuse = await fetch(`${BASE}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: old.refreshToken }),
    });
    expect(reuse.status).toBe(401);
  });

  test('signing in again on a new device works', async () => {
    const tablet = device('en');
    expect((await tablet.api.login(email, password)).preferred_language).toBe('en');
  });
});
