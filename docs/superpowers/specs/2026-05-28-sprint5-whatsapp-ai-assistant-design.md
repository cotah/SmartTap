# Sprint 5 — WhatsApp AI Assistant · Documento guarda-chuva

**Data:** 2026-05-28
**Estado:** Em curso — Feature 2 em implementação
**Autor:** Henrique + Claude

> Este é o documento de visão do Sprint 5. Cada feature tem o seu próprio
> spec detalhado + plano de implementação. Aqui fica o contexto partilhado,
> a ordem, os pré-requisitos e as decisões transversais.

---

## 1. Visão

Dar ao SmartTap um assistente conversacional e proativo construído sobre
WhatsApp (Twilio) + Claude. Três features integradas:

1. **Feature 2 — Review Nudge (outbound):** cliente que tapou mas não deixou
   review recebe um lembrete amigável. *(A mais simples — começamos aqui.)*
2. **Feature 1 — Bot do dono (bidirecional):** o dono consulta o negócio por
   WhatsApp em linguagem natural ("Quantos clientes hoje?", "Quem não voltou?",
   "Manda o relatório") e dispara ações. Expandido para um **assistente
   completo de conhecimento do negócio** (ver secção 4).
3. **Feature 3 — Resposta automática a Google Reviews:** monitoriza reviews
   novas, gera resposta humanizada com Claude, dono aprova ou publica.

A ordem de construção (Feature 2 → 1 → 3) segue complexidade crescente e
dependências de infra (aprovação Meta, OAuth Google Business).

---

## 2. Decisões transversais (fixas para o Sprint 5)

| Decisão | Escolha | Porquê |
|---|---|---|
| Modelo de AI | **`claude-sonnet-4-6`** em todas as features de AI | Economia + qualidade suficiente para análise NL e respostas a reviews. |
| Provider WhatsApp | **Twilio** | Já é a stack escolhida (CLAUDE.md). |
| Ambiente de dev | **Twilio Sandbox** | Aprovação Meta ainda pendente. Trocar o número/sender em prod **sem mudar código** (só env vars). |
| Canal da Feature 2 | **Email agora, WhatsApp após aprovação Meta** | WhatsApp business-initiated exige template pré-aprovado; o Sandbox não entrega a clientes reais. Email faz ship hoje, sem bloquear na Meta. O passo de envio fica isolado para o WhatsApp ser aditivo. |
| Auth do bot (Feature 1) | **OTP na 1ª mensagem** + mapeamento phone→tenant | O dono prova posse do número antes de ver dados. |

### Restrição WhatsApp que moldou o Sprint (importante)

Mensagens **iniciadas pelo negócio** no WhatsApp (ex.: o nudge da Feature 2,
ou o bot a enviar um alerta proativo) **exigem um template pré-aprovado** pela
Meta — não se pode enviar texto livre fora da janela de 24h iniciada pelo
cliente. Consequências de design:

- **Feature 2:** começa em **email** (texto livre, sem aprovação). Quando o
  WhatsApp for aprovado, adiciona-se um template fixo (sem AI — texto AI
  quebraria as regras do template).
- **Feature 1:** o dono **inicia** a conversa → abre janela de 24h → o bot
  pode responder com texto livre (gerado por Claude) dentro dessa janela. Para
  alertas proativos (review negativa) fora da janela é preciso template.
- **Feature 3:** drafts vão para o dono via Feature 1 (dentro da janela) ou
  por outro canal; publicação é via Google Business API, não WhatsApp.

---

## 3. Pré-requisitos de infra (partilhados)

- [ ] Conta Twilio + Account SID + Auth Token (env: `TWILIO_ACCOUNT_SID`,
      `TWILIO_AUTH_TOKEN`).
- [ ] Twilio WhatsApp Sandbox configurado para dev; Sender de produção após
      aprovação Meta (env: `TWILIO_WHATSAPP_FROM`).
- [ ] `ANTHROPIC_API_KEY` (backend Railway) — partilhado pelas Features 1 e 3.
- [ ] Google Cloud project + OAuth consent + Google Business API (Feature 3).
- [ ] Tabela de mapeamento `phone → tenant` (migration na Feature 1).
- [ ] Scheduler já existe (`POST /cron/*` com `X-Cron-Token`) — reutilizado
      pela Feature 2 (novo endpoint `/cron/review-nudge`).

> **Nota:** a Feature 2 **não** precisa de Twilio nem Anthropic — só email
> (Resend, já configurado). Por isso pode fazer ship antes de toda a infra
> de AI/WhatsApp estar pronta.

---

