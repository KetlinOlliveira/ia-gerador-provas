import asyncio
import logging
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from app.agentes.gerador import Questao, gerar_questao
from app.agentes.planejador import amostrar_material, planejar
from app.agentes.revisor import aprovada, revisar
from app.core.config import Configuracoes
from app.esquemas.provas import (
    ConfiguracaoProva,
    Dificuldade,
    Fonte,
    Prova,
    QuestaoGerada,
    QuestaoVerdadeiroFalso,
    TipoQuestao,
    Topico,
)
from app.llm.cliente import ClienteLLM

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EventoProgresso:
    etapa: Literal["planejamento", "geracao"]
    mensagem: str
    concluidas: int
    total: int


AoProgredir = Callable[[EventoProgresso], None]
# Recebe a consulta e quantos trechos devolver; devolve os mais semelhantes.
Recuperador = Callable[[str, int], Awaitable[list[Fonte]]]


@dataclass(frozen=True)
class ItemPlano:
    numero: int
    tipo: TipoQuestao
    topico: Topico


class OrquestradorProva:
    """Coordena os agentes: planejador, depois gerador e revisor para cada questão.

    Questões de tópicos diferentes são geradas em paralelo. Questões do mesmo tópico
    são geradas em sequência, para que cada uma saiba o que as anteriores já cobraram.
    """

    def __init__(
        self, llm: ClienteLLM, recuperar: Recuperador, configuracoes: Configuracoes
    ) -> None:
        self._llm = llm
        self._recuperar = recuperar
        self._configuracoes = configuracoes

    async def gerar(
        self,
        documento_id: str,
        trechos_do_documento: list[Fonte],
        configuracao: ConfiguracaoProva,
        ao_progredir: AoProgredir | None = None,
    ) -> Prova:
        inicio = time.monotonic()
        total = configuracao.total

        def avisar(etapa, mensagem: str, concluidas: int) -> None:
            if ao_progredir is not None:
                ao_progredir(EventoProgresso(etapa, mensagem, concluidas, total))

        avisar("planejamento", "Identificando os tópicos do material", 0)
        amostra = amostrar_material(
            trechos_do_documento, self._configuracoes.max_caracteres_planejador
        )
        plano = await planejar(self._llm, amostra, total)
        itens = distribuir_questoes(configuracao, plano.topicos)

        por_topico: dict[str, list[ItemPlano]] = {}
        for item in itens:
            por_topico.setdefault(item.topico.titulo, []).append(item)

        resultados: dict[int, QuestaoGerada] = {}

        async def processar_topico(itens_do_topico: list[ItemPlano]) -> None:
            topico = itens_do_topico[0].topico
            fontes = await self._recuperar(
                f"{topico.titulo}: {topico.descricao}", self._configuracoes.trechos_por_topico
            )
            ja_cobrado: list[str] = []
            for item in itens_do_topico:
                questao = await self._gerar_com_revisao(
                    item, configuracao.dificuldade, fontes, ja_cobrado
                )
                ja_cobrado.append(_resumo(questao.conteudo))
                resultados[item.numero] = questao
                avisar("geracao", f"Questão {len(resultados)} de {total} pronta", len(resultados))

        avisar("geracao", f"Gerando {total} questões", 0)
        try:
            # TaskGroup cancela os demais tópicos se um falhar, sem gastar tokens à toa.
            async with asyncio.TaskGroup() as grupo:
                for itens_do_topico in por_topico.values():
                    grupo.create_task(processar_topico(itens_do_topico))
        except* Exception as grupo_de_erros:
            raise grupo_de_erros.exceptions[0] from None

        return Prova(
            documento_id=documento_id,
            configuracao=configuracao,
            topicos=plano.topicos,
            questoes=[resultados[numero] for numero in sorted(resultados)],
            gerada_em=datetime.now(UTC),
            duracao_segundos=round(time.monotonic() - inicio, 1),
        )

    async def _gerar_com_revisao(
        self,
        item: ItemPlano,
        dificuldade: Dificuldade,
        fontes: list[Fonte],
        ja_cobrado: list[str],
    ) -> QuestaoGerada:
        """Padrão Reflection: gera, o revisor avalia e, se reprovar, o gerador refaz
        com as críticas. Fica a melhor versão, mesmo que nenhuma seja aprovada."""
        # Sorteada aqui porque modelos tendem a pôr a resposta certa sempre em A ou B.
        letra = random.choice("ABCD") if item.tipo == TipoQuestao.MULTIPLA_ESCOLHA else None
        nota_minima = self._configuracoes.nota_minima_revisao
        # Título e descrição juntos delimitam o tópico melhor que só o título.
        topico = f"{item.topico.titulo} ({item.topico.descricao})"
        melhor = None
        anterior = None

        for tentativa in range(1, self._configuracoes.max_tentativas_por_questao + 1):
            questao = await gerar_questao(
                self._llm,
                tipo=item.tipo,
                topico=topico,
                dificuldade=dificuldade,
                fontes=fontes,
                letra_correta=letra,
                evitar=ja_cobrado,
                anterior=anterior,
            )
            avaliacao = await revisar(self._llm, questao, topico, dificuldade, fontes)
            ok = aprovada(avaliacao, nota_minima)
            logger.info(
                "Questão %d (%s) tentativa %d: nota %d, fundamentada=%s",
                item.numero,
                item.tipo,
                tentativa,
                avaliacao.nota,
                avaliacao.fundamentada,
            )

            if melhor is None or (ok, avaliacao.nota) > (melhor[2], melhor[1].nota):
                melhor = (questao, avaliacao, ok)
            if ok:
                break
            anterior = (questao, avaliacao)

        questao, avaliacao, ok = melhor
        return QuestaoGerada(
            numero=item.numero,
            topico=item.topico.titulo,
            dificuldade=dificuldade,
            conteudo=questao,
            fontes=_fontes_citadas(questao, fontes),
            avaliacao=avaliacao,
            aprovada=ok,
            tentativas=tentativa,
        )


def distribuir_questoes(configuracao: ConfiguracaoProva, topicos: list[Topico]) -> list[ItemPlano]:
    """Define tipo e tópico de cada questão, na ordem em que aparecem na prova.

    Os tipos se alternam (múltipla escolha, dissertativa, V/F, ...) e os tópicos giram
    com um deslocamento a cada volta, para o mesmo tópico não cair sempre no mesmo tipo.
    """
    restantes = dict(configuracao.quantidades)
    tipos: list[TipoQuestao] = []
    while any(restantes.values()):
        for tipo in TipoQuestao:
            if restantes[tipo]:
                tipos.append(tipo)
                restantes[tipo] -= 1

    n = len(topicos)
    return [
        ItemPlano(numero=indice + 1, tipo=tipo, topico=topicos[(indice + indice // n) % n])
        for indice, tipo in enumerate(tipos)
    ]


def _resumo(questao: Questao) -> str:
    if isinstance(questao, QuestaoVerdadeiroFalso):
        return " / ".join(afirmativa.texto for afirmativa in questao.afirmativas)
    return questao.enunciado


def _fontes_citadas(questao: Questao, fontes: list[Fonte]) -> list[Fonte]:
    usados = set(questao.trechos_usados)
    citadas = [fonte for fonte in fontes if fonte.ordem in usados]
    # Se o modelo citar números que não existem, as fontes são todos os trechos que ele recebeu.
    return citadas or fontes
