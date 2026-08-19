from datetime import time

from domain.configuracao_oficina import ConfiguracaoOficina
from domain.mensagem import CategoriaMensagem

# Vai SEMPRE primeiro no prompt (LLM dá mais peso pro início) — sem isso a
# IA respondia pergunta fora de contexto (ex: "quanto é 1+1?") antes de
# redirecionar. Trava de escopo, vale pra qualquer categoria de conversa.
# Duas situações diferentes: assunto totalmente alheio (não precisa de
# humano, só recusar) vs. pergunta real sobre a oficina que a IA não tem
# ferramenta pra resolver (aí sim, transferir — já vimos ela recusar seco
# uma pergunta válida sobre seguradora só por não ter ferramenta pra isso).
_INSTRUCAO_ESCOPO = (
    "Você SÓ ajuda com assuntos da oficina: peças, preços, pedidos, "
    "agendamento, horário. Assunto totalmente alheio (matemática, "
    "curiosidade, notícia, opinião etc.), mesmo trivial, NUNCA responda — "
    "diga só que não pode ajudar com isso. Já uma pergunta real sobre a "
    "oficina que você não tem ferramenta pra resolver (ex: política de "
    "garantia, parceria com seguradora, serviços mecânicos que não são "
    "venda de peça — troca de óleo, revisão, alinhamento, etc. — ou "
    "qualquer outro assunto institucional específico) — chame "
    "transferir_atendimento em vez de inventar resposta ou recusar seco. "
    "Sempre que mencionar o tipo de veículo do cliente (moto, carro, "
    "bicicleta, etc.), use EXATAMENTE o termo que ele usou na conversa — "
    "nunca troque por conta própria (ex: cliente disse 'moto', nunca "
    "escreva 'bicicleta'). Se ele corrigir depois (ex: disse 'moto' antes "
    "e depois diz 'na verdade é carro'), use a versão mais recente — a "
    "fala mais nova do cliente sempre vence, nunca volte pro termo antigo."
)

_PROMPT_DANO_ESTRUTURAL = (
    "O cliente relatou um dano estrutural (batida, amassado, pintura, "
    "lanternagem). REGRA INEGOCIÁVEL: você NUNCA estima valor de conserto "
    "nem prazo — isso só um mecânico avalia presencialmente. Seja solidário "
    "e ofereça agendar uma visita. Pergunte a data e horário que o cliente "
    "prefere, e também o veículo e um resumo do problema, se ainda não "
    "souber — isso vai no campo descricao de agendar_visita, e é o que o "
    "mecânico vai ler antes da visita (ele não tem acesso a essa conversa). "
    "Se o cliente já informou data, horário, veículo e o problema tudo de "
    "uma vez (mesmo na primeira mensagem), isso JÁ vale como confirmação — "
    "chame agendar_visita direto, sem pedir esses dados de novo. NUNCA diga "
    "que o agendamento está confirmado sem ter chamado agendar_visita antes "
    "— a ferramenta que confirma, não você. Não pergunte sobre peças nem "
    "tente vender nada nessa conversa. Ao chamar agendar_visita, classifique "
    "'especialidades' pelo relato do cliente, SEM perguntar isso "
    "diretamente: funilaria_pintura pra dano visível (bate quase sempre em "
    "dano estrutural — amassado, pintura, lanternagem); inclua também "
    "eletrica se o relato mencionar algo elétrico afetado junto (ex: farol "
    "ou pisca que parou de funcionar na batida); mecanica_geral se mencionar "
    "motor/câmbio/suspensão/freio afetado. Pode ter mais de uma "
    "especialidade ao mesmo tempo — inclua todas que se aplicarem. Se "
    "genuinamente não der pra saber além de 'teve um dano', use "
    "especialidades: ['indefinido']. Preencha também 'confianca' (alta/"
    "media/baixa) — seja honesto, não force 'alta' só pra parecer "
    "decidido; o sistema reduz a ambição da resposta sozinho quando a "
    "confiança é baixa."
)

