/**
 * Whole-app tests: the real App, navigation, context, API client and secure
 * storage wrapper, with only the network and the device keychain replaced.
 */
import React from 'react';
import { AppState, StyleSheet } from 'react-native';
import { act, render, screen, userEvent, waitFor } from '@testing-library/react-native';

import App from '../App';
import { createApiClient } from '../src/api/client';
import i18n from '../src/localization';
import { saveChosenLanguage, tokenStore } from '../src/storage/secureStore';
import { createFakeServer, PHASE1, PHASE2 } from '../testing/fakeServer';

const keychain = jest.requireMock('react-native-keychain');
const picker = jest.requireMock('react-native-image-picker') as { launchImageLibrary: jest.Mock; launchCamera: jest.Mock };

// Capture the app's foreground/background listener so tests can bring the app "back to the foreground".
const appStateListeners: ((state: string) => void)[] = [];
jest.spyOn(AppState, 'addEventListener').mockImplementation((_event, listener) => {
  appStateListeners.push(listener as (state: string) => void);
  return { remove: jest.fn() } as any;
});

function start() {
  const server = createFakeServer();
  const api = createApiClient({
    baseUrl: 'http://test',
    tokenStore,
    getLanguage: () => i18n.language as 'en' | 'ar',
    fetchImpl: server.fetchImpl,
  });
  return { server, api, user: userEvent.setup() };
}

async function signIn(user: ReturnType<typeof userEvent.setup>, password = 'correct-horse-battery') {
  await user.type(await screen.findByTestId('email'), 'layla@example.com');
  await user.type(screen.getByTestId('password'), password);
  await user.press(screen.getByTestId('submit'));
}

const styleOf = (element: any) => StyleSheet.flatten(element.props.style);

beforeEach(async () => {
  keychain.__reset();
  await i18n.changeLanguage('en');
});

test('sign in shows only the services enabled in the active release', async () => {
  const { api, user } = start();
  await render(<App api={api} />);
  await signIn(user);

  expect(await screen.findByText('Hello, Layla')).toBeOnTheScreen();
  expect(await screen.findByText('Face shape')).toBeOnTheScreen();
  expect(screen.getByText('Discover your style')).toBeOnTheScreen();
  // Phase 2 and 3 are off: neither their entries nor their group headings exist.
  expect(screen.queryByText('Find a stylist')).toBeNull();
  expect(screen.queryByText('Work with a stylist')).toBeNull();
  expect(screen.queryByText('Shop and offers')).toBeNull();
  // Every service in the release now has a screen and can be opened.
  expect(screen.getByTestId('entry-styleAssessment')).toBeEnabled();
  expect(screen.getByTestId('entry-guides')).toBeEnabled();
});

test('a phase released on the server appears when the app returns to the foreground', async () => {
  const { api, server, user } = start();
  await render(<App api={api} />);
  await signIn(user);
  await screen.findByText('Face shape');

  server.state.features = [...PHASE1, ...PHASE2];
  const onChange = appStateListeners.at(-1)!;
  await act(async () => onChange('active'));

  expect(await screen.findByText('Find a stylist')).toBeOnTheScreen();
  expect(screen.getByText('Work with a stylist')).toBeOnTheScreen();

  // ...and disappears again when the phase is switched off.
  server.state.features = [...PHASE1];
  await act(async () => onChange('active'));
  await waitFor(() => expect(screen.queryByText('Find a stylist')).toBeNull());
});

