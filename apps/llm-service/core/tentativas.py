"""Registro de tentativas do cliente + hash imutável de assinatura."""
from __future__ import annotations
import hashlib, json
from datetime import datetime
from typing import Optional

from sqlmodel import Session, select
from core.db import engine, Tentativa, Tarefa


def _proximo_numero(tarefa_id: int) -> int:
    with Session(engine) as s:
        ult = s.exec(
            select(Tentativa)
            .where(Tentativa.tarefa_id == tarefa_id)
            .order_by(Tentativa.numero.desc())   # type: ignore
        ).first()
    return (ult.numero + 1) if ult else 1


def _hash_imutavel(
    tarefa_hash: str, numero: int, respostas_json: str,
    ip: str, ua: str, ts: str,
) -> str:
    payload = f"PARA.AI|{tarefa_hash}|{numero}|{respostas_json}|{ip}|{ua}|{ts}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def registrar(
    tarefa: Tarefa,
    respostas: dict[int | str, int],
    questoes: list[dict],
    ip: Optional[str],
    user_agent: Optional[str],
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

    aprovado = acertos >= max(1, int(total * 0.83))   # ≥ 83% (10/12)

    numero = _proximo_numero(tarefa.id)
    respostas_json = json.dumps(respostas, ensure_ascii=False, sort_keys=True)
    ip_s = ip or "?"
    ua_s = (user_agent or "?")[:300]
    ts = datetime.utcnow().isoformat()

    h = _hash_imutavel(tarefa.hash, numero, respostas_json, ip_s, ua_s, ts)

    t = Tentativa(
        tarefa_id=tarefa.id,
        numero=numero,
        respostas=respostas_json,
        acertos=acertos,
        total=total,
        aprovado=aprovado,
        hash_imutavel=h,
        ip=ip_s,
        user_agent=ua_s,
    )
    with Session(engine) as s:
        s.add(t); s.commit(); s.refresh(t)
    return t


def listar(tarefa_id: int) -> list[Tentativa]:
    with Session(engine) as s:
        return list(s.exec(
            select(Tentativa)
            .where(Tentativa.tarefa_id == tarefa_id)
            .order_by(Tentativa.numero)      # type: ignore
        ).all())


def melhor(tarefa_id: int) -> Optional[Tentativa]:
    with Session(engine) as s:
        return s.exec(
            select(Tentativa)
            .where(Tentativa.tarefa_id == tarefa_id)
            .order_by(Tentativa.acertos.desc())   # type: ignore
        ).first()


def analisar_erros(tentativa: Tentativa, questoes: list[dict]) -> list[dict]:
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