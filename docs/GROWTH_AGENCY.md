# Capivarex Growth Agency AI — Documentação

Sistema de agentes de IA em n8n para geração automatizada de material de marketing e landing pages para os produtos da Capivarex (SmartTap, TALOA, etc).

n8n: `https://n8n-production-db31.up.railway.app`

---

## Status atual (30 Jun / 01 Jul 2026)

| Agente | Status | Webhook |
|---|---|---|
| Research Agent | ✅ Funcionando | `/webhook/smarttap-research` |
| Copy Agent | ✅ Funcionando | `/webhook/smarttap-copy` |
| Creative Agent | ✅ Funcionando | `/webhook/smarttap-creative` |
| Landing Page Agent | ✅ Funcionando (v4 + AOS) | `/webhook/capivarex-landing` |

Landing page de teste ao vivo: `https://www.smarttap.ie/test/test-landing.html`
(usar sempre `www.` — o apex `smarttap.ie` faz redirect 307 e perde o header CSP)

---

## Landing Page Agent — arquitetura atual

```
Webhook → Setup Config
  → Claude Image Prompts (Sonnet, gera os 3 prompts de imagem)
  → Parse Prompts
  → GPT Hero → Store Hero URL → Prepare Hero Binary → Upload Hero Supabase
  → GPT Features → Store Features URL → Prepare Features Binary → Upload Features Supabase
  → GPT Testimonial → Store All URLs → Prepare Testimonial Binary → Upload Testimonial Supabase
  → Claude Build HTML (Sonnet, monta o HTML completo com as URLs do Supabase)
  → Build and Convert (HTML → base64)
  → GitHub Get SHA (Continue on Error — trata caso de arquivo não existir ainda)
  → Prepare Payload
  → GitHub Push File (PUT, cria ou atualiza o arquivo)
  → Format Output
```

### Decisões técnicas importantes (não mexer sem necessidade)

- **Uploads de imagem em sequência, não paralelo.** Rodar os 3 uploads em paralelo faz o workflow "terminar" antes de todos concluírem. Cada upload precisa estar encadeado um depois do outro.
- **Upload pro Supabase usa Binary, não Raw+Expression.** Tentar mandar `Buffer.from(...)` direto num campo de texto "Raw" do HTTP Request node do n8n corrompe o arquivo (chega com 0 ou 1 byte). A solução correta é: um node Code antes de cada upload que gera o binário de verdade com `this.helpers.prepareBinaryData()`, e o HTTP Request configurado com **Body Content Type: n8n Binary File** + **Input Data Field Name: data**.
- **GitHub API usa PUT, não POST**, tanto pra criar quanto pra atualizar arquivo. Pra atualizar precisa do `sha` do arquivo atual (busca via GET antes). Pra criar, sha é omitido.
- **Arquivo fica em `apps/web/public/test/test-landing.html`** — precisa estar dentro de `public/` pro Next.js servir como estático. Um arquivo na raiz do repo NUNCA é servido.
- **CSP do Next.js** (`apps/web/next.config.mjs`) tem uma regra específica pra `/test/test-landing.html` liberando `unsafe-inline` e `unsafe-eval`. Não é isso que causa página em branco geralmente — quase sempre é HTML truncado (ver abaixo).
- **max_tokens do Claude Build HTML: 9000.** Menos que isso corta o HTML no meio (geralmente no CSS ou no footer). Sempre que adicionar mais seções ou mais instruções no prompt, testar se o HTML termina com `</html>` de verdade. (Histórico: começou em 3000 → 6000 → 8500 → 9000 conforme o prompt foi crescendo com mais instruções.)
- **Bug do menu duplicado (resolvido 01/07/2026):** o Claude às vezes gerava um segundo elemento `<nav>` no rodapé com os mesmos links do menu principal, e por herdar `position: fixed` sem querer, esse menu do rodapé "vazava" e aparecia no topo da página por cima do menu real. Corrigido adicionando no prompt uma regra explícita: apenas o nav do header pode usar `position: fixed`, e o footer deve usar `<div>` em vez de `<nav>`, em fluxo estático normal.
- **Teste de integridade do HTML publicado:**
  ```powershell
  curl -s "https://www.smarttap.ie/test/test-landing.html?v=$RANDOM" -H "Cache-Control: no-cache" -o landing.html
  wc -c landing.html
  tail -c 300 landing.html   # deve terminar com </html>
  ```
- **Cache do Vercel:** depois de rodar o workflow, esperar ~20-30s antes de testar, ou usar `?v=$RANDOM` na URL pra forçar bypass.

### Animações (AOS)