## 4. Feature 1 — Bot do dono: assistente completo (escopo expandido)

O bot não é só "pergunta → resposta": é um assistente de conhecimento do
negócio. Capacidades-alvo (a detalhar no spec próprio da Feature 1):

### 4.1 Métricas de visitas
- Clientes hoje / esta semana / este mês
- Novos vs recorrentes
- Horário e dia de pico (em hora local de Dublin)
- Média de visitas por cliente

### 4.2 Segmentação automática
- Clientes fiéis (top 10 por visitas)
- Clientes em risco (sem voltar há 30+ dias)
- Clientes com reward disponível não resgatado
- Clientes novos (1ª visita)

### 4.3 Performance de reviews
- Taxa de conversão tap → review
- Reviews esta semana
- Evolução do rating no Google

### 4.4 Relatórios em linguagem natural
- "Como estão os clientes esta semana?"
- "Quem são os meus melhores clientes?"
- "Quando é mais movimentado?"
- "Quem não voltou?"
- "Manda-me um resumo do mês" (anexa o PDF mensal já existente via Twilio media)

### 4.5 Ações via bot
- "Manda email de reactivação para clientes inativos" (dispara o
  `reactivation_service` existente)
- "Cria campanha double stamp para este fim de semana" (usa `campaign_service`)
- "Mostra clientes com reward disponível" (usa `segment_service`)

### 4.6 Arquitetura pretendida (resumo — detalhe no spec da Feature 1)
- Claude (Sonnet 4.6) com **tool-use**: as ferramentas mapeiam para as APIs
  internas já existentes (`dashboard_service`, `customer_service`,
  `segment_service`, `monthly_report_service`, `campaign_service`,
  `reactivation_service`). Claude escolhe a tool, o backend executa **com
  escopo do tenant autenticado**, Claude redige a resposta em PT/EN.
- **Nunca** Claude executa SQL livre nem ações sem confirmação para
  operações destrutivas/outbound (ex.: confirmar antes de disparar emails).
- Auth: OTP na 1ª mensagem, mapeamento `phone → tenant_id`, rate-limit.

> Toda a transformação de dados → linguagem natural usa **Claude Sonnet 4.6**.

### 4.7 Decisões aprovadas (2026-05-29)
- **Auth (OTP):** **WhatsApp-first + OTP por email.** O dono manda mensagem, o
  bot pede o email da conta, envia um código 6 dígitos por **email (Resend, já
  configurado)**, o dono responde o código no WhatsApp → liga `phone → tenant_id`.
  Resposta anti-enumeration. (Migration nova de auth.)
- **Faseamento:** **Fase A = read-only** (auth/OTP + webhook Twilio + Claude
  tool-use + ferramentas de consulta); **Fase B = ações** (reactivação,
  campanhas, resumo PDF) com **confirmação obrigatória** antes de executar.
- **Limites de escopo da Fase A:**
  1. "Evolução do rating Google" precisa da Google Business API → fica para
     **depois da Feature 3**. Na Fase A, performance de reviews = conversão
     tap→review + contagem, a partir dos nossos dados de tap.
  2. Ações ficam na Fase B (com confirmação).

---

## 5. Ordem e specs

| Ordem | Feature | Spec | Estado |
|---|---|---|---|
| 1 | Feature 2 — Review Nudge (email) | `2026-05-28-feature2-review-nudge-design.md` | ✅ Deployed (prod) |
| 2 | Feature 1 — Bot do dono · **Fase A (read-only)** | `2026-05-29-feature1-bot-phase-a-design.md` | Implementação |
| 2b | Feature 1 — Bot do dono · Fase B (ações) | _a criar_ | Pendente |
| 3 | Feature 3 — Resposta a reviews | _a criar_ | Pendente |

Sprints adjacentes que reutilizam esta infra (ver CLAUDE.md): **5.6**
(identificação por OTP via SMS — reusa conta Twilio), **6** (Review
Intelligence — reusa Google Business API + Claude).

---

## 6. Princípios de implementação (todo o Sprint 5)

- Reaproveitar os padrões existentes: `routers → services → db → schemas`,
  cron via `X-Cron-Token`, "mark-before-send", filtros GDPR em SQL.
- Clientes externos (Twilio, Anthropic) seguem o molde do `resend_client`:
  `is_configured()` → no-op limpo em dev/CI sem chave; nunca crashar o caller.
- Outbound só com `gdpr_consent = true`. Custo de AI/mensagens controlado por
  rate-limit + cooldown.
- Cada feature entrega com testes que espelham `tests/test_*_service.py`.
