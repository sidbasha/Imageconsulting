# Development status

Last updated: 12 Nov 2026, after the Phase 1 self-assessment slice.

The product described in the master prompt is a multi-month build for a team. This file is
the honest ledger: nothing is listed as complete unless it exists and its tests pass.

## Milestones

| # | Milestone | Status |
|---|---|---|
| 0 | Source analysis, feature-to-phase map, RTM, architecture | Done |
| 1 | Backend foundation: auth, roles, release control (phases, feature switches, scheduling, preview, rollback, history) | Done, 33 tests passing |
| 2 | Identity and profile: email/mobile verification, password reset, rate limiting, consent, audit log, account deletion, UAE Pass adapter, eligibility, countries and languages, notifications | Not started |
| 3 | Assessments: onboarding quiz, style assessment, image upload, private storage, quality gate | Done on backend and mobile with DRAFT content (see slice report). S3 storage backend not written |
| 4 | AI analysis: face shape, body shape, colour; Celery workers; model registry; evaluation harness | Not started. Self-assessment questionnaires stand in for face shape, body shape and colour meanwhile |
| 5 | Recommendations, reports with EN/AR PDF, digital guides, entitlements, subscriptions and payment adapter, retail links, loyalty points | Partly done: rule-based outfit, eyewear and hairstyle recommendations. The rest not started |
| 6 | Mobile app for Phase 1 (EN/AR, RTL) and admin panel core with the Phase Management screen | Partly done: mobile foundation built (see below). Feature screens and the whole admin panel not started |
| 7 | Phase 2 marketplace: stylist onboarding, credentials, verification, discovery, booking, service payments, consultations, audits, expert reports | Not started |
| 8 | Phase 2 safeguards and tools: messaging, contact detection, blocking, violations, colour workspace, draping, metering, redemption, testimonials, paid promotion | Not started |
| 9 | Mobile and admin screens for Phase 2 | Not started |
| 10 | Phase 3: makeup preview, personal shopper, location discovery, physical products, brand advertising, geo promotions, vouchers, multi-country settings | Not started |
| 11 | Hardening: security and performance testing, full bilingual QA on devices, deployment guide, client delivery documents | Not started |

## Milestone 1 report

**Completed modules**

- `auth`: register, login, rotating refresh tokens (stored hashed), logout, profile, language preference. Argon2 password hashing.
- Roles and permissions: eight roles seeded. Release control is Super Admin only; the client-facing `admin` role has no access to it.
- `phase_management`: 52 feature keys traced to Excel rows, 36 dependencies, immutable release snapshots, dry-run validation, immediate and scheduled releases, cancel, rollback, preview, append-only history, one-active-release database constraint.
- `feature_flags`: `require_feature(key)` guard (404 when off) and `GET /api/v1/config/features` for navigation.
- Localized API errors in English and Arabic by saved language or `Accept-Language`.
- Alembic migration `0001` (11 tables), Dockerfile, Docker Compose, CLI.

**Tests**: 33 passed, 0 failed, on PostgreSQL 16. Mutation-checked: removing the guard fails 11 tests, removing dependency validation fails 3.

Mandatory release test cases (master prompt section 16):

| Case | Covered | Note |
|---|---|---|
| 1 Phase 1 only | Yes | |
| 2 Phase 1 and 2 | Yes | |
| 3 All three phases | Yes | |
| 4 Disable Phase 2 after activation | Yes | |
| 5 Disable Phase 3 after activation | Yes | |
| 6 Unauthorized API access to disabled features | Yes | Through test-only probe routes, because no business module exists yet |
| 7, 8 Language switching | API messages only | Screens do not exist yet |
| 9 Reports in both languages | No | Reports not built |
| 10 Data intact after deactivation | Users only | No other business data exists yet |
| 11 Users and subscriptions intact | Users only | Subscriptions not built |
| 12 Rollback | Yes | |

**Known limitations**

- No business feature behind any switch is built. The switches gate nothing real yet.
- No rate limiting, email verification, password reset or audit log outside release history (Milestone 2).
- No UAE Pass, payment, SMS, email or storage integration.
- Release state is read from PostgreSQL on every request (two indexed queries). A cache is planned when load requires it.
- Scheduled activation relies on request traffic or the `apply-due` command; Celery beat wiring comes with the workers in Milestone 4.
- Docker image and Compose file are written but were not built or run in this environment. The app, migration and tests were run directly.
- Arabic strings were written without native review.
- Dependencies between features are engineering proposals except row 23 -> row 9 (from the Excel) and three that follow MoM decisions.

## Phase 1 self-assessment slice report

**Completed (backend and mobile, both languages)**

