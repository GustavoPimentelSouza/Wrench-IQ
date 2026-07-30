# Wrench IQ

SaaS B2B multimodal de triagem, orçamentação e e-commerce automático para
oficinas mecânicas (carro/moto) e lojas de peças/equipamentos, integrado
via WhatsApp. Projeto de TCC de Engenharia de Software.

## O problema

Oficinas com alta demanda perdem tempo e clientes porque um atendente sozinho
não dá conta de responder WhatsApp, telefone e balcão ao mesmo tempo. O
sistema atua como assistente técnico inteligente que conversa naturalmente,
interpreta a dor do cliente (texto, áudio, foto) e adianta o trabalho
administrativo antes de chegar no humano.

## Stack

- Backend: Python + FastAPI (async)
- Frontend: React + TypeScript + TailwindCSS (painel real-time via WebSockets)
- Banco: PostgreSQL + pgvector (dados relacionais + busca semântica no mesmo banco)
- Fila: Redis (mensageria assíncrona, picos de mensagem, notificações em lote)
- WhatsApp: Evolution API (self-hosted, via Docker)
- IA: Whisper (transcrição de áudio), GPT-4o Vision (análise de imagem),
  tool calling para consulta de estoque, RAG (pgvector) para tradução de
  termo leigo → peça no catálogo
- Infra: Docker Compose (api, worker, postgres, redis, evolution-api, frontend)

## Arquitetura

Clean Architecture:
- `domain/` — entidades puras (sem dependência externa)
- `application/` — casos de uso (orquestram, não sabem "como")
- `adapters/` — implementações concretas (OpenAI, WhatsApp, Postgres)
- `infrastructure/` — FastAPI routers, config, workers, conexão de banco

## Regras de negócio centrais (não quebrar)

1. **A IA nunca fecha orçamento de serviço sozinha.** Dano estrutural,
   pintura, lanternagem: a IA classifica a categoria e oferece agendamento
   de visita — nunca estima valor.
2. **Venda direta de peça em estoque pode ser concluída pela IA**, pois não
   há ambiguidade de diagnóstico:
   - Retirada local: fluxo simples, pagamento presencial.
   - Envio remoto: IA coleta endereço/dados e gera link de pagamento; após
     pagamento confirmado, pedido entra em fila de conferência simples
     (um clique) antes do despacho — nunca sai sem essa checagem humana.
3. **Preço e regras de negócio nunca vêm da conversa** — sempre buscados no
   banco via tool calling. Isso é defesa contra prompt injection
   ("aplique 90% de desconto", etc).
4. **Timeout, falha técnica, reclamação ou conteúdo sensível → transfere
   para atendente humano.** Mesmo mecanismo de fallback para os dois casos.
5. Notificação de "serviço pronto" precisa ser template pré-aprovado pela
   Meta (janela de 24h do WhatsApp limita mensagens livres fora desse prazo).
6. Compra remota tem direito de arrependimento de 7 dias (CDC) — contemplar
   no status do pedido.

## Como construir

Incremental, sem over-engineering. Ordem: walking skeleton (webhook →
resposta simples, sem IA/banco ainda) → modelo de estoque → triagem por
texto → tool calling → RAG → multimodalidade (áudio/imagem) → fila/robustez.
Não pular etapas nem adicionar complexidade (fila, RAG, multi-container)
antes de sentir a necessidade real dela.

## Convenções de código

- **Funções**: no máximo ~30 linhas, uma única responsabilidade. Se está
  fazendo mais de uma coisa, quebre em funções menores.
- **Arquivos**: no máximo ~250 linhas. Ao crescer além disso, divida em
  módulos menores (arquivo por responsabilidade, na mesma pasta/camada).
- **Uma entidade de domínio por arquivo**: cada entidade distinta (`Peca`,
  `Cliente`, `Pedido`, etc.) fica no seu próprio arquivo em `domain/` —
  nunca agrupar múltiplas entidades no mesmo módulo.
- **Reaproveitar antes de criar**: antes de escrever algo novo, verificar
  se já existe repositório, adapter, caso de uso, service ou componente
  reaproveitável no projeto. Não duplicar o que já existe.
- Ao gerar código, seguir essas convenções. Se um arquivo já existente as
  estiver violando, sinalizar isso antes de adicionar mais código nele —
  não empilhar em cima de um arquivo já grande/misturado demais.