test('switching to Arabic changes text and direction immediately, and back', async () => {
  const { api, server, user } = start();
  await render(<App api={api} />);

  const title = () => screen.getByRole('header');
  expect(await screen.findByText('Welcome back')).toBeOnTheScreen();
  expect(styleOf(title())).toMatchObject({ textAlign: 'left', writingDirection: 'ltr' });
  expect(styleOf(screen.getByTestId('email'))).toMatchObject({ textAlign: 'left' });

  await user.press(screen.getByTestId('language-ar'));
  expect(await screen.findByText('مرحباً بعودتك')).toBeOnTheScreen();
  expect(styleOf(title())).toMatchObject({ textAlign: 'right', writingDirection: 'rtl' });
  expect(styleOf(screen.getByTestId('email'))).toMatchObject({ textAlign: 'right', writingDirection: 'rtl' });
  expect(screen.getByLabelText('تسجيل الدخول')).toBeOnTheScreen();

  // Signing in while in Arabic: requests are sent in Arabic, the profile is
  // updated to Arabic, and the home screen is Arabic and right-to-left.
  await signIn(user);
  expect(await screen.findByText('مرحباً، Layla')).toBeOnTheScreen();
  expect(await screen.findByText('شكل الوجه')).toBeOnTheScreen();
  expect(server.state.account('layla@example.com').preferred_language).toBe('ar');
  expect(server.state.requests.find(r => r.path === '/auth/login')?.language).toBe('ar');

  await user.press(screen.getByTestId('open-settings'));
  await user.press(await screen.findByTestId('language-en'));
  expect(await screen.findByText('Settings')).toBeOnTheScreen();
  await waitFor(() => expect(server.state.account('layla@example.com').preferred_language).toBe('en'));
});

test('rows run right-to-left in Arabic', async () => {
  const { api, user } = start();
  await saveChosenLanguage('ar');
  await render(<App api={api} />);
  await signIn(user);
  const card = await screen.findByTestId('entry-faceShape');
  const row = card.children[0] as any;
  expect(styleOf(row)).toMatchObject({ flexDirection: 'row-reverse' });

  await user.press(screen.getByTestId('open-settings'));
  await user.press(await screen.findByTestId('language-en'));
  await user.press(screen.getByTestId('back'));
  const englishRow = (await screen.findByTestId('entry-faceShape')).children[0] as any;
  expect(styleOf(englishRow)).toMatchObject({ flexDirection: 'row' });
});

test('with no language picked on the device, the profile language is used', async () => {
  const { api, server, user } = start();
  server.state.account('layla@example.com').preferred_language = 'ar';
  await render(<App api={api} />);
  expect(await screen.findByText('Welcome back')).toBeOnTheScreen();
  await signIn(user);
  expect(await screen.findByText('مرحباً، Layla')).toBeOnTheScreen();
});

test('wrong password shows the server message; fields are validated before sending', async () => {
  const { api, server, user } = start();
  await render(<App api={api} />);
  await user.press(await screen.findByTestId('submit'));
  expect(screen.getByText('Enter your email address.')).toBeOnTheScreen();
  expect(screen.getByText('Enter your password.')).toBeOnTheScreen();
  expect(server.state.requests.filter(r => r.path === '/auth/login')).toHaveLength(0);

  await signIn(user, 'wrong-password');
  expect(await screen.findByText('The email or password is incorrect.')).toBeOnTheScreen();
  expect(screen.queryByTestId('home')).toBeNull();
});

test('register creates the account in the selected language and signs in', async () => {
  const { api, server, user } = start();
  await render(<App api={api} />);
  await user.press(await screen.findByTestId('language-ar'));
  await user.press(screen.getByTestId('go-register'));

  await user.type(await screen.findByTestId('full-name'), 'Noor');
  await user.type(screen.getByTestId('email'), 'noor@example.com');
  await user.type(screen.getByTestId('password'), 'short');
  await user.press(screen.getByTestId('submit'));
  expect(screen.getByText('استخدمي 10 أحرف على الأقل.')).toBeOnTheScreen();

  // Date of birth and gender are needed for eligibility (Feature List row 2).
  expect(screen.getByText('أدخلي تاريخ ميلادك بالصيغة YYYY-MM-DD.')).toBeOnTheScreen();

  await user.clear(screen.getByTestId('password'));
  await user.type(screen.getByTestId('password'), 'long-enough-password');
  await user.type(screen.getByTestId('dob'), '1995-04-30');
  await user.press(screen.getByTestId('gender-female'));
  await user.press(screen.getByTestId('submit'));
  expect(await screen.findByText('مرحباً، Noor')).toBeOnTheScreen();
  const account = server.state.account('noor@example.com') as any;
  expect(account.preferred_language).toBe('ar');
  expect([account.date_of_birth, account.gender, account.country_code]).toEqual(['1995-04-30', 'female', 'AE']);
});