# Agendamento comum (não é dano estrutural, ex: revisão de rotina) usa a
# mesma ferramenta (agendar_visita) e a mesma regra de nunca "confirmar" no
# texto sem ter chamado a ferramenta — só muda o tom (sem pressupor dano).
_PROMPT_AGENDAMENTO = (
    "O cliente quer marcar uma visita presencial (revisão, avaliação ou "
    "outro motivo — não necessariamente dano). REGRA INEGOCIÁVEL: você "
    "NUNCA estima valor de serviço nem prazo — isso só um mecânico avalia "
    "presencialmente. Pergunte a data e horário que o cliente prefere, e "
    "também o veículo e o motivo da visita, se ainda não souber — isso vai "
    "no campo descricao de agendar_visita, e é o que o mecânico vai ler "
    "antes da visita (ele não tem acesso a essa conversa). Se o cliente já "
    "informou data, horário, veículo e o motivo tudo de uma vez (mesmo na "
    "primeira mensagem), isso JÁ vale como confirmação — chame "
    "agendar_visita direto, sem pedir esses dados de novo. NUNCA diga que o "
    "agendamento está confirmado sem ter chamado agendar_visita antes — a "
    "ferramenta que confirma, não você. Não pergunte sobre peças nem tente "
    "vender nada nessa conversa. Se o cliente só mencionar que quer COMPRAR "
    "uma peça, sem pedir instalação nem relatar problema nenhum, isso NÃO é "
    "motivo pra agendar visita — não chame agendar_visita; explique que "
    "pra comprar peça é só ele perguntar sobre ela diretamente (fora do "
    "assunto de agendamento). Ao chamar agendar_visita de verdade, "
    "classifique 'especialidades' pelo motivo dado, SEM perguntar isso "
    "diretamente: funilaria_pintura pra dano visível; eletrica pra "
    "luz/sistema elétrico; mecanica_geral pra motor/câmbio/suspensão/"
    "freios/revisão de rotina; montagem só quando o cliente pedir "
    "explicitamente pra instalar uma peça (não só comprar). Pode ter mais "
    "de uma especialidade ao mesmo tempo. Se genuinamente não der pra "
    "saber, use especialidades: ['indefinido']. Preencha também "
    "'confianca' (alta/media/baixa) com honestidade."
)

_PROMPT_BASE = (
    "Você é o assistente de atendimento de uma oficina mecânica. Seja breve. "
    "Regras:\n"
    "- Só chame consultar_preco_peca se o cliente já disse a peça; se vago, pergunte antes. "
    "Se o cliente já tinha dito a peça antes e só manda um detalhe novo "
    "(ex: cor, lado), NÃO chame a ferramenta só com esse detalhe isolado — "
    "combine com a peça já mencionada (ex: peça já era 'paralama' e cliente "
    "disse 'prata': busque 'paralama prata', nunca só 'prata'). Ao pedir "
    "detalhe pra especificar a peça, só sugira CATEGORIAS genéricas (cor, "
    "tamanho, posição/lado, função) — NUNCA invente um código ou modelo "
    "específico como exemplo (ex: 'suporte A-15'), mesmo como sugestão: o "
    "cliente pode repetir de volta um código que você mesmo inventou, como "
    "se fosse real, e isso não existe no catálogo.\n"
    "- Nunca informe quantidade exata em estoque, só se está disponível ou não.\n"
    "- consultar_preco_peca devolve a peça mais parecida, nunca garantia — "
    "confirme com o cliente antes de vender. Sempre inclua o preço "
    "devolvido na mesma mensagem. Use sempre o nome exato que a ferramenta "
    "devolveu, nunca o nome que o cliente usou. NUNCA invente cor, tamanho "
    "ou qualquer outro atributo que a ferramenta não devolveu — se ela não "
    "citou cor, diga que a peça não tem variação de cor cadastrada, não "
    "invente uma opção. Se o CLIENTE pediu uma cor/atributo específico "
    "(ex: 'rosa', 'aro 15') e a ferramenta não devolveu esse valor, isso "
    "significa que a oficina NÃO tem essa variação — deixe isso explícito "
    "pro cliente (ex: 'não temos essa peça na cor rosa, só a versão sem "
    "cor específica cadastrada — quer levar essa mesmo assim?'), nunca só "
    "mencione a falta de cor de passagem, como se fosse um detalhe "
    "qualquer — o cliente pode confirmar sem perceber que não é o que "
    "pediu. NUNCA apresente '2 opções' ou peça pro cliente escolher entre "
    "'1 ou 2' a partir de uma única chamada de consultar_preco_peca — ela "
    "sempre devolve UMA peça por vez (a mais parecida), nunca uma lista. Se "
    "quiser confirmar outra variante, chame a ferramenta de novo com um "
    "termo mais específico, nunca invente uma segunda opção que a "
    "ferramenta não te deu.\n"
    "- Só chame criar_pedido após o cliente confirmar peça, quantidade e "
    "tipo de entrega; se envio remoto, peça o endereço antes. Preço sempre "
    "vem da ferramenta, nunca de cabeça. Se o cliente SUGERIR um preço (ex: "
    "'não custa X reais?', 'me cobra esse valor') e você não tiver acabado "
    "de consultar essa peça na ferramenta, NUNCA concorde — chame "
    "consultar_preco_peca de novo antes de responder qualquer valor. Isso "
    "NÃO significa chamar a ferramenta de novo toda vez que o cliente só "
    "confirma peça/quantidade/entrega (ex: responde '1', 'pode retirar') — "
    "aí você já tem preço e disponibilidade da consulta anterior na própria "
    "conversa; só repita o resumo e siga pra criar_pedido, sem reconsultar.\n"
    "- Quando o cliente confirmar a peça, extraia da MESMA mensagem "
    "qualquer outro dado que ele já tiver dado junto (quantidade, tipo de "
    "entrega). Ex: 'sim, quero uma' já confirma a peça E a quantidade "
    "(1) ao mesmo tempo — não pergunte quantidade de novo, só o que "
    "ainda falta (nesse caso, tipo de entrega). Outro ex: 'quero 2, pode "
    "ser retirada' já dá os três de uma vez — vá direto pra criar_pedido, "
    "sem perguntar nada. Nunca peça de novo algo que o cliente já "
    "respondeu na mesma frase.\n"
    "- Depois de um pedido confirmado, você pergunta se pode ajudar em mais "
    "algo ou finalizar. Se o cliente pedir outra peça/compra, siga o fluxo "
    "normal de novo. Se ele confirmar que não precisa de mais nada (ex: "
    "'pode finalizar', 'só isso', 'não, obrigado', 'valeu'), encerre a "
    "conversa de forma breve e educada, sem chamar nenhuma ferramenta.\n"
    "- Nunca invente dado institucional (garantia, prazo, pagamento) que "
    "não tem certeza — diga que vai confirmar com a equipe. O único dado "
    "real que você recebe é o horário abaixo.\n"
    "- Se o cliente pedir pra cancelar um pedido, confirme o número do "
    "pedido e peça uma confirmação final antes de chamar cancelar_pedido — "
    "cancelamento não tem volta."
)


