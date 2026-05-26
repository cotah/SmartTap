# SmartTap — Contexto Completo do Projeto

## O QUE É O SMARTTAP

Sistema all-in-one de reputação, fidelidade e relacionamento direto com clientes para pequenos negócios locais na Irlanda. Combina hardware físico impresso em 3D com plataforma SaaS multi-tenant.

**Tagline:** "Você já pagou para trazer esse cliente uma vez. O SmartTap faz ele voltar."
**Tagline produto:** "TAP. CONNECT. GROW."
**Domínio:** smarttap.ie
**Fundador:** Henrique — indie developer baseado em Dublin, Irlanda

---

## OS 3 PILARES

- **Tap & Review:** NFC/QR → Google Review em 1 clique, sem app
- **Tap & Return:** Stamps digitais sem app → recompensas por fidelidade
- **Tap & Connect:** Coleta contato GDPR-compliant → campanhas diretas

---

## HARDWARE FÍSICO

- Impressora 3D Creality Hi CFS multi-color em Dublin
- 400 NFC tags disponíveis imediatamente
- Custo de produção: ~€0,55 por unidade | Preço: €79-€249 setup
- **3 formatos:**
  - Counter Stand (balcão) — 80x80x60mm
  - Table Tent (mesa) — 90x60mm triangular
  - Wall Plaque (parede) — 120x80mm
- **10 cores PLA:** Preto, Branco, Cinza, Navy, Roxo, Vermelho, Amarelo, Stone Age, Real Green, Forest Green

---

## IDENTIDADE VISUAL (NÃO ALTERE SEM APROVAÇÃO)

- **Logo:** símbolo ST com ondas NFC — dourado/preto — fundo transparente
- **Cores:** Verde #1B4D3E | Âmbar/Dourado #E8A020 | Off-white #F7F5F0 | Preto #1A1A1A
- **Tipografia:** DM Serif Display (display) + DM Sans (body) + JetBrains Mono (code)

---

## STACK TÉCNICO (FIXO — NÃO TROCAR SEM JUSTIFICATIVA FORTE)

```
Arquitetura: Monorepo (Turborepo)

apps/web/      → Next.js 15 + Tailwind + shadcn/ui (PWA — lança agora)
apps/mobile/   → React Native + Expo (estrutura pronta, lança fase 2)
packages/core/ → lógica de negócio compartilhada (TypeScript)
packages/ui/   → componentes compartilhados
packages/api/  → cliente HTTP compartilhado

backend/       → Python + FastAPI

Database:    Supabase (PostgreSQL + RLS multi-tenant)
Auth:        Supabase Auth
Hosting:     Railway (backend) + Vercel (frontend)
Payments:    Stripe
Emails:      Resend
WhatsApp:    Twilio
Analytics:   PostHog
Errors:      Sentry
```

**Decisão arquitetural importante:** Monorepo com packages compartilhados garante migração web→mobile sem refactor. 80% do código será reaproveitado na fase 2.

---

## PRICING (v2 — aprovado Fase 3)

| Plano | Setup | Mensal | Anual (2 meses grátis) | Clientes |
|---|---|---|---|---|
| SmartReview | €49 | €29/mês | €290 | até 200 |
| SmartLoyalty | €79 | €59/mês | €590 | até 500 |
| SmartPro | €149 | €99/mês | €990 | ilimitado |
| SmartNetwork | €299 | €179/mês | €1.790 | multi-localização |

**Oferta Founding Member (primeiros 5 clientes):**
- Stand custom GRÁTIS + 60 dias grátis + €29/mês vitalício
- Em troca: depoimento em vídeo + 2 indicações nominais

**Oferta Early Adopter (clientes 6-20):**
- €49 setup + 30 dias grátis + €29/mês por 12 meses garantidos

**Meta de upsell:** 40% dos SmartReview migram para SmartLoyalty em 90 dias (chave da unit economics).

---

## MERCADO E ICP

**Foco primeiros 90 dias:** Barbearias Dublin
- 300+ prospects em Dublin
- Decisão rápida, dono presente, dor clara
- Ticket: €79 setup + €39/mês

