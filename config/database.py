"""
🐺 Wolf Wallet — Database Connection Module

Gerencia a conexão com o PostgreSQL (Supabase) usando SQLAlchemy.
Suporta leitura de credenciais via st.secrets (deploy) ou .env (local).

Usage:
    from config.database import get_engine, get_connection

    # Com SQLAlchemy engine (para pandas, ORM, etc.)
    engine = get_engine()
    df = pd.read_sql(query, engine)

    # Com context manager (para queries diretas)
    with get_connection() as conn:
        result = conn.execute(text("SELECT * FROM users"))
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.pool import QueuePool

from config.settings import Database

logger = logging.getLogger(__name__)

# =============================================
# Singleton: engine é criado uma vez e reutilizado
# =============================================
_engine: Engine | None = None


def _get_database_url() -> str:
    """
    Obtém a DATABASE_URL das credenciais disponíveis.

    Prioridade:
        1. st.secrets (Streamlit Cloud / secrets.toml local)
        2. Variável de ambiente via python-dotenv (.env)

    Returns:
        str: Connection string do PostgreSQL.

    Raises:
        RuntimeError: Se nenhuma credencial for encontrada.
    """
    # Tentativa 1: Streamlit Secrets
    try:
        import streamlit as st
        database_url = st.secrets.get("DATABASE_URL")
        if database_url:
            logger.info("DATABASE_URL carregada via st.secrets.")
            return database_url
    except Exception:
        pass

    # Tentativa 2: Variável de ambiente (.env)
    try:
        import os
        from dotenv import load_dotenv

        load_dotenv()
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            logger.info("DATABASE_URL carregada via .env.")
            return database_url
    except ImportError:
        pass

    raise RuntimeError(
        "DATABASE_URL não encontrada. "
        "Configure em .streamlit/secrets.toml ou no arquivo .env. "
        "Consulte docs/wolf-wallet-spec.md seção 4 para detalhes."
    )


def get_engine() -> Engine:
    """
    Retorna o SQLAlchemy Engine (singleton com connection pool).

    O engine é criado uma vez e reutilizado em todas as chamadas.
    Usa QueuePool para gerenciar conexões de forma eficiente.

    Returns:
        Engine: SQLAlchemy engine configurado.

    Raises:
        RuntimeError: Se não conseguir conectar ao banco.
    """
    global _engine

    if _engine is not None:
        return _engine

    try:
        database_url = _get_database_url()

        _engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=Database.POOL_SIZE,
            max_overflow=Database.MAX_OVERFLOW,
            pool_timeout=Database.POOL_TIMEOUT,
            pool_recycle=Database.POOL_RECYCLE,
            pool_pre_ping=True,  # Verifica se a conexão está ativa antes de usar
            echo=False,  # True para debug SQL (desligar em produção)
        )

        # Testa a conexão
        with _engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        logger.info("Conexão com o banco de dados estabelecida com sucesso.")
        return _engine

    except RuntimeError:
        raise
    except Exception as e:
        _engine = None
        logger.error(f"Falha ao conectar com o banco de dados: {e}")
        raise RuntimeError(
            f"Não foi possível conectar ao banco de dados. "
            f"Verifique suas credenciais e se o Supabase está acessível. "
            f"Erro: {e}"
        ) from e


@contextmanager
def get_connection() -> Generator[Connection, None, None]:
    """
    Context manager para obter uma conexão do pool.

    Gerencia automaticamente commit/rollback e devolve a conexão ao pool.

    Usage:
        with get_connection() as conn:
            result = conn.execute(text("SELECT * FROM users WHERE id = :id"), {"id": 1})
            user = result.fetchone()

    Yields:
        Connection: Conexão ativa do SQLAlchemy.

    Raises:
        RuntimeError: Se não conseguir obter conexão.
    """
    engine = get_engine()

    try:
        with engine.connect() as conn:
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
    except RuntimeError:
        raise
    except Exception as e:
        logger.error(f"Erro durante operação no banco de dados: {e}")
        raise


def execute_query(query: str, params: dict | None = None) -> list[dict]:
    """
    Executa uma query SELECT e retorna os resultados como lista de dicts.

    Atalho conveniente para queries simples de leitura.

    Args:
        query: SQL query string (use :param para parâmetros).
        params: Dicionário de parâmetros para a query.

    Returns:
        list[dict]: Lista de registros como dicionários.

    Example:
        users = execute_query(
            "SELECT * FROM users WHERE role = :role",
            {"role": "admin"}
        )
    """
    with get_connection() as conn:
        result = conn.execute(text(query), params or {})
        columns = result.keys()
        return [dict(zip(columns, row)) for row in result.fetchall()]


def execute_insert(query: str, params: dict | None = None) -> int | None:
    """
    Executa uma query INSERT e retorna o ID do registro inserido.

    Args:
        query: SQL INSERT com RETURNING id.
        params: Dicionário de parâmetros.

    Returns:
        int | None: ID do registro inserido, ou None se não retornar.

    Example:
        user_id = execute_insert(
            "INSERT INTO users (name, email) VALUES (:name, :email) RETURNING id",
            {"name": "João", "email": "joao@ufu.br"}
        )
    """
    with get_connection() as conn:
        result = conn.execute(text(query), params or {})
        row = result.fetchone()
        return row[0] if row else None


def execute_update(query: str, params: dict | None = None) -> int:
    """
    Executa uma query UPDATE/DELETE e retorna a quantidade de linhas afetadas.

    Args:
        query: SQL UPDATE ou DELETE.
        params: Dicionário de parâmetros.

    Returns:
        int: Número de linhas afetadas.

    Example:
        affected = execute_update(
            "UPDATE users SET is_active = false WHERE id = :id",
            {"id": 5}
        )
    """
    with get_connection() as conn:
        result = conn.execute(text(query), params or {})
        return result.rowcount


def check_health() -> bool:
    """
    Verifica se o banco de dados está acessível.

    Returns:
        bool: True se a conexão está saudável.
    """
    try:
        with get_connection() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Health check falhou: {e}")
        return False
