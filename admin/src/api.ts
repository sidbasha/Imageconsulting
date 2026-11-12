/**
 * Calls the API with the signed-in administrator's token. Tokens are kept in
 * sessionStorage: they end with the browser tab. A 401 triggers one refresh
 * (refresh tokens work once); if that fails the session ends.
 */
export const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000';

export class ApiError extends Error {
  constructor(readonly status: number, readonly code: string, message: string, readonly detail?: unknown) {
    super(message);
  }
}

type Tokens = { access: string; refresh: string };
const KEY = 'ic-admin-tokens';

export const tokens = {
  load(): Tokens | null {
    try {
      return JSON.parse(sessionStorage.getItem(KEY) ?? 'null');
    } catch {
      return null;
    }
  },
  save(t: Tokens) {
    sessionStorage.setItem(KEY, JSON.stringify(t));
  },
  clear() {
    sessionStorage.removeItem(KEY);
  },
};

let language = 'en';
let onExpired: () => void = () => undefined;
export function configure(options: { language?: string; onExpired?: () => void }) {
  if (options.language) {
    language = options.language;
  }
  if (options.onExpired) {
    onExpired = options.onExpired;
  }
}

async function send(method: string, path: string, body: unknown, access?: string): Promise<Response> {
  const headers: Record<string, string> = { Accept: 'application/json', 'Accept-Language': language };
  const form = body instanceof FormData;
  if (body !== undefined && !form) {
    headers['Content-Type'] = 'application/json';
  }
  if (access) {
    headers.Authorization = `Bearer ${access}`;
  }
  try {
    return await fetch(`${BASE}/api/v1${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : form ? (body as FormData) : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, 'network_error', 'The server cannot be reached.');
  }
}

async function toError(response: Response): Promise<ApiError> {
  const payload = await response.json().catch(() => null);
  if (payload?.error) {
    return new ApiError(response.status, payload.error.code, payload.error.message, payload.error.detail);
  }
  if (response.status === 422 && payload?.detail) {
    const first = Array.isArray(payload.detail) ? payload.detail[0] : null;
    const where = first?.loc?.slice(1).join('.') ?? '';
    return new ApiError(422, 'validation_error', first ? `${where}: ${first.msg}` : 'Invalid input', payload.detail);
  }
  return new ApiError(response.status, 'unexpected_error', `HTTP ${response.status}`);
}

let refreshing: Promise<Tokens | null> | null = null;
function refresh(current: Tokens): Promise<Tokens | null> {
  refreshing ??= (async () => {
    try {
      const r = await send('POST', '/auth/refresh', { refresh_token: current.refresh });
      if (!r.ok) {
        return null;
      }
      const body = await r.json();
      const next = { access: body.access_token, refresh: body.refresh_token };
      tokens.save(next);
      return next;
    } finally {
      refreshing = null;
    }
  })();
  return refreshing;
}

async function call(method: string, path: string, body?: unknown): Promise<Response> {
  const current = tokens.load();
  let response = await send(method, path, body, current?.access);
  if (response.status === 401 && current) {
    const next = await refresh(current);
    if (!next) {
      tokens.clear();
      onExpired();
      throw await toError(response);
    }
    response = await send(method, path, body, next.access);
  }
  if (!response.ok) {
    throw await toError(response);
  }
  return response;
}

export async function api<T = any>(method: string, path: string, body?: unknown): Promise<T> {
  const response = await call(method, path, body);
  return (response.status === 204 ? undefined : await response.json()) as T;
}

/** A protected file (ID document, credential, cut-out) as an object URL for <img> or a new tab. */
export async function fileUrl(path: string): Promise<string> {
  const response = await call('GET', path);
  return URL.createObjectURL(await response.blob());
}

export async function login(email: string, password: string) {
  const r = await send('POST', '/auth/login', { email, password });
  if (!r.ok) {
    throw await toError(r);
  }
  const body = await r.json();
  tokens.save({ access: body.access_token, refresh: body.refresh_token });
}

export async function logout() {
  const current = tokens.load();
  tokens.clear();
  if (current) {
    await send('POST', '/auth/logout', { refresh_token: current.refresh }).catch(() => undefined);
  }
}

export const money = (minor: number, currency = 'AED') => `${currency} ${(minor / 100).toFixed(2)}`;
export const day = (iso: string | null | undefined) => (iso ? iso.slice(0, 16).replace('T', ' ') : '');
