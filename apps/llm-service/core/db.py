from __future__ import annotations
from datetime import datetime
import os
from pathlib import Path
from typing import Optional

from sqlmodel import SQLModel, Field, Session, create_engine
from sqlalchemy import text

DB_PATH = Path(os.getenv("DB_PATH", str(Path(os.getenv("DATA_DIR", ".")) / "gestao.db")))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)


# ══════════════════════════════════════════════════════════════════════════
#  MODELOS
# ══════════════════════════════════════════════════════════════════════════
class Usuario(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    senha_hash: str
    nome: str
    papel: str = "advogado"
    session_token: Optional[str] = Field(default=None, index=True)
    criado_em: datetime = Field(default_factory=datetime.utcnow)


class Tarefa(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hash: str = Field(index=True, unique=True)
    titulo: str
    advogado_id: int = Field(foreign_key="usuario.id", index=True)
    status: str = "criada"
    pdf_nome: Optional[str] = None
    workspace_path: Optional[str] = None
    clone_de: Optional[int] = Field(default=None, foreign_key="tarefa.id")
    rodada: int = 1
    criada_em: datetime = Field(default_factory=datetime.utcnow)
    atualizada_em: datetime = Field(default_factory=datetime.utcnow)


class LogEvento(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tarefa_id: int = Field(foreign_key="tarefa.id", index=True)
    ts: datetime = Field(default_factory=datetime.utcnow)
    tipo: str
    payload: Optional[str] = None


class Tentativa(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tarefa_id: int = Field(foreign_key="tarefa.id", index=True)
    numero: int = 1
    respostas: str
    acertos: int
    total: int
    aprovado: bool
    hash_imutavel: str
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    criada_em: datetime = Field(default_factory=datetime.utcnow)


# ══════════════════════════════════════════════════════════════════════════
#  MIGRAÇÕES IDEMPOTENTES
# ══════════════════════════════════════════════════════════════════════════
def _colunas(conn, tabela: str) -> set[str]:
    """Retorna o conjunto de colunas existentes de uma tabela SQLite."""
    rows = conn.execute(text(f"PRAGMA table_info({tabela})")).fetchall()
    return {r[1] for r in rows}


def _aplicar_migracoes() -> None:
    """
    Adiciona colunas que faltam sem quebrar o banco existente.
    Cada ALTER TABLE é verificado — só roda se a coluna não existir.
    """
    with engine.begin() as conn:
        # ── Tabela tarefa ────────────────────────────────────────────────
        try:
            cols = _colunas(conn, "tarefa")
        except Exception:
            return  # tabela não existe ainda — init_db cria

        if "clone_de" not in cols:
            conn.execute(text(
                "ALTER TABLE tarefa ADD COLUMN clone_de INTEGER"
            ))
            print("🔧 migração: tarefa.clone_de adicionada")

        if "rodada" not in cols:
            conn.execute(text(
                "ALTER TABLE tarefa ADD COLUMN rodada INTEGER DEFAULT 1"
            ))
            print("🔧 migração: tarefa.rodada adicionada")

        # ── Tabela tentativa (nova — pode não existir) ───────────────────
        # init_db() cria se não existir; aqui só garantimos que está lá.
        # Se a tabela existir mas faltar coluna, adiciona.
        try:
            cols_t = _colunas(conn, "tentativa")
        except Exception:
            cols_t = set()

        # (nenhuma migração de tentativa por enquanto — tabela é nova)


def init_db() -> None:
    """Cria tabelas novas + aplica migrações em tabelas existentes."""
    SQLModel.metadata.create_all(engine)
    _aplicar_migracoes()


def get_session():
    with Session(engine) as s:
        yield s