**Hierarquia de ICPs (revisada Fase 1):**
1. Barbearias Dublin (primário — 300+ prospects)
2. Cafés especialidade / 3rd wave Dublin (independentes, não redes)
3. Pet Grooming Dublin (perfil similar a barbearia, frequência mensal)
4. Salões pequenos (1-2 cadeiras, dono presente)
5. Tattoo Studios pequenos (dono techy, adoram reviews)

Hostels e Clínicas Dentárias foram movidos para **Fase 3+** (loyalty irrelevante para turistas one-off; clínicas têm decisão lenta + compliance).

**Concorrentes principais:**
- SQUID Loyalty (dados deles, sem white-label)
- Stamp Me (app obrigatório)
- ReviewsCard (one-off, sem SaaS)

**Diferenciação:** único com hardware + reviews + loyalty + white-label + dados próprios + presença local Dublin

---

## DATABASE SCHEMA (MVP)

```sql
tenants (id, name, slug, subdomain, logo_url, primary_color, business_type,
         google_review_url, stamps_for_reward, reward_description,
         plan, stripe_customer_id, stripe_subscription_id, trial_ends_at, is_active)

nfc_tags (id, tenant_id, tag_uuid, format, color, location_name,
          active_campaign_id, is_active)

taps (id, tag_id, tenant_id, customer_id, device_type, interaction_type,
      action_taken, created_at)

customers (id, tenant_id, phone, email, name, birthday,
           gdpr_consent, gdpr_consent_at, total_visits, total_stamps,
           last_visit_at, created_at)

stamps (id, customer_id, tenant_id, tap_id, multiplier, created_at)

rewards (id, customer_id, tenant_id, stamps_used, validation_code,
         redeemed_at, expires_at, created_at)

campaigns (id, tenant_id, name, type, status, config jsonb,
           sent_count, created_at)
```

---

## ROADMAP COMPLETO

### FASE 0 — Validação (Semanas 1-3) 🎯 AGORA
**Objetivo:** Confirmar que pessoas pagam ANTES de construir

**Semana 1 (paralelo):**
- [ ] Imprimir 5 protótipos (3 formatos, 2 cores)
- [ ] Registrar smarttap.ie no Cloudflare + DNS
- [ ] Criar landing page simples (formulário de interesse)
- [ ] Demo digital FUNCIONAL — página /t/[uuid] com stamps animados + botão Google Review real (não pode ser estática)

**Semana 2:**
- [ ] Lista nominal de 32 prospects no Google Maps (5h em 2 sessões — Henrique)
- [ ] Treino do pitch (60s gravado e refinado 3 vezes)

**Semanas 2-3 (campo):**
- [ ] Visitar 32 negócios Dublin (4 visitas/dia × 8 dias) — barbearias prioritárias
- [ ] Captura: Voice Memos pós-visita + planilha Google Sheets
- [ ] **Meta:** 5 positivos + 3 compromissos de piloto
- [ ] **Oferta Founding Member:** stand grátis + 60 dias grátis + €29/mês vitalício

**Critério para avançar para Fase 1:** 3 negócios comprometidos como pilotos founding.

---

### FASE 1 — MVP (Semanas 3-8)
**Objetivo:** 10 clientes pagantes com produto funcional

**Sprint 0 — Setup (Semana 1)**
- [ ] Monorepo Turborepo criado
- [ ] Supabase project (prod + staging) com schema
- [ ] Railway + Vercel configurados
- [ ] Stripe test mode
- [ ] CI/CD GitHub Actions
- [ ] .env.example documentado

**Sprint 1 — NFC Core (Semanas 1-2)**
- [ ] POST /tap/{tag_uuid} — registra tap, retorna redirect
- [ ] Página mobile /t/[uuid] (Next.js, mobile-first)
- [ ] StampCard visual gamificado
- [ ] Botão Google Review com UTM tracking
- [ ] OptIn form GDPR-compliant
- [ ] Magic link para cliente recorrente

