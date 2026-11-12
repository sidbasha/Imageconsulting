/**
 * In-memory imitation of the backend's HTTP contract, for component tests.
 * The real contract is exercised by e2e/api.e2e.test.ts against the live API.
 */
import type { Language } from '../src/api/client';

type Account = { id: string; email: string; password: string; full_name: string; preferred_language: Language; role: string };

const MESSAGES: Record<string, Record<Language, string>> = {
  invalid_credentials: { en: 'The email or password is incorrect.', ar: 'البريد الإلكتروني أو كلمة المرور غير صحيحة.' },
  invalid_token: { en: 'Your session is no longer valid. Please sign in again.', ar: 'انتهت صلاحية الجلسة. يرجى تسجيل الدخول مرة أخرى.' },
  email_exists: { en: 'This email is already registered.', ar: 'هذا البريد الإلكتروني مسجّل مسبقاً.' },
};

export const PHASE1 = [
  'phase1.photo_assessment', 'phase1.customer_subscriptions', 'phase1.digital_guides', 'phase1.eyewear', 'phase1.face_shape',
  'phase1.onboarding_quiz', 'phase1.outfit_recommendations', 'phase1.style_assessment',
];
export const PHASE2 = ['phase2.booking', 'phase2.messaging', 'phase2.stylist_discovery'];

const STYLE = {
  title: { en: 'Personal style assessment', ar: 'تقييم الأسلوب الشخصي' },
  intro: { en: 'Two questions.', ar: 'سؤالان.' },
  questions: [
    { key: 'line', prompt: { en: 'Which lines do you prefer?', ar: 'أي الخطوط تفضّلين؟' },
      options: [
        { key: 'straight', label: { en: 'Straight lines', ar: 'خطوط مستقيمة' }, profile: 'classic' },
        { key: 'curved', label: { en: 'Curved lines', ar: 'خطوط منحنية' }, profile: 'romantic' },
      ] },
    { key: 'pattern', prompt: { en: 'Which patterns do you choose?', ar: 'أي النقوش تختارين؟' },
      options: [
        { key: 'subtle', label: { en: 'Subtle stripes', ar: 'خطوط خفيفة' }, profile: 'classic' },
        { key: 'floral', label: { en: 'Florals', ar: 'نقوش الأزهار' }, profile: 'romantic' },
      ] },
  ],
  profiles: {
    classic: { title: { en: 'Classic', ar: 'كلاسيكي' }, summary: { en: 'Timeless pieces.', ar: 'قطع خالدة.' },
      advice: { en: ['Build around tailored blazers.'], ar: ['اعتمدي على السترات المفصّلة.'] } },
    romantic: { title: { en: 'Romantic', ar: 'رومانسي' }, summary: { en: 'Soft lines.', ar: 'خطوط ناعمة.' },
      advice: { en: ['Choose dresses that define the waist.'], ar: ['اختاري الفساتين التي تحدّد الخصر.'] } },
  } as Record<string, { title: Record<Language, string>; summary: Record<Language, string>; advice: Record<Language, string[]> }>,
};

