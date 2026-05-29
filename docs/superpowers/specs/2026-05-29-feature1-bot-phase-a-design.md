# Feature 1 — Bot bidirecional do dono · Fase A (read-only) · Spec

**Data:** 2026-05-29
**Sprint:** 5 (WhatsApp AI Assistant) — Feature 1, Fase A
**Estado:** Aprovado para implementação
**Doc guarda-chuva:** `2026-05-28-sprint5-whatsapp-ai-assistant-design.md`

---

## 1. Objetivo

O dono conversa com o negócio por WhatsApp em linguagem natural e recebe
respostas com dados reais — **só consulta** (a Fase A não altera nada). Ex.:
*"Quantos clientes esta semana?"*, *"Quem não voltou?"*, *"Quando é mais
movimentado?"*, *"Quem são os meus melhores clientes?"*.

A AI (Claude **Sonnet 4.6**) traduz a pergunta → escolhe ferramentas read-only
→ o backend executa **com escopo do `tenant_id` autenticado** → Claude redige a
resposta em linguagem natural, espelhando o idioma do dono (PT/EN).

---

## 2. Decisões (do guarda-chuva §4.7)

- **Transporte (revisto 2026-05-29):** **Meta WhatsApp Business Cloud API
  direto** (REST via Graph API), **sem Twilio** — já temos conta Meta Business
  + número registado. A auth do dono (OTP por email) e o resto da arquitetura
  não mudam; muda só o cliente de transporte e o webhook.
- **Auth:** WhatsApp-first + OTP por **email** (Resend).
- **Read-only**: ações (reactivação, campanhas, PDF) ficam para a Fase B com
  confirmação obrigatória.
- **Rating Google** fica para a Feature 3. Performance de reviews na Fase A =
  conversão tap→review + contagens, a partir dos nossos dados de tap.

---

## 3. Fluxo de autenticação (OTP por email)

Máquina de estados por número de telefone (`whatsapp_links.state`):

```
(número desconhecido manda 1ª mensagem)
   → estado AWAITING_EMAIL
   bot: "Olá! Para ligar a tua conta SmartTap, responde com o email da conta."

(dono responde texto que parece email)
   → backend: users.get_user_id_by_email(email) → tenant_members → tenant_id
   → SEMPRE responde "Se essa conta existir, enviei um código de 6 dígitos para o email."
     (anti-enumeration — não revela se o email é cliente nosso)
   → se existir: gera OTP 6 dígitos, guarda hash em whatsapp_otp_codes
     (TTL 10min, attempts=0), envia por email (Resend), estado AWAITING_CODE

(dono responde o código)
   → verifica constant-time vs hash, TTL, attempts<5
   → sucesso: liga phone→tenant_id, estado VERIFIED, verified_at=now
     bot: "Conta ligada ✅. Pergunta-me o que quiseres sobre o teu negócio."
   → falha: attempts++; após 5 erradas, bloqueia 1h (lockout_until)

(número VERIFIED manda mensagem)
   → resolve tenant_id, entra no loop de tool-use do Claude
```

**Regras de segurança:**
- Resposta de "envia email" é sempre idêntica exista ou não a conta.
- OTP: 6 dígitos, TTL 10 min, máx. 5 tentativas, depois lockout 1h.
- Rate-limit de pedidos de OTP: máx. 3 emails por phone por hora.
- O código é guardado **só como hash** (sha256), nunca em claro.

---

## 4. Migration 008 — `whatsapp_links` + `whatsapp_otp_codes`

```sql
-- Liga um número de WhatsApp a um tenant + estado da conversa de auth.
CREATE TABLE whatsapp_links (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone         TEXT NOT NULL UNIQUE,          -- E.164, ex. +3538...
    tenant_id     UUID REFERENCES tenants(id) ON DELETE CASCADE,  -- null até verificar
    state         TEXT NOT NULL DEFAULT 'awaiting_email',
                  -- awaiting_email | awaiting_code | verified
    pending_email TEXT,                          -- email em verificação
    verified_at   TIMESTAMPTZ,
    lockout_until TIMESTAMPTZ,                   -- bloqueio anti-abuso
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TRIGGER trg_whatsapp_links_updated BEFORE UPDATE ON whatsapp_links
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TABLE whatsapp_otp_codes (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone       TEXT NOT NULL,
    email       TEXT NOT NULL,
    tenant_id   UUID REFERENCES tenants(id) ON DELETE CASCADE,
    code_hash   TEXT NOT NULL,                   -- sha256(code)
    expires_at  TIMESTAMPTZ NOT NULL,
    attempts    INT NOT NULL DEFAULT 0,
    consumed_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_whatsapp_otp_phone ON whatsapp_otp_codes(phone, created_at DESC);

-- RLS: backend usa service_role (bypassa), mas mantemos coerência multi-tenant.
ALTER TABLE whatsapp_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE whatsapp_otp_codes ENABLE ROW LEVEL SECURITY;
```

