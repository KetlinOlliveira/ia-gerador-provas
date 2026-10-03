"""Monta o conteúdo da prova em blocos neutros, que cada formato só precisa desenhar.

Assim Markdown, DOCX e PDF nunca divergem no texto: a decisão do que aparece em
cada versão (aluno ou professor) fica num lugar só.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from app.esquemas.provas import (
    Dificuldade,
    ProvaDetalhe,
    QuestaoDissertativa,
    QuestaoGerada,
    QuestaoMultiplaEscolha,
    QuestaoVerdadeiroFalso,
)


class Versao(StrEnum):
    ALUNO = "aluno"
    PROFESSOR = "professor"


TipoBloco = Literal["titulo", "subtitulo", "questao", "paragrafo", "item", "gabarito", "linhas"]


@dataclass(frozen=True)
class Bloco:
    tipo: TipoBloco
    texto: str = ""


NOMES_DIFICULDADE = {
    Dificuldade.FACIL: "Fácil",
    Dificuldade.MEDIO: "Média",
    Dificuldade.DIFICIL: "Difícil",
}
NOMES_TIPO = {
    "multipla_escolha": "Múltipla escolha",
    "dissertativa": "Dissertativa",
    "verdadeiro_falso": "Verdadeiro ou falso",
}
LETRAS = "ABCD"


def montar_blocos(prova: ProvaDetalhe, versao: Versao) -> list[Bloco]:
    professor = versao == Versao.PROFESSOR
    blocos = [
        Bloco("titulo", prova.titulo + (" (gabarito)" if professor else "")),
        Bloco(
            "subtitulo",
            f"{prova.total_questoes} questões · Nível {NOMES_DIFICULDADE[prova.dificuldade]}",
        ),
    ]
    if not professor:
        blocos.append(
            Bloco("paragrafo", "Nome: ______________________________   Data: ___/___/______")
        )

    for questao in prova.questoes:
        blocos.extend(_questao(questao, professor))
    return blocos


def _questao(questao: QuestaoGerada, professor: bool) -> list[Bloco]:
    conteudo = questao.conteudo
    blocos = [
        Bloco("questao", f"Questão {questao.numero} ({NOMES_TIPO[conteudo.tipo]})"),
        Bloco("paragrafo", conteudo.enunciado),
    ]

    if isinstance(conteudo, QuestaoMultiplaEscolha):
        blocos += [
            Bloco("item", f"{letra}) {texto}")
            for letra, texto in zip(LETRAS, conteudo.alternativas, strict=True)
        ]
        if professor:
            blocos += [
                Bloco("gabarito", f"Resposta correta: {conteudo.resposta_correta}"),
                Bloco("paragrafo", conteudo.justificativa),
            ]

    elif isinstance(conteudo, QuestaoDissertativa):
        if professor:
            blocos += [
                Bloco("gabarito", "Resposta esperada"),
                Bloco("paragrafo", conteudo.resposta_esperada),
                Bloco("gabarito", "Critérios de correção"),
            ]
            blocos += [
                Bloco("item", f"{criterio.descricao} ({criterio.pontos:g} pts)")
                for criterio in conteudo.criterios
            ]
        else:
            blocos.append(Bloco("linhas"))

    elif isinstance(conteudo, QuestaoVerdadeiroFalso):
        for afirmativa in conteudo.afirmativas:
            if professor:
                valor = "V" if afirmativa.verdadeira else "F"
                blocos.append(Bloco("item", f"({valor}) {afirmativa.texto}"))
                blocos.append(Bloco("paragrafo", afirmativa.justificativa))
            else:
                blocos.append(Bloco("item", f"(   ) {afirmativa.texto}"))

    if professor and questao.fontes:
        paginas = sorted({fonte.pagina for fonte in questao.fontes if fonte.pagina is not None})
        referencia = f" (páginas {', '.join(map(str, paginas))})" if paginas else ""
        blocos.append(
            Bloco(
                "paragrafo",
                f"Base no material: {len(questao.fontes)} trecho(s){referencia}. "
                f"Nota do revisor: {questao.avaliacao.nota}/10.",
            )
        )
    return blocos
