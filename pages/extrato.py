"""
🐺 Wolf Wallet — Extrato (Histórico de Transações)

Página de extrato completo com:
    - Cards de resumo
    - Filtros (data, tipo, direção, busca)
    - Tabela de transações estilizada
    - Paginação
    - Exportação CSV

Usage:
    from pages.extrato import render_extrato
"""

from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
import streamlit as st

from auth.session import is_visitor, require_auth
from components.filters import render_pagination, render_transaction_filters
from components.sync_status import render_sync_banner
from components.transaction_table import render_summary_cards, render_transaction_table
from config.settings import Messages, UI, to_brasilia
from services.report_service import classify_transaction, format_currency


def render_extrato() -> None:
    """Renderiza a página de extrato."""
    if not require_auth():
        return

    render_sync_banner()

    st.title("📋 Extrato de Transações")
    st.caption("Histórico completo de movimentações da conta Mercado Pago.")

    if is_visitor():
        _render_visitor_extrato()
    else:
        _render_real_extrato()


def _render_real_extrato() -> None:
    """Extrato com dados reais do banco."""
    from models.transaction import get_transactions

    # Filtros
    filters = render_transaction_filters(key_prefix="extrato")

    # Busca transações
    per_page = UI.ITEMS_PER_PAGE
    page = st.session_state.get("extrato_page", 1)

    transactions, total = get_transactions(
        start_date=filters["start_date"],
        end_date=filters["end_date"],
        transaction_type=filters["transaction_type"],
        payment_method=filters.get("payment_method"),
        direction=filters["direction"],
        search=filters["search"],
        page=page,
        per_page=per_page,
    )

    if total == 0:
        st.info(Messages.NO_DATA)
        return

    # Cards de resumo
    render_summary_cards(transactions, total)

    st.divider()

    # Tabela
    render_transaction_table(transactions)

    st.divider()

    # Paginação
    current_page = render_pagination(total, per_page, key_prefix="extrato")

    # Se a página mudou, busca novamente
    if current_page != page:
        st.session_state["extrato_page"] = current_page

    # Exportação CSV
    st.divider()
    _render_csv_export(filters)


def _render_visitor_extrato() -> None:
    """Extrato com dados mock para visitantes."""
    from auth.session import render_visitor_banner
    from mock.mock_data import get_mock_transactions

    render_visitor_banner()

    transactions = get_mock_transactions()

    if not transactions:
        st.info(Messages.NO_DATA)
        return

    # Filtros (sem efeito real no mock, mas mostra a UI)
    filters = render_transaction_filters(key_prefix="extrato_visitor")

    # Aplica filtros simples no mock
    filtered = _filter_mock_transactions(transactions, filters)

    # Cards de resumo
    render_summary_cards(filtered, len(filtered))

    st.divider()

    # Tabela
    render_transaction_table(filtered)


def _filter_mock_transactions(transactions: list[dict], filters: dict) -> list[dict]:
    """Aplica filtros básicos nas transações mock."""
    result = transactions

    if filters.get("direction") == "inflows":
        result = [t for t in result if float(t.get("transaction_amount", 0)) > 0]
    elif filters.get("direction") == "outflows":
        result = [t for t in result if float(t.get("transaction_amount", 0)) < 0]

    if filters.get("transaction_type"):
        result = [
            t for t in result
            if t.get("transaction_type") == filters["transaction_type"]
        ]

    if filters.get("search"):
        search_lower = filters["search"].lower()
        result = [
            t for t in result
            if search_lower in str(t.get("source_id", "")).lower()
            or search_lower in str(t.get("external_reference", "")).lower()
        ]

    return result


def _render_csv_export(filters: dict) -> None:
    """Botão direto para exportar transações filtradas como CSV."""
    st.markdown("##### 📥 Exportar Dados")

    try:
        from models.transaction import get_transactions

        # Busca TODAS as transações (sem paginação)
        all_txns, total = get_transactions(
            start_date=filters["start_date"],
            end_date=filters["end_date"],
            transaction_type=filters["transaction_type"],
            payment_method=filters.get("payment_method"),
            direction=filters["direction"],
            search=filters["search"],
            page=1,
            per_page=999999,
        )

        if not all_txns:
            st.caption("Nenhuma transação para exportar.")
            return

        df = _transactions_to_dataframe(all_txns)
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, sep=";", encoding="utf-8")

        st.download_button(
            label=f"📄 Baixar {total} transações (CSV)",
            data=csv_buffer.getvalue(),
            file_name=f"wolf-wallet-extrato-{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            key="download_csv",
        )

    except Exception as e:
        st.error(f"Erro ao exportar: {e}")


_TYPE_LABELS: dict[str, str] = {
    "SETTLEMENT": "Liquidação",
    "REFUND": "Devolução",
    "PAYOUTS": "Saque",
}

_METHOD_LABELS: dict[str, str] = {
    "pix": "PIX",
    "account_money": "Saldo em conta",
    "available_money": "Dinheiro disponível",
    "": "CDI",
}


def _transactions_to_dataframe(transactions: list[dict]) -> pd.DataFrame:
    """Converte lista de transações para DataFrame formatado para exportação."""
    rows = []
    for txn in transactions:
        classification = classify_transaction(txn)
        raw_type = txn.get("transaction_type", "")
        raw_method = txn.get("payment_method", "")
        rows.append({
            "Data": _format_date_export(txn.get("transaction_date")),
            "Descrição": classification["description"],
            "Tipo": _TYPE_LABELS.get(raw_type, raw_type),
            "Método": _METHOD_LABELS.get(raw_method, raw_method),
            "Valor Bruto": float(txn.get("transaction_amount", 0)),
            "Taxa": float(txn.get("fee_amount", 0)),
            "Valor Líquido": float(txn.get("settlement_net_amount", 0)),
            "Moeda": txn.get("transaction_currency", "BRL"),
            "Source ID": txn.get("source_id", ""),
            "Referência": txn.get("external_reference", ""),
        })
    return pd.DataFrame(rows)


def _format_date_export(dt: datetime | str | None) -> str:
    """Formata data para exportação CSV (horário de Brasília)."""
    if dt is None:
        return ""
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except ValueError:
            return dt
    # Converte para horário de Brasília
    dt = to_brasilia(dt)
    return dt.strftime("%d/%m/%Y %H:%M:%S")