---

## 5. Arquitetura e ficheiros

```
migrations/008_whatsapp_bot.sql              [NOVO]
config.py                                    [EDIT] env vars (Twilio, Anthropic)
app/db/whatsapp.py                           [NOVO] links + otp codes
app/db/users.py                              [EDIT] get_user_id_by_email
app/services/whatsapp_client.py             [NOVO] Meta Cloud API: is_configured() + send_text() + validate_signature()
app/services/anthropic_client.py             [NOVO] cliente Sonnet 4.6 + loop tool-use
app/services/whatsapp_bot_service.py         [NOVO] auth/OTP + dispatch de tools + orquestração
app/services/bot_tools.py                    [NOVO] as 4 tools read-only (definição + execução por tenant)
app/emails/templates.py                      [EDIT] whatsapp_otp_email
app/services/email_service.py                [EDIT] send_whatsapp_otp
app/routers/webhooks.py                      [EDIT] GET + POST /webhooks/whatsapp (verify + assinatura)
```

### Cliente externo (molde `resend_client`) — Meta WhatsApp Cloud API
- `whatsapp_client.is_configured()` → False sem `WHATSAPP_ACCESS_TOKEN`/`WHATSAPP_PHONE_NUMBER_ID`; no-op limpo em dev.
- `whatsapp_client.send_text(to, body)` → `POST https://graph.facebook.com/{version}/{phone_number_id}/messages` com `Authorization: Bearer <token>` e body `{"messaging_product":"whatsapp","to":<wa_id>,"type":"text","text":{"body":...}}` (via `httpx`, já dependência). Texto livre é permitido dentro da janela de 24h (o dono iniciou).
- `whatsapp_client.validate_signature(raw_body, signature)` → HMAC-SHA256 do corpo **cru** com `WHATSAPP_APP_SECRET`, comparado com `X-Hub-Signature-256: sha256=...`.
- `anthropic_client.is_configured()` → False sem `ANTHROPIC_API_KEY`; `run_conversation(system, user_text, tools, dispatch)` corre o loop tool-use.

### Webhook Meta (2 métodos no mesmo path `/v1/webhooks/whatsapp`)
- **GET** — handshake de verificação da Meta: recebe `hub.mode`, `hub.verify_token`, `hub.challenge`. Se `verify_token == WHATSAPP_VERIFY_TOKEN`, devolve o `challenge` em texto puro (200); senão 403.
- **POST** — mensagens inbound (JSON aninhado `entry[].changes[].value.messages[]`). Valida `X-Hub-Signature-256` sobre o corpo cru; extrai `from` (wa_id) + `text.body`; ignora callbacks de status (`value.statuses`, sem `messages`) devolvendo 200; despacha ao bot service; resposta enviada via `whatsapp_client.send_text`; devolve 200.

---

## 6. Ferramentas read-only (tool-use)

Claude recebe **só** o `tenant_id` autenticado (injetado pelo backend, nunca
escolhido por Claude) e estas tools. Cada uma executa com escopo do tenant.

| Tool | Input | Mapeia para | Devolve |
|---|---|---|---|
| `get_overview` | — | `dashboard_service.overview(tenant_id)` | total clientes, taps 7d, reviews 30d, em risco, stamps ativos |
| `query_customers` | `filter: all\|loyal\|at_risk\|has_reward\|new`, `limit≤20` | `customers.list_for_tenant` (filter+sort) | lista resumida (nome, visitas, stamps, última visita) |
| `get_peak_times` | `days: 7\|30\|90` | `taps.list_in_range` + grouping local Dublin | dia e hora de pico |
| `get_review_performance` | `days: 7\|30\|90` | counts de taps `review_clicked` / total | conversão tap→review + nº reviews |

`query_customers` mapeia o filtro semântico → (`FilterMode`,`SortMode`):
- `loyal` → (all, visits)  · `at_risk` → (at_risk, recent) · `has_reward` →
  (has_reward, stamps) · `new` → (all, recent) · `all` → (all, recent).