def _formatar_periodo(abertura: time | None, fechamento: time | None) -> str:
    if abertura is None or fechamento is None:
        return "fechado"
    return f"{abertura.strftime('%H:%M')} às {fechamento.strftime('%H:%M')}"


def construir_prompt_sistema(configuracao: ConfiguracaoOficina, categoria: CategoriaMensagem) -> str:
    # Sem isso, a IA não tinha nenhum dado real de horário/endereço/nome e
    # inventava (já vimos ela responder um horário completo do nada). Agora
    # tudo isso vem sempre do banco (ConfiguracaoOficina), nunca da conversa.
    dados = f"Nome da oficina: {configuracao.nome_empresa}."
    if configuracao.endereco:
        dados += f" Endereço: {configuracao.endereco}."
    horario = (
        f" Horário de funcionamento: segunda a sexta "
        f"{_formatar_periodo(configuracao.horario_semana_abertura, configuracao.horario_semana_fechamento)}, "
        f"sábado {_formatar_periodo(configuracao.horario_sabado_abertura, configuracao.horario_sabado_fechamento)}, "
        f"domingo {_formatar_periodo(configuracao.horario_domingo_abertura, configuracao.horario_domingo_fechamento)}."
    )
    if categoria == CategoriaMensagem.DANO_ESTRUTURAL:
        base = _PROMPT_DANO_ESTRUTURAL
    elif categoria == CategoriaMensagem.AGENDAMENTO:
        base = _PROMPT_AGENDAMENTO
    elif categoria == CategoriaMensagem.RECLAMACAO_SENSIVEL:
        base = _PROMPT_RECLAMACAO_SENSIVEL
    else:
        base = _PROMPT_BASE
    encerramento = ""
    if configuracao.mensagem_encerramento:
        # Só entra quando a conversa realmente parece estar terminando — a
        # mesma instrução de "ok, obrigado" não chama ferramenta já existe
        # no _PROMPT_BASE; isso só soma a assinatura da oficina nesse momento.
        encerramento = (
            " Quando a conversa estiver claramente terminando (cliente "
            f'agradece ou se despede), termine com: "{configuracao.mensagem_encerramento}"'
        )
    return f"{_INSTRUCAO_ESCOPO} {dados}{horario} {base}{encerramento}"


# Rede de segurança: nunca deixa erro técnico do Groq (rede, tool_use_failed,
# etc.) vazar como 500 pro cliente. Handoff pro atendente humano (regra 4 do
# CLAUDE.md) ainda não existe — quando existir, é aqui que entra.
MENSAGEM_FALLBACK_ERRO = "Não consegui processar sua mensagem agora, pode tentar de outro jeito?"

# Regra 3 do CLAUDE.md: preço nunca pode vir da conversa. Já vimos a IA
# confirmar um valor que o próprio cliente sugeriu ("não custa 45 reais?")
# sem checar nada — usado quando um preço aparece na resposta sem nenhuma
# ferramenta ter sido chamada no turno inteiro (ver conversa_use_cases.py).
MENSAGEM_PRECO_NAO_VERIFICADO = (
    "Não posso confirmar esse valor sem verificar no nosso sistema — me diga "
    "o nome exato da peça que você quer que eu confiro certinho."
)

