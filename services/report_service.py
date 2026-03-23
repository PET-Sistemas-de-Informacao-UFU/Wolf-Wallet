"""
🐺 Wolf Wallet — Report Service

Lógica de negócio para cálculos financeiros, classificação de transações,
formatação de valores e construção do feed de atividades.

Usage:
    from services.report_service import format_currency, classify_transaction, build_activity_feed
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from config.settings import Colors, Finance, UI


def format_currency(value: Decimal | float | int, show_sign: bool = False) -> str:
    """
    Formata um valor numérico como moeda brasileira.

    Args:
        value: Valor a formatar.
        show_sign: Se True, exibe '+' para positivos.

    Returns:
        String formatada (ex: "R$ 1.234,56" ou "+ R$ 10,00").

    Examples:
        >>> format_currency(1234.56)
        'R$ 1.234,56'
        >>> format_currency(-500)
        '- R$ 500,00'
        >>> format_currency(10, show_sign=True)
        '+ R$ 10,00'
    """
    val = float(value)
    abs_val = abs(val)

    # Formata com separadores brasileiros
    formatted = f"{abs_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    if val < 0:
        return f"- R$ {formatted}"
    elif show_sign and val > 0:
        return f"+ R$ {formatted}"
    else:
        return f"R$ {formatted}"


def classify_transaction(transaction: dict) -> dict:
    """
    Classifica uma transação com ícone, descrição e cor.

    Args:
        transaction: Dict com dados da transação (transaction_type,
                     payment_method, transaction_amount).

    Returns:
        Dict com: icon, description, color, category.
    """
    t_type = transaction.get("transaction_type", "")
    method = transaction.get("payment_method", "") or ""
    amount = float(transaction.get("transaction_amount", 0))
    threshold = float(Finance.YIELD_THRESHOLD)

    # Rendimento CDI (SETTLEMENT, sem método, valor pequeno positivo)
    if t_type == "SETTLEMENT" and method == "" and 0 < amount < threshold:
        return {
            "icon": "📈",
            "description": "Rendimento CDI",
            "color": Colors.YIELD,
            "category": "yield",
        }

    # Imposto sobre rendimento (SETTLEMENT, sem método, valor pequeno negativo)
    if t_type == "SETTLEMENT" and method == "" and -threshold < amount < 0:
        return {
            "icon": "🏛️",
            "description": "Imposto sobre rendimento",
            "color": Colors.NEGATIVE,
            "category": "tax",
        }

    # Pix recebido (SETTLEMENT, pix, positivo)
    if t_type == "SETTLEMENT" and method == "pix" and amount > 0:
        return {
            "icon": "📥",
            "description": "Pix recebido",
            "color": Colors.POSITIVE,
            "category": "pix_in",
        }

    # Transferência interna (SETTLEMENT, available_money, negativo)
    if t_type == "SETTLEMENT" and method == "available_money" and amount < 0:
        return {
            "icon": "🔄",
            "description": "Transferência interna",
            "color": Colors.ALERT,
            "category": "transfer",
        }

    _METHOD_DISPLAY: dict[str, str] = {
        "pix": "PIX",
        "account_money": "saldo em conta",
        "available_money": "disponível",
    }

    # Liquidação genérica positiva
    if t_type == "SETTLEMENT" and amount > 0:
        return {
            "icon": "📥",
            "description": f"Recebimento ({_METHOD_DISPLAY.get(method, method or 'outros')})",
            "color": Colors.POSITIVE,
            "category": "settlement_in",
        }

    # Liquidação genérica negativa
    if t_type == "SETTLEMENT" and amount < 0:
        return {
            "icon": "📤",
            "description": f"Pagamento ({_METHOD_DISPLAY.get(method, method or 'outros')})",
            "color": Colors.NEGATIVE,
            "category": "settlement_out",
        }

    # Devolução
    if t_type == "REFUND":
        return {
            "icon": "↩️",
            "description": "Devolução",
            "color": Colors.ALERT,
            "category": "refund",
        }

    # Saque
    if t_type == "PAYOUTS":
        return {
            "icon": "🏦",
            "description": "Saque para conta bancária",
            "color": Colors.NEGATIVE,
            "category": "payout",
        }

    # Fallback
    return {
        "icon": "💳",
        "description": t_type or "Transação",
        "color": Colors.NEUTRAL,
        "category": "other",
    }


def build_activity_feed(transactions: list[dict]) -> list[dict]:
    """
    Constrói o feed de atividades recentes a partir de uma lista de transações.

    Args:
        transactions: Lista de dicts com dados das transações.

    Returns:
        Lista de dicts com: icon, date_str, description, amount_str, color.
    """
    feed: list[dict] = []

    for t in transactions:
        classification = classify_transaction(t)
        amount = float(t.get("transaction_amount", 0))
        t_date = t.get("transaction_date")

        # Formata a data
        if isinstance(t_date, datetime):
            date_str = t_date.strftime("%d/%m")
            sort_key = t_date.strftime("%Y-%m-%d")
        elif isinstance(t_date, str):
            try:
                dt = datetime.fromisoformat(t_date)
                date_str = dt.strftime("%d/%m")
                sort_key = dt.strftime("%Y-%m-%d")
            except ValueError:
                date_str = t_date[:10]
                sort_key = t_date[:10]
        else:
            date_str = "—"
            sort_key = "0000-00-00"

        feed.append({
            "icon": classification["icon"],
            "date_str": date_str,
            "description": classification["description"],
            "amount_str": format_currency(amount, show_sign=True),
            "color": classification["color"],
            "category": classification["category"],
            "sort_key": sort_key,
        })

    return feed


def build_bill_alerts(upcoming_bills: list[dict]) -> list[dict]:
    """
    Constrói alertas de contas próximas do vencimento.

    Args:
        upcoming_bills: Lista de contas com vencimento próximo.

    Returns:
        Lista de dicts com: icon, description, amount_str, due_day, days_until.
    """
    today = date.today()
    alerts: list[dict] = []

    for bill in upcoming_bills:
        due_day = bill.get("due_day", 0)

        # Calcula dias até o vencimento
        try:
            due_date = today.replace(day=due_day)
            if due_date < today:
                # Já passou neste mês, próximo mês
                if today.month == 12:
                    due_date = due_date.replace(year=today.year + 1, month=1)
                else:
                    due_date = due_date.replace(month=today.month + 1)
            days_until = (due_date - today).days
        except ValueError:
            days_until = 0

        amount = float(bill.get("amount", 0))

        if days_until == 0:
            time_str = "vence hoje"
        elif days_until == 1:
            time_str = "vence amanhã"
        else:
            time_str = f"vence em {days_until} dias"

        alerts.append({
            "icon": "⚠️",
            "description": f"{bill['name']} — {time_str}",
            "amount_str": format_currency(amount),
            "due_day": due_day,
            "days_until": days_until,
        })

    return sorted(alerts, key=lambda x: x["days_until"])
