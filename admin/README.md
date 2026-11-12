# Admin panel

React (Vite, TypeScript) web panel for the client's team and the Super Admin.
English and Arabic, right-to-left in Arabic. Sections appear according to the
signed-in user's role permissions:

| Section | Permission | Feature List |
|---|---|---|
| Releases (phases, feature switches, schedule, history, restore) | `release.view` / `release.manage` (Super Admin only) | release control |
| Users (eligibility queue, ID document review) | `users.review` | 1, 2, 53 |
| Stylists (applications, credentials, approve/suspend) | `stylists.review` | 15-17, 53, 54 |
| Products, Retail links, Report templates, Try-on library | `content.manage` | 36-39, 48, 56, 57, 11, 12 |
| Plans and prices | `pricing.manage` | 35, 40, 55 |
| Orders (refunds, delivery status) | `orders.manage` | 41, 48 |
| Moderation (flagged messages, suspensions, testimonials) | `moderation.manage` | 31-33, 45, 58 |
| Rewards | `rewards.manage` | 43, 44, 59 |
| Promotions and vouchers | `promotions.manage` | 42, 49-51, 60 |
| Settings and countries | `settings.manage` | 3, 52, 61-66 |

## Run

```bash
npm install
VITE_API_URL=http://localhost:8000 npm run dev     # http://localhost:5173
npm test                                           # vitest
npm run build                                      # static files in dist/
```

The API must allow the panel's origin: `IC_CORS_ORIGINS=https://admin.example.com` (comma-separated;
default `http://localhost:5173`). Tokens live in `sessionStorage` and end with the browser tab.

Needs Node 20.19+ or 22.12+.