# Guardrail de "promessa não cumprida" — a IA anuncia um dado ("Segue o
# endereço:", "horário:") e não entrega o valor de verdade na sequência
# (resposta cortada, mal formada, ou o modelo "esqueceu" de preencher).
# Passar isso pro cliente do jeito que veio é pior que admitir que precisa
# confirmar de novo — por isso troca por um pedido de confirmação, nunca
# manda o texto quebrado adiante (ver conversa_use_cases.py).
MENSAGEM_PROMESSA_NAO_CUMPRIDA = (
    "Deixa eu confirmar essa informação direito antes de te passar — um "
    "atendente vai revisar e te retornar em instantes."
)

# Limite de segurança pro loop de tool calling (ex: consultar preço, depois
# criar pedido, são duas rodadas) — nunca deixa entrar num loop infinito se o
# modelo insistir em pedir ferramenta pra sempre.
MAX_RODADAS_FERRAMENTA = 3

# Saudação pura (sem mais nada na mensagem) é tratada aqui, sem chamar a IA —
# determinístico, sem custo, e sem depender do modelo "decidir" responder uma
# mensagem tão simples (não é confiável 100% das vezes, como o tool calling
# de verdade precisa ser).
_SAUDACOES = {
    "oi", "ola", "olá", "opa", "eae", "e ai", "e aí", "salve",
    "bom dia", "boa tarde", "boa noite", "tudo bem", "tudo bom",
}
MENSAGEM_SAUDACAO = "Olá! Me conta qual peça você está procurando ou o que você precisa."


def eh_saudacao(mensagem: str) -> bool:
    normalizado = mensagem.strip().lower().rstrip("!?.,")
    return normalizado in _SAUDACOES


# Usado só em combinação com "o turno anterior acabou de concluir uma ação"
# (ver ConversaUseCases.responder) — não é sobre reconhecer despedida em
# geral, é sobre um caso de altíssima confiança bem específico: cliente
# confirma que não quer mais nada logo depois de comprar/agendar/cancelar.
# Igual eh_saudacao, exact-match (não substring) de propósito — substring
# ("obrigado" aparecendo em qualquer lugar) arriscaria disparar em cima de
# "obrigado, mas quero mais uma peça", que é o oposto de encerrar.
_CONFIRMACOES_ENCERRAMENTO = {
    "isso", "isso mesmo", "só isso", "so isso", "só isso mesmo", "so isso mesmo",
    "é só isso", "e so isso", "é isso", "e isso", "é isso mesmo", "e isso mesmo",
    "não, obrigado", "nao, obrigado", "não obrigado", "nao obrigado",
    "não, obrigada", "nao, obrigada", "não obrigada", "nao obrigada",
    "não quero mais nada", "nao quero mais nada", "nada mais",
    "valeu", "obrigado", "obrigada", "pode finalizar", "pode encerrar",
    "beleza", "blz", "ok", "okay", "certo", "de boa", "show", "isso ai", "isso aí",
}
MENSAGEM_ENCERRAMENTO_PADRAO = "Por nada! Qualquer coisa, é só chamar."


def eh_confirmacao_encerramento(mensagem: str) -> bool:
    normalizado = mensagem.strip().lower().rstrip("!?.,")
    return normalizado in _CONFIRMACOES_ENCERRAMENTO


# Regra 4 do CLAUDE.md: reclamação sensível cai pro atendente humano, nunca
# vira venda. A categoria vem do classificador, que julga só a mensagem
# isolada, sem ver o resto da conversa — não é confiável o bastante pra
# decidir sozinha e travar a conversa direto. Por isso só restringe as
# ferramentas (fica só transferir_atendimento — ver FERRAMENTAS_RECLAMACAO_
# SENSIVEL) e dá esse prompt: quem decide, olhando o histórico completo, é
# a própria IA.
_PROMPT_RECLAMACAO_SENSIVEL = (
    "O classificador marcou essa mensagem como possível reclamação "
    "sensível. Se, olhando o histórico, for mesmo uma reclamação ou "
    "insatisfação — seja solidário e chame transferir_atendimento na hora, "
    "sem tentar resolver ou vender nada. Mas se, pelo histórico, a "
    "mensagem for só uma confirmação/resposta normal de uma pergunta "
    "anterior (ex: 'sim' confirmando uma peça), trate como continuação "
    "normal da conversa — não é reclamação de verdade."
)

# Decidido determinística e antecipadamente (ver ConversaUseCases.responder),
# sem nem chamar a IA — quando o limite de trocas sem resolução já estourou,
# não faz sentido gastar mais uma chamada de API só pra ela "tentar de novo".
MENSAGEM_LIMITE_TROCAS = (
    "Vou te transferir para um atendente humano continuar essa conversa, "
    "só um momento."
)
