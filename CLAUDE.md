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
7. **Especialidade (funilaria_pintura/eletrica/mecanica_geral/montagem) é
   sempre lista, nunca valor único** — um mesmo caso pode precisar de mais
   de uma área ao mesmo tempo (ex: batida com dano elétrico junto).
8. **`indefinido` é tratado como mecânica geral só na hora de buscar
   disponibilidade/mecânico qualificado** — o dado salvo continua
   `indefinido` (nunca é convertido silenciosamente ao criar o registro);
   forçar uma especialidade errada é pior do que admitir incerteza.
9. **Comprar peça e pedir instalação/avaliação são ferramentas de IA
   diferentes** (`consultar_preco_peca` vs `agendar_visita`), nunca um
   campo extra numa ferramenta só — evita a IA agendar visita por engano
   só porque o cliente mencionou uma peça.
10. **Toda resposta de "sem horário disponível" tem que vir junto com a
    próxima data que tem vaga** (ou lista de espera) — nunca só "não tem
    horário", pra não perder cliente por resposta de porta fechada.

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