test('the session survives an app restart, and sign out ends it', async () => {
  const { api, server, user } = start();
  const first = await render(<App api={api} />);
  await signIn(user);
  await screen.findByText('Hello, Layla');
  await first.unmount();

  server.state.expireAccessTokens(); // the stored access token is stale by the next launch
  await render(<App api={api} />);
  expect(await screen.findByText('Hello, Layla')).toBeOnTheScreen();

  await user.press(screen.getByTestId('open-settings'));
  await user.press(await screen.findByTestId('sign-out'));
  expect(await screen.findByText('Welcome back')).toBeOnTheScreen();
  expect(await tokenStore.load()).toBeNull();
});

test('a revoked session returns the user to sign-in with an explanation', async () => {
  const { api, server, user } = start();
  await render(<App api={api} />);
  await signIn(user);
  await screen.findByText('Hello, Layla');

  server.state.revokeEverything();
  await act(async () => appStateListeners.at(-1)!('active'));

  expect(await screen.findByText('Your session has ended. Please sign in again.')).toBeOnTheScreen();
  expect(screen.getByText('Welcome back')).toBeOnTheScreen();
  expect(await tokenStore.load()).toBeNull();
});

test('offline at launch offers a retry instead of signing the user out', async () => {
  const { api, server, user } = start();
  const first = await render(<App api={api} />);
  await signIn(user);
  await screen.findByText('Hello, Layla');
  await first.unmount();

  server.state.offline = true;
  await render(<App api={api} />);
  expect(await screen.findByTestId('unreachable')).toBeOnTheScreen();
  expect(await tokenStore.load()).not.toBeNull();

  server.state.offline = false;
  await user.press(screen.getByTestId('retry-start'));
  expect(await screen.findByText('Hello, Layla')).toBeOnTheScreen();
});

describe('assessments', () => {
  test('answer every question, see the result, and find it again later', async () => {
    const { api, user } = start();
    await render(<App api={api} />);
    await signIn(user);
    await user.press(await screen.findByTestId('entry-styleAssessment'));

    expect(await screen.findByText('Two questions.')).toBeOnTheScreen();
    await user.press(screen.getByTestId('start'));
    expect(screen.getByTestId('progress')).toHaveTextContent('Question 1 of 2');
    // No way forward until the question is answered.
    expect(screen.queryByTestId('next')).toBeNull();
    await user.press(screen.getByTestId('option-curved'));
    expect(screen.getByTestId('option-curved')).toBeSelected();
    await user.press(screen.getByTestId('next'));

    expect(screen.getByTestId('progress')).toHaveTextContent('Question 2 of 2');
    await user.press(screen.getByTestId('previous'));
    expect(screen.getByTestId('option-curved')).toBeSelected(); // earlier answers are kept
    await user.press(screen.getByTestId('next'));
    await user.press(screen.getByTestId('option-floral'));
    await user.press(screen.getByText('See my result'));

    expect(await screen.findByTestId('result-title')).toHaveTextContent('Romantic');
    expect(screen.getByText('Choose dresses that define the waist.')).toBeOnTheScreen();
    expect(screen.getByText('Based on your own answers. This is not an expert assessment.')).toBeOnTheScreen();
    expect(screen.getByText('Florals')).toBeOnTheScreen();

    // Leave and come back: the saved result is shown, not the questions.
    await user.press(screen.getByTestId('back'));
    await user.press(await screen.findByTestId('entry-styleAssessment'));
    expect(await screen.findByTestId('result-title')).toHaveTextContent('Romantic');

    await user.press(screen.getByTestId('retake'));
    await user.press(await screen.findByTestId('start'));
    await user.press(screen.getByTestId('option-straight'));
    await user.press(screen.getByTestId('next'));
    await user.press(screen.getByTestId('option-subtle'));
    await user.press(screen.getByTestId('next'));
    expect(await screen.findByTestId('result-title')).toHaveTextContent('Classic');
  });

  test('questions and results follow the language, right-to-left in Arabic', async () => {
    const { api, user } = start();
    await saveChosenLanguage('ar');
    await render(<App api={api} />);
    await signIn(user);
    await user.press(await screen.findByTestId('entry-styleAssessment'));
    await user.press(await screen.findByText('ابدئي'));
    expect(screen.getByTestId('progress')).toHaveTextContent('السؤال 1 من 2');
    expect(styleOf(screen.getByText('أي الخطوط تفضّلين؟'))).toMatchObject({ textAlign: 'right', writingDirection: 'rtl' });
    await user.press(screen.getByTestId('option-curved'));
    await user.press(screen.getByTestId('next'));
    await user.press(screen.getByTestId('option-floral'));
    await user.press(screen.getByTestId('next'));
    expect(await screen.findByTestId('result-title')).toHaveTextContent('رومانسي');
    expect(screen.getByText('اختاري الفساتين التي تحدّد الخصر.')).toBeOnTheScreen();
  });

  test('recommendations prompt for the missing assessment, then show advice', async () => {
    const { api, user } = start();
    await render(<App api={api} />);
    await signIn(user);
    await user.press(await screen.findByTestId('entry-outfits'));
    expect(await screen.findByText('Complete an assessment to get your recommendations.')).toBeOnTheScreen();

    await user.press(screen.getByTestId('take-style'));
    await user.press(await screen.findByTestId('start'));
    await user.press(screen.getByTestId('option-straight'));
    await user.press(screen.getByTestId('next'));
    await user.press(screen.getByTestId('option-subtle'));
    await user.press(screen.getByTestId('next'));
    await screen.findByTestId('result-title');
    await user.press(screen.getByTestId('back'));

    expect(await screen.findByText('Build around tailored blazers.')).toBeOnTheScreen();
    expect(screen.getByText('Personal style assessment: Classic')).toBeOnTheScreen();
    expect(screen.queryByTestId('take-style')).toBeNull();
  });
});

