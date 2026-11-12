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
  /** What this user may do; staff permissions open the Admin tab. */
  permissions?: string[];
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


// ---------- photo analysis and previews ----------
export type AnalysisKind = 'face_shape' | 'body_shape' | 'seasonal_color';
export type PhotoAnalysis = {
  id: string;
  kind: AnalysisKind;
  image_id: string | null;
  basis: 'photo_analysis';
  indicative: true;
  created_at: string;
  confidence: number;
  low_confidence: boolean;
  notes: string[];
  scores: { key: string; title: string; score: number }[];
  swatches?: Record<string, string>;
  profile: { key: string; title: string; summary: string; palette: string[] | null; advice: Record<string, string[]> } | null;
  colour_type?: ColourTypeSummary | null;
};
export type PreviewKind = 'hair-colour' | 'outfit-colour' | 'makeup';

// ---------- profile and identity ----------
export type Gender = 'female' | 'male';
export type Profile = {
  date_of_birth: string | null;
  gender: Gender | null;
  country_code: string | null;
  city: string | null;
  phone: string | null;
  eligibility_status: 'incomplete' | 'eligible' | 'ineligible' | 'pending_review';
  eligibility_reasons: string[];
  identity_status: 'unverified' | 'pending' | 'verified' | 'rejected';
};
export type Country = { code: string; name: string; currency: string };
export type Verification = { id: string; method: string; status: string; reason: string | null; created_at: string };

// ---------- commerce ----------
export type Product = {
  key: string; kind: string; title: string; description: string; price_minor: number; currency: string;
  is_free: boolean; requires_shipping: boolean; owned: boolean | null;
};
export type Plan = { key: string; audience: string; title: string; description: string; price_minor: number; currency: string; interval: 'month' | 'year' };
export type Checkout = { order_id: string; status: string; amount_minor: number; currency: string; provider: string | null; payment_url: string | null };
export type Subscription = { id: string; status: string; plan: Plan; current_period_end: string | null; cancel_at_period_end: boolean };
export type RetailItem = { id: string; retailer: string; title: string; image_url: string | null; price_text: string | null; match: number };
export type Rewards = { balance: number; how_to_earn: { event: string; points: number; description: string }[]; history: { delta: number; event: string; created_at: string }[] };
export type RedemptionOption = { key: string; title: string; points_cost: number };

// ---------- marketplace ----------
export type StylistService = { id: string; kind: string; title: string; description: string; price_minor: number; currency: string; duration_minutes: number; mode: 'online' | 'in_person' };
export type StylistSummary = {
  id: string; display_name: string; bio: string; city: string | null; languages: string[]; specialities: string[];
  rating_avg: number; rating_count: number; promoted: boolean; distance_km: number | null; services: StylistService[];
};
export type StylistDetail = StylistSummary & {
  years_experience: number | null;
  testimonials: { rating: number; text: string; created_at: string }[];
  slots: { id: string; starts_at: string; ends_at: string }[];
};
export type Booking = {
  id: string; status: string; kind: string; starts_at: string; ends_at: string; price_minor: number; currency: string;
  paid_with: string | null; stylist: { id: string; display_name: string }; service: StylistService; address: Record<string, string> | null;
  cancelled_by: string | null;
};
export type ReportSection = { key: string; title: string; type: string; value: any };
export type Consultation = {
  id: string; booking_id: string; kind: string; status: string; intake: Record<string, string>; role: 'customer' | 'stylist';
  stylist: { id: string; display_name: string };
  files: { id: string; purpose: string; caption: string | null; verdict: { verdict: string; note: string | null } | null }[];
  report: { title: string; status: string; sections: ReportSection[] } | null;
  required_intake: string[]; allowed_purposes: string[];
};
export type Thread = { id: string; with: { id: string; name: string }; last_message_at: string | null; unread: boolean };
export type Message = { id: string; mine: boolean; body: string; created_at: string; status: 'delivered' | 'not_delivered'; read: boolean };
export type SendResult = { message: Message; warning: { code: string; kinds: string[]; consequence?: string } | null };
export type StylistApplication = {
  id: string; display_name: string; bio: string; city: string | null; languages: string[]; status: string; review_note: string | null;
};
export type Campaign = { id: string; advertiser: string; placement: string; title: string; body: string; image_url: string | null; has_link: boolean };
export type Voucher = { id: string; partner: string; title: string; terms: string; ends_at: string; remaining: number | null; code: string | null };

