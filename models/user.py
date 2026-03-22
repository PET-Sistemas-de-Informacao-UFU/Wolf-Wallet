"""
🐺 Wolf Wallet — User Model (CRUD)

Operações de banco de dados para a tabela `users`.
Todas as queries são parametrizadas para prevenir SQL injection.

Usage:
    from models.user import get_user_by_email, create_user
"""

from __future__ import annotations

import logging
from datetime import datetime

from config.database import execute_insert, execute_query, execute_update

logger = logging.getLogger(__name__)


def get_user_by_email(email: str) -> dict | None:
    """
    Busca um usuário pelo email.

    Args:
        email: Email do usuário.

    Returns:
        Dicionário com os dados do usuário, ou None se não encontrado.
    """
    rows = execute_query(
        "SELECT id, name, email, password_hash, role, is_active, created_at, updated_at "
        "FROM users WHERE email = :email",
        {"email": email.strip().lower()},
    )
    return rows[0] if rows else None


def get_user_by_id(user_id: int) -> dict | None:
    """
    Busca um usuário pelo ID.

    Args:
        user_id: ID do usuário.

    Returns:
        Dicionário com os dados do usuário, ou None se não encontrado.
    """
    rows = execute_query(
        "SELECT id, name, email, password_hash, role, is_active, created_at, updated_at "
        "FROM users WHERE id = :id",
        {"id": user_id},
    )
    return rows[0] if rows else None


def get_all_users(include_inactive: bool = False) -> list[dict]:
    """
    Retorna todos os usuários.

    Args:
        include_inactive: Se True, inclui usuários desativados.

    Returns:
        Lista de dicionários com os dados dos usuários.
    """
    if include_inactive:
        return execute_query(
            "SELECT id, name, email, role, is_active, created_at, updated_at "
            "FROM users ORDER BY name"
        )
    return execute_query(
        "SELECT id, name, email, role, is_active, created_at, updated_at "
        "FROM users WHERE is_active = true ORDER BY name"
    )


def get_active_members() -> list[dict]:
    """
    Retorna todos os membros ativos (para contribuições).

    Returns:
        Lista de usuários ativos com id, name, email.
    """
    return execute_query(
        "SELECT id, name, email, role "
        "FROM users WHERE is_active = true ORDER BY name"
    )


def create_user(name: str, email: str, password_hash: str, role: str = "user") -> dict | None:
    """
    Cria um novo usuário.

    Args:
        name: Nome completo.
        email: Email (será normalizado para lowercase).
        password_hash: Hash bcrypt da senha.
        role: 'admin' ou 'user'.

    Returns:
        Dicionário com os dados do usuário criado, ou None em caso de erro.

    Raises:
        ValueError: Se o email já estiver cadastrado ou role inválido.
    """
    email = email.strip().lower()

    if role not in ("admin", "user"):
        raise ValueError(f"Role inválido: {role}. Use 'admin' ou 'user'.")

    existing = get_user_by_email(email)
    if existing:
        raise ValueError(f"Email já cadastrado: {email}")

    try:
        user_id = execute_insert(
            "INSERT INTO users (name, email, password_hash, role) "
            "VALUES (:name, :email, :password_hash, :role) RETURNING id",
            {
                "name": name.strip(),
                "email": email,
                "password_hash": password_hash,
                "role": role,
            },
        )
        logger.info(f"Usuário criado: {email} (role={role}, id={user_id})")
        return get_user_by_id(user_id)

    except Exception as e:
        logger.error(f"Erro ao criar usuário {email}: {e}")
        raise


def update_user(user_id: int, **fields) -> bool:
    """
    Atualiza campos de um usuário.

    Args:
        user_id: ID do usuário.
        **fields: Campos a atualizar (name, email, role, password_hash).

    Returns:
        True se atualizou, False se nenhum registro foi afetado.

    Raises:
        ValueError: Se tentar atualizar campo não permitido.
    """
    allowed_fields = {"name", "email", "role", "password_hash", "is_active"}
    invalid = set(fields.keys()) - allowed_fields
    if invalid:
        raise ValueError(f"Campos não permitidos: {invalid}")

    if not fields:
        return False

    # Normaliza email se presente
    if "email" in fields:
        fields["email"] = fields["email"].strip().lower()

    # Monta SET dinâmico
    set_clauses = [f"{key} = :{key}" for key in fields]
    set_sql = ", ".join(set_clauses)

    params = {**fields, "id": user_id}

    affected = execute_update(
        f"UPDATE users SET {set_sql}, updated_at = NOW() WHERE id = :id",
        params,
    )

    if affected > 0:
        logger.info(f"Usuário {user_id} atualizado: {list(fields.keys())}")

    return affected > 0


def deactivate_user(user_id: int) -> bool:
    """
    Desativa um usuário (soft delete).

    Args:
        user_id: ID do usuário.

    Returns:
        True se desativou, False se não encontrou.
    """
    affected = execute_update(
        "UPDATE users SET is_active = false, updated_at = NOW() WHERE id = :id AND is_active = true",
        {"id": user_id},
    )

    if affected > 0:
        logger.info(f"Usuário {user_id} desativado.")

    return affected > 0


def reactivate_user(user_id: int) -> bool:
    """
    Reativa um usuário desativado.

    Args:
        user_id: ID do usuário.

    Returns:
        True se reativou, False se não encontrou.
    """
    affected = execute_update(
        "UPDATE users SET is_active = true, updated_at = NOW() WHERE id = :id AND is_active = false",
        {"id": user_id},
    )

    if affected > 0:
        logger.info(f"Usuário {user_id} reativado.")

    return affected > 0


def count_users(active_only: bool = True) -> int:
    """
    Conta o total de usuários.

    Args:
        active_only: Se True, conta apenas ativos.

    Returns:
        Quantidade de usuários.
    """
    if active_only:
        rows = execute_query("SELECT COUNT(*) as total FROM users WHERE is_active = true")
    else:
        rows = execute_query("SELECT COUNT(*) as total FROM users")

    return rows[0]["total"] if rows else 0
