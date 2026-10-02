import re
from bisect import bisect_right
from dataclasses import dataclass

from app.ingestao.extratores import TextoExtraido

# Fim de frase seguido de espaço, ou quebra de parágrafo.
_FRONTEIRA = re.compile(r"(?<=[.!?])\s+|\n{2,}")
_SEPARADOR_DE_PAGINA = "\n\n"


@dataclass(frozen=True)
class Trecho:
    ordem: int
    texto: str
    pagina: int | None


def dividir_em_trechos(extraido: TextoExtraido, tamanho: int, sobreposicao: int) -> list[Trecho]:
    """Divide o texto em trechos de até `tamanho` caracteres, sem cortar frases.

    Trechos vizinhos compartilham as últimas frases (até `sobreposicao` caracteres)
    para que uma ideia que atravessa a fronteira não se perca na busca. A página
    registrada é aquela em que o trecho começa.
    """
    texto = _SEPARADOR_DE_PAGINA.join(extraido.paginas)
    inicios_de_pagina = _inicios_de_pagina(extraido.paginas)

    trechos: list[Trecho] = []
    for inicio, fim in _agrupar(_unidades(texto, tamanho), tamanho, sobreposicao):
        pagina = bisect_right(inicios_de_pagina, inicio) if extraido.paginado else None
        trechos.append(Trecho(ordem=len(trechos), texto=texto[inicio:fim], pagina=pagina))
    return trechos


def _inicios_de_pagina(paginas: list[str]) -> list[int]:
    inicios, posicao = [], 0
    for pagina in paginas:
        inicios.append(posicao)
        posicao += len(pagina) + len(_SEPARADOR_DE_PAGINA)
    return inicios


def _unidades(texto: str, tamanho: int) -> list[tuple[int, int]]:
    """Posições (início, fim) de cada frase; frases maiores que `tamanho` são fatiadas."""
    limites, inicio = [], 0
    for fronteira in _FRONTEIRA.finditer(texto):
        limites.append((inicio, fronteira.start()))
        inicio = fronteira.end()
    limites.append((inicio, len(texto)))

    unidades = []
    for inicio, fim in limites:
        if not texto[inicio:fim].strip():
            continue
        for corte in range(inicio, fim, tamanho):
            unidades.append((corte, min(corte + tamanho, fim)))
    return unidades


def _agrupar(
    unidades: list[tuple[int, int]], tamanho: int, sobreposicao: int
) -> list[tuple[int, int]]:
    grupos: list[tuple[int, int]] = []
    atual: list[tuple[int, int]] = []

    for unidade in unidades:
        if atual and unidade[1] - atual[0][0] > tamanho:
            grupos.append((atual[0][0], atual[-1][1]))
            atual = _cauda(atual, sobreposicao)
            # Se a sobreposição somada à próxima frase estoura o limite, abre mão dela.
            if atual and unidade[1] - atual[0][0] > tamanho:
                atual = []
        atual.append(unidade)

    if atual:
        grupos.append((atual[0][0], atual[-1][1]))
    return grupos


def _cauda(unidades: list[tuple[int, int]], sobreposicao: int) -> list[tuple[int, int]]:
    fim = unidades[-1][1]
    cauda: list[tuple[int, int]] = []
    # A primeira unidade nunca entra: repetir o trecho inteiro não é sobreposição.
    for unidade in reversed(unidades[1:]):
        if fim - unidade[0] > sobreposicao:
            break
        cauda.insert(0, unidade)
    return cauda
