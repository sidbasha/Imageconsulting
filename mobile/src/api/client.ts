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

export type Questionnaire = {
  key: string;
  title: string;
  intro: string;
  questions: { key: string; prompt: string; options: { key: string; label: string }[] }[];
};

export type AssessmentResult = {
  questionnaire: string;
  title: string;
  completed_at: string;
  basis: 'self_assessment';
  profile: {
    key: string;
    title: string;
    summary: string;
    palette: string[] | null;
    advice: Record<string, string[]>;
  } | null;
  answers: { question: string; answer: string }[];
};

export type RecommendationCategory = 'outfits' | 'eyewear' | 'hair';

export type Recommendations = {
  category: RecommendationCategory;
  sections: { source: string; source_title: string; result: string; palette: string[] | null; items: string[] }[];
  /** Assessments the user has not completed yet that would add advice here. */
  missing: { key: string; title: string }[];
};

export type Photo = { id: string; kind: PhotoKind; width: number; height: number; size_bytes: number; created_at: string };
export type PhotoKind = 'face' | 'full_body';
/** A file picked on the device (React Native form part), or a Blob when running under Node. */
export type PhotoFile = { uri: string; name: string; type: string } | Blob;

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
    const isForm = typeof FormData !== 'undefined' && body instanceof FormData;
    if (body !== undefined && !isForm) {
      headers['Content-Type'] = 'application/json'; // for a form, fetch sets the multipart boundary itself
    }
    if (accessToken) {
      headers.Authorization = `Bearer ${accessToken}`;
    }
    try {
      return await doFetch(`${baseUrl}/api/v1${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : isForm ? (body as FormData) : JSON.stringify(body),
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

    questionnaire: (key: string) => request<Questionnaire>('GET', `/assessments/${key}`),

    submitAnswers: (key: string, answers: Record<string, string>) =>
      request<AssessmentResult>('POST', `/assessments/${key}/responses`, { body: { answers } }),

    /** The latest result, or null if the assessment has not been completed. */
    latestResult: (key: string) => request<AssessmentResult | null>('GET', `/assessments/${key}/result`),

    recommendations: (category: RecommendationCategory) =>
      request<Recommendations>('GET', `/recommendations/${category}`),

    /** `consent` must be the user's explicit agreement, given on screen, to process this photo. */
    uploadPhoto(file: PhotoFile, kind: PhotoKind, consent: boolean) {
      const form = new FormData();
      if (typeof Blob !== 'undefined' && file instanceof Blob) {
        (form as any).append('file', file, 'photo.jpg'); // Node/web signature; React Native's typings omit the file name
      } else {
        form.append('file', file as any);
      }
      form.append('kind', kind);
      form.append('consent', String(consent));
      return request<Photo>('POST', '/assessment-images', { body: form });
    },

    photos: () => request<Photo[]>('GET', '/assessment-images'),

    deletePhoto: (id: string) => request<void>('DELETE', `/assessment-images/${id}`),

    /** Enabled phases and features for the active release. Drives navigation. */
    enabledFeatures: () => request<EnabledFeatures>('GET', '/config/features'),
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;