**Sprint 2 — Dashboard (Semanas 2-3)**
- [ ] Auth do negócio (email + Google OAuth)
- [ ] Dashboard: membros, visitas, stamps, reviews
- [ ] Lista de clientes com filtros
- [ ] Configuração de recompensa (X stamps = Y prêmio)
- [ ] Validação de recompensa (código 6 dígitos)

**Sprint 3 — Billing (Semanas 3-4)**
- [ ] Stripe Checkout (planos Review, Loyalty, Pro)
- [ ] Webhooks Stripe (ativa/desativa tenant)
- [ ] Trial 30 dias automático
- [ ] Onboarding wizard
- [ ] Emails transacionais (Resend)

**Meta Fase 1 (revisada Fase 3):** 8-15 clientes pagantes ao fim do mês 6 → ~€570 MRR + setup fees acumulados.

---

### FASE 2 — Produto Completo (Meses 2-4)
**Objetivo:** 50 clientes, produto completo, primeiros cases

**Sprint 4 — Campanhas (Semanas 4-6)**
- [ ] Double Stamp (janela de tempo)
- [ ] Reactivation (inativos há N dias)
- [ ] Relatório mensal PDF automático
- [ ] Segmentação de clientes

**Sprint 5 — WhatsApp + Reviews (Semanas 6-8)**
- [ ] WhatsApp Business API (Twilio)
- [ ] Google Business API (monitorar rating)
- [ ] Alerta nova review negativa
- [ ] Sugestão de resposta por IA

**Apps Mobile — Estrutura**
- [ ] React Native + Expo configurado
- [ ] Compartilhando packages/core e packages/ui
- [ ] Funcionalidade básica (tap, stamps, dashboard)

**Meta Fase 2 (revisada Fase 3):** 35-50 clientes ativos ao fim do mês 12 → ~€1.750 MRR (BASE) / €2.950 MRR (otimista).

---

### FASE 3 — Escala (Meses 4-12)
**Objetivo:** 200 clientes, expansão geográfica

- [ ] AI Helper (sugestões de campanha automáticas)
- [ ] Staff app (PWA para validação de stamps)
- [ ] Integração POS (Square, SumUp, Lightspeed)
- [ ] Partner program (agências revendem SmartTap)
- [ ] Expansão: Dublin → Cork → Galway
- [ ] White-label enterprise

**Meta Fase 3 (revisada Fase 3):** 100-180 clientes ativos ao fim do mês 24 → €5.200-8.500 MRR (BASE) / até €13k MRR (otimista, com network effect Dublin).

---

## MÉTRICAS DE SUCESSO (revisado Fase 3 — números defensáveis)

### Business — Cenário BASE
| Métrica | Mês 3 | Mês 6 | Mês 12 | Mês 24 |
|---|---|---|---|---|
| Clientes pagantes | 5 | 15 | 38 | 104 |
| MRR | €145 | €570 | €1.748 | €5.200 |
| ARR run-rate | €1.740 | €6.840 | €20.976 | €62.400 |
| Setup fees acum | €98 | €784 | €2.058 | €5.733 |
| Churn mensal | 0% (pilotos) | 0% | 6% | 5% |

### Cenário CONSERVADOR (50% do BASE) — fallback
- Mês 24: ~52 clientes, MRR ~€2.200, ARR ~€26k → negócio como side-project

### Cenário OTIMISTA (network effect Dublin + WoM forte)
- Mês 24: ~180-200 clientes, MRR ~€13.000, ARR ~€156k → momento de contratar SDR/CS

### Break-even
- **Operacional** (sem salário fundador): Mês 3
- **Com salário fundador €3k/mês:** Mês 21-22 (BASE)
- **Runway necessária:** ~€25k gap salarial em 12-18 meses → cobrir com Palmeiras Dublin + freelance parcial

### Produto (indicadores de saúde)
- Taps por stand por dia: **meta >5**
- Tap → Review: **meta >20%**
- Tap → Stamp: **meta >40%**
- Retorno em 30 dias: **meta >30%**

### North Star Metric
**Cliente com >50 membros cadastrados = produto funcionando**

---

## REGRAS DO PROJETO (SIGA SEMPRE)

