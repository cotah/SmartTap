# Feature 3 — Resposta automática a Google Reviews · Fase A · Spec

**Data:** 2026-05-29
**Sprint:** 5 — Feature 3, Fase A
**Estado:** Aprovado para implementação
**Doc guarda-chuva:** `2026-05-28-sprint5-whatsapp-ai-assistant-design.md`

---

## 1. Objetivo

Cron busca reviews novas do Google → Claude (Sonnet 4.6) gera uma **resposta
sugerida** → fica **pendente no dashboard** → o dono **edita e aprova** →
publica no Google. **Nada é publicado sem aprovação humana** (decisão v1).

Sem acesso à Google Business Profile API (gated, ainda por aprovar), tudo corre
em **modo no-op** — dev/testes funcionam; ativa-se com env vars + ligação por
tenant, sem mudar código (build-to-activate, igual ao padrão Meta/Resend).

## 2. Decisões (aprovadas 2026-05-29)
- **Fase A = dashboard-first.** Autopost, push de draft via WhatsApp e alertas
  de review negativa ficam para a **Fase B**.
- **Sempre aprovação humana** no v1 (sem autopost).
- **Acesso Google API: ainda não** → build-to-activate.
- **Frontend incluído:** página `/dashboard/reviews`.

## 3. Ligação Google (OAuth por tenant)
- `GET /v1/google/connect` → redirect para o consent do Google (scope
  `https://www.googleapis.com/auth/business.manage`), `state` assinado com o
  tenant.
- `GET /v1/google/callback` → troca `code` por tokens, guarda `refresh_token` +
  `account_id`/`location_id` em `tenant_google_connections`.
- `google_client.is_configured()` → False sem `GOOGLE_CLIENT_ID/SECRET`.
  `list_new_reviews()` / `publish_reply()` → no-op (`[]` / log) sem credenciais
  ou sem ligação.
- ⚠️ **Refresh token é sensível.** Tabela acedida só por service-role (RLS).
  v1: guardar texto; **encriptar em repouso (pgcrypto) é recomendado** —
  sinalizado para decisão antes de ligar contas reais.

## 4. Migration 009
```sql
CREATE TABLE tenant_google_connections (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     UUID NOT NULL UNIQUE REFERENCES tenants(id) ON DELETE CASCADE,
    refresh_token TEXT NOT NULL,
    account_id    TEXT,
    location_id   TEXT,
    connected_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TRIGGER trg_tgc_updated BEFORE UPDATE ON tenant_google_connections
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TABLE reviews (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    google_review_id  TEXT NOT NULL,             -- dedupe key from Google
    author            TEXT,
    rating            INT,                        -- 1..5
    comment           TEXT,
    created_at_google TIMESTAMPTZ,
    ai_draft          TEXT,                       -- Claude's suggested reply
    reply_text        TEXT,                       -- owner-edited final reply
    status            TEXT NOT NULL DEFAULT 'pending',
                      -- pending | published | dismissed | failed
    published_at      TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, google_review_id)
);
CREATE INDEX idx_reviews_tenant_status ON reviews(tenant_id, status, created_at_google DESC);
CREATE TRIGGER trg_reviews_updated BEFORE UPDATE ON reviews
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

ALTER TABLE tenant_google_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE reviews ENABLE ROW LEVEL SECURITY;
```

## 5. Arquitetura e ficheiros
```
migrations/009_review_responses.sql          [NOVO]
config.py                                     [EDIT] GOOGLE_CLIENT_ID/SECRET/REDIRECT
app/db/google_connections.py                  [NOVO] get/upsert por tenant
app/db/reviews.py                             [NOVO] dedupe + list + update status/reply
app/services/google_client.py                 [NOVO] OAuth + list_new_reviews + publish_reply (no-op sem creds)
app/services/anthropic_client.py              [EDIT] generate_text() single-shot (reusa is_configured)
app/services/review_response_service.py       [NOVO] cron: fetch -> draft -> store; e publish()
app/schemas/review.py                          [NOVO]
app/routers/reviews.py                         [NOVO] GET list / PUT reply / POST publish / POST dismiss
app/routers/google_oauth.py                    [NOVO] GET /google/connect + GET /google/callback
app/routers/cron.py                            [EDIT] POST /cron/review-responses
app/main.py                                    [EDIT] regista routers
apps/web/src/app/dashboard/reviews/            [NOVO] página Next.js
```

## 6. Backend — fluxo
- **Cron** `POST /cron/review-responses` (X-Cron-Token): por tenant com ligação
  → `google_client.list_new_reviews(conn)` → para cada `google_review_id` ainda
  não em `reviews` → `anthropic_client.generate_text(...)` gera `ai_draft` →
  insere `status=pending`. Idempotente (UNIQUE tenant+google_review_id).
- **Endpoints** (auth tenant via `get_current_tenant_id`):
  - `GET /v1/reviews?status=pending` → lista (rating, autor, comment, ai_draft, reply_text, status).
  - `PUT /v1/reviews/{id}/reply` `{reply_text}` → guarda edição do dono.
  - `POST /v1/reviews/{id}/publish` → usa `reply_text` (ou `ai_draft` se vazio),
    chama `google_client.publish_reply` (no-op sem API) → `status=published`,
    `published_at`. Falha de API → `status=failed` + erro.
  - `POST /v1/reviews/{id}/dismiss` → `status=dismissed`.
  - Todos verificam que a review pertence ao tenant (404 caso contrário).

## 7. Geração com Claude (Sonnet 4.6)
`anthropic_client.generate_text(system, user_text) -> str` — chamada simples,
sem tools. System prompt: responde como o dono do negócio `{name}` (`{type}`),
curto, caloroso, no **idioma da review**; agradece elogios; em reviews
negativas, empatia + convite a resolver offline, **sem admitir culpa nem
detalhes**; nunca inventa factos. No-op sem chave (caller trata).

## 8. Frontend — `/dashboard/reviews`
Página Next.js (padrão do dashboard existente, shadcn/ui): badge de ligação
Google em Settings (Connect Google); lista de reviews `pending` (estrelas,
autor, texto, data), textarea com o `ai_draft` editável, botões **Publicar** e
**Descartar**; reviews 1-2★ destacadas visualmente. Consome os endpoints do §6
com o token Supabase (mesmo padrão das outras páginas do dashboard).

## 9. Build-to-activate
Sem `GOOGLE_CLIENT_ID/SECRET`: `google_client.is_configured()=False`,
`list_new_reviews→[]`, `publish_reply→no-op log`. Cron corre limpo; geração e
dashboard testam-se com dados de teste. Ativação: env vars + cada tenant liga a
conta via OAuth → funciona sem mudar código.

## 10. Testes
- `review_response_service`: dedupe (não regenera review já existente), gera
  draft só para novas, no-op sem ligação, isolamento de erro por review.
- `reviews` endpoints: editar/publicar/descartar; scope de tenant (404 cross-tenant);
  publish usa reply_text>ai_draft; falha de API → failed.
- `google_client`: no-op sem creds; parsing de reviews; construção do consent URL.
- `anthropic_client.generate_text`: stub do SDK; no-op sem chave.
- OAuth callback: troca de token (stub) + upsert da ligação; `state` inválido → 400.

## 11. Fora de escopo (→ Fase B / Sprint 6)
- Autopost 4-5★.
- Push de draft + alertas 1-2★ via WhatsApp (reusa Feature 1).
- TripAdvisor / análise de padrões (Sprint 6).
- Encriptação do refresh token (recomendada; decisão antes de ligar contas reais).