**Limites:** read-only; nenhuma tool escreve. `limit` sempre ≤20 (resposta de
WhatsApp é curta). Nenhuma tool recebe `tenant_id` do modelo.

---

## 7. Loop de tool-use (anthropic_client)

```
messages = [{role:user, content: texto do dono}]
loop (máx N=4 iterações):
    resp = claude.messages.create(model=sonnet-4-6, system=..., tools=..., messages)
    se resp.stop_reason == "tool_use":
        para cada tool_use block: result = dispatch(name, input, tenant_id)
        messages += [assistant(resp), user(tool_result blocks)]
        continua
    senão: devolve resp.text  (resposta final em NL)
```
- `dispatch` é fornecido pelo `whatsapp_bot_service`, injeta `tenant_id`.
- Teto de iterações evita loops; teto diário de chamadas por tenant (custo).
- System prompt: nome do negócio, business_type, "responde curto, no idioma do
  dono, só com dados das tools; se não souberes, diz que não tens esse dado".

---

## 8. Config — novas env vars

```
WHATSAPP_ACCESS_TOKEN    (default "")   # token do system user / app (Bearer)
WHATSAPP_PHONE_NUMBER_ID (default "")   # id do número na Cloud API
WHATSAPP_APP_SECRET      (default "")   # valida X-Hub-Signature-256
WHATSAPP_VERIFY_TOKEN    (default "")   # segredo nosso p/ handshake GET
WHATSAPP_API_VERSION     (default "v21.0")
ANTHROPIC_API_KEY        (default "")
ANTHROPIC_MODEL          (default "claude-sonnet-4-6")
```
Já temos número Meta registado — sem Sandbox. Empty values → cliente no-op
(dev/CI seguros).

---

## 9. Segurança

- **Assinatura Meta:** valida `X-Hub-Signature-256` (HMAC-SHA256 do corpo cru
  com o App Secret). 403 se inválida. Mesmo espírito da validação da assinatura
  Stripe já existente. O handshake GET valida `WHATSAPP_VERIFY_TOKEN`.
- **Auth do dono:** OTP por email (§3). Só números VERIFIED chegam ao Claude.
- **Isolamento multi-tenant:** `tenant_id` resolvido no backend a partir do
  `whatsapp_links` verificado; nunca vem do modelo nem da mensagem.
- **Anti-enumeration** no pedido de email; OTP só hash; rate-limit + lockout.
- **Clientes externos** no-op sem chave → dev/CI seguros.

---

## 10. Testes

- **bot_tools:** cada tool devolve o esperado para um tenant (db stubbed);
  `tenant_id` é sempre o injetado; `limit` clamped a 20.
- **whatsapp_bot_service (auth):** número novo → AWAITING_EMAIL; email válido →
  OTP enviado + AWAITING_CODE; email inválido → mesma resposta (anti-enum);
  código certo → VERIFIED + link; código errado → attempts++; 5 erradas →
  lockout; rate-limit de OTP.
- **whatsapp_bot_service (verified):** mensagem de número verificado → chama o
  loop Claude (anthropic stubbed) e envia resposta via Twilio (stubbed).
- **anthropic_client:** loop de tool-use com fake client (stop_reason tool_use
  → executa dispatch → final text); teto de iterações.
- **whatsapp_client:** `validate_signature` aceita assinatura HMAC-SHA256 válida
  e rejeita inválida/ausente; `send_text` no-op sem config; normalização do `to`.
- **webhook:** GET com verify_token certo → devolve challenge; errado → 403.
  POST com assinatura inválida → 403; válida → 200 e despacha (service stubbed);
  parsing do JSON aninhado da Meta; callbacks de status (sem `messages`) → 200
  sem despacho.
- **template:** `whatsapp_otp_email` contém o código e sem emoji/exclamação no
  assunto.

Tudo stubando Meta/Anthropic/Supabase — sem chamadas externas reais.

---

## 11. Fora de escopo (Fase A)

- **Ações** (reactivação, campanhas, resumo PDF) → Fase B com confirmação.
- **Rating Google** → depois da Feature 3.
- **Histórico de conversa multi-turno** persistido entre mensagens (Fase A
  trata cada mensagem do dono como um pedido independente; o loop tool-use é
  multi-turno só dentro de uma mensagem). Memória entre mensagens → futuro.
- **Templates WhatsApp proativos** (mensagens fora da janela 24h) → futuro.