Adicionado suporte a scroll animations via [AOS](https://michalsnik.github.io/aos/) (biblioteca leve, ~14KB). O prompt do `Claude Build HTML` instrui o Claude a incluir os `<link>` e `<script>` do AOS e aplicar `data-aos="fade-up"` nas seções.

**Lição aprendida:** escrever HTML com aspas duplas escapadas dentro de um JSON body quebra facilmente (erro de parsing). Prompt reescrito descrevendo os placeholders em texto simples (ex: "LINK_AOS_CSS becomes a link tag pointing to...") em vez de HTML literal escapado — funcionou de forma confiável.

### Hero em tela cheia (full-bleed)

A imagem do hero cobre a seção inteira como background (via `<img>` posicionado absoluto com `object-fit: cover`, com um overlay gradiente escuro por cima pra manter o texto legível), em vez de aparecer numa caixinha ao lado do texto. Instrução específica no prompt garante altura mínima de `90vh` e camadas (`z-index`) corretas entre imagem, overlay e conteúdo.

---

## Backlog / Roadmap

### Curto prazo
- [ ] Orquestrador — workflow master que dispara Research → Copy → Creative → Landing Page em sequência com um único webhook
- [ ] Brand Context compartilhado — injetar diretrizes de marca (cores, tom de voz, produtos) em todos os agentes de forma centralizada, em vez de hardcoded em cada prompt
- [ ] Video Agent — via Higgsfield, usando as imagens já geradas no Supabase Storage
- [ ] Social Media Agent — posts prontos pra Instagram/Facebook
- [ ] Email Agent — sequência de prospecção pra donos de negócio em Dublin

### Melhorias visuais da landing page (avaliar uma por vez, com cuidado pra não voltar a quebrar o CSP/truncamento)
- [x] AOS — fade-in/scroll animations (feito 01/07/2026)
- [ ] GSAP — transições mais refinadas
- [ ] Three.js — elemento 3D no hero (ex: NFC card girando)
- [ ] Vanta.js — fundo animado (partículas/ondas)

### Fase de produto (quando for vender pra clientes)

**Editor Agent (Landing Page Editor)** — não construir ainda, é para quando o produto for vendido a clientes reais.

Motivação: hoje, qualquer ajuste na landing gerada significa recriar o HTML inteiro do zero (gasta tokens à toa, risco de perder qualidade em partes que já estavam boas, sem controle de versão). Em fase de teste isso não é problema — dá pra pedir ajuste direto pro Claude Code. Mas quando o produto for vendido, o cliente vai precisar pedir ajustes pontuais ("muda a cor do botão", "tira essa seção", "corrige meu telefone") sem regenerar tudo.

Arquitetura proposta:
```
Webhook recebe: { instruction: "instrução do cliente em linguagem natural" }
  → Busca o HTML atual publicado (GitHub)
  → Claude recebe HTML completo + instrução
  → Claude retorna o HTML completo já editado (edição cirúrgica, não recriação)
  → Publica (mesma lógica de GitHub Push File já existente)
```

Isso também viabiliza um modelo comercial de "X revisões incluídas no plano" — como agências de verdade vendem esse tipo de serviço.

### Fase futura — Creative Strategy Agency
Agente "gerador/otimizador de ideias" — fecha o gap entre pesquisa de mercado (Research Agent) e execução (Copy/Creative/Landing). Recebe uma ideia vaga de produto/segmento, pesquisa, gera ângulos de posicionamento, valida, e entrega um brief pros outros agentes executarem.

### Fase futura — Legal Agent
Agente jurídico — revisa termos de uso, política de privacidade, contratos, e qualquer texto legal gerado ou usado pelos outros agentes (ex: termos que aparecem numa landing page, contrato de assinatura, disclaimers). Objetivo: garantir que nada saia com falha jurídica antes de ir ao ar — especialmente importante quando o produto começar a ser vendido de verdade pra clientes reais (GDPR, termos de cancelamento, etc, considerando operação na Irlanda/UE).

### Fase futura — Naming / Virality Agent
Agente que gera nomes virais e memoráveis para produtos, campanhas, features, ou até variações de teste A/B de nome. Pode também sugerir taglines curtas e ganchos (hooks) para uso em social media e ads. Entra bem no início do funil, antes ou junto do Research Agent, quando um novo produto/ideia está sendo validado.

### Itens em aberto (adicionar aqui sempre que lembrar de algo novo)
- (espaço reservado — Henrique vai completando conforme for lembrando de peças que faltam)

---

## Credenciais e recursos usados

- Anthropic API — Claude Sonnet (`claude-sonnet-4-6`) para prompts de imagem e geração de HTML
- OpenAI API — `gpt-image-1` para geração de imagens
- Supabase Storage — bucket `agency-assets` (público), projeto `qmemsvkeiygdwxyzadrc`
- GitHub API — repo `cotah/SmartTap`, branch `main`

**Nota de segurança:** tokens do GitHub e chaves de API foram expostos e revogados/regenerados durante o desenvolvimento em 29-30/06/2026. Sempre usar variáveis de credencial do n8n, nunca colar chaves em texto puro em prints ou documentos compartilhados.
