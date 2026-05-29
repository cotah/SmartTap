# Feature 1 — Bot do dono · Fase B (ações com confirmação) · Spec

**Data:** 2026-05-29
**Sprint:** 5 — Feature 1, Fase B
**Estado:** Aprovado para implementação
**Specs base:** `2026-05-29-feature1-bot-phase-a-design.md`

---

## 1. Objetivo
O bot passa a **agir**, não só consultar. Três ações (decisão aprovada):
- **Com confirmação obrigatória** (afetam clientes/dados): `send_reactivation`,
  `create_double_stamp`.
- **Direta** (owner-facing, baixo risco): `send_monthly_report` (PDF via WhatsApp).

## 2. Fluxo de confirmação (peça nova)
As tools de escrita confirmáveis **não executam** — preparam a ação (validam,
calculam o resumo) e **registam uma pending action** (TTL 5 min) no
`whatsapp_links`; o bot pede confirmação. A mensagem seguinte:
- `SIM`/`YES`/`CONFIRMO`/`OK`/`PODE` → executa → limpa → responde resultado.
- `NÃO`/`NO`/`CANCELA`/`PARA` → limpa → "cancelado".
- outra coisa → limpa a pending e trata como novo pedido (vai ao Claude).

Verdict por **keyword (PT+EN)**, não por AI. Confirmação tem prioridade no topo
do fluxo de número verificado, antes de chamar o Claude.

## 3. Migration 010
```sql
ALTER TABLE whatsapp_links
    ADD COLUMN IF NOT EXISTS pending_action JSONB,
    ADD COLUMN IF NOT EXISTS pending_action_expires_at TIMESTAMPTZ;
```
`pending_action` = `{tool, args..., summary}`.

## 4. Arquitetura e ficheiros
```
migrations/010_whatsapp_pending_actions.sql   [NOVO]
app/db/whatsapp.py                             [EDIT] set_pending_action / clear_pending_action
app/services/reactivation_service.py           [EDIT] run_for_tenant(tenant_id)
app/services/whatsapp_client.py                [EDIT] send_document (Meta media upload + send)
app/services/bot_actions.py                    [NOVO] WRITE_TOOLS + handle_write_tool + execute_action
app/services/whatsapp_bot_service.py           [EDIT] confirmação + dispatch routing + system prompt
```

## 5. Tools de escrita (schemas para o Claude)
| Tool | Input | Confirmação | Mapeia para |
|---|---|---|---|
| `send_reactivation` | — | sim | `reactivation_service.run_for_tenant` |
| `create_double_stamp` | `name?`, `starts_at` (ISO), `ends_at` (ISO), `multiplier?`=2 | sim | `campaign_service.create_double_stamp(status="active")` |
| `send_monthly_report` | `month?`, `year?` | não (direto) | `monthly_report_service.compute` + `pdf_renderer` + `whatsapp_client.send_document` |

- Claude infere datas de "este fim de semana" — a **data de hoje vai no system
  prompt**. O resumo de confirmação mostra as datas/multiplicador parseados.
- `send_monthly_report` sem mês → mês completo anterior (`resolve_previous_complete_month`).

## 6. Gate de trial
Ações confirmáveis respeitam o mesmo gate das mutações do dashboard:
`trial_service.compute_trial_status(tenant)` ∈ {expired, inactive} → bloqueia
(o bot diz que precisa de subscrição ativa, não regista pending).
`send_monthly_report` é owner-facing → sem gate.

## 7. Execução das ações
- **reactivation:** `run_for_tenant` reusa `_process_tenant` (mark-before-send,
  cooldown 90d, GDPR em SQL). Devolve nº de envios.
- **double_stamp:** parseia ISO → datetimes, cria `status="active"`. Conflito
  (já existe uma ativa) → mensagem amigável, não crash.
- **monthly_report:** gera PDF on-demand e envia via `send_document`
  (no-op sem credenciais Meta → mensagem honesta).

## 8. whatsapp_client.send_document
Meta media: upload (`POST /{phone_number_id}/media`, multipart) → media id →
envia mensagem `type=document`. No-op sem credenciais (dev/CI).

## 9. System prompt (atualização)
Passa a incluir a data de hoje + as ações disponíveis + a regra de confirmação
(o da Fase A dizia "só consultas").

## 10. Testes
- Confirmação: SIM executa / NÃO cancela / TTL expirado não executa / texto
  aleatório limpa e segue para o Claude.
- `handle_write_tool`: regista pending com resumo; gate de trial bloqueia
  expired/inactive; `send_monthly_report` executa direto.
- `execute_action`: mapeia tool→serviço; conflito de campanha → mensagem.
- `reactivation_service.run_for_tenant` (stub db/email).
- `whatsapp_client.send_document` no-op sem creds.

## 11. Fora de escopo (futuro)
- Push proativo fora da janela 24h (alertas de review negativa) → template Meta.
- Outras campanhas além de double-stamp.
