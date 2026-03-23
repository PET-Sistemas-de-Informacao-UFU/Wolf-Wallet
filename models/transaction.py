"""
🐺 Wolf Wallet — Transaction Model (CRUD)

Operações de banco de dados para a tabela `transactions`.
Fonte única de verdade financeira — dados sincronizados do Mercado Pago.

Usage:
    from models.transaction import get_balance, get_monthly_summary, get_recent_transactions
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal

import pandas as pd

from config.database import execute_query, get_engine
from config.settings import Finance

logger = logging.getLogger(__name__)


def get_balance() -> Decimal:
    """
    Calcula o saldo atual (soma líquida de todas as transações).

    Returns:
        Decimal: Saldo total.
    """
    rows = execute_query(
        "SELECT COALESCE(SUM(settlement_net_amount), 0) as balance FROM transactions"
    )
    return Decimal(str(rows[0]["balance"])) if rows else Decimal("0")


def get_monthly_inflows(year: int, month: int) -> Decimal:
    """
    Soma das entradas (valores positivos) de um mês.

    Args:
        year: Ano.
        month: Mês (1-12).

    Returns:
        Decimal: Total de entradas.
    """
    rows = execute_query(
        "SELECT COALESCE(SUM(transaction_amount), 0) as total "
        "FROM transactions "
        "WHERE transaction_amount > 0 "
        "AND EXTRACT(YEAR FROM transaction_date) = :year "
        "AND EXTRACT(MONTH FROM transaction_date) = :month",
        {"year": year, "month": month},
    )
    return Decimal(str(rows[0]["total"])) if rows else Decimal("0")


def get_monthly_outflows(year: int, month: int) -> Decimal:
    """
    Soma das saídas (valores negativos) de um mês.

    Args:
        year: Ano.
        month: Mês (1-12).

    Returns:
        Decimal: Total de saídas (valor negativo).
    """
    rows = execute_query(
        "SELECT COALESCE(SUM(transaction_amount), 0) as total "
        "FROM transactions "
        "WHERE transaction_amount < 0 "
        "AND EXTRACT(YEAR FROM transaction_date) = :year "
        "AND EXTRACT(MONTH FROM transaction_date) = :month",
        {"year": year, "month": month},
    )
    return Decimal(str(rows[0]["total"])) if rows else Decimal("0")


def get_monthly_yields(year: int, month: int) -> Decimal:
    """
    Soma dos rendimentos CDI de um mês.

    Rendimentos: SETTLEMENT, payment_method vazio, valor positivo < threshold.

    Args:
        year: Ano.
        month: Mês (1-12).

    Returns:
        Decimal: Total de rendimentos líquidos.
    """
    rows = execute_query(
        "SELECT COALESCE(SUM(settlement_net_amount), 0) as total "
        "FROM transactions "
        "WHERE transaction_type = 'SETTLEMENT' "
        "AND (payment_method IS NULL OR payment_method = '') "
        "AND ABS(transaction_amount) < :threshold "
        "AND EXTRACT(YEAR FROM transaction_date) = :year "
        "AND EXTRACT(MONTH FROM transaction_date) = :month",
        {"threshold": float(Finance.YIELD_THRESHOLD), "year": year, "month": month},
    )
    return Decimal(str(rows[0]["total"])) if rows else Decimal("0")


def get_monthly_yield_breakdown(year: int, month: int) -> dict:
    """
    Breakdown dos rendimentos CDI de um mês: bruto, imposto, líquido.

    - Bruto: SETTLEMENT, sem payment_method, valor positivo < threshold
    - Imposto: SETTLEMENT, sem payment_method, valor negativo, ABS < threshold
    - Líquido: bruto + imposto

    Args:
        year: Ano.
        month: Mês (1-12).

    Returns:
        Dict com: gross, tax, net (todos Decimal).
    """
    rows = execute_query(
        "SELECT "
        "  COALESCE(SUM(CASE WHEN transaction_amount > 0 THEN transaction_amount ELSE 0 END), 0) as gross, "
        "  COALESCE(SUM(CASE WHEN transaction_amount < 0 THEN transaction_amount ELSE 0 END), 0) as tax, "
        "  COALESCE(SUM(settlement_net_amount), 0) as net "
        "FROM transactions "
        "WHERE transaction_type = 'SETTLEMENT' "
        "AND (payment_method IS NULL OR payment_method = '') "
        "AND ABS(transaction_amount) < :threshold "
        "AND EXTRACT(YEAR FROM transaction_date) = :year "
        "AND EXTRACT(MONTH FROM transaction_date) = :month",
        {"threshold": float(Finance.YIELD_THRESHOLD), "year": year, "month": month},
    )

    if rows:
        return {
            "gross": Decimal(str(rows[0]["gross"])),
            "tax": Decimal(str(rows[0]["tax"])),
            "net": Decimal(str(rows[0]["net"])),
        }

    return {"gross": Decimal("0"), "tax": Decimal("0"), "net": Decimal("0")}


def get_yield_history(months: int = 12) -> pd.DataFrame:
    """
    Histórico de rendimentos agrupados por mês (bruto, imposto, líquido).

    Args:
        months: Quantidade de meses para trás.

    Returns:
        DataFrame com colunas: month, gross, tax, net_yield.
    """
    rows = execute_query(
        "SELECT "
        "  TO_CHAR(transaction_date, 'YYYY-MM') as month, "
        "  COALESCE(SUM(CASE WHEN transaction_amount > 0 THEN transaction_amount ELSE 0 END), 0) as gross, "
        "  COALESCE(SUM(CASE WHEN transaction_amount < 0 THEN ABS(transaction_amount) ELSE 0 END), 0) as tax, "
        "  COALESCE(SUM(settlement_net_amount), 0) as net_yield "
        "FROM transactions "
        "WHERE transaction_type = 'SETTLEMENT' "
        "AND (payment_method IS NULL OR payment_method = '') "
        "AND ABS(transaction_amount) < :threshold "
        "GROUP BY TO_CHAR(transaction_date, 'YYYY-MM') "
        "ORDER BY month",
        {"threshold": float(Finance.YIELD_THRESHOLD)},
    )

    if not rows:
        return pd.DataFrame(columns=["month", "gross", "tax", "net_yield"])

    return pd.DataFrame(rows)


def get_monthly_summary(year: int, month: int) -> dict:
    """
    Resumo financeiro de um mês.

    Returns:
        Dict com: inflows, outflows, yields, net.
    """
    inflows = get_monthly_inflows(year, month)
    outflows = get_monthly_outflows(year, month)
    yields = get_monthly_yields(year, month)

    return {
        "inflows": inflows,
        "outflows": outflows,
        "yields": yields,
        "net": inflows + outflows,  # outflows é negativo
    }


def get_recent_transactions(limit: int = 10) -> list[dict]:
    """
    Retorna as transações mais recentes.

    Args:
        limit: Quantidade máxima de resultados.

    Returns:
        Lista de dicts com dados da transação.
    """
    return execute_query(
        "SELECT id, source_id, external_reference, payment_method, "
        "transaction_type, transaction_amount, transaction_currency, "
        "transaction_date, fee_amount, settlement_net_amount, payment_description "
        "FROM transactions "
        "ORDER BY transaction_date DESC "
        "LIMIT :limit",
        {"limit": limit},
    )


def get_transactions(
    start_date: date | None = None,
    end_date: date | None = None,
    transaction_type: str | None = None,
    payment_method: str | None = None,
    direction: str | None = None,
    search: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[dict], int]:
    """
    Busca transações com filtros, paginação e contagem total.

    Args:
        start_date: Data início do filtro.
        end_date: Data fim do filtro.
        transaction_type: SETTLEMENT, REFUND, PAYOUTS.
        payment_method: pix, account_money, credit_card.
        direction: 'inflows' (positivo), 'outflows' (negativo), None (todos).
        search: Busca por source_id ou external_reference.
        page: Número da página (1-based).
        per_page: Itens por página.

    Returns:
        Tupla (lista de transações, total de registros).
    """
    conditions: list[str] = []
    params: dict = {}

    if start_date:
        conditions.append("transaction_date >= :start_date")
        params["start_date"] = datetime.combine(start_date, datetime.min.time())

    if end_date:
        conditions.append("transaction_date <= :end_date")
        params["end_date"] = datetime.combine(end_date, datetime.max.time())

    if transaction_type:
        conditions.append("transaction_type = :transaction_type")
        params["transaction_type"] = transaction_type

    if payment_method:
        conditions.append("payment_method = :payment_method")
        params["payment_method"] = payment_method

    if direction == "inflows":
        conditions.append("transaction_amount > 0")
    elif direction == "outflows":
        conditions.append("transaction_amount < 0")

    if search:
        conditions.append(
            "(source_id ILIKE :search OR external_reference ILIKE :search)"
        )
        params["search"] = f"%{search}%"

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Total count
    count_rows = execute_query(
        f"SELECT COUNT(*) as total FROM transactions WHERE {where_clause}",
        params,
    )
    total = count_rows[0]["total"] if count_rows else 0

    # Paginated results
    offset = (page - 1) * per_page
    params["limit"] = per_page
    params["offset"] = offset

    rows = execute_query(
        f"SELECT id, source_id, external_reference, payment_method, "
        f"transaction_type, transaction_amount, transaction_currency, "
        f"transaction_date, fee_amount, settlement_net_amount, payment_description "
        f"FROM transactions WHERE {where_clause} "
        f"ORDER BY transaction_date DESC "
        f"LIMIT :limit OFFSET :offset",
        params,
    )

    return rows, total


def get_monthly_chart_data(months: int = 12) -> pd.DataFrame:
    """
    Dados agrupados por mês para gráfico de barras (entradas vs saídas).

    Args:
        months: Quantidade de meses para trás.

    Returns:
        DataFrame com colunas: month, inflows, outflows.
    """
    rows = execute_query(
        "SELECT "
        "  TO_CHAR(transaction_date, 'YYYY-MM') as month, "
        "  COALESCE(SUM(CASE WHEN transaction_amount > 0 THEN transaction_amount ELSE 0 END), 0) as inflows, "
        "  COALESCE(SUM(CASE WHEN transaction_amount < 0 THEN ABS(transaction_amount) ELSE 0 END), 0) as outflows "
        "FROM transactions "
        "WHERE transaction_date >= NOW() - INTERVAL ':months months' "
        "GROUP BY TO_CHAR(transaction_date, 'YYYY-MM') "
        "ORDER BY month",
        {"months": months},
    )

    if not rows:
        return pd.DataFrame(columns=["month", "inflows", "outflows"])

    return pd.DataFrame(rows)


# Métodos de pagamento de cartão de crédito — excluídos da importação.
# A API Settlement Report do Mercado Pago inclui compras pessoais feitas
# com cartão de crédito vinculado à conta, que NÃO pertencem ao caixa
# do PET-SI. Apenas PIX, saldo em conta e rendimentos são relevantes.
_EXCLUDED_PAYMENT_METHODS: set[str] = {
    "master", "visa", "amex", "debit_card", "credit_card",
    "elo", "hipercard", "diners",
}


def insert_transactions_batch(df: pd.DataFrame) -> int:
    """
    Insere transações em batch (ignora duplicatas).

    Transações com payment_method de cartão de crédito/débito são
    automaticamente filtradas pois não pertencem ao caixa do PET-SI.

    Args:
        df: DataFrame com colunas alinhadas à tabela transactions.

    Returns:
        Número de registros efetivamente inseridos.
    """
    from config.database import get_connection
    from sqlalchemy import text

    if df.empty:
        return 0

    # Filtra transações de cartão de crédito/débito
    if "payment_method" in df.columns:
        before = len(df)
        df = df[~df["payment_method"].fillna("").str.lower().isin(_EXCLUDED_PAYMENT_METHODS)]
        excluded = before - len(df)
        if excluded > 0:
            logger.info(f"Filtradas {excluded} transações de cartão de crédito/débito.")

    if df.empty:
        return 0

    inserted = 0
    with get_connection() as conn:
        for _, row in df.iterrows():
            try:
                result = conn.execute(
                    text(
                        "INSERT INTO transactions "
                        "(source_id, external_reference, payment_method, "
                        "transaction_type, transaction_amount, transaction_currency, "
                        "transaction_date, fee_amount, settlement_net_amount) "
                        "VALUES (:source_id, :external_reference, :payment_method, "
                        ":transaction_type, :transaction_amount, :transaction_currency, "
                        ":transaction_date, :fee_amount, :settlement_net_amount) "
                        "ON CONFLICT (source_id, transaction_type, transaction_amount, transaction_date) "
                        "DO NOTHING"
                    ),
                    {
                        "source_id": row.get("source_id"),
                        "external_reference": row.get("external_reference"),
                        "payment_method": row.get("payment_method"),
                        "transaction_type": row["transaction_type"],
                        "transaction_amount": float(row["transaction_amount"]),
                        "transaction_currency": row.get("transaction_currency", "BRL"),
                        "transaction_date": row["transaction_date"],
                        "fee_amount": float(row.get("fee_amount", 0)),
                        "settlement_net_amount": float(row["settlement_net_amount"]),
                    },
                )
                if result.rowcount > 0:
                    inserted += 1
            except Exception as e:
                logger.warning(f"Erro ao inserir transação: {e}")

    logger.info(f"Batch insert: {inserted}/{len(df)} transações inseridas.")
    return inserted
