/**
 * Whole-app tests for the screens added for photo analysis, commerce and the
 * marketplace: real App, navigation and API client, fake network.
 */
import React from 'react';
import { Linking } from 'react-native';
import { render, screen, userEvent } from '@testing-library/react-native';

import App from '../App';
import { createApiClient, toBase64 } from '../src/api/client';
import i18n from '../src/localization';
import { tokenStore } from '../src/storage/secureStore';
import { createFakeServer, PHASE1, PHASE2 } from '../testing/fakeServer';

const keychain = jest.requireMock('react-native-keychain');
const picker = jest.requireMock('react-native-image-picker') as { launchImageLibrary: jest.Mock };

function start(features: string[]) {
  const server = createFakeServer();
  server.state.features = features;
  const api = createApiClient({ baseUrl: 'http://test', tokenStore, getLanguage: () => i18n.language as 'en' | 'ar', fetchImpl: server.fetchImpl });
  return { server, api, user: userEvent.setup() };
}

async function signIn(user: ReturnType<typeof userEvent.setup>) {
  await user.type(await screen.findByTestId('email'), 'layla@example.com');
  await user.type(screen.getByTestId('password'), 'correct-horse-battery');
  await user.press(screen.getByTestId('submit'));
  await screen.findByTestId('home');
}

const FACE_PHOTO = { id: 'p1', kind: 'face', width: 900, height: 900, size_bytes: 1, created_at: '2026-11-12T00:00:00Z' };
const ANALYSIS = {
  id: 'a1', kind: 'seasonal_color', basis: 'photo_analysis', indicative: true, created_at: '2026-11-12T00:00:00Z',
  confidence: 0.62, low_confidence: false, notes: [], swatches: { skin: '#bb7550', hair: '#281d1b', eyes: '#221515' },
  scores: [{ key: 'autumn', title: 'Autumn', score: 0.62 }, { key: 'spring', title: 'Spring', score: 0.2 }],
  profile: { key: 'autumn', title: 'Autumn', summary: 'Warm, deep and soft.', palette: ['#8e3b2c'], advice: { outfits: ['Rust and olive.'] } },
};

beforeEach(async () => {
  keychain.__reset();
  await i18n.changeLanguage('en');
  jest.spyOn(Linking, 'openURL').mockResolvedValue(undefined);
});

test('photo analysis: run on a photo, see an indicative result, or the reasons it could not be used', async () => {
  const { api, server, user } = start([...PHASE1, 'phase1.seasonal_color']);
  let reject = true;
  server.state.routes = {
    'GET /assessment-images': () => [200, [FACE_PHOTO]],
    'GET /analysis/seasonal_color': () => [200, null],
    'POST /analysis/seasonal_color': body => {
      expect(body).toEqual({ image_id: 'p1' });
      return reject
        ? [422, { error: { code: 'photo_not_analysable', message: 'x', detail: { reasons: ['not_a_colour_photo'] } } }]
        : [201, ANALYSIS];
    },
  };
  await render(<App api={api} />);
  await signIn(user);
  await user.press(screen.getByTestId('entry-photoAssessment'));
  await user.press(await screen.findByTestId('analyse-seasonal_color-p1'));
  await user.press(await screen.findByTestId('analyse-p1'));
  expect(await screen.findByText('Use a colour photo without filters.')).toBeOnTheScreen();

  reject = false;
  await user.press(screen.getByTestId('analyse-p1'));
  expect(await screen.findByTestId('analysis-result')).toHaveTextContent('Autumn');
  expect(screen.getByTestId('indicative')).toHaveTextContent('Indicative result from photo analysis');
  expect(screen.getByText('62%')).toBeOnTheScreen();
  expect(screen.getByTestId('swatch-#bb7550')).toBeOnTheScreen();
});

test('previews come back as an image', async () => {
  const { api, server, user } = start([...PHASE1, 'phase1.hair_preview']);
  const jpeg = new Uint8Array([0xff, 0xd8, 0xff, 0xe0]);
  let sent: any = null;
  server.state.routes = {
    'GET /assessment-images': () => [200, [FACE_PHOTO]],
    'GET /analysis/seasonal_color': () => [200, null],
    'POST /previews/hair-colour': body => {
      sent = body;
      return [200, jpeg];
    },
  };
  await render(<App api={api} />);
  await signIn(user);
  await user.press(screen.getByTestId('entry-hairColour'));
  await user.press(await screen.findByTestId('colour-#8b2e1a'));
  await user.press(screen.getByTestId('show-preview'));
  const image = await screen.findByTestId('preview-image');
  expect(image.props.source.uri).toBe(`data:image/jpeg;base64,${toBase64(jpeg)}`);
  expect(sent).toEqual({ image_id: 'p1', colour: '#8b2e1a' });
});

