# SmartTap — Production Deploy Runbook

This is the **one source of truth** for getting SmartTap live on
`smarttap.ie`. Follow phases in order — each one assumes the previous
one is green. If a phase fails, stop and investigate before continuing;
do not skip ahead.

**Decisions locked in (don't re-debate without alignment):**

| Topic | Decision |
|---|---|
| API subdomain | `api.smarttap.ie` (CNAME → Railway, Cloudflare proxy OFF) |
| Frontend domain | `smarttap.ie` apex, `www.smarttap.ie` → 301 redirect to apex |
| Cron provider | cron-job.org (free tier) |
| Supabase project | `qmemsvkeiygdwxyzadrc` (eu-west-1) — **this is prod** |
| Stripe mode | Live (sk_live_…). Requires live-mode approval on the Stripe account |
| Hosting tier | Vercel Hobby + Railway Free until first paying customer |

---

## Phase 1 — Supabase prod

### 1.1 Confirm project + capture credentials

In Supabase Dashboard:

1. Switch to project `qmemsvkeiygdwxyzadrc` (eu-west-1).
2. Settings → API. Copy these 4 values to a password manager (you'll
   paste them into Railway + Vercel later):
   - **Project URL** (looks like `https://qmemsvkeiygdwxyzadrc.supabase.co`)
   - **anon / public** key
   - **service_role** key (treat like a password)
   - **JWT Secret** (under "JWT Settings") — only needed if you ever switch
     to HS256; current code uses ES256 via JWKS so this can stay empty.

### 1.2 Apply migrations 001 → 006 in order

In Supabase Dashboard → SQL Editor → New query, paste each migration
file's contents in order and click Run. **Verify each one succeeds before
moving on.**

```
backend/migrations/001_initial_schema.sql
backend/migrations/002_rls_policies.sql
backend/migrations/003_stripe_webhook_events.sql
backend/migrations/004_campaigns_indexes.sql
backend/migrations/005_customers_reactivation.sql
backend/migrations/006_customer_segments.sql
```

After all 6 are applied, run this validation query — every line should
return `t` (true):

```sql
SELECT
  (SELECT count(*) FROM information_schema.tables WHERE table_schema='public') >= 9 AS tables_ok,
  (SELECT relrowsecurity FROM pg_class WHERE relname='tenants')           AS rls_tenants,
  (SELECT relrowsecurity FROM pg_class WHERE relname='customers')         AS rls_customers,
  (SELECT relrowsecurity FROM pg_class WHERE relname='customer_segments') AS rls_segments,
  (SELECT relrowsecurity FROM pg_class WHERE relname='campaigns')         AS rls_campaigns,
  (SELECT relrowsecurity FROM pg_class WHERE relname='stripe_webhook_events') AS rls_webhooks;
```

### 1.3 Auth providers

Settings → Authentication → Providers:
- Email: enabled, confirm "Confirm email" matches your onboarding choice.
- Google: optional, leave for later if not wired.

✅ **Checkpoint:** all migrations green, validation query returns 6 trues.

---

## Phase 2 — Stripe live mode

**Pre-req:** Stripe account must be in live mode (look for the "View test
data" toggle and turn it OFF). If approval is still pending, stop and
finish Phase 5 (Railway) and Phase 6 (Vercel) with `sk_test_…` keys;
swap to live later.

### 2.1 Create recurring products

Dashboard → Products → Add product. For each one, set the product
billing to "Recurring", monthly, EUR:

| Product | Monthly | Price ID env var |
|---|---|---|
| SmartReview | €29.00 | `STRIPE_PRICE_REVIEW` |
| SmartLoyalty | €59.00 | `STRIPE_PRICE_LOYALTY` |
| SmartPro | €99.00 | `STRIPE_PRICE_PRO` |
| SmartNetwork | €179.00 | `STRIPE_PRICE_NETWORK` |

### 2.2 Create one-time setup fees

Same flow but billing = "One-time", EUR:

| Product | One-time | Price ID env var |
|---|---|---|
| SmartReview setup | €49.00 | `STRIPE_PRICE_REVIEW_SETUP` |
| SmartLoyalty setup | €79.00 | `STRIPE_PRICE_LOYALTY_SETUP` |
| SmartPro setup | €149.00 | `STRIPE_PRICE_PRO_SETUP` |
| SmartNetwork setup | €299.00 | `STRIPE_PRICE_NETWORK_SETUP` |

After each product, copy the `price_…` ID from the price detail page
(NOT the `prod_…` product ID) into your password manager.

### 2.3 Capture the live secret key

Dashboard → Developers → API keys → reveal "Secret key" (starts with
`sk_live_…`). Copy.

✅ **Checkpoint:** 8 price IDs + 1 secret key saved.

> Webhook setup happens in Phase 7, AFTER the backend has a public URL.

---

## Phase 3 — Resend domain verification

### 3.1 Add the domain in Resend

Dashboard → Domains → Add domain → `smarttap.ie`. Resend gives you 3 DNS
records to add (SPF TXT, DKIM CNAME, return-path CNAME).

### 3.2 Add DNS records in Cloudflare

For each Resend record:
- Type: as shown by Resend.
- Name: as shown.
- Value: as shown.
- **Proxy status: DNS only (grey cloud)** — Cloudflare proxying breaks
  email auth records.

### 3.3 Wait for verification

In Resend, hit "Verify". Usually 5-30 min; can take up to 24h. The
domain status must show ✅ green before any prod email will land in inbox.

### 3.4 Capture API key

Dashboard → API Keys → create one with "Sending access". Copy `re_…`.

✅ **Checkpoint:** `smarttap.ie` shows verified in Resend.

---

## Phase 4 — Sentry projects

1. Create 2 projects in Sentry:
   - `smarttap-backend` (platform: Python / FastAPI)
   - `smarttap-web` (platform: Next.js)
2. Copy each project's DSN (Settings → Projects → [name] → Client Keys).

✅ **Checkpoint:** 2 DSNs saved.

---

## Phase 5 — Railway backend

### 5.1 Generate the CRON_TOKEN

Run this on your laptop (Git Bash / WSL / any Python 3):

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the output — that's your `CRON_TOKEN`. Save it; you'll need the
same value in Phase 8 when configuring cron-job.org.

### 5.2 Create the Railway project

1. railway.com → New project → Deploy from GitHub repo → `cotah/SmartTap`.
2. Settings → Service → Root directory: `backend`.
3. Settings → Service → Watch paths: `backend/**` (avoids rebuilds on
   web-only commits).

### 5.3 Set environment variables

Variables tab → Raw editor → paste the block below, fill in the `<…>`
placeholders from the credentials you captured in Phases 1-4.

```
APP_ENV=production
LOG_LEVEL=INFO
CORS_ORIGINS=https://smarttap.ie,https://www.smarttap.ie
SITE_URL=https://smarttap.ie

SUPABASE_URL=https://qmemsvkeiygdwxyzadrc.supabase.co
SUPABASE_ANON_KEY=<phase 1.1>
SUPABASE_SERVICE_ROLE_KEY=<phase 1.1>
SUPABASE_JWT_SECRET=

STRIPE_SECRET_KEY=<phase 2.3, sk_live_…>
STRIPE_WEBHOOK_SECRET=
STRIPE_PRICE_REVIEW=<phase 2.1>
STRIPE_PRICE_LOYALTY=<phase 2.1>
STRIPE_PRICE_PRO=<phase 2.1>
STRIPE_PRICE_NETWORK=<phase 2.1>
STRIPE_PRICE_REVIEW_SETUP=<phase 2.2>
STRIPE_PRICE_LOYALTY_SETUP=<phase 2.2>
STRIPE_PRICE_PRO_SETUP=<phase 2.2>
STRIPE_PRICE_NETWORK_SETUP=<phase 2.2>

RESEND_API_KEY=<phase 3.4>
RESEND_FROM_EMAIL=hello@smarttap.ie

CRON_TOKEN=<phase 5.1>

SENTRY_DSN=<phase 4, backend DSN>
```

Note: `STRIPE_WEBHOOK_SECRET` stays empty for now — gets filled in Phase 7.

### 5.4 Deploy + verify

Railway auto-builds from `backend/Dockerfile`. Wait for deploy to go
green (~2-4 min). Find the auto-assigned URL (Settings → Networking →
Public Networking → "Generate Domain"). Hit it:

```
curl https://<your-railway-url>/health
# Expected: {"status":"ok"}
```

If you get a 500, check Railway logs for missing env vars.

### 5.5 Custom domain `api.smarttap.ie`

Railway → Settings → Networking → Custom Domain → `api.smarttap.ie`.
Railway shows you a CNAME target (looks like
`xyz.up.railway.app`).

In Cloudflare DNS for smarttap.ie:
- Type: CNAME
- Name: `api`
- Target: as shown by Railway
- **Proxy: DNS only (grey cloud)** — Railway terminates its own TLS

Wait ~5 min for TLS provision, then:

```
curl https://api.smarttap.ie/health
# Expected: {"status":"ok"}
```

✅ **Checkpoint:** `api.smarttap.ie/health` returns 200.

---

## Phase 6 — Vercel frontend

### 6.1 Create the Vercel project

1. vercel.com → New Project → Import `cotah/SmartTap`.
2. Configure Project:
   - **Root Directory:** `apps/web`
   - **Framework Preset:** Next.js (auto-detected)
   - Build/Install commands: leave default — the `apps/web/vercel.json`
     in the repo handles the monorepo `cd ../..` for pnpm install + turbo build.

### 6.2 Environment variables

Settings → Environment Variables. Set the following for **Production**
(and ideally **Preview** too so PR deploys also work):

```
NEXT_PUBLIC_API_URL=https://api.smarttap.ie
NEXT_PUBLIC_SITE_URL=https://smarttap.ie

NEXT_PUBLIC_SUPABASE_URL=https://qmemsvkeiygdwxyzadrc.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<phase 1.1>
SUPABASE_SERVICE_ROLE_KEY=<phase 1.1>

SENTRY_DSN=<phase 4, web DSN>
SENTRY_AUTH_TOKEN=

NEXT_PUBLIC_POSTHOG_KEY=
NEXT_PUBLIC_POSTHOG_HOST=https://eu.i.posthog.com
```

PostHog keys can stay empty — code tolerates it. Sentry auth token only
needed if you want sourcemap upload (skip for v1).

### 6.3 Deploy

Vercel auto-deploys from the import. Wait for green (~3-5 min). It'll
give you a URL like `smarttap.vercel.app`. Open it — landing page should
render.

### 6.4 Custom domains

Settings → Domains → Add `smarttap.ie`. Vercel will ask you to add:
- A record for apex (or CNAME flattening on Cloudflare via `@`)
- CNAME for `www` → `cname.vercel-dns.com`

In Cloudflare DNS:
- Type: A, Name: `@`, IPv4: as shown by Vercel (likely `76.76.21.21`),
  **Proxy: DNS only**
- Type: CNAME, Name: `www`, Target: `cname.vercel-dns.com`,
  **Proxy: DNS only**

Vercel auto-provisions TLS (~2-5 min). Add `www.smarttap.ie` as a
secondary domain in Vercel and check the "Redirect to smarttap.ie" box
(301).

✅ **Checkpoint:** `https://smarttap.ie` and `https://www.smarttap.ie`
both load (www redirects to apex).

---

## Phase 7 — Stripe webhook

Now that the backend has its public URL:

1. Stripe Dashboard (live mode) → Developers → Webhooks → Add endpoint.
2. URL: `https://api.smarttap.ie/v1/webhooks/stripe`
3. Events to send (use "Select events" → filter):
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
4. Add endpoint → click into it → reveal **Signing secret** (`whsec_…`).
5. Railway → Variables → set `STRIPE_WEBHOOK_SECRET=<the whsec_…>`. Save
   → Railway auto-redeploys.
6. Back in Stripe → the webhook page → "Send test webhook" → pick
   `checkout.session.completed`. Should show 200 response.

✅ **Checkpoint:** test webhook returns 200.

---

## Phase 8 — Cron jobs

In cron-job.org:

### 8.1 Daily reactivation

- Title: `SmartTap — daily reactivation`
- URL: `https://api.smarttap.ie/v1/cron/reactivation`
- Schedule: every day at `06:30` (UTC)
- Request method: `POST`
- Request headers:
  - `X-Cron-Token: <your CRON_TOKEN from phase 5.1>`
- Save & enable.

### 8.2 Monthly report

- Title: `SmartTap — monthly report`
- URL: `https://api.smarttap.ie/v1/cron/monthly-report`
- Schedule: day `1` of every month at `06:30` (UTC)
- Same POST + header as above.

### 8.3 Manual trigger to verify

In cron-job.org, hit "Execute now" on each. Then check Railway logs for
`reactivation_run_complete` / `monthly_report_run_complete` events.

✅ **Checkpoint:** both jobs return 200 manually.

---

## Phase 9 — Smoke tests E2E

Walk the full user journey on production. **Use a real email you can
check.**

| # | Action | Expected |
|---|---|---|
| 1 | Open `https://smarttap.ie/signup`, sign up | Redirected to `/onboarding` |
| 2 | Complete onboarding (business name, type, Google URL, reward) | Redirected to `/dashboard`, trial badge shows "30 days" |
| 3 | Inbox check | Welcome email from `hello@smarttap.ie` (not spam) |
| 4 | Insert 1 NFC tag manually in Supabase (no UI yet — Sprint 5) | Row exists with `tag_uuid` |
| 5 | Open `https://smarttap.ie/t/<tag_uuid>` on phone | Stamp card view loads, "Google Review" button visible |
| 6 | Submit opt-in form with email + GDPR check | Stamp count increments |
| 7 | Repeat taps until reward threshold reached | Reward code (6 digits) shown |
| 8 | Open `/dashboard/redeem`, enter code | Success message, reward marked redeemed |
| 9 | Open `/dashboard/billing`, click "Upgrade to SmartReview" | Stripe Checkout opens in **live** mode |
| 10 | Pay with real card (or your own — €49 setup + €29) | Redirected back to dashboard, plan shows "SmartReview" |
| 11 | Inbox check | Payment receipt email arrives |
| 12 | Open `/dashboard/segments/new`, set "visits ≥ 1", Run preview | At least 1 customer (yourself) listed |
| 13 | Open `/dashboard`, click "Download monthly PDF" | PDF downloads with `smarttap-<slug>-<YYYY>-<MM>.pdf` |

If any step fails, **stop the launch** and root-cause before
opening to pilot customers.

✅ **Checkpoint:** all 13 pass.

---

## Phase 10 — Hardening (post-launch, not blocking)

Track as Sprint 5 candidates:

- **Rate limiting** on `/v1/taps/{uuid}` (Cloudflare WAF or FastAPI middleware)
- **GDPR cookie banner** (required for EU)
- **Backups** confirmation in Supabase
- **Uptime monitoring** (UptimeRobot free → `/health` every 5min)
- **Status page** (Instatus / Statuspage)
- **NFC tag CRUD UI** (Phase 9 step 4 currently needs manual SQL)

---

## Rollback playbook

If something breaks badly post-launch:

- **Bad code deploy:** Railway → Deployments → click previous successful
  → "Redeploy". Vercel → Deployments → "Promote to Production" on the
  last green one.
- **Bad Stripe price config:** disable the affected price in Stripe;
  Railway env vars cached on the running deploy, so set new price IDs
  + redeploy.
- **Email reputation tanking (Resend score drops):** pause cron-job.org
  jobs, audit recent sends in Resend dashboard.
- **DNS rolled back accidentally:** Cloudflare keeps history under
  DNS → Audit Log, can revert from there.

---

## Credentials checklist (what to have in your password manager when starting)

- [ ] Supabase URL + anon + service_role + JWT secret (Phase 1.1)
- [ ] Stripe 8 price IDs + sk_live_… (Phase 2)
- [ ] Resend API key (Phase 3.4)
- [ ] Sentry 2 DSNs (Phase 4)
- [ ] Railway-generated public URL (Phase 5.4) + custom domain confirmed (5.5)
- [ ] CRON_TOKEN (Phase 5.1)
- [ ] Stripe webhook signing secret (Phase 7)
- [ ] cron-job.org account (Phase 8)

Nothing in this list ever gets committed to git. If it does, rotate
immediately.
