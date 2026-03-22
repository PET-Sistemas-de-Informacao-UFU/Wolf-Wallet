"""
🐺 Wolf Wallet — Password & Token Management

Módulo responsável por:
    - Hashing e verificação de senhas (bcrypt)
    - Geração de senhas temporárias
    - Geração, salvamento e validação de tokens de redefinição de senha
    - Validação de requisitos de força de senha

Usage:
    from auth.password import hash_password, verify_password, validate_password_strength
"""

from __future__ import annotations

import logging
import secrets
import string
from datetime import datetime, timedelta
from uuid import uuid4

import bcrypt

from config.database import execute_insert, execute_query, execute_update
from config.settings import Auth

logger = logging.getLogger(__name__)


# =============================================
# Password Hashing (bcrypt)
# =============================================

def hash_password(plain: str) -> str:
    """
    Gera o hash bcrypt de uma senha em texto puro.

    Args:
        plain: Senha em texto puro.

    Returns:
        Hash bcrypt como string.
    """
    salt = bcrypt.gensalt(rounds=Auth.BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(plain.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verifica se uma senha em texto puro corresponde ao hash.

    Args:
        plain: Senha em texto puro.
        hashed: Hash bcrypt armazenado.

    Returns:
        True se a senha corresponde ao hash.
    """
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception as e:
        logger.error(f"Erro ao verificar senha: {e}")
        return False


# =============================================
# Password Validation
# =============================================

def validate_password_strength(password: str) -> list[str]:
    """
    Valida a força de uma senha contra os requisitos do sistema.

    Args:
        password: Senha a ser validada.

    Returns:
        Lista de mensagens de erro. Lista vazia = senha válida.
    """
    errors: list[str] = []

    if len(password) < Auth.MIN_PASSWORD_LENGTH:
        errors.append(
            f"A senha deve ter no mínimo {Auth.MIN_PASSWORD_LENGTH} caracteres."
        )

    if Auth.REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
        errors.append("A senha deve conter pelo menos uma letra maiúscula.")

    if Auth.REQUIRE_DIGIT and not any(c.isdigit() for c in password):
        errors.append("A senha deve conter pelo menos um número.")

    return errors


# =============================================
# Temporary Password Generation
# =============================================

def generate_temp_password() -> str:
    """
    Gera uma senha temporária aleatória e segura.

    Returns:
        String alfanumérica com comprimento definido em Auth.TEMP_PASSWORD_LENGTH.
    """
    alphabet = string.ascii_letters + string.digits
    # Garante pelo menos 1 maiúscula e 1 dígito
    password = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
    ]
    password += [
        secrets.choice(alphabet) for _ in range(Auth.TEMP_PASSWORD_LENGTH - 2)
    ]
    # Embaralha para não ter padrão previsível
    shuffled = list(password)
    secrets.SystemRandom().shuffle(shuffled)
    return "".join(shuffled)


# =============================================
# Password Reset Tokens
# =============================================

def generate_reset_token() -> str:
    """
    Gera um token único para redefinição de senha.

    Returns:
        UUID4 como string.
    """
    return str(uuid4())


def save_reset_token(user_id: int, token: str) -> None:
    """
    Salva um token de redefinição no banco com expiração.

    Invalida tokens anteriores do mesmo usuário antes de criar o novo.

    Args:
        user_id: ID do usuário.
        token: Token gerado.
    """
    # Invalida tokens anteriores do mesmo usuário
    execute_update(
        "UPDATE password_reset_tokens SET used = true "
        "WHERE user_id = :user_id AND used = false",
        {"user_id": user_id},
    )

    expires_at = datetime.now() + timedelta(minutes=Auth.TOKEN_EXPIRATION_MINUTES)

    execute_insert(
        "INSERT INTO password_reset_tokens (user_id, token, expires_at) "
        "VALUES (:user_id, :token, :expires_at) RETURNING id",
        {
            "user_id": user_id,
            "token": token,
            "expires_at": expires_at,
        },
    )

    logger.info(f"Token de reset criado para user_id={user_id}, expira em {expires_at}")


def validate_reset_token(token: str) -> dict | None:
    """
    Valida um token de redefinição de senha.

    Verifica se:
        - O token existe
        - Não foi usado
        - Não expirou

    Args:
        token: Token recebido via URL.

    Returns:
        Dicionário com dados do token (id, user_id), ou None se inválido.
    """
    rows = execute_query(
        "SELECT id, user_id, expires_at "
        "FROM password_reset_tokens "
        "WHERE token = :token AND used = false",
        {"token": token},
    )

    if not rows:
        return None

    token_data = rows[0]

    # Verifica expiração
    if datetime.now() > token_data["expires_at"]:
        # Marca como expirado
        mark_token_used(token_data["id"])
        return None

    return token_data


def mark_token_used(token_id: int) -> None:
    """
    Marca um token como utilizado.

    Args:
        token_id: ID do token no banco.
    """
    execute_update(
        "UPDATE password_reset_tokens SET used = true WHERE id = :id",
        {"id": token_id},
    )
