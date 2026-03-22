"""
🐺 Wolf Wallet — Bill Model (CRUD)

Operações de banco de dados para as tabelas `monthly_bills` e `bill_payments`.

Usage:
    from models.bill import get_active_bills, get_upcoming_bills, create_bill
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from config.database import execute_insert, execute_query, execute_update
from config.settings import UI

logger = logging.getLogger(__name__)


def get_all_bills() -> list[dict]:
    """
    Retorna todas as contas (ativas e inativas). Uso admin.

    Returns:
        Lista de contas com todos os campos.
    """
    return execute_query(
        "SELECT id, name, description, amount, due_day, recurrence, "
        "start_date, end_date, is_active, created_by, created_at "
        "FROM monthly_bills "
        "ORDER BY is_active DESC, due_day"
    )


def get_active_bills() -> list[dict]:
    """
    Retorna todas as contas ativas.

    Returns:
        Lista de contas com todos os campos.
    """
    return execute_query(
        "SELECT id, name, description, amount, due_day, recurrence, "
        "start_date, end_date, is_active, created_by, created_at "
        "FROM monthly_bills "
        "WHERE is_active = true "
        "ORDER BY due_day"
    )


def get_upcoming_bills(days: int | None = None) -> list[dict]:
    """
    Retorna contas cujo vencimento está nos próximos N dias.

    Args:
        days: Janela de dias (padrão: UI.BILL_ALERT_DAYS).

    Returns:
        Lista de contas com vencimento próximo.
    """
    if days is None:
        days = UI.BILL_ALERT_DAYS

    today = date.today()
    current_day = today.day

    # Calcula os dias alvo (considerando virada de mês)
    target_days = []
    for i in range(days + 1):
        future = today + timedelta(days=i)
        target_days.append(future.day)

    if not target_days:
        return []

    # Busca contas ativas cujo due_day está na janela
    placeholders = ", ".join(f":day_{i}" for i in range(len(target_days)))
    params = {f"day_{i}": d for i, d in enumerate(target_days)}

    return execute_query(
        f"SELECT id, name, description, amount, due_day, recurrence "
        f"FROM monthly_bills "
        f"WHERE is_active = true AND due_day IN ({placeholders}) "
        f"ORDER BY due_day",
        params,
    )


def get_bill_by_id(bill_id: int) -> dict | None:
    """Busca uma conta pelo ID."""
    rows = execute_query(
        "SELECT * FROM monthly_bills WHERE id = :id",
        {"id": bill_id},
    )
    return rows[0] if rows else None


def create_bill(
    name: str,
    amount: float,
    due_day: int,
    start_date: date,
    created_by: int,
    description: str | None = None,
    recurrence: str = "monthly",
    end_date: date | None = None,
) -> dict | None:
    """
    Cria uma nova conta mensal.

    Args:
        name: Nome da conta.
        amount: Valor mensal.
        due_day: Dia do vencimento (1-31).
        start_date: Data de início.
        created_by: ID do admin que criou.
        description: Descrição opcional.
        recurrence: 'monthly' ou 'temporary'.
        end_date: Data fim (obrigatória se temporary).

    Returns:
        Dict com dados da conta criada.

    Raises:
        ValueError: Se parâmetros inválidos.
    """
    if due_day < 1 or due_day > 31:
        raise ValueError("Dia de vencimento deve ser entre 1 e 31.")
    if amount <= 0:
        raise ValueError("Valor deve ser positivo.")
    if recurrence not in ("monthly", "temporary"):
        raise ValueError("Recorrência deve ser 'monthly' ou 'temporary'.")
    if recurrence == "temporary" and not end_date:
        raise ValueError("Contas temporárias precisam de data de fim.")

    bill_id = execute_insert(
        "INSERT INTO monthly_bills "
        "(name, description, amount, due_day, recurrence, start_date, end_date, created_by) "
        "VALUES (:name, :description, :amount, :due_day, :recurrence, :start_date, :end_date, :created_by) "
        "RETURNING id",
        {
            "name": name,
            "description": description,
            "amount": amount,
            "due_day": due_day,
            "recurrence": recurrence,
            "start_date": start_date,
            "end_date": end_date,
            "created_by": created_by,
        },
    )

    logger.info(f"Conta criada: {name} (id={bill_id})")
    return get_bill_by_id(bill_id) if bill_id else None


def update_bill(bill_id: int, **fields) -> bool:
    """Atualiza campos de uma conta."""
    allowed = {"name", "description", "amount", "due_day", "recurrence", "end_date", "is_active"}
    invalid = set(fields.keys()) - allowed
    if invalid:
        raise ValueError(f"Campos não permitidos: {invalid}")

    if not fields:
        return False

    set_clauses = [f"{k} = :{k}" for k in fields]
    params = {**fields, "id": bill_id}

    affected = execute_update(
        f"UPDATE monthly_bills SET {', '.join(set_clauses)} WHERE id = :id",
        params,
    )
    return affected > 0


def deactivate_bill(bill_id: int) -> bool:
    """Desativa uma conta (soft delete)."""
    affected = execute_update(
        "UPDATE monthly_bills SET is_active = false WHERE id = :id AND is_active = true",
        {"id": bill_id},
    )
    return affected > 0


def mark_bill_paid(
    bill_id: int,
    reference_month: date,
    paid_by: int,
    notes: str | None = None,
) -> bool:
    """
    Marca uma conta como paga em um mês.

    Args:
        bill_id: ID da conta.
        reference_month: Primeiro dia do mês de referência.
        paid_by: ID do admin que marcou.
        notes: Observações opcionais.

    Returns:
        True se marcou com sucesso.
    """
    execute_insert(
        "INSERT INTO bill_payments (bill_id, reference_month, paid, paid_at, paid_by, notes) "
        "VALUES (:bill_id, :ref_month, true, NOW(), :paid_by, :notes) "
        "ON CONFLICT (bill_id, reference_month) "
        "DO UPDATE SET paid = true, paid_at = NOW(), paid_by = :paid_by, notes = :notes "
        "RETURNING id",
        {
            "bill_id": bill_id,
            "ref_month": reference_month,
            "paid_by": paid_by,
            "notes": notes,
        },
    )
    return True


def get_bill_payment_status(bill_id: int, reference_month: date) -> dict | None:
    """Retorna o status de pagamento de uma conta em um mês."""
    rows = execute_query(
        "SELECT * FROM bill_payments WHERE bill_id = :bill_id AND reference_month = :ref_month",
        {"bill_id": bill_id, "ref_month": reference_month},
    )
    return rows[0] if rows else None


def get_monthly_bills_total() -> float:
    """Soma de todas as contas ativas."""
    rows = execute_query(
        "SELECT COALESCE(SUM(amount), 0) as total FROM monthly_bills WHERE is_active = true"
    )
    return float(rows[0]["total"]) if rows else 0.0
