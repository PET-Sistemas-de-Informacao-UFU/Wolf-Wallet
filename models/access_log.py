"""
🐺 Wolf Wallet — Access Log Model (CRUD)

Operações de banco para a tabela `access_log`.
Auditoria de acessos: 1 evento por sessão (login de membro ou visitante).

Usage:
    from models.access_log import log_access, get_access_stats, get_top_users
"""

from __future__ import annotations

import logging

from config.database import execute_insert, execute_query

logger = logging.getLogger(__name__)

_VALID_EVENTS = ("login", "visitor")


def log_access(
    event_type: str,
    user_id: int | None = None,
    user_email: str | None = None,
    role: str | None = None,
) -> int | None:
    """
    Registra um acesso no log de auditoria.

    Args:
        event_type: 'login' (membro autenticado) ou 'visitor' (modo demo).
        user_id: ID do usuário (None para visitante).
        user_email: Email do usuário (snapshot; None para visitante).
        role: Papel do usuário (admin/user; None para visitante).

    Returns:
        ID do registro criado, ou None em caso de falha (best-effort).
    """
    if event_type not in _VALID_EVENTS:
        raise ValueError(f"event_type inválido: {event_type}. Use {_VALID_EVENTS}.")

    try:
        return execute_insert(
            "INSERT INTO access_log (event_type, user_id, user_email, role) "
            "VALUES (:event_type, :user_id, :user_email, :role) "
            "RETURNING id",
            {
                "event_type": event_type,
                "user_id": user_id,
                "user_email": user_email,
                "role": role,
            },
        )
    except Exception:
        # Auditoria nunca deve quebrar o fluxo de login/acesso
        logger.exception("Falha ao registrar acesso no access_log.")
        return None


def get_access_stats(days: int = 30) -> dict:
    """
    Retorna estatísticas agregadas de acesso no período.

    Args:
        days: Janela em dias (a partir de agora).

    Returns:
        Dict com: total, logins, visitors, unique_users.
    """
    rows = execute_query(
        "SELECT "
        "  COUNT(*) AS total, "
        "  COUNT(*) FILTER (WHERE event_type = 'login') AS logins, "
        "  COUNT(*) FILTER (WHERE event_type = 'visitor') AS visitors, "
        "  COUNT(DISTINCT user_email) FILTER (WHERE event_type = 'login') AS unique_users "
        "FROM access_log "
        "WHERE created_at >= NOW() - (:days || ' days')::interval",
        {"days": days},
    )
    if rows and rows[0]:
        return rows[0]
    return {"total": 0, "logins": 0, "visitors": 0, "unique_users": 0}


def get_top_users(days: int = 30, limit: int = 10) -> list[dict]:
    """
    Ranking de quem mais acessa (por email), apenas eventos de login.

    Args:
        days: Janela em dias.
        limit: Máximo de usuários no ranking.

    Returns:
        Lista de dicts com: user_email, role, accesses, last_access.
    """
    return execute_query(
        "SELECT "
        "  COALESCE(user_email, '(sem email)') AS user_email, "
        "  MAX(role) AS role, "
        "  COUNT(*) AS accesses, "
        "  MAX(created_at) AS last_access "
        "FROM access_log "
        "WHERE event_type = 'login' "
        "  AND created_at >= NOW() - (:days || ' days')::interval "
        "GROUP BY user_email "
        "ORDER BY accesses DESC, last_access DESC "
        "LIMIT :limit",
        {"days": days, "limit": limit},
    )


def get_access_timeseries(days: int = 30) -> list[dict]:
    """
    Série temporal diária de acessos (membros x visitantes).

    Args:
        days: Janela em dias.

    Returns:
        Lista de dicts com: dia, logins, visitors.
    """
    return execute_query(
        "SELECT "
        "  created_at::date AS dia, "
        "  COUNT(*) FILTER (WHERE event_type = 'login') AS logins, "
        "  COUNT(*) FILTER (WHERE event_type = 'visitor') AS visitors "
        "FROM access_log "
        "WHERE created_at >= NOW() - (:days || ' days')::interval "
        "GROUP BY dia "
        "ORDER BY dia",
        {"days": days},
    )


def get_recent_accesses(limit: int = 30) -> list[dict]:
    """
    Últimos acessos registrados.

    Args:
        limit: Quantidade máxima de registros.

    Returns:
        Lista de dicts com: event_type, user_email, role, created_at.
    """
    return execute_query(
        "SELECT event_type, user_email, role, created_at "
        "FROM access_log "
        "ORDER BY created_at DESC "
        "LIMIT :limit",
        {"limit": limit},
    )
