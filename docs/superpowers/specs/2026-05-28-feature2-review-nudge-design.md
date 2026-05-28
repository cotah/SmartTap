# Feature 2 — Review Nudge (email) · Spec

**Data:** 2026-05-28
**Sprint:** 5 (WhatsApp AI Assistant) — primeira feature a entregar
**Estado:** Aprovado para implementação
**Doc guarda-chuva:** `2026-05-28-sprint5-whatsapp-ai-assistant-design.md`

---

## 1. Objetivo

Um cliente que tapou e ganhou um stamp mas **não clicou no botão de review**
recebe, passadas 24h, um email amigável a pedir a review do negócio. Aumenta a
conversão tap → review sem depender de aprovação Meta nem de AI.

Espelha o `reactivation_service` existente, com o **passo de envio isolado**
para que adicionar o canal WhatsApp mais tarde seja aditivo (não reescrita).

---

## 2. Diferença face ao `reactivation_service` (não confundir)

| | `reactivation_service` (existe) | **Feature 2 — review nudge** (nova) |
|---|---|---|
| Trigger | Cliente inativo há **30+ dias** | Cliente tapou há **24h–7 dias** e **não** clicou review |
| Mensagem | "Volta cá" | "Deixa-nos uma review" |
| Cooldown | 90 dias | **30 dias** |
| CTA | `/m/<token>` (mostrar stamps) | `google_review_url` do tenant |
| Marker | `last_reactivation_sent_at` | `last_review_nudge_sent_at` (novo) |

Ambos partilham: cron diário, filtro `gdpr_consent=true` + email em SQL,
"mark-before-send", opt-out via `magic_link_token` (`/u/<token>`) — revogar
consent pára os dois tipos de email.

---

## 3. Política (constantes fixas no v1)

```
NUDGE_AFTER_HOURS = 24    # não incomodar antes de 24h
LOOKBACK_DAYS     = 7     # só taps dos últimos 7 dias (evita spammar histórico)
COOLDOWN_DAYS     = 30    # máx. 1 nudge/cliente por mês
PER_TENANT_LIMIT  = 500   # trava anti-monopólio do cron
```

Per-tenant config (ligar/desligar, mudar o atraso) fica para uma iteração
futura — igual à decisão tomada no S4-W2 para o reactivation.

---

## 4. Critérios de elegibilidade

Um cliente recebe o nudge se **todos** forem verdade:

1. Tenant **ativo** (`is_active=true`) e com **`google_review_url`** preenchido.
2. Cliente com **`email`** não-nulo e **`gdpr_consent = true`**.
3. Cliente com **`magic_link_token`** (necessário para o link de opt-out;
   sem token, skip com erro registado — igual ao reactivation).
4. O **tap mais recente que ganhou stamp** (`action_taken = 'stamp_earned'`)
   está na janela `[now - 7d, now - 24h]`.
5. O cliente **não tem** nenhum tap `action_taken = 'review_clicked'` com
   `created_at >= ` o desse stamp mais recente.
6. `last_review_nudge_sent_at` é **null** ou **< now - 30d**.

> **Limitação conhecida (aceite):** só sabemos que o cliente não *clicou* no
> botão de review (`review_clicked`), não se ele realmente publicou no Google.
> Usamos o clique como proxy. Documentado, não bloqueia.

**Semântica "tap mais recente que ganhou stamp":** se o cliente voltou a tapar
há < 24h (novo stamp), o stamp mais recente cai fora da janela → **não** é
incomodado (acabou de visitar). Se o stamp mais recente é de há 2 dias e não
houve clique de review desde então → qualifica.

---

## 5. Arquitetura e ficheiros

```
migrations/007_customers_review_nudge.sql   [NOVO]
  └─ customers.last_review_nudge_sent_at TIMESTAMPTZ + índice composto

app/db/tenants.py                            [EDIT]
  └─ list_active_for_cron: adicionar google_review_url ao SELECT

app/db/taps.py                               [EDIT]
  └─ list_customer_review_signals(tenant_id, *, since)
     → rows {customer_id, action_taken, created_at} da janela de lookback

app/db/customers.py                          [EDIT]
  ├─ find_review_nudge_eligible(tenant_id, customer_ids, cooldown_cutoff)
  │    → filtra em SQL: gdpr_consent + email + cooldown; SELECT id,name,email,
  │      magic_link_token
  └─ mark_review_nudge_sent(customer_id, sent_at)

app/emails/templates.py                      [EDIT]
  └─ review_nudge_email(tenant, customer, review_url, opt_out_url) -> RenderedEmail

app/services/email_service.py                [EDIT]
  └─ send_review_nudge(tenant, customer, review_url, opt_out_url) -> bool

app/services/review_nudge_service.py         [NOVO]
  └─ run_daily(now=None) -> ReviewNudgeRunResult  (orquestração + política)

app/routers/cron.py                          [EDIT]
  └─ POST /cron/review-nudge  (auth X-Cron-Token, igual aos outros)
```