1. **Stack é fixo** — não trocar tecnologias sem justificativa muito forte
2. **Identidade visual é sagrada** — não mudar cores, fontes, logo sem aprovação
3. **MVP é MVP** — não adicionar features não listadas sem aprovação
4. **Monorepo sempre** — todo código novo vai para o package correto
5. **RLS obrigatório** — todo acesso ao banco passa por Row Level Security
6. **GDPR por design** — todo dado de consumidor precisa de consent explícito
7. **Mobile-first** — toda interface começa pensando no celular
8. **Testes antes de código** — TDD para lógica de negócio crítica
9. **Sem segredos no código** — toda key vai para .env
10. **Documentar decisões** — toda decisão técnica importante vai para ADR

---

## ESTADO ATUAL DO PROJETO

**Data:** Maio 2026
**Fase atual:** 🟢 **PRODUÇÃO LIVE** — Sprint 4 completo, deploy em prod concluído. Aguardando primeiro pilot real.
**Próximo passo:** S5-W0 (NFC tag CRUD UI) — bloqueador identificado: sem UI de tags, fechar o primeiro cliente exige SQL manual.

**O que está LIVE em produção:**
- **Frontend:** https://smarttap.ie (Vercel, apex + www redirect)
- **Backend:** https://api.smarttap.ie (Railway, Dockerfile + uv + uvicorn)
- **DB:** Supabase prod `qmemsvkeiygdwxyzadrc` (eu-west-1) — 6 migrations aplicadas, RLS ativo em 10 tabelas
- **Stripe:** live mode com 8 price IDs (4 recurring + 4 setup) + webhook validado
- **Resend:** smarttap.ie verificado, emails entregando
- **Cron:** cron-job.org agendado (daily reactivation + monthly report dia 1)
- **Observabilidade:** Sentry (backend + web), Vercel Analytics
- **Runbook completo:** `DEPLOY.md` na raiz do repo

**Sprints completos:**
- Sprint 0 ✅ Setup monorepo + CI/CD
- Sprint 1 ✅ NFC tap loop + customer view + GDPR opt-in
- Sprint 2 ✅ Auth + dashboard + customers + reward config + settings + redeem + CSV export
- Sprint 3 ✅ Stripe (checkout + webhook + billing UI + trial enforcement + transactional emails)
- Sprint 4 ✅ Campaigns (double-stamp + reactivation + monthly PDF report + customer segmentation)

**O que NÃO foi exercitado em prod ainda (smoke tests deferidos):**
- Signup → onboarding → dashboard com pagamento real
- NFC tap → stamp → reward em hardware físico
- Stripe checkout completando + ativando plano via webhook
- Deferidos intencionalmente para o primeiro pilot real (não desperdiçar €78 num teste sintético)

**Operacional:**
- Nenhum cliente pagante ainda
- Pendente: primeira NFC tag impressa + primeiro stand entregue
- Founding member offer pronta (stand grátis + 60d grátis + €29/mês vitalício pros 5 primeiros)

---

## COMO TRABALHAR NESTE PROJETO

Quando retomar uma sessão, comece sempre com:
```
Lê o CLAUDE.md e me diz em qual sprint estamos e qual é o próximo passo.
```

**Cadência atual** (sprints incrementais, pequenos, com aprovação por escopo):
1. Propor escopo da sprint/feature antes de codar (lista de entregáveis + decisões abertas)
2. Henrique aprova ou ajusta
3. Implementar com commits atômicos por sub-fase
4. Lint/typecheck/tests verdes antes de cada commit
5. Push direto pra `main` (sem PR — single dev) — deploy automático: Vercel + Railway auto-redeployam

**Para reverter um deploy ruim:**
- Railway: Deployments → previous green → "Redeploy"
- Vercel: Deployments → "Promote to Production" na última green
- Rollback completo no `DEPLOY.md` §"Rollback playbook"

**Para tarefas específicas (skills gstack):**
- `/office-hours` — revisão executiva antes de decisão estratégica
- `/review` — code review antes de commit grande
- `/qa` — QA completo antes de mudança em produção
- `/cso` — auditoria de segurança