test('base64 matches the standard encoding', () => {
  const bytes = new Uint8Array([...'Many hands make light work.'].map(c => c.charCodeAt(0)));
  expect(toBase64(bytes)).toBe(Buffer.from(bytes).toString('base64'));
  expect(toBase64(new Uint8Array([1, 2]))).toBe('AQI=');
});

test('library: add a free palette, buy a guide through the test gateway, open the PDF', async () => {
  const { api, server, user } = start([...PHASE1, 'phase1.free_resources', 'phase1.free_paid_access']);
  const owned = new Set<string>();
  const product = (key: string, free: boolean) => ({
    key, kind: 'guide', title: key, description: 'd', price_minor: free ? 0 : 2900, currency: 'AED', is_free: free,
    requires_shipping: false, owned: owned.has(key),
  });
  server.state.routes = {
    'GET /shop/products?kind=guide': () => [200, [product('guide.palette.spring', true), product('guide.body.pear', false)]],
    'POST /library/guide.palette.spring/claim': () => { owned.add('guide.palette.spring'); return [201, { key: 'x', owned: true }]; },
    'POST /checkout/product': body => {
      expect(body.product_key).toBe('guide.body.pear');
      return [201, { order_id: 'o1', status: 'pending', amount_minor: 2900, currency: 'AED', provider: 'sandbox', payment_url: '/sandbox/pay/sbx_1' }];
    },
    'POST /sandbox/pay/sbx_1': () => { owned.add('guide.body.pear'); return [200, { status: 'paid' }]; },
    'GET /library/guide.body.pear/link': () => [200, { path: '/api/v1/files/token-1' }],
  };
  await render(<App api={api} />);
  await signIn(user);
  await user.press(screen.getByTestId('entry-guides'));
  await user.press(await screen.findByTestId('claim-guide.palette.spring'));
  expect(await screen.findByTestId('open-guide.palette.spring')).toBeOnTheScreen();

  await user.press(screen.getByTestId('buy-guide.body.pear'));
  expect(await screen.findByText('To pay: AED 29.00')).toBeOnTheScreen();
  await user.press(screen.getByTestId('sandbox-pay'));
  await user.press(await screen.findByTestId('open-guide.body.pear'));
  expect(Linking.openURL).toHaveBeenCalledWith('http://test/api/v1/files/token-1');
});

test('marketplace: find a stylist, book a time, pay, and see it in bookings', async () => {
  const { api, server, user } = start([...PHASE1, ...PHASE2, 'phase2.service_payments', 'phase2.consultations']);
  const service = { id: 's1', kind: 'consultation', title: '30-minute consultation', description: '', price_minor: 25000, currency: 'AED', duration_minutes: 30, mode: 'online' };
  const stylist = { id: 'st1', display_name: 'Amal', bio: 'Colour specialist', city: 'Dubai', languages: ['en'], specialities: [], rating_avg: 4.8, rating_count: 12, promoted: false, distance_km: null, services: [service] };
  const bookings: any[] = [];
  server.state.routes = {
    'GET /stylists': () => [200, [stylist]],
    'GET /stylists/st1': () => [200, { ...stylist, years_experience: 5, testimonials: [{ rating: 5, text: 'Wonderful', created_at: '' }],
      slots: [{ id: 'slot1', starts_at: '2026-11-20T10:00:00Z', ends_at: '2026-11-20T10:30:00Z' }] }],
    'POST /bookings': body => {
      expect(body).toMatchObject({ service_id: 's1', slot_id: 'slot1', use_reward: false });
      bookings.push({ id: 'b1', status: 'pending_payment', kind: 'consultation', starts_at: '2026-11-20T10:00:00Z', ends_at: '', price_minor: 25000,
        currency: 'AED', paid_with: null, stylist: { id: 'st1', display_name: 'Amal' }, service, address: null, cancelled_by: null });
      return [201, { booking: bookings[0], checkout: { order_id: 'o1', status: 'pending', amount_minor: 25000, currency: 'AED', provider: 'sandbox', payment_url: '/sandbox/pay/sbx_2' } }];
    },
    'POST /sandbox/pay/sbx_2': () => { bookings[0].status = 'confirmed'; return [200, { status: 'paid' }]; },
    'GET /bookings': () => [200, bookings],
    'GET /consultations': () => [200, []],
  };
  await render(<App api={api} />);
  await signIn(user);
  await user.press(screen.getByTestId('entry-findStylist'));
  await user.press(await screen.findByTestId('stylist-st1'));
  expect(await screen.findByText('Wonderful')).toBeOnTheScreen();
  await user.press(screen.getByTestId('service-s1'));
  await user.press(screen.getByTestId('slot-slot1'));
  await user.press(screen.getByTestId('book'));
  expect(await screen.findByText('To pay: AED 250.00')).toBeOnTheScreen();
  await user.press(screen.getByTestId('sandbox-pay'));
  expect(await screen.findByTestId('booked')).toHaveTextContent('Your booking is confirmed.');
  await user.press(screen.getByTestId('go-bookings'));
  expect(await screen.findByText(/Confirmed/)).toBeOnTheScreen();
});

