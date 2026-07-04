"""
🐺 Wolf Wallet — Mock Data (Modo Visitante)

Dados fictícios para demonstração. Gera 6 meses de transações variadas,
membros fictícios e contas de exemplo.

Usage:
    from mock.mock_data import get_mock_dashboard_data, get_mock_transactions
"""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta
from decimal import Decimal

import pandas as pd

from config.settings import Finance


# Seed para reprodutibilidade
random.seed(42)


def _generate_months(count: int = 6) -> list[date]:
    """Gera lista dos últimos N meses (primeiro dia)."""
    today = date.today()
    months = []
    for i in range(count - 1, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        months.append(date(y, m, 1))
    return months


def get_mock_transactions() -> list[dict]:
    """
    Gera ~6 meses de transações fictícias variadas.

    Returns:
        Lista de dicts simulando a tabela transactions.
    """
    transactions = []
    months = _generate_months(6)
    tx_id = 1000

    for month_start in months:
        # Determina último dia do mês
        if month_start.month == 12:
            month_end = date(month_start.year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(month_start.year, month_start.month + 1, 1) - timedelta(days=1)

        # --- Pix recebidos (8-12 por mês) ---
        num_pix = random.randint(8, 12)
        for _ in range(num_pix):
            day = random.randint(1, min(28, month_end.day))
            amount = random.choice([10.00, 10.00, 10.00, 20.00, 15.00, 10.00])
            tx_date = datetime(month_start.year, month_start.month, day, random.randint(8, 22), random.randint(0, 59))
            tx_id += 1
            transactions.append({
                "id": tx_id,
                "source_id": str(random.randint(70000000, 79999999)),
                "external_reference": f"PIX-{tx_id}",
                "payment_method": "pix",
                "transaction_type": "SETTLEMENT",
                "transaction_amount": amount,
                "transaction_currency": "BRL",
                "transaction_date": tx_date,
                "fee_amount": 0.00,
                "settlement_net_amount": amount,
            })

        # --- Rendimentos CDI (diários, ~R$ 0.30-1.50) ---
        for day in range(1, min(29, month_end.day + 1)):
            if random.random() < 0.7:  # 70% dos dias
                yield_amount = round(random.uniform(0.30, 1.50), 2)
                tax_amount = round(yield_amount * random.uniform(0.15, 0.225), 2)
                tx_date = datetime(month_start.year, month_start.month, day, 8, 0)
                tx_id += 1

                # Rendimento (positivo)
                transactions.append({
                    "id": tx_id,
                    "source_id": "",
                    "external_reference": "",
                    "payment_method": "",
                    "transaction_type": "SETTLEMENT",
                    "transaction_amount": yield_amount,
                    "transaction_currency": "BRL",
                    "transaction_date": tx_date,
                    "fee_amount": 0.00,
                    "settlement_net_amount": yield_amount,
                })
                tx_id += 1

                # Imposto (negativo)
                transactions.append({
                    "id": tx_id,
                    "source_id": "",
                    "external_reference": "",
                    "payment_method": "",
                    "transaction_type": "SETTLEMENT",
                    "transaction_amount": -tax_amount,
                    "transaction_currency": "BRL",
                    "transaction_date": tx_date,
                    "fee_amount": 0.00,
                    "settlement_net_amount": -tax_amount,
                })

        # --- Saques esporádicos (0-1 por mês, valores menores) ---
        num_payouts = random.randint(0, 1)
        for _ in range(num_payouts):
            day = random.randint(5, min(25, month_end.day))
            amount = random.choice([30.00, 50.00, 80.00])
            tx_date = datetime(month_start.year, month_start.month, day, 14, 30)
            tx_id += 1
            transactions.append({
                "id": tx_id,
                "source_id": str(random.randint(80000000, 89999999)),
                "external_reference": f"PAYOUT-{tx_id}",
                "payment_method": "account_money",
                "transaction_type": "PAYOUTS",
                "transaction_amount": -amount,
                "transaction_currency": "BRL",
                "transaction_date": tx_date,
                "fee_amount": 0.00,
                "settlement_net_amount": -amount,
            })

        # --- Devolução rara (10% de chance por mês) ---
        if random.random() < 0.1:
            day = random.randint(1, min(28, month_end.day))
            amount = random.choice([10.00, 20.00])
            tx_date = datetime(month_start.year, month_start.month, day, 10, 0)
            tx_id += 1
            transactions.append({
                "id": tx_id,
                "source_id": str(random.randint(90000000, 99999999)),
                "external_reference": f"REFUND-{tx_id}",
                "payment_method": "pix",
                "transaction_type": "REFUND",
                "transaction_amount": -amount,
                "transaction_currency": "BRL",
                "transaction_date": tx_date,
                "fee_amount": 0.00,
                "settlement_net_amount": -amount,
            })

    # Ordena por data
    transactions.sort(key=lambda t: t["transaction_date"], reverse=True)
    return transactions


def get_mock_dashboard_data() -> dict:
    """
    Retorna dados pré-calculados para o dashboard no modo visitante.

    Returns:
        Dict com: balance, inflows, outflows, yields, transactions, chart_data, upcoming_bills.
    """
    transactions = get_mock_transactions()
    today = date.today()

    # Calcula saldo total
    balance = sum(t["settlement_net_amount"] for t in transactions)

    # Entradas e saídas do mês atual
    current_month_txns = [
        t for t in transactions
        if t["transaction_date"].month == today.month
        and t["transaction_date"].year == today.year
    ]

    inflows = sum(
        t["transaction_amount"] for t in current_month_txns
        if t["transaction_amount"] > 0
    )
    outflows = sum(
        t["transaction_amount"] for t in current_month_txns
        if t["transaction_amount"] < 0
    )

    # Rendimentos do mês
    threshold = float(Finance.YIELD_THRESHOLD)
    yields = sum(
        t["settlement_net_amount"] for t in current_month_txns
        if t["transaction_type"] == "SETTLEMENT"
        and (t["payment_method"] == "" or t["payment_method"] is None)
        and abs(t["transaction_amount"]) < threshold
    )

    # Dados do gráfico (por mês)
    chart_data = _build_mock_chart_data(transactions)

    # Contas fictícias
    upcoming_bills = get_mock_bills()

    return {
        "balance": round(balance, 2),
        "inflows": round(inflows, 2),
        "outflows": round(outflows, 2),
        "yields": round(yields, 2),
        "transactions": transactions[:10],
        "chart_data": chart_data,
        "upcoming_bills": upcoming_bills,
    }


def _build_mock_chart_data(transactions: list[dict]) -> pd.DataFrame:
    """Agrupa transações por mês para o gráfico de barras (com caixa de abertura)."""
    monthly: dict[str, dict] = {}

    for t in transactions:
        month_key = t["transaction_date"].strftime("%Y-%m")
        if month_key not in monthly:
            monthly[month_key] = {"month": month_key, "inflows": 0.0, "outflows": 0.0, "net": 0.0}

        amount = t["transaction_amount"]
        net = t.get("settlement_net_amount", amount)
        if amount > 0:
            monthly[month_key]["inflows"] += amount
        else:
            monthly[month_key]["outflows"] += abs(amount)
        monthly[month_key]["net"] += net

    rows = sorted(monthly.values(), key=lambda x: x["month"])

    # Caixa na virada do mês = soma líquida acumulada dos meses anteriores
    running = 0.0
    for r in rows:
        r["opening_balance"] = running
        running += r.pop("net")

    if not rows:
        return pd.DataFrame(columns=["month", "inflows", "outflows", "opening_balance"])
    return pd.DataFrame(rows)


def get_mock_bills() -> list[dict]:
    """Retorna contas fictícias para demonstração."""
    today = date.today()
    return [
        {
            "id": 1,
            "name": "Servidor Cloud",
            "description": "Hospedagem do site",
            "amount": 49.90,
            "due_day": max(1, today.day + 2),  # vence em 2 dias
            "recurrence": "monthly",
        },
        {
            "id": 2,
            "name": "Domínio .com.br",
            "description": "Registro anual",
            "amount": 40.00,
            "due_day": max(1, today.day + 5),  # vence em 5 dias
            "recurrence": "monthly",
        },
        {
            "id": 3,
            "name": "API Premium",
            "description": "Serviço de integração",
            "amount": 29.90,
            "due_day": max(1, min(28, today.day + 12)),  # vence em 12 dias (fora do alerta)
            "recurrence": "monthly",
        },
    ]


def get_mock_members() -> list[dict]:
    """Retorna membros fictícios para demonstração."""
    statuses = ["paid", "paid", "paid", "paid", "paid",
                "paid", "paid", "paid", "pending", "pending",
                "late", "late", "paid", "paid"]

    names = [
        "Ana Beatriz", "Bruno Henrique", "Camila Rocha",
        "Diego Martins", "Elena Souza", "Fernando Lima",
        "Gabriela Costa", "Hugo Pereira", "Isabela Nunes",
        "João Pedro", "Karen Oliveira", "Lucas Almeida",
        "Mariana Santos", "Nicolas Ribeiro",
    ]

    members = []
    for i, name in enumerate(names):
        status = statuses[i]
        members.append({
            "id": i + 1,
            "name": name,
            "email": f"{name.lower().replace(' ', '.')}@demo.com",
            "expected_amount": 10.00,
            "status": status,
            "confirmed_by": "Admin Demo" if status == "paid" else None,
            "confirmed_at": datetime.now().strftime("%d/%m") if status == "paid" else None,
        })

    return members