### Fluxo de deteção (no service, Python — abordagem A aprovada)

```
para cada tenant ativo com google_review_url:
    signals = taps.list_customer_review_signals(tenant_id, since=now-7d)
    agrupar signals por customer_id:
        last_stamp_at   = max(created_at where action='stamp_earned')
        last_review_at  = max(created_at where action='review_clicked')
    candidatos = customers cujo:
        last_stamp_at ∈ [now-7d, now-24h]  E
        (last_review_at é None  OU  last_review_at < last_stamp_at)
    eligible = customers.find_review_nudge_eligible(
        tenant_id, candidatos.ids, cooldown_cutoff=now-30d)   # filtro GDPR em SQL
    para cada eligible (até PER_TENANT_LIMIT):
        se não tem magic_link_token: registar erro, skip
        customers.mark_review_nudge_sent(id, now)   # MARK-BEFORE-SEND
        email_service.send_review_nudge(tenant, customer, review_url, opt_out_url)
```

Volumes minúsculos (~250 taps/mês/tenant) → agrupar em Python é simples e
testável, igual ao `monthly_report_service`. PostgREST `NOT EXISTS` evitado.

### Link de review (v1)

Usar `tenant.google_review_url` **verbatim**. Não anexar UTM: URLs de review do
Google (`g.page/r/...`, `writereview?placeid=...`) podem partir com query
extra e o Google ignora UTMs na maioria dos casos. Tracking de conversão
faz-se pelo lado do tap (`review_clicked`), não pela URL.

---

## 6. Migration 007 (esboço)

```sql
-- SmartTap S5 Feature 2: review-nudge email tracking
-- Apply AFTER 006_customer_segments.sql

ALTER TABLE customers
    ADD COLUMN IF NOT EXISTS last_review_nudge_sent_at TIMESTAMPTZ;

-- Cron filtra candidatos por id (IN) + gdpr/email; este índice parcial cobre
-- a checagem de cooldown sem varrer a tabela toda.
CREATE INDEX IF NOT EXISTS idx_customers_tenant_review_nudge
    ON customers(tenant_id, last_review_nudge_sent_at)
    WHERE email IS NOT NULL AND gdpr_consent = TRUE;
```

---

## 7. Segurança e GDPR

- **Mark-before-send:** escreve `last_review_nudge_sent_at` antes do envio. Um
  crash a meio faz o cliente perder um ciclo — nunca recebe dois.
- **Filtros em SQL:** `find_review_nudge_eligible` nunca devolve cliente sem
  consent ou sem email — chamar `send` em massa é seguro por construção.
- **Opt-out:** reutiliza `/u/<magic_link_token>` (revoga `gdpr_consent`),
  parando reactivation **e** review-nudge.
- **Falha de envio:** contida pelo `email_service` (Resend down ≠ cron falha).
- **Cron auth:** `X-Cron-Token` constant-time, 503 se não configurado.

---

## 8. Métrica de conversão (v1 mínimo)

O endpoint devolve `{tenants_scanned, total_sent}` e loga por tenant (igual aos
outros crons). A conversão completa (cruzar quem recebeu nudge × clicou review
depois) fica como follow-up leve — **não** bloqueia o ship.

---

## 9. Testes (espelham `tests/test_reactivation_service.py`)

Stubam db + email (FakeTapsDB, FakeCustomersDB, FakeTenantsDB, captura de
`send_review_nudge`). Casos:

1. Cliente elegível → 1 envio + marker escrito ao `now` do cron.
2. Cliente que clicou review **depois** do stamp → **não** recebe.
3. Stamp < 24h (visitou agora) → **não** recebe.
4. Stamp > 7 dias → **não** recebe (fora do lookback).
5. Dentro do cooldown (`last_review_nudge_sent_at` recente) → **não** recebe.
6. Tenant sem `google_review_url` → tenant inteiro saltado.
7. Sem email / sem consent → filtrado em SQL (não devolvido).
8. Sem `magic_link_token` → skip com erro, **não** marca cooldown.
9. Exceção no envio de um cliente → isolada, restantes continuam, marker fica.
10. Idempotência: 2 runs no mesmo dia → 1 envio (cooldown).
11. URL de review e de opt-out construídas corretamente.
12. Sem tenants ativos → zero.

Mais: um teste de template (`review_nudge_email`) verifica que o assunto não
tem emojis/exclamação e que o `review_url`/`opt_out_url` aparecem no HTML.

---

## 10. Explicitamente fora de escopo

- WhatsApp (após aprovação Meta — passo de envio já isolado).
- AI / Sonnet (template fixo).
- Config por tenant.
- Dashboard de conversão (follow-up).
- UTM nas URLs de review.