describe('photos', () => {
  const asset = { uri: 'file:///tmp/selfie.jpg', fileName: 'selfie.jpg', type: 'image/jpeg' };

  async function openPhotos(user: ReturnType<typeof userEvent.setup>) {
    await signIn(user);
    await user.press(await screen.findByTestId('entry-photoAssessment'));
    await screen.findByText('No photos yet.');
  }

  beforeEach(() => {
    picker.launchImageLibrary.mockReset().mockResolvedValue({ assets: [asset] });
    picker.launchCamera.mockReset().mockResolvedValue({ assets: [asset] });
  });

  test('nothing is picked or sent until the user gives consent', async () => {
    const { api, server, user } = start();
    await render(<App api={api} />);
    await openPhotos(user);

    await user.press(screen.getByTestId('choose'));
    expect(await screen.findByText('Please agree before adding a photo.')).toBeOnTheScreen();
    expect(picker.launchImageLibrary).not.toHaveBeenCalled();
    expect(server.state.uploads).toHaveLength(0);

    await user.press(screen.getByTestId('consent'));
    expect(screen.getByTestId('consent')).toBeChecked();
    await user.press(screen.getByTestId('kind-full_body'));
    await user.press(screen.getByTestId('choose'));

    expect(await screen.findByTestId('added')).toBeOnTheScreen();
    expect(server.state.uploads).toHaveLength(1);
    expect(server.state.uploads[0]).toMatchObject({ kind: 'full_body', consent: 'true' });
    expect(await screen.findByText('1200 × 1600 · 2026-11-12')).toBeOnTheScreen();
  });

  test('a rejected photo explains what to fix, in the user language', async () => {
    const { api, server, user } = start();
    server.state.rejectPhotosWith = ['too_blurry', 'no_face'];
    await render(<App api={api} />);
    await openPhotos(user);
    await user.press(screen.getByTestId('consent'));
    await user.press(screen.getByTestId('take'));

    expect(await screen.findByText('The photo is blurry. Hold the phone steady.')).toBeOnTheScreen();
    expect(screen.getByText('No face was found. Face the camera directly.')).toBeOnTheScreen();
    expect(picker.launchCamera).toHaveBeenCalledTimes(1);
    expect(screen.getByText('No photos yet.')).toBeOnTheScreen();
  });

  test('cancelling the picker uploads nothing; a photo can be deleted', async () => {
    const { api, server, user } = start();
    await render(<App api={api} />);
    await openPhotos(user);
    await user.press(screen.getByTestId('consent'));

    picker.launchImageLibrary.mockResolvedValueOnce({ didCancel: true });
    await user.press(screen.getByTestId('choose'));
    expect(server.state.uploads).toHaveLength(0);

    await user.press(screen.getByTestId('choose'));
    await user.press(await screen.findByTestId('delete-photo-1'));
    expect(await screen.findByText('No photos yet.')).toBeOnTheScreen();
  });
});