export type FilePart = PhotoFile;
export type TryOnKind = 'garment' | 'hairstyle';
export type TryOnItem = { id: string; kind: TryOnKind; title: string; category: string | null; suggested: boolean };
export type Slot = { id: string; starts_at: string; ends_at: string; booked: boolean };
export type TemplateSection = { key: string; title: string; type: 'decision' | 'text' | 'list' | 'choice' | 'palette'; options: string[]; required: boolean };
export type ReportTemplate = { key: string; title: string; sections: TemplateSection[] };
export type Indicative = { indicative: true; season: string; scores: Record<string, number>; swatches: Record<string, string>; notes: string[] };
export type Swatch = { hex: string; name: string; family?: string; tone?: 'light' | 'mid' | 'deep' };
export type ColourTypeKey =
  | 'light_spring' | 'warm_spring' | 'bright_spring' | 'light_summer' | 'cool_summer' | 'soft_summer'
  | 'soft_autumn' | 'warm_autumn' | 'deep_autumn' | 'deep_winter' | 'cool_winter' | 'bright_winter';
export type ColourTypeListItem = { key: ColourTypeKey; season: string; dominant: string; title: string; signature: string[] };
export type ColourTypeSummary = {
  key: ColourTypeKey; season: string; dominant: string; title: string; summary: string;
  axes: { warmth: number; depth: number; clarity: number };
  neutrals: Swatch[]; colours: Swatch[]; lips: Swatch[]; hair: Swatch[]; metals: string[]; avoid: Swatch[];
  avoid_type: ColourTypeKey; signature: string[];
  scores?: { key: ColourTypeKey; title: string; score: number }[];
};
export type DrapingStep =
  | { step: 'undertone' | 'depth' | 'clarity'; number: number; of: number; title: string; prompt: string;
      pair: { index: number; a: string; b: string }; labels: { a: string; b: string }; progress: { answered: number; total: number } }
  | { step: 'confirm'; number: number; of: number; title: string; prompt: string;
      options: { key: ColourTypeKey; title: string; score: number; drapes: string[] }[] };
export type DrapingSession = {
  id: string; file_id: string | null; status: 'in_progress' | 'complete'; answers: number; created_at: string;
  axes: { warmth: number; depth: number; clarity: number }; custom_palette: string[] | null; notes: string | null;
  next?: DrapingStep | null;
  result?: { colour_type: ColourTypeSummary; scores: { key: ColourTypeKey; title: string; score: number }[] };
};
export type ClientSummary = { id: string; name: string; last_seen: string; consultations: number; photos: number;
  colour_type: { key: ColourTypeKey; title: string } | null };
export type ClientDetail = {
  id: string; name: string;
  consultations: { id: string; kind: string; status: string; created_at: string; report: 'draft' | 'delivered' | null }[];
  photos: { id: string; consultation_id: string; created_at: string }[];
  analyses: { id: string; consultation_id: string; file_id: string | null; status: 'in_progress' | 'complete'; created_at: string;
    colour_type: { key: ColourTypeKey; title: string } | null; custom_palette: string[] | null; notes: string | null }[];
};
export type DrapingAnswer = { step: DrapingStep['step']; pair?: number; pick: string };
export type FeaturedCampaign = { id: string; status: string; starts_at: string; ends_at: string; impressions: number };
export type Near = { lat?: number; lng?: number };

const BASE64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';