export function createFakeServer() {
  const results = new Map<string, Record<string, string>>(); // account id -> style answers
  const photos = new Map<string, { id: string; kind: string; width: number; height: number; size_bytes: number; created_at: string }[]>();
  const describeResult = (answers: Record<string, string>, language: Language) => {
    const first = STYLE.questions[0].options.find(o => o.key === answers.line)!;
    const profile = STYLE.profiles[first.profile];
    return {
      questionnaire: 'style', title: STYLE.title[language], completed_at: '2026-11-12T00:00:00Z', basis: 'self_assessment',
      profile: { key: first.profile, title: profile.title[language], summary: profile.summary[language], palette: null,
        advice: { outfits: profile.advice[language] } },
      answers: STYLE.questions.map(q => ({
        question: q.prompt[language], answer: q.options.find(o => o.key === answers[q.key])!.label[language] })),
    };
  };

  const accounts: Account[] = [
    { id: 'u1', email: 'layla@example.com', password: 'correct-horse-battery', full_name: 'Layla', preferred_language: 'en', role: 'customer' },
  ];
  const access = new Map<string, string>(); // access token -> account id
  const refresh = new Map<string, string>();
  let counter = 0;

  const state = {
    /** Set to reason codes to make the next uploads fail the quality gate. */
    rejectPhotosWith: null as string[] | null,
    uploads: [] as { kind: unknown; consent: unknown; file: unknown }[],
    features: [...PHASE1],
    offline: false,
    requests: [] as { method: string; path: string; language: string | undefined; body: any }[],
    expireAccessTokens: () => access.clear(),
    revokeEverything: () => {
      access.clear();
      refresh.clear();
    },
    account: (email: string) => accounts.find(a => a.email === email)!,
    /**
     * Extra endpoints for a test: "METHOD /path" -> handler. The handler gets the
     * parsed JSON body (or the form) and the request language, and returns
     * [status, body]. A body of type Uint8Array is sent as image bytes.
     */
    routes: {} as Record<string, (body: any, language: Language) => [number, unknown]>,
  };

  const json = (status: number, body?: unknown) =>
    ({ ok: status < 400, status, json: async () => body } as unknown as Response);
  const fail = (status: number, code: string, language: Language) =>
    json(status, { error: { code, message: MESSAGES[code]?.[language] ?? code } });
  const issue = (account: Account) => {
    counter += 1;
    const tokens = { access_token: `access-${counter}`, refresh_token: `refresh-${counter}`, token_type: 'bearer' };
    access.set(tokens.access_token, account.id);
    refresh.set(tokens.refresh_token, account.id);
    return tokens;
  };
  const publicUser = ({ password: _password, ...user }: Account) => user;

  const fetchImpl = (async (url: string, init: RequestInit = {}) => {
    const path = String(url).replace(/^.*\/api\/v1/, '');
    const method = init.method ?? 'GET';
    const headers = (init.headers ?? {}) as Record<string, string>;
    const form = typeof FormData !== 'undefined' && init.body instanceof FormData ? (init.body as any) : null;
    const body = init.body && !form ? JSON.parse(String(init.body)) : undefined;
    const language = (headers['Accept-Language'] ?? 'en') as Language;
    state.requests.push({ method, path, language, body });
    if (state.offline) {
      throw new TypeError('Network request failed');
    }
    const bearer = headers.Authorization?.replace('Bearer ', '');
    const current = accounts.find(a => a.id === access.get(bearer ?? ''));

    if (method === 'POST' && path === '/auth/login') {
      const account = accounts.find(a => a.email === body.email.toLowerCase() && a.password === body.password);
      return account ? json(200, issue(account)) : fail(401, 'invalid_credentials', language);
    }
    if (method === 'POST' && path === '/auth/register') {
      if (accounts.some(a => a.email === body.email.toLowerCase())) {
        return fail(409, 'email_exists', language);
      }
      const account: Account = { id: `u${accounts.length + 1}`, role: 'customer', ...body, email: body.email.toLowerCase() };
      accounts.push(account);
      return json(201, issue(account));
    }
    if (method === 'POST' && path === '/auth/refresh') {
      const account = accounts.find(a => a.id === refresh.get(body.refresh_token));
      refresh.delete(body.refresh_token); // each refresh token works once
      return account ? json(200, issue(account)) : fail(401, 'invalid_token', language);
    }
    if (method === 'POST' && path === '/auth/logout') {
      refresh.delete(body.refresh_token);
      return json(204);
    }
    if (path === '/config/features') {
      if (bearer && !current) {
        return fail(401, 'invalid_token', language);
      }
      const phases = [...new Set(state.features.map(f => f.split('.')[0]))].sort();
      return json(200, { release_version: 1, preview: false, phases, features: [...state.features].sort() });
    }
    if (path === '/users/me') {
      if (!current) {
        return fail(401, 'invalid_token', language);
      }
      if (method === 'PATCH') {
        Object.assign(current, body);
      }
      return json(200, publicUser(current));
    }
    const route = state.routes[`${method} ${path}`];
    if (route) {
      if (!current) {
        return fail(401, 'invalid_token', language);
      }
      const [status, payload] = route(form ?? body, language);
      if (payload instanceof Uint8Array) {
        return { ok: status < 400, status, arrayBuffer: async () => payload.buffer } as unknown as Response;
      }
      return json(status, payload);
    }
    if (path.startsWith('/assessments/') || path.startsWith('/recommendations/') || path.startsWith('/assessment-images')) {
      if (!current) {
        return fail(401, 'invalid_token', language);
      }
      const mine = photos.get(current.id) ?? [];
      if (path === '/assessments/style' && state.features.includes('phase1.style_assessment')) {
        return json(200, {
          key: 'style', title: STYLE.title[language], intro: STYLE.intro[language],
          questions: STYLE.questions.map(q => ({ key: q.key, prompt: q.prompt[language],
            options: q.options.map(o => ({ key: o.key, label: o.label[language] })) })),
        });
      }
      if (path === '/assessments/style/result') {
        const answers = results.get(current.id);
        return json(200, answers ? describeResult(answers, language) : null);
      }
      if (method === 'POST' && path === '/assessments/style/responses') {
        results.set(current.id, body.answers);
        return json(201, describeResult(body.answers, language));
      }
      if (path === '/recommendations/outfits') {
        const answers = results.get(current.id);
        const done = answers && describeResult(answers, language);
        return json(200, {
          category: 'outfits',
          sections: done ? [{ source: 'style', source_title: STYLE.title[language], result: done.profile.title,
            palette: null, items: done.profile.advice.outfits }] : [],
          missing: done ? [] : [{ key: 'style', title: STYLE.title[language] }],
        });
      }
      if (method === 'POST' && path === '/assessment-images') {
        const part = (name: string) => form?.getParts?.().find((p: any) => p.fieldName === name);
        const read = (name: string) => form?.get?.(name) ?? part(name)?.string ?? part(name);
        state.uploads.push({ kind: read('kind'), consent: read('consent'), file: read('file') });
        if (state.rejectPhotosWith) {
          return json(422, { error: { code: 'photo_rejected', message: 'rejected', detail: { reasons: state.rejectPhotosWith } } });
        }
        const photo = { id: `photo-${mine.length + 1}`, kind: String(read('kind')), width: 1200, height: 1600, size_bytes: 1, created_at: '2026-11-12T00:00:00Z' };
        photos.set(current.id, [photo, ...mine]);
        return json(201, photo);
      }
      if (method === 'DELETE' && path.startsWith('/assessment-images/')) {
        photos.set(current.id, mine.filter(p => `/assessment-images/${p.id}` !== path));
        return json(204);
      }
      if (path === '/assessment-images') {
        return json(200, mine);
      }
      return json(404, { error: { code: 'feature_not_available', message: 'This feature is not available.' } });
    }
    return json(404, { error: { code: 'not_found', message: 'not found' } });
  }) as unknown as typeof fetch;

  return { fetchImpl, state };
}
