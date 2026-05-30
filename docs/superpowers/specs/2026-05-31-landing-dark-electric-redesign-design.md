# SmartTap Landing — Dark Electric Redesign (v2)

**Status:** ✅ Approved 2026-05-31 by Henrique.
**Scope:** Visual + animation redesign of the existing landing at `apps/web/src/app/(landing)/`. Copy, section order, IA, data, routes, and SEO text are **locked and untouched** (approved in `LANDING-SPEC.md` 2026-05-26).
**Supersedes:** the visual system (§4) of `LANDING-SPEC.md` only. Everything else in that spec still holds.

---

## 0. Why this exists

The landing shipped with a warm cream/green/amber "Dublin craft café" identity and a placeholder SVG stand (real photo never arrived). The founder is pivoting the whole brand to **Dark Electric** — a near-black + electric-cyan, Linear/Vercel/Stripe-grade aesthetic. This redesign proves the new palette on the landing first, then it cascades to the rest of the product.

**This is a brand-identity change** that overrides the "identidade visual é sagrada" rule in `CLAUDE.md`. Authorized by the founder on 2026-05-31.

**Rollout sequence (whole product):** landing → dashboard → NFC customer page → emails → physical stand (new black+cyan filament on reprint). This spec covers the **landing only**.

---

## 1. Locked decisions

| Item | Decision |
|---|---|
| Palette | Dark Electric — `#0A0A0F` base + cyan `#00D4FF` accent |
| Headings | **Geist Sans** (geometric). DM Serif Display removed. |
| Body | **Inter**. DM Sans removed. |
| Mono/eyebrow | **Geist Mono**. JetBrains Mono removed. |
| Logo | Recolored cyan/white (not a from-scratch redesign) |
| Hero visual | **AI 3D render** of the stand in the new colors; crafted SVG fallback. No real photos exist yet. |
| Scope | Visual + animation only. Copy/SEO/IA untouched. |
| Magnetic Dock | Deferred to phase 2 |
| Auth Modal | Deferred to phase 2 |
| External components | Vendored + adapted for Tailwind v3 (project is v3, components assume v4) |

---

## 2. Tokenized palette

