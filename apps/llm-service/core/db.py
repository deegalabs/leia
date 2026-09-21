from __future__ import annotations
from datetime import datetime
import os
from pathlib import Path
from typing import Optional

from sqlmodel import SQLModel, Field, Session, create_engine, select
from sqlalchemy import Index, UniqueConstraint, inspect, text

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
    # LeIA: os dois são opcionais porque a cidadã não cria conta. O link que ela recebeu já prova que é ela:
    # foi endereçado a ela, tem validade e pode ser cancelado por quem enviou. Pedir senha depois disso é
    # pedir duas provas da mesma coisa, e cada campo a mais é uma pessoa a menos que chega ao fim.
    #
    # O `unique=True` do e-mail saiu daqui e virou índice único **parcial** em ``UNIQUE_INDEXES``: com várias
    # contas sem e-mail, "único" precisa passar a significar "único entre os que têm", senão a segunda
    # cidadã que entrar pelo link colide com a primeira.
    email: Optional[str] = Field(default=None, index=True)
    senha_hash: Optional[str] = None
    nome: str
    # LeIA: o número da OAB de quem se cadastra como advogado. Fica aqui e não em tabela própria porque é um
    # dado do cadastro, e é o que E16 vai precisar para publicar quem se cadastrou.
    oab: Optional[str] = None
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
    # LeIA: o SHA-256 do PDF como ele chegou, gravado no envio. O `documentSha256` do comprovante era
    # recalculado lendo `original.pdf`, e o arquivo passa a ser apagado logo depois da extração: sem esta
    # coluna, todo comprovante emitido depois disso apontaria para um documento que ninguém pode mais
    # conferir. O hash não é dado pessoal e sobrevive ao documento de propósito.
    document_sha256: Optional[str] = None
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
    # LeIA: quantas vezes a pessoa pediu para rever o trecho antes de responder cada pergunta, como JSON
    # ``{"id_da_pergunta": vezes}``. Entra no preimage do hash (``leia.attempt.v3``) e no comprovante, porque
    # número que circula ao lado da prova sem estar dentro dela é número que qualquer um troca depois.
    consultas: Optional[str] = None
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
    # LeIA: o nome de quem vai receber o documento. É obrigatório e o e-mail não é, porque é ele que a tela
    # da cidadã mostra para ela confirmar ("Sou eu, Maria") — e é o nome, não o endereço, que identifica
    # alguém para alguém. Endereço serve para entregar; nome serve para reconhecer.
    nome: Optional[str] = None
    email: Optional[str] = Field(default=None, index=True)
    # LeIA: de quem este convite passou a ser. A destinatária deixou de ser um endereço e passou a ser uma
    # conta, porque a conta que a confirmação de nome cria não tem e-mail nenhum para comparar. Fica nulo
    # enquanto ninguém reivindicou o convite.
    usuario_id: Optional[int] = Field(default=None, foreign_key="usuario.id", index=True)
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

        # ── Tabela usuario e convite ─────────────────────────────────────
        if inspect(conn).has_table("usuario") and "oab" not in _colunas(conn, "usuario"):
            conn.execute(text("ALTER TABLE usuario ADD COLUMN oab VARCHAR"))
            print("🔧 migração: usuario.oab adicionada")
        if inspect(conn).has_table("invite") and "nome" not in _colunas(conn, "invite"):
            conn.execute(text("ALTER TABLE invite ADD COLUMN nome VARCHAR"))
            print("🔧 migração: invite.nome adicionada")
        if inspect(conn).has_table("invite") and "usuario_id" not in _colunas(conn, "invite"):
            conn.execute(text("ALTER TABLE invite ADD COLUMN usuario_id INTEGER"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_invite_usuario_id ON invite (usuario_id)"))
            print("🔧 migração: invite.usuario_id adicionada")
        # O e-mail e a senha deixaram de ser obrigatórios, e banco que já existe mantém o `NOT NULL` de
        # quando foi criado. No Postgres dá para soltar; no SQLite exigiria reconstruir a tabela, e banco de
        # desenvolvimento é descartável, então ali a falha é registrada e a vida segue.
        if inspect(conn).has_table("usuario"):
            for coluna in ("email", "senha_hash"):
                try:
                    conn.execute(text(f"ALTER TABLE usuario ALTER COLUMN {coluna} DROP NOT NULL"))
                except Exception:
                    pass
            # O índice único antigo do e-mail precisa sair para o parcial entrar no lugar dele.
            try:
                conn.execute(text("DROP INDEX IF EXISTS ix_usuario_email"))
            except Exception:
                pass

        if "document_sha256" not in cols:
            conn.execute(text("ALTER TABLE tarefa ADD COLUMN document_sha256 VARCHAR"))
            print("🔧 migração: tarefa.document_sha256 adicionada")

        # ── Tabela tentativa ─────────────────────────────────────────────
        if inspect(conn).has_table("tentativa"):
            cols_tent = _colunas(conn, "tentativa")
            if "consultas" not in cols_tent:
                conn.execute(text("ALTER TABLE tentativa ADD COLUMN consultas VARCHAR"))
                print("🔧 migração: tentativa.consultas adicionada")
            # Esta é a única migração que **apaga** dado, e é essa a intenção: endereço de rede e navegador
            # ficaram no esquema depois que a v2 do hash parou de gravá-los, e o PDF assinado ainda os lia e
            # imprimia. Guardar dado sem finalidade contraria o art. 6º, III, e o que está sendo removido não
            # sustenta nada: não entra em prova, não entra no comprovante e nenhuma tela o usa.
            # As duas instruções são escritas por extenso, e não montadas num laço com interpolação: nome de
            # coluna não pode ser parâmetro de bind, então a única defesa é não construir o SQL por texto.
            # A versão interpolada seria segura por acidente, que é exatamente o que já foi corrigido em
            # ``_garantir_indices_unicos``.
            if "ip" in cols_tent:
                conn.execute(text("ALTER TABLE tentativa DROP COLUMN ip"))
                print("🔧 migração: tentativa.ip removida")
            if "user_agent" in cols_tent:
                conn.execute(text("ALTER TABLE tentativa DROP COLUMN user_agent"))
                print("🔧 migração: tentativa.user_agent removida")


# LeIA: ``create_all`` cria tabela que falta, nunca restrição em tabela que já existe. Um índice único
# criado à mão vale nos dois bancos e alcança o banco que já está em produção, que é onde a corrida mora.
# Cada linha é (nome, tabela, colunas, coluna que precisa não ser nula). A quarta, quando existe, torna o
# índice **parcial**: ele vale só para as linhas em que aquela coluna está preenchida. É o que permite muitas
# contas sem e-mail convivendo com e-mail único entre as que têm.
UNIQUE_INDEXES = (
    ("uq_tentativa_rodada", "tentativa", "tarefa_id, numero", None),
    ("uq_tentativa_hash", "tentativa", "hash_imutavel", None),
    ("uq_usuario_email", "usuario", "email", "email"),
)


def _garantir_indices_unicos() -> None:
    """Cria os índices acima, montando a instrução como estrutura e nunca como texto.

    Identificador de SQL não pode ser parâmetro de bind, então a defesa usual não se aplica: o que resolve
    é não construir a instrução por interpolação. ``Index`` resolve cada coluna contra a tabela declarada e
    cita os identificadores por conta própria, então um nome que não existe vira erro aqui em vez de virar
    SQL lá. O texto interpolado que estava aqui era seguro por acidente: os valores são literais deste
    módulo, e o driver do SQLite recusa duas instruções num ``execute``. Nenhuma das duas garantias é do
    nosso desenho, e produção roda Postgres.
    """
    for nome, tabela, colunas, nao_nula in UNIQUE_INDEXES:
        try:
            alvo = SQLModel.metadata.tables[tabela]
            colunas_do_indice = [alvo.c[c.strip()] for c in colunas.split(",")]
            # O predicado do índice parcial vai nos dois dialetos: os dois bancos o suportam, e a alternativa
            # seria escrever a instrução à mão, que é justamente o que esta função existe para não fazer.
            extra = {}
            if nao_nula:
                onde = alvo.c[nao_nula].isnot(None)
                extra = {"sqlite_where": onde, "postgresql_where": onde}
            with engine.begin() as conn:
                Index(nome, *colunas_do_indice, unique=True, **extra).create(conn, checkfirst=True)
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