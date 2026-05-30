# SmartTap Landing Page — Master Spec

**Status:** ✅ Approved 2026-05-26 — all 5 conflicts resolved, ready for implementation.
**Synthesis of:** CEO advisor + Copywriter + PMM + CRO + UI/UX designer + Frontend developer.
**Target route:** `apps/web/src/app/(landing)/page.tsx` (full replacement of current 27-line placeholder).
**Est. build:** 30–34h (+20% buffer = ~40h wall-clock).

---

## ✅ CONFLICTS — RESOLVED 2026-05-26

| # | Topic | Resolution | Notes |
|---|---|---|---|
| **C1** | Photos of real stand | ✅ Photo coming | Founder photographing stand 2026-05-26; placeholder until photo arrives |
| **C2** | Section order | ✅ CEO reorder accepted | Hero → Demo → How → Pricing → Problem → Comparison → SocialProofSignals → FAQ → CTAFinal |
| **C3** | Cut Social Proof section | ✅ Hybrid | Section killed; 3 micro-signals sprinkled (hero microtrust + pricing badges + banner counter) |
| **C4** | Comparison table | ✅ Keep but move | Lives post-pricing, max 5 axes |
| **C5** | Primary CTA | ✅ Keep "Start free" | A/B test "Book a call as primary" planned post-launch |
| **C6** | Amber WCAG fail (technical) | ✅ Auto-fix | Amber restricted to ≥18px bold, hover, decorative, badges. Never body text. |

**Other locked decisions:**
- Cal.com: Henrique creating account; mailto fallback if URL not ready by build day
- Founding counter: `5 of 5 spots still open` (no customers yet)
- Founder bio: "Built by Henrique in Dublin"

---

## 1. EXECUTIVE SUMMARY

A 7-section landing (8 with banner) that sells the SmartTap stand to a Dublin barbershop owner in 3 scrolls. Visual model: **Linear's structural precision meets a Dublin craft café's chalkboard menu — Stripe-grade polish in cream and forest green, with amber used like a single neon sign in a quiet shop.**

Tone: direct, local, confident. Founder is the trust signal at N=0 customers — Henrique's face + Dublin address + GDPR badge + scarcity counter do the work that logos can't.

Category frame (PMM-locked): **"The anti-app loyalty stand"** — alternative, not creator/challenger. Lets you be small, new, and rebel rather than presumptuous.

Top 3 value props ranked (PMM):
1. **No app needed** — visible miracle the owner can demo
2. **Hardware included** — tangible, justifies setup fee
3. **Three-in-one** (review + loyalty + CRM)

