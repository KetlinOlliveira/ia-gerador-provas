class ErroAplicacao(Exception):
    """Base dos erros que viram resposta HTTP. `mensagem` é exibida ao usuário."""

    status_http = 500
    codigo = "erro_interno"

    def __init__(self, mensagem: str) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem


class ErroLLMNaoConfigurado(ErroAplicacao):
    status_http = 503
    codigo = "llm_nao_configurado"


class ErroLLM(ErroAplicacao):
    """A chamada ao provedor falhou (limite de taxa esgotado, rede, 5xx, requisição inválida)."""

    status_http = 502
    codigo = "erro_llm"


class ErroSaidaLLM(ErroAplicacao):
    """O provedor respondeu, mas nunca com uma saída compatível com o esquema esperado."""

    status_http = 502
    codigo = "saida_llm_invalida"
