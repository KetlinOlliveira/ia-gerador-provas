from tests.arquivos import criar_pdf

AULA_REST = (
    "REST é um estilo arquitetural baseado em recursos identificados por URIs. "
    "Os métodos HTTP mais usados são GET, POST, PUT e DELETE. "
    "Uma API REST deve ser stateless, sem guardar sessão do cliente no servidor. "
    "Os códigos de status da faixa 2xx indicam sucesso na requisição. "
    "Os códigos da faixa 4xx indicam erro do cliente, como 404 Not Found. "
    "Autenticação com tokens JWT usa o cabeçalho Authorization. "
    "Boas práticas incluem versionar a API e paginar listas grandes."
)
AULA_BIOLOGIA = (
    "A fotossíntese ocorre nos cloroplastos das células vegetais. "
    "A clorofila absorve a luz solar para produzir glicose. "
    "A respiração celular acontece nas mitocôndrias e libera energia. "
    "O ciclo de Krebs é uma etapa da respiração celular aeróbica."
)


def enviar(cliente, nome, conteudo):
    if isinstance(conteudo, str):
        conteudo = conteudo.encode()
    return cliente.post("/api/v1/documentos", files={"arquivo": (nome, conteudo)})


def buscar(cliente, documento_id, consulta, k=3):
    return cliente.post(
        f"/api/v1/documentos/{documento_id}/busca", json={"consulta": consulta, "k": k}
    )


def test_envio_indexa_o_documento(cliente):
    resposta = enviar(cliente, "rest.txt", AULA_REST)

    assert resposta.status_code == 201
    documento = resposta.json()
    assert documento["nome_arquivo"] == "rest.txt"
    assert documento["tipo"] == "txt"
    assert documento["total_trechos"] > 1
    assert documento["total_caracteres"] == len(AULA_REST)
    assert documento["total_paginas"] is None


def test_envio_de_pdf_registra_as_paginas(cliente):
    resposta = enviar(cliente, "aula.pdf", criar_pdf(["Pagina um.", "Pagina dois."]))

    assert resposta.status_code == 201
    assert resposta.json()["total_paginas"] == 2


def test_reenvio_do_mesmo_conteudo_devolve_o_documento_existente(cliente):
    primeiro = enviar(cliente, "rest.txt", AULA_REST)
    segundo = enviar(cliente, "copia.txt", AULA_REST)

    assert segundo.status_code == 200
    assert segundo.json()["id"] == primeiro.json()["id"]
    assert len(cliente.get("/api/v1/documentos").json()) == 1


def test_lista_e_consulta_por_id(cliente):
    documento = enviar(cliente, "rest.txt", AULA_REST).json()
    enviar(cliente, "bio.txt", AULA_BIOLOGIA)

    listados = cliente.get("/api/v1/documentos").json()
    assert {item["nome_arquivo"] for item in listados} == {"rest.txt", "bio.txt"}
    assert cliente.get(f"/api/v1/documentos/{documento['id']}").json() == documento


def test_busca_devolve_o_trecho_mais_relevante_primeiro(cliente):
    documento = enviar(cliente, "rest.txt", AULA_REST).json()

    resultados = buscar(cliente, documento["id"], "autenticação com tokens JWT").json()

    assert "JWT" in resultados[0]["texto"]
    pontuacoes = [resultado["pontuacao"] for resultado in resultados]
    assert pontuacoes == sorted(pontuacoes, reverse=True)


def test_busca_fica_restrita_ao_documento_consultado(cliente):
    rest = enviar(cliente, "rest.txt", AULA_REST).json()
    enviar(cliente, "bio.txt", AULA_BIOLOGIA)

    resultados = buscar(cliente, rest["id"], "respiração celular nas mitocôndrias", k=20).json()

    assert len(resultados) == rest["total_trechos"]
    assert all("mitocôndrias" not in resultado["texto"] for resultado in resultados)


def test_exclusao_remove_o_documento_e_seus_vetores(cliente):
    rest = enviar(cliente, "rest.txt", AULA_REST).json()
    bio = enviar(cliente, "bio.txt", AULA_BIOLOGIA).json()

    assert cliente.delete(f"/api/v1/documentos/{rest['id']}").status_code == 204

    assert cliente.get(f"/api/v1/documentos/{rest['id']}").status_code == 404
    assert buscar(cliente, rest["id"], "REST").status_code == 404
    assert len(buscar(cliente, bio["id"], "fotossíntese").json()) > 0
    # O conteúdo pode ser enviado de novo depois de excluído.
    assert enviar(cliente, "rest.txt", AULA_REST).status_code == 201


def test_documento_inexistente_devolve_404(cliente):
    resposta = cliente.get("/api/v1/documentos/nao-existe")

    assert resposta.status_code == 404
    assert resposta.json()["erro"]["codigo"] == "nao_encontrado"


def test_recusa_formato_nao_suportado(cliente):
    resposta = enviar(cliente, "planilha.xlsx", b"dados")

    assert resposta.status_code == 415
    assert resposta.json()["erro"]["codigo"] == "tipo_nao_suportado"


def test_recusa_arquivo_acima_do_limite(cliente):
    resposta = enviar(cliente, "grande.txt", b"a" * (1024 * 1024 + 1))

    assert resposta.status_code == 413


def test_recusa_arquivo_sem_texto(cliente):
    resposta = enviar(cliente, "vazio.txt", b"   ")

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "documento_sem_texto"
    assert cliente.get("/api/v1/documentos").json() == []
