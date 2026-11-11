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
  'phase1.customer_subscriptions', 'phase1.digital_guides', 'phase1.eyewear', 'phase1.face_shape',
  'phase1.onboarding_quiz', 'phase1.outfit_recommendations', 'phase1.style_assessment',
];
export const PHASE2 = ['phase2.booking', 'phase2.messaging', 'phase2.stylist_discovery'];

export function createFakeServer() {
  const accounts: Account[] = [
    { id: 'u1', email: 'layla@example.com', password: 'correct-horse-battery', full_name: 'Layla', preferred_language: 'en', role: 'customer' },
  ];
  const access = new Map<string, string>(); // access token -> account id
  const refresh = new Map<string, string>();
  let counter = 0;

  const state = {
    features: [...PHASE1],
    offline: false,
    requests: [] as { method: string; path: string; language: string | undefined; body: any }[],
    expireAccessTokens: () => access.clear(),
    revokeEverything: () => {
      access.clear();
      refresh.clear();
    },
    account: (email: string) => accounts.find(a => a.email === email)!,
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
    const body = init.body ? JSON.parse(String(init.body)) : undefined;
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
    return json(404, { error: { code: 'not_found', message: 'not found' } });
  }) as unknown as typeof fetch;

  return { fetchImpl, state };
}