Data ownership is a *closer*, not a hook (#4 on the priority list).

---

## 2. FINAL STRUCTURE (post-CEO reorder)

```
[Top Banner] ─ thin sticky strip, founding spots counter
  ↓
[Section 1: Hero]      H1 + subhead + 2 CTAs + REAL stand photo + founder micro-trust
  ↓
[Section 2: Demo]      Animated SVG mockup (4.5s loop): stand pulse → phone slide → review submitted
  ↓
[Section 3: How It Works]   3 steps with icons + 5-min setup promise
  ↓
[Section 4: Pricing]   4 plans (Loyalty highlighted) + founding-member callout
  ↓
[Section 5: Problem→Solution]   3 punch-list problems + transition line (confirmation, not setup)
  ↓
[Section 6: Comparison]    5 axes vs "Typical alternatives" — Cal.com-style
  ↓
[Section 7: FAQ]       8 Q/A in accordion
  ↓
[Section 8: CTA Final]  Founding-member offer block + primary signup + alternative link
  ↓
[Footer]               Green-dominant, 3-col, GDPR microcopy
```

Total: 8 sections + banner + footer. Was 9 in your spec, cut to 7 content sections + 1 final CTA after killing the dedicated Social Proof section (C3).

---

## 3. COPY (final, picked from copywriter variants)

### Top Banner
> 🇮🇪 **5 founding spots open** — stand free, €29/mo for life

(Counter is hardcoded in `lib/landing/constants.ts:FOUNDING_SPOTS_REMAINING`. Update manually when a founding member signs. When `0`, banner switches to "Founding offer closed — standard pricing live" with no urgency.)

### Hero
- **Eyebrow:** `Built in Dublin, for Dublin shops.`
- **H1:** `One tap. Reviews go up. Regulars come back.` (locked — copywriter agrees no alternative beats it)
- **Subhead:** `Your stand. Your customers. Your data. Not stuck inside someone else's app.`
- **Primary CTA:** `Start free — no card needed`
- **Secondary CTA:** `15 minutes with the founder`
- **Below CTAs (microtrust line):** `★★★★★ Built by Henrique in Dublin · GDPR-ready · No app for your customers`

### Section 2 — Demo caption
> `This is what your customers see. One tap. That's it.`

### Section 3 — How It Works
- **Header:** `How it works`
- **Step 1 — They tap the stand**
  > Phone touches the stand. Page opens. No app, no download, nothing to install.
- **Step 2 — They leave a review**
  > One tap sends them straight to your Google page. Stamp gets added too.
- **Step 3 — They come back**
  > Stamps fill up. Reward unlocks. You message them direct — no middleman.

### Section 4 — Pricing
- **Header:** `Simple pricing. No contracts.`
- **Eyebrow:** `Setup fee covers your custom 3D-printed stand, shipped from Dublin.`
- **CTA on every card:** `Start free trial`
- **Plans:**

| Plan | Setup | Monthly | Tagline | Highlight |
|---|---|---|---|---|
| SmartReview | €49 | €29 | `For shops focused on reviews` | — |
| SmartLoyalty | €79 | €59 | `Reviews plus digital stamps` | **★ Most popular** |
| SmartPro | €149 | €99 | `For shops that want everything` | — |
| SmartNetwork | €299 | €179 | `For multi-location owners` | — |

Bullets per plan and full content in `apps/web/src/lib/landing/pricing-plans.ts` (frontend agent's structure).

- **Founding callout under grid** (separate component, amber-tinted card):
  > **First 5 Dublin shops only:** stand free, 60 days free, €29/mo locked for life. [Claim my founding spot →]
- **Footer note under grid:** `30-day free trial. No card to start. Cancel any time — your data exports with you.`

### Section 5 — Problem → Solution
- **Header:** `Sound familiar?`
- **3 problems** (punch-list, owner's voice):
  - `You ask for reviews. Most never leave one.`
  - `Regulars stop coming. You never find out why.`
  - `You pay for ads to bring strangers in.`
- **Transition:** `SmartTap turns one tap into both.`

### Section 6 — Comparison (post-CEO override — kept but minimal, see C4)
- **Header:** `Why shops switch to SmartTap`
- **Columns:** `SmartTap` vs `Typical alternatives`
- **5 axes (cut from copywriter's 6, removed "Long-term contract" — already covered in FAQ):**

| Axis | SmartTap | Typical alternatives |
|---|---|---|
| Customer data ownership | You own it | They own it |
| App download required | No — just tap | Yes |
| Physical stand included | Yes, custom 3D-printed | Sold separately |
| Built for your shop | White-label, your brand | Their logo |
| Support from Ireland | Founder, in Dublin | Call centre abroad |

### Section 7 — FAQ (8 Q/A in accordion)
Full Q/A in `apps/web/src/lib/landing/faq-data.ts`. Headers:
- `Do my customers need to download an app?` → **No.**
- `Does it work on iPhone and Android?` → **Yes — both.**
- `Are customers forced to give their details?` → **Never.**
- `Can I cancel whenever I want?` → **Yes, no contracts.**
- `Who actually owns the customer data?` → **You do.**
- `What if my shop Wi-Fi is patchy?` → **Doesn't matter — uses customer's own data.**
- `Is this GDPR compliant?` → **Yes, built for it from day one.**
- `What does the setup fee cover?` → **Custom stand + setup + walkthrough call.**

### Section 8 — CTA Final
- **H2:** `Five shops. One price. Locked for life.`
- **Supporting:** `Founding members get the stand free and €29/month forever — long after public pricing goes up.`
- **Offer block (3 lines):**
  > **You get:** Free custom stand, 60 days free, €29/mo locked for life.
  > **You give:** A short video saying what worked, and two shops we should talk to.
  > **Closing:** 5 spots total. All 5 still open. First come, first served. (Counter pulled from `FOUNDING_SPOTS_REMAINING`.)
- **Primary CTA:** `Claim my founding spot`
- **Alt link:** `Not a founder? Start a free 30-day trial instead →`

### Footer
- **Tagline:** `TAP. CONNECT. GROW.`
- **Trust microcopy:** `Built and hosted in Ireland. GDPR compliant. Your data, always.`
- **Columns:** Product (`/`, `#pricing`, `#faq`) · Company (`Founder note`, `Contact`, `Roadmap`) · Legal (`/privacy`, `/terms`, `/gdpr`)
- **Bottom strip:** © 2026 SmartTap · Built in Dublin · GDPR-compliant

---

## 4. VISUAL SYSTEM (UI/UX-locked)

> ⚠️ **SUPERSEDED 2026-05-31 by the Dark Electric redesign.** This entire §4 (palette, type scale, colour usage, animation defaults) is replaced by `docs/superpowers/specs/2026-05-31-landing-dark-electric-redesign-design.md`. The palette is now near-black `#0A0A0F` + cyan `#00D4FF`; headings are Geist Sans, body Inter. **Everything else in this file — copy (§3), section order (§2), structure (§5), SEO, data — remains locked and in force.** Only the visual layer changed. The original §4 below is kept for historical reference.

### Type scale
| Token | Family | Desktop / Mobile | LH | Weight |
|---|---|---|---|---|
| `display` | DM Serif Display | 80 / 44 | 1.05 | 400 |
| `h1` | DM Serif Display | 64 / 40 | 1.08 | 400 |
| `h2` | DM Serif Display | 44 / 32 | 1.15 | 400 |
| `h3` | DM Sans | 24 / 20 | 1.3 | 600 |
| `body` | DM Sans | 17 / 16 | 1.6 | 400 |
| `body-lg` | DM Sans | 20 / 18 | 1.55 | 400 |
| `small` | DM Sans | 14 / 13 | 1.5 | 500 |
| `eyebrow` | JetBrains Mono | 12 | 1.4 | 500 (uppercase, 0.12em tracking) |

**Rule:** DM Serif Display ONLY for display/h1/h2. Never on buttons, badges, or body.

### Color usage (page-area %)
- **Off-white** `#F7F5F0` — 70% — page + card bg
- **Brand Green** `#1B4D3E` — 15% — primary CTA, headline accent words, footer bg, "Most popular" card bg
- **Brand Amber** `#E8A020` — 5% — hover states, founding badge, counter highlight, link underlines. **Never on body text (WCAG fail).**
- **Black** `#1A1A1A` — 10% — body text + headings

Derived tokens to add to `tailwind.config.ts`:
```
green-50: #EAF0EE   green-800: #245C4B (hover)   green-900: #1B4D3E (base)
amber-50: #FBF3E4   amber-500: #E8A020 (base)    amber-600: #C8861A (hover)
neutral-300: #D8D5CD   neutral-600: #5A5A5A   neutral-900: #1A1A1A
cream: #F7F5F0
```

### Spacing & rhythm
- Section py: `py-32 md:py-24 sm:py-18` (128 / 96 / 72px)
- Section px: 24 / 48 / 64
- Container max-width: `max-w-[1200px]` standard, `max-w-[1280px]` hero & CTA Final
- Body copy blocks: `max-w-[680px]`
- Card padding: 32 desktop / 24 mobile
- 8px baseline grid

### Animation
- Default fade-in: 600ms, opacity 0→1 + translateY 16→0
- Easing: `cubic-bezier(0.16, 1, 0.3, 1)` (named `smooth-out`)
- Stagger: 80ms between siblings
- IntersectionObserver: threshold 0.15, rootMargin `-50px 0px`
- Counter: 1800ms, easeOutCubic, once on enter
- Parallax: hero mockup 0.15× scroll rate, blobs 0.08×, **never on text**
- Demo SVG: 4.5s loop with 800ms pause between cycles

### Components (Tailwind specs in section §5)
Buttons (primary/secondary/tertiary), Card (default + highlighted variant for "Most popular"), Badge (green/amber/neutral), Section eyebrow (mono dot prefix), Top banner (sticky, dismissable, localStorage 7d).

---

## 5. IMPLEMENTATION (Frontend-locked)

### Component tree (`apps/web/src/app/(landing)/`)

23 components total. Server components by default; Client only where animation/state needed.

```
(landing)/
├── layout.tsx                        Server, wraps TopBanner + main + Footer
├── page.tsx                          Server, composes 8 sections
└── _components/
    ├── top-banner.tsx                Client (dismiss + counter)
    ├── hero/
    │   ├── hero.tsx                  Server wrapper
    │   ├── hero-content.tsx          Server (H1 + subhead + CTAs + microtrust)
    │   └── hero-mockup.tsx           Client (real photo + parallax)
    ├── animated-demo/
    │   ├── animated-demo.tsx         Client (4.5s timeline)
    │   └── demo-svg.tsx              Client (inline SVG primitives)
    ├── how-it-works/
    │   ├── how-it-works.tsx          Server
    │   └── step-card.tsx             Client (fade-in stagger)
    ├── pricing/
    │   ├── pricing.tsx               Server
    │   ├── pricing-card.tsx          Server
    │   └── founding-callout.tsx      Client (counter)
    ├── problem-solution/
    │   ├── problem-solution.tsx      Server
    │   └── problem-card.tsx          Client (fade-in)
    ├── comparison/
    │   ├── comparison-table.tsx      Server (desktop)
    │   └── comparison-accordion.tsx  Client (mobile)
    ├── faq/
    │   └── faq.tsx                   Client (shadcn Accordion)
    ├── cta-final.tsx                 Server
    ├── book-call-button.tsx          Client (Dialog + Cal.com embed)
    ├── footer.tsx                    Server
    ├── section.tsx                   Server (semantic wrapper)
    ├── scroll-fade.tsx               Client (animation wrapper)
    └── brand-logo.tsx                Server (inline SVG)
```

### Hooks (`apps/web/src/lib/hooks/`)
- `use-scroll-fade-in.ts` — IntersectionObserver + framer-motion variants
- `use-counter.ts` — RAF tween 0→target, respects reduced motion
- `use-reduced-motion.ts` — SSR-safe matchMedia wrapper
- `use-mounted.ts` — hydration-safe boolean

### Data (`apps/web/src/lib/landing/`)
- `pricing-plans.ts` — plan array
- `faq-data.ts` — Q/A array
- `comparison-data.ts` — 5-row feature matrix
- `constants.ts` — `BOOK_CALL_URL`, `FOUNDING_SPOTS_REMAINING`

### Assets (`apps/web/public/`)
- `favicon.ico` (32×32) + `favicon.svg`
- `apple-touch-icon.png` (180×180)
- **`hero-stand.jpg`** ← needs your photo (C1 — if you accept, ship iPhone shot by build day)
- OG/Twitter via Next 15 `app/opengraph-image.tsx` (no static file)
- All other illustrations = inline SVG inside components

### Animated demo (Section 2) — 4.5s timeline
| Stage | Time | What |
|---|---|---|
| 1 | 0.0–0.8s | Stand fades in, amber glow pulse on tap zone |
| 2 | 0.8–1.6s | Phone slides in from right |
| 3 | 1.6–2.4s | Tap ripple (circle expands + fades) |
| 4 | 2.4–3.4s | Stars fill left→right (100ms stagger), "Review submitted ✓" slides up |
| 5 | 3.4–4.5s | Hold + fade out, restart |

Pause when off-screen (`useInView`). Mobile: simplified 3-stage 3s loop. Reduced motion: static end-state.

### "Book a 15-min call" CTA — Cal.com inside shadcn Dialog
- Lib: `@calcom/embed-react`
- Fallback if `BOOK_CALL_URL` env var empty: Dialog renders mailto button with prefilled subject
- Pre-launch action item: create Cal.com account, expose `BOOK_CALL_URL` env var

### Routes that need stubbing
`/privacy`, `/terms`, `/gdpr` — each gets 15-min "Coming soon" stub with contact email.

### SEO + metadata
- `metadata` export in layout (title template, OG, Twitter, themeColor)
- OG image via `app/opengraph-image.tsx` (Edge runtime, ImageResponse)
- `app/robots.ts` + `app/sitemap.ts` (Next 15 native)
- JSON-LD: Organization + LocalBusiness (Dublin address)
- Lighthouse mobile target ≥95

### Build phases + hours
| Phase | Scope | Hours |
|---|---|---|
| 1 | Scaffold, layout, top banner, footer, hooks, section primitives | 5 |
| 2 | Hero + animated demo SVG | 9 |
| 3 | Problem/Solution + How It Works | 3 |
| 4 | Pricing + Comparison (desktop + mobile accordion) | 6 |
| 5 | FAQ + Final CTA + BookCall Dialog + polish | 5 |
| 6 | SEO + OG + JSON-LD + sitemap + a11y audit + Lighthouse | 4 |
| | **Subtotal** | **32** |
| | +20% buffer | **38–40 wall-clock** |

**Top 3 risks:**
1. Animated demo iteration creep — timebox to 8h, ship simpler if over
2. Cal.com embed CSP/iframe conflicts in Dialog — mailto fallback ready
3. Lighthouse 95+ blocked by framer-motion bundle — dynamic import, audit with `@next/bundle-analyzer`

### Accessibility (non-negotiable)
- `useReducedMotion` short-circuits all framer-motion `animate` (returns final state)
- Counter `aria-live="polite"`, final value in `<span class="sr-only">`
- Demo SVG: `role="img" aria-label="..."`, inner `aria-hidden`
- Skip link `<a href="#main">`
- Strict H1→H2→H3 order
- shadcn Accordion + Dialog = Radix ARIA-complete out of box

---

## 6. POST-LAUNCH (deferred — not blocking launch)

### Analytics — track from day 1
PostHog events to fire (CRO-locked priorities):
1. `signup_completed` / unique visitors — primary KPI
2. `call_booked` (Cal.com webhook → PostHog)
3. `$scroll` to pricing section (70% threshold)
4. `cta_clicked` with `location` prop (hero/sticky/pricing/final)
5. `trial_to_paid_14d` (Supabase derived metric)

Benchmarks: signup CR 1.5-3%, call CR 0.5-1.5%, pricing reach 35-50%.

### A/B tests when ≥100 weekly visitors
1. **Hero headline specificity** — generic vs Dublin-named in H1
2. **Primary CTA copy** — "Start free" vs "Get my free stand →" (founding angle)
3. **Book-a-call as PRIMARY** vs signup primary (CRO test #3 — high-trust ICP hypothesis)

### Phase 2 polish (not v1)
- Sticky bottom CTA bar on mobile (CRO recommendation; defer to A/B test)
- WhatsApp sticky button bottom-right (CRO recommendation; needs WhatsApp Business setup from Sprint 5)
- Real customer testimonial video when founding member ships (replaces founder microtrust)
- Annual pricing toggle (default monthly, reveals "save 2 months")

---

## 7. WHAT I NEED FROM YOU (action items)

1. **Resolve the 5 conflicts (C1–C5)** at the top — ✅ / ❌ each
2. **Decide on the photo (C1)** — if ✅, send me an iPhone shot of the stand on any counter by build day. If ❌, I use SVG illustration as primary visual.
3. **Cal.com setup** — create free account, share booking URL. If you don't want to set this up before launch, I'll wire the mailto fallback.
4. **Founding-spots counter** — confirm current value (`3 of 5 left`? `5 of 5 still open`?)
5. **Founder bio one-liner** for the hero microtrust — `Built by Henrique in Dublin` is the default; adjust if you want different wording.
6. **Approve this spec** so I can start Phase 1 implementation.

---

**Once you approve + resolve conflicts, this becomes a single sprint** (8 sub-phases over ~40h work) and the landing ships at `https://smarttap.ie` replacing the placeholder.