test('a message with contact details is held back and the sender is told why, in Arabic', async () => {
  const { api, server, user } = start([...PHASE1, ...PHASE2]);
  const messages: any[] = [];
  server.state.routes = {
    'GET /messages': () => [200, [{ id: 't1', with: { id: 'u9', name: 'Amal' }, last_message_at: null, unread: false }]],
    'GET /messages/t1': () => [200, messages],
    'POST /messages/t1': body => {
      const message = { id: `m${messages.length}`, mine: true, body: body.body, created_at: '', status: 'not_delivered', read: false };
      messages.push(message);
      return [201, { message, warning: { code: 'contact_details_blocked', kinds: ['phone'], consequence: 'warning' } }];
    },
  };
  await render(<App api={api} />);
  await user.press(await screen.findByTestId('language-ar'));
  await signIn(user);
  await user.press(screen.getByTestId('entry-messages'));
  await user.press(await screen.findByTestId('thread-t1'));
  await user.type(await screen.findByTestId('message-input'), '050 123 4567');
  await user.press(screen.getByTestId('send-message'));
  expect(await screen.findByTestId('message-warning')).toHaveTextContent('لم تُسلَّم هذه الرسالة لأنها تحتوي على بيانات تواصل أو دفع.');
  expect(screen.getByText('لم تُسلَّم')).toBeOnTheScreen();
});

test('profile explains why an account is not eligible and lets her upload an ID', async () => {
  const { api, server, user } = start([...PHASE1, 'phase1.eligibility_verification', 'phase1.identity_verification']);
  let uploaded = false;
  server.state.routes = {
    'GET /users/me/profile': () => [200, { date_of_birth: '2012-01-01', gender: 'female', country_code: 'AE', city: null, phone: null,
      eligibility_status: 'ineligible', eligibility_reasons: ['under_minimum_age'], identity_status: uploaded ? 'pending' : 'unverified' }],
    'GET /countries': () => [200, [{ code: 'AE', name: 'United Arab Emirates', currency: 'AED' }]],
    'POST /identity/documents': () => { uploaded = true; return [201, { id: 'v1', method: 'id_document', status: 'pending', reason: null, created_at: '' }]; },
  };
  picker.launchImageLibrary.mockResolvedValueOnce({ assets: [{ uri: 'file:///front.jpg', fileName: 'front.jpg', type: 'image/jpeg' }, { uri: 'file:///back.jpg' }] });
  await render(<App api={api} />);
  await signIn(user);
  await user.press(screen.getByTestId('entry-profile'));
  expect(await screen.findByTestId('eligibility-status')).toHaveTextContent('This service is not available for your account.');
  expect(screen.getByText('You are under the minimum age.')).toBeOnTheScreen();
  await user.press(screen.getByTestId('upload-id'));
  expect(await screen.findByTestId('id-sent')).toBeOnTheScreen();
  expect(screen.getByTestId('identity-status')).toHaveTextContent('Being reviewed');
});
