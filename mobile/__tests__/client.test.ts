import { ApiError, createApiClient, type Tokens, type TokenStore } from '../src/api/client';
import { createFakeServer } from '../testing/fakeServer';

function setup() {
  const server = createFakeServer();
  let stored: Tokens | null = null;
  const tokenStore: TokenStore = {
    load: async () => stored,
    save: async tokens => {
      stored = tokens;
    },
    clear: async () => {
      stored = null;
    },
  };
  const expired = jest.fn();
  let language: 'en' | 'ar' = 'en';
  const api = createApiClient({
    baseUrl: 'http://test',
    tokenStore,
    getLanguage: () => language,
    onSessionExpired: expired,
    fetchImpl: server.fetchImpl,
  });
  return { api, server, expired, tokens: () => stored, setLanguage: (l: 'en' | 'ar') => (language = l) };
}

const refreshCalls = (server: ReturnType<typeof createFakeServer>) =>
  server.state.requests.filter(r => r.path === '/auth/refresh').length;

test('login stores tokens and returns the profile', async () => {
  const { api, tokens } = setup();
  const user = await api.login('layla@example.com', 'correct-horse-battery');
  expect(user.full_name).toBe('Layla');
  expect(tokens()).toEqual({ accessToken: 'access-1', refreshToken: 'refresh-1' });
});

test('wrong password surfaces the server code and message, and stores nothing', async () => {
  const { api, tokens, setLanguage } = setup();
  setLanguage('ar');
  const error = await api.login('layla@example.com', 'nope').catch(e => e);
  expect(error).toBeInstanceOf(ApiError);
  expect(error).toMatchObject({ status: 401, code: 'invalid_credentials' });
  expect(error.message).toBe('البريد الإلكتروني أو كلمة المرور غير صحيحة.');
  expect(tokens()).toBeNull();
});

test('an expired access token is renewed once and the request retried', async () => {
  const { api, server, expired, tokens } = setup();
  await api.login('layla@example.com', 'correct-horse-battery');
  server.state.expireAccessTokens();
  expect((await api.me()).email).toBe('layla@example.com');
  expect(refreshCalls(server)).toBe(1);
  expect(tokens()?.refreshToken).toBe('refresh-2');
  expect(expired).not.toHaveBeenCalled();
});

test('concurrent requests share one refresh, because a refresh token works once', async () => {
  const { api, server } = setup();
  await api.login('layla@example.com', 'correct-horse-battery');
  server.state.expireAccessTokens();
  const [me, features] = await Promise.all([api.me(), api.enabledFeatures()]);
  expect(me.email).toBe('layla@example.com');
  expect(features.phases).toEqual(['phase1']);
  expect(refreshCalls(server)).toBe(1);
});

test('when the session cannot be renewed, tokens are cleared and the app is told once', async () => {
  const { api, server, expired, tokens } = setup();
  await api.login('layla@example.com', 'correct-horse-battery');
  server.state.revokeEverything();
  await expect(api.me()).rejects.toMatchObject({ status: 401, code: 'invalid_token' });
  expect(tokens()).toBeNull();
  expect(expired).toHaveBeenCalledTimes(1);
});

test('no connection becomes a network_error and keeps the session', async () => {
  const { api, server, tokens, expired } = setup();
  await api.login('layla@example.com', 'correct-horse-battery');
  server.state.offline = true;
  await expect(api.me()).rejects.toMatchObject({ status: 0, code: 'network_error' });
  expect(tokens()).not.toBeNull();
  expect(expired).not.toHaveBeenCalled();
});

test('logout clears local tokens even if the server cannot be reached', async () => {
  const { api, server, tokens } = setup();
  await api.login('layla@example.com', 'correct-horse-battery');
  server.state.offline = true;
  await api.logout();
  expect(tokens()).toBeNull();
});

test('every request carries the current language', async () => {
  const { api, server, setLanguage } = setup();
  await api.enabledFeatures();
  setLanguage('ar');
  await api.enabledFeatures();
  expect(server.state.requests.map(r => r.language)).toEqual(['en', 'ar']);
});

test('restoreSession returns null without tokens and makes no request', async () => {
  const { api, server } = setup();
  expect(await api.restoreSession()).toBeNull();
  expect(server.state.requests).toHaveLength(0);
});
