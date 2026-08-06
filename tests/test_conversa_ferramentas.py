from application.conversa_ferramentas import endereco_parece_valido


def test_endereco_valido_aceito():
    assert endereco_parece_valido("Rua das Flores, 123, Bairro Centro, Uberlândia") is True


def test_endereco_none_rejeitado():
    assert endereco_parece_valido(None) is False


def test_endereco_curto_demais_rejeitado():
    assert endereco_parece_valido("abc") is False


def test_endereco_sem_numero_rejeitado():
    # Bug real: a IA já mandou "Por favor, forneça o endereço de entrega
    # para concluir o pedido." como se fosse o endereço de verdade.
    assert endereco_parece_valido("Por favor, forneça o endereço de entrega.") is False
