# Mobile app (React Native 0.88, TypeScript)

Bare React Native project with native `android/` and `ios/` folders. Bundle id `com.imageconsulting`.

## What works today

- Sign up, sign in, sign out against the real API. Tokens are kept in the iOS Keychain / Android Keystore and renewed automatically.
- English and Arabic. Switching language changes all text and the layout direction at once, and is saved to the user's profile.
- The home screen is built from `GET /api/v1/config/features`. Releasing or withdrawing a phase in the admin API changes what the app shows the next time it comes to the foreground, with no new build.
- Offline at launch keeps the session and offers a retry.

The services listed on the home screen are marked "In development" and cannot be opened: the features behind them are not built yet (see `../STATUS.md`).

## Run it

Prerequisites: Node 22+, the React Native environment for your platform (Android Studio with an SDK and emulator; Xcode and CocoaPods on a Mac). Follow https://reactnative.dev/docs/set-up-your-environment.

```bash
# 1. Backend (from the repository root)
docker compose up --build              # API on http://localhost:8000

# 2. App
cd mobile
npm install
npm start                              # Metro, leave running

# Android (emulator running or device attached)
npm run android

# iOS (Mac only)
bundle install && (cd ios && bundle exec pod install)
npm run ios
```

Debug builds look for the API at `http://10.0.2.2:8000` on the Android emulator and `http://localhost:8000` on the iOS simulator. For a physical phone, set `DEV_API_URL` in `src/config.ts` to your computer's LAN address. Release builds require `PRODUCTION_API_URL` (HTTPS) in the same file and refuse to start without it.

## Checks

```bash
npm run typecheck
npm run lint
npm test                               # 24 unit and whole-app tests
../scripts/e2e.sh                      # 10 end-to-end tests against a live API and PostgreSQL
```

## How it is put together

```
src/api/client.ts        HTTP client: language header, token refresh (single-flight), error mapping
src/storage/             Keychain-backed token and language storage
src/contexts/AppContext  Session, language, enabled features
src/navigation/registry  Every customer entry point and the feature key that unlocks it
src/localization/en|ar   All text. Components contain no literal strings
src/components/ui.tsx    Direction-aware building blocks
src/screens/             Login, Register, Home, Settings
```

**Adding a screen for a feature:** build the screen, register it in `RootNavigator`, and set `screen` on its entry in `registry.ts`. The entry then becomes tappable wherever its feature is enabled.

**Direction.** Layout direction follows the language chosen in the app, not the phone's system language, and applies without restarting. To make that possible the platform's automatic mirroring is switched off (`I18nManager.allowRTL(false)` in `index.js`, `android:supportsRtl="false"` in the manifest) and every shared component reads direction from `useDirection()`. Consequence: always build rows with `<Row>` and text with `<AppText>`; a raw `flexDirection: 'row'` will not flip. System-drawn UI such as OS alerts follows the phone's language.

**Adding a language:** add `src/localization/<code>/translation.json`, register it in `src/localization/index.ts`, and add it to the API's `supported_languages`.
