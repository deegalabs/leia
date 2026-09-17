from __future__ import annotations
from datetime import datetime
import os
from pathlib import Path
from typing import Optional

from sqlmodel import SQLModel, Field, Session, create_engine, select
from sqlalchemy import UniqueConstraint, inspect, text

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
    # LeIA: as duas restrições abaixo são o que impede a corrida em ``core.attempts.record``. Sem elas o
    # número da rodada era escolhido numa sessão e gravado em outra, então dois envios simultâneos ficavam
    # com o mesmo número, furavam o teto de tentativas e produziam o mesmo ``hash_imutavel``, que é o
    # identificador público do comprovante. O banco é o único lugar onde isso se decide sem corrida.
    __table_args__ = (UniqueConstraint("tarefa_id", "numero", name="uq_tentativa_rodada"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    tarefa_id: int = Field(foreign_key="tarefa.id", index=True)
    numero: int = 1
    respostas: str
    acertos: int
    total: int
    aprovado: bool
    hash_imutavel: str = Field(unique=True)
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
    """Colunas existentes de uma tabela, em qualquer banco.

    O inspector do SQLAlchemy conversa com cada banco no dialeto dele — ``PRAGMA`` no SQLite,
    ``information_schema`` no Postgres. Consulta escrita à mão só funcionaria num dos dois.
    """
    return {c["name"] for c in inspect(conn).get_columns(tabela)}


def _aplicar_migracoes() -> None:
    """
    Adiciona colunas que faltam sem quebrar o banco existente.
    Cada ALTER TABLE é verificado — só roda se a coluna não existir.

    Roda nos dois bancos. ``create_all`` cria tabela que falta, nunca coluna que falta em tabela que já
    existe, e em produção o banco é Postgres: enquanto isto saía cedo fora do SQLite, coluna nova nascia
    só na máquina de quem desenvolve e a produção subia com o esquema antigo.
    """
    with engine.begin() as conn:
        # ── Tabela tarefa ────────────────────────────────────────────────
        if not inspect(conn).has_table("tarefa"):
            return  # banco novo — init_db cria o esquema inteiro

        cols = _colunas(conn, "tarefa")

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


# LeIA: ``create_all`` cria tabela que falta, nunca restrição em tabela que já existe. Um índice único
# criado à mão vale nos dois bancos e alcança o banco que já está em produção, que é onde a corrida mora.
UNIQUE_INDEXES = (
    ("uq_tentativa_rodada", "tentativa", "tarefa_id, numero"),
    ("uq_tentativa_hash", "tentativa", "hash_imutavel"),
)


def _garantir_indices_unicos() -> None:
    for nome, tabela, colunas in UNIQUE_INDEXES:
        try:
            with engine.begin() as conn:
                conn.execute(text(f"CREATE UNIQUE INDEX IF NOT EXISTS {nome} ON {tabela} ({colunas})"))
        except Exception as e:
            # Falha aqui quase sempre significa que o banco já tem duplicata, e recusar o boot por isso
            # seria pior que seguir. Mas o defeito precisa aparecer inteiro, não virar silêncio.
            print(f"⚠️  índice único {nome} em {tabela}({colunas}) não pôde ser criado: {e}. "
                  f"Enquanto ele não existir, duas tentativas simultâneas podem repetir rodada e hash.")


def init_db() -> None:
    """Cria tabelas novas + aplica migrações em tabelas existentes."""
    SQLModel.metadata.create_all(engine)
    _aplicar_migracoes()
    _garantir_indices_unicos()
    recover_orphaned_tasks()


def recover_orphaned_tasks() -> int:
    """Marca como ``falhou`` toda tarefa que ficou ``processando`` de um processo anterior.

    O workflow roda como ``BackgroundTask`` dentro deste processo, então quando o contêiner reinicia, e a
    hospedagem reinicia a cada deploy, a tarefa em voo fica ``processando`` para sempre: nada retoma, e
    ``reprocess`` recusa exatamente esse estado. O dono não reprocessa, não revisa e não aprova, enquanto a
    tela da pessoa segue dizendo "Estamos preparando a explicação". O documento morre calado.

    Rodar isto no boot é seguro porque o processo acabou de subir e ainda não agendou trabalho nenhum: toda
    tarefa ``processando`` no banco é, por definição, órfã de um processo que não existe mais. Isso vale
    enquanto o serviço rodar com um worker só (ver o CMD do Dockerfile); com mais de um, a varredura precisaria
    saber de quem é cada tarefa antes de mexer.
    """
    from core import workspace as ws

    with Session(engine) as s:
        presas = list(s.exec(select(Tarefa).where(Tarefa.status == "processando")))
        # Os valores saem daqui de dentro: fora da sessão o objeto está desanexado e ler um atributo estoura.
        marcadas = [(t.hash, t.id) for t in presas]
        for t in presas:
            t.status = "falhou"
            t.atualizada_em = datetime.utcnow()
            s.add(t)
        if presas:
            s.commit()
    for hash_, tarefa_id in marcadas:
        # O log é onde a jornada conta o que houve, então o motivo fica escrito e não só inferido.
        ws.record_event(hash_, "interrompida_por_reinicio", tarefa_id=tarefa_id)
    if marcadas:
        print(f"🔧 {len(marcadas)} tarefa(s) presas em 'processando' de um processo anterior marcadas como 'falhou'")
    return len(marcadas)


def get_session():
    with Session(engine) as s:
        yield s