- Questionnaire engine: configurable questions, options, weighted scoring and result profiles stored in the database, served in the request language. Retakes keep history.
- Five questionnaires seeded: style quiz, personal style (line, shape, colour, texture, pattern), body shape, face shape, seasonal colour.
- Recommendations for outfits, eyewear and hairstyles, drawn from the user's own results, with prompts for assessments still to take.
- Photos: consent required and recorded, JPEG/PNG up to 10 MB, quality gate (size, blur, exposure, face present and large enough), private storage under random keys, list and delete.
- Every endpoint is behind its feature switch. Switching a feature off returns 404 and keeps the data.
- Mobile: assessment runner and result screen, recommendations screen, photos screen. Nine home entries now open; the rest still say "In development".
- App icon and splash screen for both platforms (placeholder monogram artwork, regenerable with `mobile/scripts/make_icons.py`).
- Migration `0002` (6 tables).

**Tests**: backend 53 passed; mobile 30 passed; end-to-end 14 passed against the live API (including an Arabic assessment, recommendations, real photo upload and rejection, and a feature switched off and back on). Mandatory case 10 now passes with real assessment data.

**Important caveats**

- ALL questionnaire content, scoring weights, result texts, advice and colour palettes are DRAFTS written by the development team from general styling conventions. They are not the client's methodology and not validated. Each questionnaire is flagged `content_status = draft`. The client must review and replace them before any release.
- Face shape, body shape and seasonal colour are SELF-ASSESSMENTS, not AI analysis. Excel rows 7, 8 and 9 call for photo-based analysis; that is not built. The face landmark model could not be downloaded in the build environment, so no landmark code was written rather than shipping analysis that was never run. Results are labelled as self-assessed in the app.
- Uploaded photos are checked and stored but not analysed yet.
- Photo quality thresholds were set on one sample portrait and need tuning on real user photos. The face detector is OpenCV's Haar cascade (requires opencv 4.x).
- Storage is local disk only. The S3-compatible backend is not written.
- Analysis and uploads run inside the request; Celery workers are not wired.
- The photo picker (`react-native-image-picker`) is a fourth native library and, like the rest of the native build, has not been compiled or run on a device.
- No admin screens exist to edit the content; it can only be changed in the database for now.
- The API now prefers the request's `Accept-Language` over the saved profile language (the app sends its current language on every request).

**Not done from the "build all" request, and why**

- Push notifications: need a Firebase project (`google-services.json`, `GoogleService-Info.plist`) and an Apple push key. Adding the Firebase library without those files breaks the Android build, so nothing was added.
- Arabic review: needs a native speaker. All Arabic in the app and content remains an unreviewed draft.
- Native build verification: still impossible here (no Android SDK, Xcode or Gradle download).
- Remaining Phase 1 features: virtual try-on (11), hair preview on photo (12), retail links (36), subscriptions and paid access (34, 35, 37), guides (38, 39), loyalty points (43), identity and eligibility (1 to 3), reports.
- All of Phase 2 and Phase 3.

## Mobile foundation report

**Completed**

- Bare React Native 0.88 project in `mobile/` with `android/` and `ios/` folders from the official template, bundle id `com.imageconsulting`.
- Screens: sign in, create account, home, settings. Tokens in Keychain/Keystore with automatic single-flight refresh.
- English and Arabic with immediate direction switch, saved to the profile. No literal text in components.
- Home built from the enabled features reported by the API; refreshes on return to foreground and on pull.
- `scripts/e2e.sh`: starts the API on a scratch database and runs the app's client against it.

**Tests**: 24 unit and whole-app tests passed; 10 end-to-end tests passed against the live API and PostgreSQL 16 (register, Phase 1 only, Arabic errors, language saved, token renewal, release Phase 2, rollback, access control, sign out). Type-check and lint clean. Release JavaScript bundles build for both platforms. Mutation-checked: removing feature filtering fails 3 tests, removing RTL handling fails 2.

**Not verified**

- The native Android and iOS builds were NOT compiled or run. This environment has no Android SDK, no Xcode, and cannot download Gradle. `npm run android` / `npm run ios` have never been executed for this project. The native folders are the unmodified official template plus one manifest change (`supportsRtl="false"`); three native libraries are autolinked (keychain, screens, safe-area-context).
- No test has run on a device or simulator, so real RTL rendering, keyboard behaviour and Keychain access are untested.
- iOS needs `pod install` on a Mac before the first build.

**Known limitations**

- Every service on the home screen is marked "In development" and cannot be opened.
- Mandatory cases 7 and 8 (language switching) now pass at screen level in Jest for the four existing screens, not on devices.
- No app icon, splash screen, push notifications, deep links or store configuration.
- Arabic copy is unreviewed and uses the feminine form, following the women-only audience decision in the minutes.

**Open before Milestone 2 can be finalised**: the client questions in section 3 of the analysis document, above all the verification method, women-only and teenage rules, and what virtual try-on means.

**Next milestone**: 2, identity and profile.
