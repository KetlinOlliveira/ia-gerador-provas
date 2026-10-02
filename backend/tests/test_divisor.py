from app.ingestao.divisor import dividir_em_trechos
from app.ingestao.extratores import TextoExtraido


def frases(quantidade, prefixo="Frase"):
    return " ".join(f"{prefixo} número {i} do texto de exemplo." for i in range(quantidade))


def dividir(paginas, tamanho=120, sobreposicao=40, paginado=False):
    return dividir_em_trechos(TextoExtraido(paginas, paginado), tamanho, sobreposicao)


def test_texto_curto_vira_um_unico_trecho():
    trechos = dividir(["Uma frase só."])

    assert [trecho.texto for trecho in trechos] == ["Uma frase só."]
    assert trechos[0].ordem == 0
    assert trechos[0].pagina is None


def test_respeita_o_tamanho_maximo_e_numera_em_ordem():
    trechos = dividir([frases(20)])

    assert len(trechos) > 1
    assert all(len(trecho.texto) <= 120 for trecho in trechos)
    assert [trecho.ordem for trecho in trechos] == list(range(len(trechos)))


def test_nao_corta_frases_no_meio():
    trechos = dividir([frases(20)])

    assert all(trecho.texto.startswith("Frase") for trecho in trechos)
    assert all(trecho.texto.endswith(".") for trecho in trechos)


def test_trechos_vizinhos_compartilham_a_ultima_frase():
    trechos = dividir([frases(20)])

    for anterior, seguinte in zip(trechos, trechos[1:], strict=False):
        ultima_frase = anterior.texto.split(". ")[-1]
        assert seguinte.texto.startswith(ultima_frase)


def test_sem_sobreposicao_nao_repete_texto():
    texto = frases(20)
    trechos = dividir([texto], sobreposicao=0)

    assert " ".join(trecho.texto for trecho in trechos) == texto


def test_frase_maior_que_o_limite_e_fatiada():
    trechos = dividir(["x" * 300], tamanho=120, sobreposicao=0)

    assert [len(trecho.texto) for trecho in trechos] == [120, 120, 60]


def test_registra_a_pagina_em_que_o_trecho_comeca():
    paginas = [frases(6, "Primeira"), frases(6, "Segunda"), frases(6, "Terceira")]
    trechos = dividir(paginas, paginado=True)

    assert trechos[0].pagina == 1
    assert trechos[-1].pagina == 3
    for trecho in trechos:
        inicio = trecho.texto.split()[0]
        assert trecho.pagina == {"Primeira": 1, "Segunda": 2, "Terceira": 3}[inicio]


def test_ignora_paginas_vazias():
    trechos = dividir(["", "Texto da segunda página.", ""], paginado=True)

    assert [(trecho.texto, trecho.pagina) for trecho in trechos] == [
        ("Texto da segunda página.", 2)
    ]
