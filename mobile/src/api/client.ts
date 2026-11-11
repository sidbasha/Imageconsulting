/**
 * HTTP client for the Image Consulting API.
 *
 * No React Native imports on purpose: the same code runs in the app, in unit
 * tests and in the Node end-to-end test against a live backend.
 */

export type Language = 'en' | 'ar';

export type Tokens = { accessToken: string; refreshToken: string };

export type TokenStore = {
  load(): Promise<Tokens | null>;
  save(tokens: Tokens): Promise<void>;
  clear(): Promise<void>;
};

export type User = {
  id: string;
  email: string;
  full_name: string;
  preferred_language: Language;
  role: string;
};

export type EnabledFeatures = {
  release_version: number;
  preview: boolean;
  phases: string[];
  features: string[];
};

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly detail?: unknown,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

type Options = {
  baseUrl: string;
  tokenStore: TokenStore;
  getLanguage: () => Language;
  /** Called once when the session cannot be renewed and the user must sign in again. */
  onSessionExpired?: () => void;
  fetchImpl?: typeof fetch;
};

type RequestOptions = { body?: unknown; auth?: boolean };

type TokenResponse = { access_token: string; refresh_token: string };

const toTokens = (r: TokenResponse): Tokens => ({
  accessToken: r.access_token,
  refreshToken: r.refresh_token,
});

export function createApiClient(options: Options) {
  const { baseUrl, tokenStore, getLanguage, onSessionExpired } = options;
  const doFetch = options.fetchImpl ?? fetch;
  const expiryListeners = new Set<() => void>();
  if (onSessionExpired) {
    expiryListeners.add(onSessionExpired);
  }
  let refreshing: Promise<Tokens | null> | null = null;

  async function send(
    method: string,
    path: string,
    body: unknown,
    accessToken: string | null,
  ): Promise<Response> {
    const headers: Record<string, string> = {
      Accept: 'application/json',
      'Accept-Language': getLanguage(),
    };
    if (body !== undefined) {
      headers['Content-Type'] = 'application/json';
    }
    if (accessToken) {
      headers.Authorization = `Bearer ${accessToken}`;
    }
    try {
      return await doFetch(`${baseUrl}/api/v1${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch {
      throw new ApiError(0, 'network_error', 'Network request failed');
    }
  }

  async function toError(response: Response): Promise<ApiError> {
    let payload: any = null;
    try {
      payload = await response.json();
    } catch {
      // Non-JSON error body: fall through to the generic error.
    }
    if (payload?.error?.code) {
      const { code, message, detail } = payload.error;
      return new ApiError(response.status, code, message ?? code, detail);
    }
    if (response.status === 422) {
      return new ApiError(422, 'validation_error', 'Invalid input', payload?.detail);
    }
    return new ApiError(response.status, 'unexpected_error', `HTTP ${response.status}`);
  }

  /** Single-flight: concurrent 401s share one refresh, because each refresh token works once. */
  function refreshTokens(refreshToken: string): Promise<Tokens | null> {
    if (!refreshing) {
      refreshing = (async () => {
        try {
          const response = await send('POST', '/auth/refresh', { refresh_token: refreshToken }, null);
          if (!response.ok) {
            return null;
          }
          const tokens = toTokens(await response.json());
          await tokenStore.save(tokens);
          return tokens;
        } finally {
          refreshing = null;
        }
      })();
    }
    return refreshing;
  }

  async function request<T>(method: string, path: string, opts: RequestOptions = {}): Promise<T> {
    const useAuth = opts.auth !== false;
    const tokens = useAuth ? await tokenStore.load() : null;
    let response = await send(method, path, opts.body, tokens?.accessToken ?? null);

    if (response.status === 401 && tokens) {
      const renewed = await refreshTokens(tokens.refreshToken);
      if (!renewed) {
        await tokenStore.clear();
        expiryListeners.forEach(listener => listener());
        throw await toError(response);
      }
      response = await send(method, path, opts.body, renewed.accessToken);
    }
    if (!response.ok) {
      throw await toError(response);
    }
    return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
  }

  async function startSession(path: string, body: unknown): Promise<User> {
    const tokens = toTokens(await request<TokenResponse>('POST', path, { body, auth: false }));
    await tokenStore.save(tokens);
    return request<User>('GET', '/users/me');
  }

  return {
    /** Subscribe to "the session could not be renewed". Returns an unsubscribe function. */
    onSessionExpired(listener: () => void): () => void {
      expiryListeners.add(listener);
      return () => {
        expiryListeners.delete(listener);
      };
    },

    register: (input: { email: string; password: string; full_name: string; preferred_language: Language }) =>
      startSession('/auth/register', input),

    login: (email: string, password: string) => startSession('/auth/login', { email, password }),

    async logout(): Promise<void> {
      const tokens = await tokenStore.load();
      await tokenStore.clear();
      if (tokens) {
        // Best effort: the local session is gone either way.
        await send('POST', '/auth/logout', { refresh_token: tokens.refreshToken }, null).catch(() => undefined);
      }
    },

    async restoreSession(): Promise<User | null> {
      if (!(await tokenStore.load())) {
        return null;
      }
      return request<User>('GET', '/users/me');
    },

    me: () => request<User>('GET', '/users/me'),

    updateMe: (changes: { full_name?: string; preferred_language?: Language }) =>
      request<User>('PATCH', '/users/me', { body: changes }),

    /** Enabled phases and features for the active release. Drives navigation. */
    enabledFeatures: () => request<EnabledFeatures>('GET', '/config/features'),
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;