/** Bytes to base64 without a native module (used to show generated previews). */
/* eslint-disable no-bitwise */
export function toBase64(bytes: Uint8Array): string {
  let out = '';
  for (let i = 0; i < bytes.length; i += 3) {
    const [a, b = 0, c = 0] = [bytes[i], bytes[i + 1], bytes[i + 2]];
    const n = (a << 16) | (b << 8) | c;
    out += BASE64[(n >> 18) & 63] + BASE64[(n >> 12) & 63];
    out += i + 1 < bytes.length ? BASE64[(n >> 6) & 63] : '=';
    out += i + 2 < bytes.length ? BASE64[n & 63] : '=';
  }
  return out;
}
/* eslint-enable no-bitwise */

function appendFile(form: FormData, name: string, file: FilePart) {
  if (typeof Blob !== 'undefined' && file instanceof Blob) {
    (form as any).append(name, file, `${name}.jpg`);
  } else {
    form.append(name, file as any);
  }
}

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

  /** A request whose answer is an image: returned as a data URI for <Image source={{ uri }} />. */
  async function requestImage(method: string, path: string, body: unknown): Promise<string> {
    const tokens = await tokenStore.load();
    let response = await send(method, path, body, tokens?.accessToken ?? null);
    if (response.status === 401 && tokens) {
      const renewed = await refreshTokens(tokens.refreshToken);
      if (!renewed) {
        await tokenStore.clear();
        expiryListeners.forEach(listener => listener());
        throw await toError(response);
      }
      response = await send(method, path, body, renewed.accessToken);
    }
    if (!response.ok) {
      throw await toError(response);
    }
    const bytes = new Uint8Array(await response.arrayBuffer());
    const type = response.headers?.get?.('content-type') ?? 'image/jpeg';
    return `data:${type};base64,${toBase64(bytes)}`;
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

    register: (input: {
      email: string;
      password: string;
      full_name: string;
      preferred_language: Language;
      date_of_birth?: string;
      gender?: Gender;
      country_code?: string;
    }) => startSession('/auth/register', input),

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

    /** Questionnaires in this release, with the user's latest result if any. */
    assessments: () => request<{ key: string; title: string; completed_at: string | null; result: string | null }[]>('GET', '/assessments'),

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


    /** Absolute URL for a path the API returned (payment pages, download links). */
    absolute: (path: string) => (path.startsWith('http') ? path : `${baseUrl}${path.startsWith('/api/') ? '' : '/api/v1'}${path}`),

    // ---------- photo analysis and previews ----------
    photoFile: (id: string) => requestImage('GET', `/assessment-images/${id}/file`, undefined),
    analysePhoto: (kind: AnalysisKind, imageId: string) =>
      request<PhotoAnalysis>('POST', `/analysis/${kind}`, { body: { image_id: imageId } }),
    latestAnalysis: (kind: AnalysisKind) => request<PhotoAnalysis | null>('GET', `/analysis/${kind}`),
    preview: (kind: PreviewKind, body: Record<string, unknown>) => requestImage('POST', `/previews/${kind}`, body),

    // ---------- profile, markets, identity ----------
    profile: () => request<Profile>('GET', '/users/me/profile'),
    updateProfile: (changes: Partial<Pick<Profile, 'date_of_birth' | 'gender' | 'country_code' | 'city' | 'phone'>>) =>
      request<Profile>('PUT', '/users/me/profile', { body: changes }),
    countries: () => request<Country[]>('GET', '/countries', { auth: false }),
    uaePassStart: () => request<{ provider: string; authorize_url: string }>('GET', '/identity/uae-pass/start'),
    uaePassComplete: (code: string) => request<Verification>('POST', '/identity/uae-pass/complete', { body: { code } }),
    uploadIdDocument(front: FilePart, back?: FilePart) {
      const form = new FormData();
      appendFile(form, 'front', front);
      if (back) {
        appendFile(form, 'back', back);
      }
      return request<Verification>('POST', '/identity/documents', { body: form });
    },
    verifications: () => request<Verification[]>('GET', '/identity/verifications'),

    // ---------- shop, library, plans ----------
    products: (kind?: string) => request<Product[]>('GET', `/shop/products${kind ? `?kind=${kind}` : ''}`),
    plans: (audience = 'customer') => request<Plan[]>('GET', `/shop/plans?audience=${audience}`),
    buyProduct: (productKey: string, quantity = 1, shipping?: Record<string, string>) =>
      request<Checkout>('POST', '/checkout/product', { body: { product_key: productKey, quantity, shipping } }),
    buyPlan: (planKey: string) => request<Checkout>('POST', '/checkout/plan', { body: { plan_key: planKey } }),
    /** Development only: completes a sandbox payment the way the gateway's webhook would. */
    sandboxPay: (paymentUrl: string) => request<{ status: string }>('POST', paymentUrl),
    library: () => request<Product[]>('GET', '/library'),
    claimFree: (productKey: string) => request<{ key: string; owned: boolean }>('POST', `/library/${productKey}/claim`),
    downloadLink: (productKey: string) => request<{ path: string }>('GET', `/library/${productKey}/link`),
    subscriptions: () => request<Subscription[]>('GET', '/me/subscriptions'),
    cancelSubscription: (id: string) => request<Subscription>('POST', `/me/subscriptions/${id}/cancel`),
    entitlements: () => request<{ key: string; quantity: number; expires_at: string | null }[]>('GET', '/me/entitlements'),
    retail: (category = 'outfits') => request<{ based_on: Record<string, string>; items: RetailItem[] }>('GET', `/shop/retail?category=${category}`),
    retailClick: (id: string) => request<{ url: string }>('POST', `/shop/retail/${id}/click`),

    // ---------- rewards ----------
    rewards: () => request<Rewards>('GET', '/rewards'),
    dailyVisit: () => request<{ awarded: number; balance: number }>('POST', '/rewards/daily-visit'),
    redemptionOptions: () => request<RedemptionOption[]>('GET', '/rewards/redeem'),
    redeem: (key: string) => request<{ redeemed: string; balance: number }>('POST', `/rewards/redeem/${key}`),

    // ---------- marketplace ----------
    stylists: (filters: { kind?: string; city?: string; language?: string; lat?: number; lng?: number; radius_km?: number } = {}) => {
      const query = Object.entries(filters).filter(([, v]) => v !== undefined && v !== '').map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`).join('&');
      return request<StylistSummary[]>('GET', `/stylists${query ? `?${query}` : ''}`);
    },
    stylist: (id: string) => request<StylistDetail>('GET', `/stylists/${id}`),
    book: (input: { service_id: string; slot_id: string; use_reward?: boolean; address?: { line1: string; city: string; notes?: string } }) =>
      request<{ booking: Booking; checkout: Checkout | null }>('POST', '/bookings', { body: input }),
    bookings: () => request<Booking[]>('GET', '/bookings'),
    cancelBooking: (id: string) => request<Booking>('POST', `/bookings/${id}/cancel`),
    testimonial: (bookingId: string, rating: number, text: string) =>
      request<{ id: string }>('POST', `/bookings/${bookingId}/testimonial`, { body: { rating, text } }),
    consultations: () => request<Consultation[]>('GET', '/consultations'),
    consultation: (id: string) => request<Consultation>('GET', `/consultations/${id}`),
    saveIntake: (id: string, intake: Record<string, string>) => request<Consultation>('PUT', `/consultations/${id}/intake`, { body: { intake } }),
    sharePhoto: (id: string, imageId: string) =>
      request<{ id: string }>('POST', `/consultations/${id}/share-photo`, { body: { image_id: imageId, consent: true } }),
    addConsultationPhoto(id: string, file: FilePart, purpose: string, caption?: string) {
      const form = new FormData();
      appendFile(form, 'file', file);
      form.append('purpose', purpose);
      form.append('consent', 'true');
      if (caption) {
        form.append('caption', caption);
      }
      return request<{ id: string }>('POST', `/consultations/${id}/files`, { body: form });
    },
    reportLink: (id: string) => request<{ path: string }>('GET', `/consultations/${id}/report-link`),
    threads: () => request<Thread[]>('GET', '/messages'),
    openThread: (stylistId: string) => request<Thread>('POST', '/messages', { body: { stylist_id: stylistId } }),
    messages: (threadId: string) => request<Message[]>('GET', `/messages/${threadId}`),
    sendMessage: (threadId: string, body: string) => request<SendResult>('POST', `/messages/${threadId}`, { body: { body } }),

    // ---------- stylist side ----------
    myApplication: () => request<StylistApplication | null>('GET', '/stylist/application'),
    saveApplication: (fields: Partial<StylistApplication>) => request<StylistApplication>('PUT', '/stylist/application', { body: fields }),
    addCredential(kind: string, title: string, file: FilePart) {
      const form = new FormData();
      appendFile(form, 'file', file);
      form.append('kind', kind);
      form.append('title', title);
      return request<{ id: string }>('POST', '/stylist/application/credentials', { body: form });
    },
    credentials: () => request<{ id: string; kind: string; title: string; status: string }[]>('GET', '/stylist/application/credentials'),
    submitApplication: () => request<StylistApplication>('POST', '/stylist/application/submit'),
    practiceBookings: () => request<Booking[]>('GET', '/stylist/bookings'),
    completeBooking: (id: string) => request<Booking>('POST', `/stylist/bookings/${id}/complete`),

    // ---------- try-on (rows 11, 12) ----------
    tryOnItems: (kind: TryOnKind) => request<TryOnItem[]>('GET', `/tryon/items?kind=${kind}`),
    tryOnImage: (id: string) => requestImage('GET', `/tryon/items/${id}/image`, undefined),
    tryOn: (kind: TryOnKind, imageId: string, itemId: string, colour?: string) =>
      requestImage('POST', `/previews/${kind}`, { image_id: imageId, item_id: itemId, colour }),

    // ---------- stylist practice ----------
    myServices: () => request<(StylistService & { is_active: boolean })[]>('GET', '/stylist/services'),
    addService: (input: Omit<StylistService, 'id' | 'currency'> & { is_active?: boolean }) =>
      request<StylistService>('POST', '/stylist/services', { body: input }),
    updateService: (id: string, input: Omit<StylistService, 'id' | 'currency'> & { is_active: boolean }) =>
      request<StylistService>('PUT', `/stylist/services/${id}`, { body: input }),
    mySlots: () => request<Slot[]>('GET', '/stylist/slots'),
    addSlots: (starts: string[], minutes: number) => request<Slot[]>('POST', '/stylist/slots', { body: { starts, minutes } }),
    deleteSlot: (id: string) => request<void>('DELETE', `/stylist/slots/${id}`),
    reportTemplate: (consultationId: string) => request<ReportTemplate>('GET', `/consultations/${consultationId}/report/template`),
    saveReport: (consultationId: string, content: Record<string, unknown>) =>
      request<{ status: string }>('PUT', `/consultations/${consultationId}/report`, { body: { content } }),
    deliverReport: (consultationId: string) => request<{ status: string }>('POST', `/consultations/${consultationId}/report/deliver`),
    setVerdict: (consultationId: string, fileId: string, verdict: string, note?: string) =>
      request<unknown>('PUT', `/consultations/${consultationId}/files/${fileId}/verdict`, { body: { verdict, note } }),
    consultationFile: (consultationId: string, fileId: string) => requestImage('GET', `/consultations/${consultationId}/files/${fileId}`, undefined),
    clients: () => request<ClientSummary[]>('GET', '/stylist/clients'),
    clientDetail: (id: string) => request<ClientDetail>('GET', `/stylist/clients/${id}`),
    colourTypes: () => request<ColourTypeListItem[]>('GET', '/colour-types'),
    colourType: (key: string) => request<ColourTypeSummary>('GET', `/colour-types/${key}`),
    drapePair: (consultationId: string, fileId: string, a: string, b: string) =>
      requestImage('GET', `/workspace/${consultationId}/drape-pair?file_id=${fileId}&a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`, undefined),
    lipStudio: (consultationId: string, fileId: string, colours: string[]) =>
      requestImage('POST', `/workspace/${consultationId}/lips`, { file_id: fileId, colours }),
    startDraping: (consultationId: string, fileId: string) =>
      request<DrapingSession>('POST', `/workspace/${consultationId}/draping`, { body: { file_id: fileId } }),
    drapingSessions: (consultationId: string) => request<DrapingSession[]>('GET', `/workspace/${consultationId}/draping`),
    drapingSession: (consultationId: string, sessionId: string) =>
      request<DrapingSession>('GET', `/workspace/${consultationId}/draping/${sessionId}`),
    answerDraping: (consultationId: string, sessionId: string, answer: DrapingAnswer) =>
      request<DrapingSession>('POST', `/workspace/${consultationId}/draping/${sessionId}/answer`, { body: answer }),
    undoDraping: (consultationId: string, sessionId: string) =>
      request<DrapingSession>('POST', `/workspace/${consultationId}/draping/${sessionId}/undo`),
    editDraping: (consultationId: string, sessionId: string, body: { custom_palette?: string[]; notes?: string }) =>
      request<DrapingSession>('PATCH', `/workspace/${consultationId}/draping/${sessionId}`, { body }),
    openWorkspace: (consultationId: string) => request<{ open: boolean; credits_used: number }>('POST', `/workspace/${consultationId}/open`),
    drape: (consultationId: string, fileId: string, colour: string) =>
      requestImage('GET', `/workspace/${consultationId}/drape?file_id=${fileId}&colour=${encodeURIComponent(colour)}`, undefined),
    compareDrapes: (consultationId: string, fileId: string, colours: string[]) =>
      requestImage('POST', `/workspace/${consultationId}/compare`, { file_id: fileId, colours }),
    indicativeColour: (consultationId: string, fileId: string) =>
      request<Indicative>('POST', `/workspace/${consultationId}/indicative?file_id=${fileId}`),
    buyFeatured: (startsAt: string, days: number) =>
      request<{ campaign_id: string; checkout: Checkout }>('POST', '/stylist/promotions', { body: { starts_at: startsAt, days } }),
    myFeatured: () => request<FeaturedCampaign[]>('GET', '/stylist/promotions'),

    // ---------- promotions ----------
    promotions: (placement = 'home_banner', near: Near = {}) =>
      request<Campaign[]>('GET', `/promotions?placement=${placement}${near.lat !== undefined ? `&lat=${near.lat}&lng=${near.lng}` : ''}`),
    promotionClick: (id: string) => request<{ url: string }>('POST', `/promotions/${id}/click`),
    vouchers: (near: Near = {}) => request<Voucher[]>('GET', `/vouchers${near.lat !== undefined ? `?lat=${near.lat}&lng=${near.lng}` : ''}`),
    myVouchers: () => request<Voucher[]>('GET', '/vouchers/mine'),
    claimVoucher: (id: string) => request<Voucher>('POST', `/vouchers/${id}/claim`),

    // ---------- staff (Admin tab) ----------
    /** Any API call, for the admin screens that read and write admin endpoints. */
    call: <T = any>(method: string, path: string, body?: unknown) => request<T>(method, path, { body }),
    /** A protected image (ID document, credential, try-on cut-out) as a data URI. */
    image: (path: string) => requestImage('GET', path, undefined),
    uploadTryOn(file: FilePart, fields: Record<string, string>) {
      const form = new FormData();
      appendFile(form, 'file', file);
      Object.entries(fields).forEach(([k, v]) => form.append(k, v));
      return request<any>('POST', '/admin/tryon-items', { body: form });
    },

    /** Enabled phases and features for the active release. Drives navigation. */
    enabledFeatures: () => request<EnabledFeatures>('GET', '/config/features'),
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;
