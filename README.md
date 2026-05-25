# SmartTap

> TAP. CONNECT. GROW.

Loyalty and reviews system for Dublin local businesses. NFC-based, no app required.

For full project context, roadmap, decisions and pricing see [CLAUDE.md](./CLAUDE.md).

## Stack

- **Monorepo:** Turborepo + pnpm workspaces
- **Frontend:** Next.js 15 + Tailwind v3 + shadcn/ui (PWA)
- **Mobile:** React Native + Expo (Phase 2 launch)
- **Backend:** FastAPI + Python 3.12
- **Database:** Supabase (Postgres + RLS)
- **Hosting:** Vercel (frontend) + Railway (backend)
- **Payments:** Stripe
- **Email:** Resend

## Layout

```
smarttap/
├── apps/
│   ├── web/         Next.js 15 — landing, customer view, dashboard
│   └── mobile/      Expo — Phase 2 structure
├── packages/
│   ├── core/        Business logic, types, Zod schemas (shared)
│   ├── ui/          Shared design tokens and components
│   └── api/         HTTP client for FastAPI backend (shared)
├── backend/         FastAPI + Supabase + Stripe + Resend
└── .github/         CI/CD
```

## Local dev

```bash
nvm use                       # Node 20.18.1
pnpm install
cp apps/web/.env.example apps/web/.env.local
cp backend/.env.example backend/.env
pnpm dev                      # web on :3000
cd backend && uv run uvicorn app.main:app --reload   # backend on :8000
```

## Built by

Henrique Pasquetto — Dublin, Ireland.
