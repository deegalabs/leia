"""Registro de tentativas do cliente + hash imutável de assinatura."""
from __future__ import annotations
import hashlib, json, os
from datetime import datetime
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from core.db import engine, Tentativa, Tarefa


def _next_round(tarefa_id: int) -> int:
    with Session(engine) as s:
        ult = s.exec(
            select(Tentativa)
            .where(Tentativa.tarefa_id == tarefa_id)
            .order_by(Tentativa.numero.desc())   # type: ignore
        ).first()
    return (ult.numero + 1) if ult else 1


PREIMAGE_SCHEMA = "leia.attempt.v2"


def attempt_hash(tarefa_hash: str, numero: int, respostas_json: str, criada_em: datetime) -> str:
    """Hash da tentativa, recalculável por terceiro a partir do que fica gravado.

    A v1 misturava IP, navegador e um instante que não era persistido, então ninguém, nem a própria
    equipe, conseguia recalcular o valor publicado, e o preimage carregava dado pessoal. A v2 usa
    apenas o que está no registro, e o documento entra como referência derivada, nunca como o link.
    """
    quando = criada_em.replace(microsecond=0).isoformat()
    preimage = json.dumps({
        "schema": PREIMAGE_SCHEMA,
        "documentRef": hashlib.sha256(tarefa_hash.encode("utf-8")).hexdigest(),
        "attemptRound": numero,
        "answers": json.loads(respostas_json),
        "createdAt": quando,
    }, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(preimage.encode("utf-8")).hexdigest()


class AttemptsExhausted(Exception):
    """A pessoa usou o número máximo de tentativas de conferência deste documento."""


def _cap() -> int:
    return max(1, int(os.getenv("QUIZ_MAX_ATTEMPTS", "3")))


def attempts_exhausted(tarefa_id: int) -> bool:
    """Verdadeiro quando não cabe mais tentativa sem que alguém já tenha sido aprovado.

    O teto existe porque cada envio devolve quais perguntas foram erradas, e sem limite o registro
    de compreensão é obtido por tentativa e erro, sem ler nada. Ele não reprova a pessoa: quem chega
    ao fim da conta continua com a explicação aberta e é levada a falar com quem enviou o documento.
    """
    with Session(engine) as s:
        feitas = list(s.exec(select(Tentativa).where(Tentativa.tarefa_id == tarefa_id)))
    if any(t.aprovado for t in feitas):
        return False
    return len(feitas) >= _cap()


def record(
    tarefa: Tarefa,
    respostas: dict[int | str, int],
    questoes: list[dict],
    ip: Optional[str] = None,        # aceito e descartado: ver attempt_hash
    user_agent: Optional[str] = None,
) -> Tentativa:
    """
    Valida as respostas contra o gabarito das questões, grava a tentativa
    e retorna a linha persistida com hash imutável.
    """
    total = len(questoes)
    acertos = 0
    for q in questoes:
        qid = str(q.get("id"))
        correta = int(q.get("correta", -1))
        escolhida = respostas.get(qid)
        if escolhida is not None and int(escolhida) == correta:
            acertos += 1

    aprovado = acertos >= max(1, int(total * float(os.getenv("QUIZ_PASS_RATIO", "0.83"))))   # ≥ 83% (10/12)

    respostas_json = json.dumps(respostas, ensure_ascii=False, sort_keys=True)
    criada_em = datetime.utcnow().replace(microsecond=0)
    cap = _cap()

    # Escolher o número da rodada numa sessão e gravar em outra é checar-depois-gravar: entre as duas coisas
    # cabe outro envio. O número passa a ser decidido pelo banco, pela restrição única em (tarefa_id, numero):
    # quem perder a disputa recebe IntegrityError, lê de novo e tenta o número seguinte. O teto sai da
    # contagem e passa a ser o próprio número da rodada, então furar o teto exigiria furar a restrição.
    for _ in range(cap + 5):
        with Session(engine) as s:
            feitas = list(s.exec(select(Tentativa).where(Tentativa.tarefa_id == tarefa.id)))
        if not any(x.aprovado for x in feitas) and len(feitas) >= cap:
            raise AttemptsExhausted()
        numero = max((x.numero for x in feitas), default=0) + 1
        if not any(x.aprovado for x in feitas) and numero > cap:
            raise AttemptsExhausted()

        h = attempt_hash(tarefa.hash, numero, respostas_json, criada_em)

        # IP e navegador não são gravados: não entram na prova, não são necessários ao produto,
        # e estavam impressos no comprovante que a cidadã mostra a terceiros.
        t = Tentativa(
            tarefa_id=tarefa.id,
            numero=numero,
            respostas=respostas_json,
            acertos=acertos,
            total=total,
            aprovado=aprovado,
            hash_imutavel=h,
            criada_em=criada_em,
        )
        try:
            with Session(engine) as s:
                s.add(t); s.commit(); s.refresh(t)
            return t
        except IntegrityError:
            # Outro envio ficou com esta rodada. O segundo não pode virar a mesma linha nem o mesmo hash,
            # então recomeça: ou acha o número seguinte, ou descobre que o teto acabou.
            continue

    raise AttemptsExhausted()


def list_all(tarefa_id: int) -> list[Tentativa]:
    with Session(engine) as s:
        return list(s.exec(
            select(Tentativa)
            .where(Tentativa.tarefa_id == tarefa_id)
            .order_by(Tentativa.numero)      # type: ignore
        ).all())


def best(tarefa_id: int) -> Optional[Tentativa]:
    with Session(engine) as s:
        return s.exec(
            select(Tentativa)
            .where(Tentativa.tarefa_id == tarefa_id)
            .order_by(Tentativa.acertos.desc())   # type: ignore
        ).first()


def review_points(tentativa: Tentativa, questoes: list[dict]) -> list[dict]:
    """
    Retorna lista de {id, area, enunciado, escolhida, correta, justificativa}
    apenas das questões ERRADAS.
    """
    try:
        respostas = json.loads(tentativa.respostas or "{}")
    except Exception:
        respostas = {}
    erros = []
    for q in questoes:
        qid = str(q.get("id"))
        correta = int(q.get("correta", -1))
        escolhida = respostas.get(qid)
        if escolhida is None or int(escolhida) != correta:
            erros.append({
                "id": q.get("id"),
                "area": q.get("area"),
                "enunciado": q.get("enunciado"),
                "escolhida": escolhida,
                "correta": correta,
                "justificativa": q.get("justificativa", ""),
                "alternativas": q.get("alternativas", []),
            })
    return erros