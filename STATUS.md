# Development status

Last updated: 12 Nov 2026, after try-on, stylist tools, location and the admin panel.

The product described in the master prompt is a multi-month build for a team. This file is
the honest ledger: nothing is listed as complete unless it exists and its tests pass.

## Milestones

| # | Milestone | Status |
|---|---|---|
| 0 | Source analysis, feature-to-phase map, RTM, architecture | Done (RTM not regenerated for this build, see below) |
| 1 | Backend foundation: auth, roles, release control | Done |
| 2 | Identity and profile | Mostly done: eligibility, markets, ID upload and review, UAE Pass sandbox, settings. Not done: email/mobile verification, password reset, rate limiting, audit log, account deletion, notifications |
| 3 | Assessments and photo upload | Done with DRAFT content |
| 4 | AI analysis | Done as indicative photo analysis (face, body, colour) on on-device models. Accuracy unmeasured. Celery workers not wired |
| 5 | Recommendations, reports, guides, entitlements, subscriptions, payments, retail links, loyalty | Done against a SANDBOX payment gateway. Real gateway not chosen |
| 6 | Mobile app for Phase 1 and admin panel | Done: mobile for customers, stylists and staff (Admin tab). Release control is developer-only (app/release_plan.py and the CLI) |
| 7 | Phase 2 marketplace | Done (backend and customer screens). Stylist screens partial |
| 8 | Phase 2 safeguards and tools | Done. Product recognition and video calls have no provider |
| 9 | Mobile and admin screens for Phase 2 | Done |
| 10 | Phase 3 | Done (location uses a newly added native library, not yet run on a device) |
| 11 | Hardening | Not started |

## Admin inside the app; release control developer-only (12 Nov 2026)

- The separate web admin (`admin/`) is removed. Staff accounts see an **Admin** tab in the app with the
  sections their role allows: approvals, stylists, orders, moderation, products, try-on library, retail
  links, plans, promotions and vouchers, rewards, settings.
- Phase management is no longer in the API or any screen. Developers switch phases and features in
  `backend/app/release_plan.py` and apply with `python -m app.cli release apply --note "..."`
  (also `status`, `check`, `history`, `rollback`, `cancel`). Deploys apply the file at container start.
  History, dependency checks, scheduling and rollback are unchanged.
- Tests: backend 121, mobile 46.

## Try-on, stylist tools, location and admin panel (12 Nov 2026)

**Tests**: backend 118, mobile 44, admin 7, all passing; migration 0005 round-trips.

- Garment and hairstyle try-on by transfer from approved reference photos (backend, admin library, mobile picker).
- Mobile stylist tools: services and availability, report editor, colour workspace, featured placement.
- Location: approximate position on request for "near me" stylists and offers.
- Web admin panel for every admin function (rows 53-60) and release control, English and Arabic, sections by permission. CORS is configured by `IC_CORS_ORIGINS`.

## Photo analysis and all-phases report (12 Nov 2026)

**Tests**: backend 113 passed (PostgreSQL 16, real MediaPipe models); mobile 38 passed; end-to-end 16 passed against the live API, including real model inference and a sandbox purchase. Type-check and lint clean. Migrations 0003 and 0004 round-trip (upgrade, downgrade, upgrade, `alembic check`).

### Photo analysis (rows 6-9, 11, 12, 14, 27, 28)

- On-device Google MediaPipe models (face landmarks, pose with body mask, multiclass hair/skin/clothes segmentation). `python -m app.cli fetch-models` downloads them and checks SHA-256; the Dockerfile runs it. They are not in git.
- **Face shape**: five measurements from 478 landmarks (length/cheekbone ratio, jaw ratio, forehead-to-jaw taper, jaw and chin angles), nearest-prototype classification with a confidence. Refuses turned heads, no face, several faces.
- **Body shape**: shoulder, waist and hip widths from the body silhouette, measured only on rows where an arm does not touch the body. Refuses arms on hips, arms touching the body, side-on poses, partial bodies. On 8 public runway photos only 1 was accepted, because models walk with arms against the body: users must follow the photo tips (arms slightly away), which the app shows.
- **Seasonal colour**: skin (cheeks and forehead), hair (optional, so a covered head works) and iris colour in CIELAB; warmth, depth and clarity scores mapped to the four seasons. Refuses black-and-white, sepia and badly exposed photos; flags tinted light from the colour of the eye whites. Correcting the colour from the eye whites was tried and made results worse, so it is not done.
- Results are stored with model version, scores and measurements; labelled "indicative" everywhere; a newer photo result replaces an older questionnaire result in recommendations and vice versa.
- **Previews**, returned as JPEG and never stored: hair colour, outfit colour, lip and brow tint, consultant drape and side-by-side drape comparison.

**Important caveats**
- The classification constants are DRAFTS calibrated by eye on about a dozen public photos. **Accuracy has not been measured.** That needs photos labelled by the client's consultants (row 64). All constants are in one table per analyser for recalibration.
- Try-on (rows 11, 12) works by **transfer**: an admin uploads a photo of a model wearing a garment or with a hairstyle; it is cut out, approved, and fitted onto the user's photo by body or face landmarks. It is not generative: a garment keeps the drape of the reference photo and her own clothes are not removed; a shorter hairstyle fills the uncovered area smoothly from the background and skin, which looks soft. A generative service would look more natural but means sending user photos to a third party (row 65). No garments or hairstyles are seeded: the client must supply photos it has the rights to.
- Analysis runs inside the request (about a second on CPU). Celery workers are still not wired.

### Feature rows

Status: Built = works end to end with tests; Partial = see note; API = backend only, no screen.