Mapped into `tailwind.config.ts` under the `electric` namespace. `surface` and `surface-2` are **added** (not in the founder's original list) because cards at `#0A0A0F` are invisible on a `#0A0A0F` background — they need a subtle elevation.

```
electric.bg          #0A0A0F   page base
electric.surface     #121219   cards / elevated sections      (ADDED)
electric.surface-2   #1A1A24   card hover / inputs            (ADDED)
electric.border      #1A2A3A   dividers (near-invisible)
electric.cyan        #00D4FF   accent + CTA + glow
electric.cyan-deep   #00BFEA   hover / gradients
electric.text        #FFFFFF   primary text (on dark)
electric.text-muted  #8899AA   secondary text
electric.light       #F0FAFE   light surface (1-2 breather sections)
```

**Contrast discipline (WCAG):**
- White on `#0A0A0F` ≈ 20:1 ✅
- `#8899AA` muted on `#0A0A0F` ≈ 7:1 ✅ (ok even for body)
- Cyan `#00D4FF` on `#0A0A0F` ≈ 12:1 ✅ (text + icons allowed)
- CTA = cyan fill + **black** text ≈ 12:1 ✅
- ⚠️ Cyan on light `#F0FAFE` ≈ 1.4:1 ❌ — on light surfaces cyan is fills/large-decorative only, never small text. (Same rule amber had.)

---

## 3. Typography

| Token | Family | Use |
|---|---|---|
| `display` / `h1` / `h2` | Geist Sans (600/700, tight tracking) | Headlines |
| `h3` / `body` / UI | Inter | Text, buttons, cards |
| `eyebrow` / code | Geist Mono (uppercase, 0.12em) | Eyebrows, mono badges |

Loaded via `next/font`: `geist` package (Sans + Mono) + Inter via `next/font/google`. Remove the three DM/JetBrains font imports from `app/layout.tsx` and the font-family tokens.

---

## 4. Logo

Recolor the inline SVG `ST + NFC waves` mark in `brand-logo.tsx`: waves/stroke cyan `#00D4FF`, ST in white, transparent background. Tokenized, not a redesign. A true logo redesign is a separate future task.

---

## 5. 3D render placeholder

No photos exist. The hero product visual comes from a render.

- **Primary — AI photoreal render** (Higgsfield): Counter Stand in matte black PLA, ST logo + NFC waves in electric cyan, dark studio backdrop with cyan rim light. Iterate prompt 1–2×. Export to `apps/web/public/stand-render.png`, place inside the Showcase Card (3D tilt).
- **Fallback — crafted SVG 3D**: elevate the current stand SVG to dark + cyan with glow + depth. Fully controlled, on-brand, zero AI uncertainty.

Either way the asset is marked **placeholder** in code, to swap for a real photo after the black+cyan reprint.

---

## 6. Component-by-section map

| # | Section | Change | Component / reference |
|---|---|---|---|
| Banner | Top banner | Dark strip, founding counter in cyan + underglow | — |
| 1 | Hero | `#0A0A0F`. H1 Geist with **Text Repel (Subtle Drift)** on hover. Cyan/ghost CTAs. 3D render inside **Showcase Card** (tilt + parallax) with cyan glow. **Dotmatrix** pulse at tap zone. Faint dot-grid/circuit bg. | Showcase Card + Text Repel + Dotmatrix |
| 2 | Animated Demo | Same 4.5s timeline, dark reskin: cyan tap ripple, stars fill, "Review submitted ✓". Dotmatrix tap motif. | Dotmatrix + framer-motion |
| 3 | How It Works | 3 steps linked by animated cyan **circuit traces** (tap→review→return). Cards on `surface` with cyan icons. | Circuit Board (adapted, subtle) |
| 4 | Pricing | Dark cards; "Most popular" with cyan border glow + `#00D4FF→#00BFEA` gradient. Founding callout in cyan-tinted card. | reskin |
| 5 | Problem→Solution | 3 dark cards, cyan transition line. | reskin |
| 6 | Comparison | Dark table; SmartTap column cyan-highlighted, alternatives muted. Mobile accordion. | reskin |
| 7 | FAQ | Dark accordion, cyan active state. | shadcn Accordion |
| 8 | CTA Final | Big dark moment, cyan gradient glow, founding block, cyan CTA. | reskin |
| Footer | Footer | Near-black, cyan accents, dotmatrix logo motif. | — |
| — | Magnetic Dock | Floating 3-pillar nav | **phase 2** |
| — | Auth Modal | Premium "Start free" modal | **phase 2** |

---

## 7. New dependencies

- `geist` (Vercel font) via npm.
- Componentry.fun (Showcase Card, Text Repel, Circuit Board) + Aceternity Carousel: **vendored + adapted** for Tailwind v3 (they assume v4). Copy code, rewire to our tokens.
- `framer-motion`: already installed.

---

## 8. Implementation phases

Each phase = atomic commit, `pnpm lint + typecheck + build` green before push. Vercel auto-deploys.

| Phase | Scope | Est. |
|---|---|---|
| 0 — Foundation | Tailwind tokens + globals.css + font swap + cyan/white logo | 3h |
| 1 — Chrome + primitives | Section, Button (cyan/ghost), Badge, TopBanner, Footer → dark | 3h |
| 2 — Hero | 3D render + Showcase Card tilt + Text Repel + Dotmatrix | 6h |
| 3 — Demo + How It Works | Cyan demo reskin + Circuit Board motif | 5h |
| 4 — Pricing + Problem + Comparison | Reskin cards, cyan highlight, founding callout, table | 5h |
| 5 — FAQ + CTA Final | Dark accordion + CTA glow (Auth Modal deferred) | 3h |
| 6 — SEO/OG + a11y + Lighthouse | Recolor OG, theme-color, contrast audit, reduced-motion, Lighthouse ≥95 | 4h |
| | **Total** | **~29h** (+buffer ~35h) |

---

## 9. Risks + mitigation

1. External components target Tailwind v4 → vendor + adapt to v3 (no blind install).
2. AI render may not be good enough → crafted SVG 3D fallback guaranteed.
3. framer-motion bundle vs Lighthouse 95 → dynamic import + bundle-analyzer.
4. Cyan overuse → §2 contrast discipline; reduced-motion respected everywhere.
5. Diverges from `CLAUDE.md` brand section → update CLAUDE.md + LANDING-SPEC after approval (done alongside this spec).

---

## 10. What does NOT change

Copy, the 8-section order, component structure, data files (pricing/faq/comparison), routes, textual SEO. Visual layer + animations only.
