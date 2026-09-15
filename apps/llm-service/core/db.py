from __future__ import annotations
from datetime import datetime
import os
from pathlib import Path
from typing import Optional

from sqlmodel import SQLModel, Field, Session, create_engine
from sqlalchemy import text

DB_PATH = Path(os.getenv("DB_PATH", str(Path(os.getenv("DATA_DIR", ".")) / "gestao.db")))


# LeIA: Postgres when DATABASE_URL is set (Railway), SQLite at DB_PATH otherwise
def _database_url() -> str:
    url = (os.getenv("DATABASE_URL") or "").strip()
    if not url:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{DB_PATH}"
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


DATABASE_URL = _database_url()
IS_SQLITE = DATABASE_URL.startswith("sqlite")
engine = (create_engine(DATABASE_URL, echo=False) if IS_SQLITE
          else create_engine(DATABASE_URL, echo=False, pool_pre_ping=True))


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
    # LeIA: citizen account linked to the task (null when nobody linked it) and who sent the document
    cidadao_id: Optional[int] = Field(default=None, foreign_key="usuario.id", index=True)
    origem: str = "advogado"


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


# LeIA: the consent record as it was published, frozen when the attempt was approved.
# Rebuilding it from the database on every visit meant the record changed whenever a row changed, and the
# timestamp then proved a record that no longer existed. New table, so no column migration is needed.
class ConsentRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    attempt_hash: str = Field(index=True, unique=True)
    document_sha256: str = ""
    summary_sha256: str = ""
    canonical: str = ""
    payload_sha256: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


# LeIA: the invite that governs a document link. Without one, the link works as it always did;
# with one, the link can expire, be revoked, and be addressed to a single person.
# New table, so create_all builds it on Postgres too: this needs no column migration.
class Invite(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="tarefa.id", index=True)
    email: Optional[str] = Field(default=None, index=True)
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: int = Field(foreign_key="usuario.id")


# LeIA: doubt sent by the citizen to the lawyer who owns the task
class Duvida(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tarefa_id: int = Field(foreign_key="tarefa.id", index=True)
    texto: str
    contexto: Optional[str] = None  # JSON text: [{"role": "user"|"bot", "text": "..."}]
    criada_em: datetime = Field(default_factory=datetime.utcnow)
    respondida: bool = False
    resposta: Optional[str] = None
    respondida_em: Optional[datetime] = None


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
    if not IS_SQLITE:  # LeIA: PRAGMA is SQLite only; on Postgres create_all builds the full schema
        return
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

        # LeIA: v3 columns (citizen link and origin of the document)
        if "cidadao_id" not in cols:
            conn.execute(text(
                "ALTER TABLE tarefa ADD COLUMN cidadao_id INTEGER REFERENCES usuario(id)"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_tarefa_cidadao_id ON tarefa (cidadao_id)"
            ))
            print("🔧 migração: tarefa.cidadao_id adicionada")

        if "origem" not in cols:
            conn.execute(text(
                "ALTER TABLE tarefa ADD COLUMN origem VARCHAR NOT NULL DEFAULT 'advogado'"
            ))
            print("🔧 migração: tarefa.origem adicionada")

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