| Row | Feature | Status | Note |
|---|---|---|---|
| 1 | Identity verification | Partial | ID upload and staff review built; documents deleted after review. UAE Pass is a sandbox: the real provider needs the client's UAE Pass onboarding |
| 2 | Eligibility verification | Built | Age and women-only from declared or verified facts; thresholds are settings (row 63 open) |
| 3 | UAE-only launch access | Built | Country rule; launch market cannot be disabled |
| 4 | Visual onboarding quiz | Built | Draft content; image options await client images |
| 5 | Personal style assessment | Built | Draft content |
| 6 | Photo-based assessment | Built | |
| 7 | Face-shape analysis | Built | Photo and questionnaire; indicative, accuracy unmeasured |
| 8 | Body-shape analysis | Built | Photo and questionnaire; strict pose requirements |
| 9 | Preliminary seasonal color | Built | Photo and questionnaire; indicative |
| 10 | Outfit recommendations | Built | Rule-based, draft advice |
| 11 | Virtual outfit try-on | Built | Garments transferred from approved reference photos onto her photo, plus colour try-on. Not generative (see below) |
| 12 | Hair makeover preview | Built | Cut and style transferred from reference photos, any colour; plus advice. Not generative |
| 13 | Eyewear recommendations | Built | |
| 14 | Permanent-makeup preview | Built | Lip and brow tint |
| 15 | Stylist onboarding | Built | |
| 16 | Credential submission | Built | Mobile takes photos of documents; PDF upload from the phone needs a document picker |
| 17 | Stylist verification | Built | Approval needs at least one accepted credential |
| 18 | Stylist profiles and discovery | Built | Ranking weights are a setting (row 66 open) |
| 19 | Consultation booking | Built | Slot hold 15 min, cancellation window is a setting |
| 20 | In-app consultations | Partial | Intake, photos, report, messaging. No video: provider not chosen |
| 21 | Occasion-specific style audit | Built | |
| 22 | Wardrobe audit | Built | |
| 23 | Makeup audit | Built | Requires a seasonal colour result (Excel note) |
| 24 | Expert color analysis | Built | Report template has temperature, contrast, palette, makeup, hair, clothing, metals |
| 25 | Standardized expert reports | Built | Templates (admin-editable), mobile report editor, validation, PDF in EN/AR |
| 26 | Product recognition from photos | Not built | Endpoint says "integration not configured": needs a recognition service and product database |
| 27 | Consultant colour workspace | Built | Stylist screen with credits, drapes, comparison, automated reading |
| 28 | Digital color draping | Built | |
| 29 | Metered tool access | Built | Credits per client, bought as a product |
| 30 | In-app messaging | Built | Only after a booking |
| 31 | Contact-sharing detection | Built | Phones, emails, IBAN/cards, links, social handles, incl. Arabic digits and spelled-out numbers. Rule-based; will not catch everything |
| 32 | Message blocking and warnings | Built | |
| 33 | Violation tracking and suspension | Built | Thresholds are settings (row 33 open) |
| 34 | Free and paid feature access | Built | Entitlements; what is free is a placeholder (row 62 open) |
| 35 | Customer subscriptions | Partial | Plans, renewal job, cancellation. Automatic card charging needs a real gateway with saved cards |
| 36 | Retail product recommendations | Built | No retailer items seeded: the client must supply them |
| 37 | Paid report access | Built | Full assessment report PDF EN/AR |
| 38 | Digital guide catalog | Built | Draft guides; lip/blush shades are drafts |
| 39 | Complimentary digital resources | Built | |
| 40 | Consultant subscriptions | Built | Annual membership required to offer services |
| 41 | In-app service payments | Partial | Through the sandbox gateway only |
| 42 | Paid consultant promotion | Built | Stylist buys, admin approves, ranking boost |
| 43 | Loyalty points | Built | Draft rules |
| 44 | Reward redemption | Built | Free consultation credit |
| 45 | Testimonials and recognition | Built | Moderation by admin |
| 46 | In-person personal shopper | Built | |
| 47 | Location-based discovery | Built | Approximate device position on request; not yet run on a device |
| 48 | Physical product catalog | Built | Fulfilment status set by admin; no courier integration |
| 49 | Brand advertising | Built | Campaigns entered by admin |
| 50 | Location-targeted promotions | Built | As 47 |
| 51 | Vouchers and offers | Built | |
| 52 | International expansion | Partial | Markets switchable; no currency conversion, local payment or local content |
| 53-60 | Supporting administration | Built | Admin tab inside the mobile app, sections by role permission (no separate web portal) |

### Integrations that are sandboxes or missing (need client decisions or accounts)

- Payments: sandbox only. Needs a chosen UAE gateway and merchant account.
- UAE Pass: sandbox only. Needs UAE Pass onboarding (client id, secret, redirect URI).
- Video consultations, product recognition, push notifications (Firebase and Apple keys), SMS/email, courier: not connected.
- Both sandboxes refuse to start when `IC_ENV=production`, so they cannot be shipped by mistake.

### Not verified

- Native Android and iOS builds are still uncompiled on a device. One native library was added: `@react-native-community/geolocation` (coarse location permission on Android, usage text on iOS). iOS needs `pod install`.
- Arabic text (app, API messages, PDFs) is still unreviewed by a native speaker. PDF Arabic shaping and right-to-left layout were checked by rendering.
- The Docker image was changed (system libraries for OpenCV, model download) but not built here.
- The RTM spreadsheet was not regenerated: `docs/build_rtm.py` needs the client's workbook, which is not on this machine. Its planned API column predates this build.

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
