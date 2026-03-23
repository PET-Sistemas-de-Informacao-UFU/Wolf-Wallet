"""
🐺 Wolf Wallet — Transaction Table Component

Tabela estilizada de transações com ícones, cores e valores formatados.
Utiliza classify_transaction do report_service para classificação visual.

Usage:
    from components.transaction_table import render_transaction_table
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from components.hide_balance import mask_value
from services.report_service import classify_transaction, format_currency

# Mapas de tradução para exibição na tabela
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


def render_transaction_table(transactions: list[dict]) -> None:
    """
    Renderiza uma tabela de transações estilizada.

    Args:
        transactions: Lista de dicts com dados da transação.
    """
    if not transactions:
        st.info("Nenhuma transação encontrada para os filtros selecionados.")
        return

    # Header
    cols = st.columns([0.5, 2.5, 1.5, 1.5, 1.5, 1.5])
    headers = [" ", "Descrição", "Tipo", "Valor Bruto", "Taxa", "Valor Líquido"]
    for col, header in zip(cols, headers):
        with col:
            if header.strip():
                st.markdown(f"**{header}**")

    st.divider()

    # Rows
    for txn in transactions:
        classification = classify_transaction(txn)
        _render_transaction_row(txn, classification)


def _render_transaction_row(txn: dict, classification: dict) -> None:
    """Renderiza uma linha da tabela de transação."""
    icon = classification["icon"]
    description = classification["description"]
    color = classification["color"]

    amount = float(txn.get("transaction_amount", 0))
    fee = float(txn.get("fee_amount", 0))
    net = float(txn.get("settlement_net_amount", 0))
    txn_type = txn.get("transaction_type", "")
    txn_date = txn.get("transaction_date")
    source_id = txn.get("source_id", "")
    payment_desc = txn.get("payment_description", "") or ""

    # Formata data
    date_str = _format_date(txn_date)

    # Formata valores
    amount_str = mask_value(format_currency(amount, show_sign=True))
    fee_str = mask_value(format_currency(fee)) if fee != 0 else "—"
    net_str = mask_value(format_currency(net, show_sign=True))

    # Cor do valor
    amount_color = color

    cols = st.columns([0.5, 2.5, 1.5, 1.5, 1.5, 1.5])

    with cols[0]:
        st.markdown(f"### {icon}")

    with cols[1]:
        label = f"**{description}**"
        if payment_desc:
            label += f"  \n*{payment_desc}*"
        st.markdown(label)
        st.caption(f"{date_str} • {source_id}" if source_id else date_str)

    with cols[2]:
        type_label = _TYPE_LABELS.get(txn_type, txn_type)
        st.markdown(f"`{type_label}`")

    with cols[3]:
        st.markdown(
            f"<span style='color: {amount_color}'>{amount_str}</span>",
            unsafe_allow_html=True,
        )

    with cols[4]:
        st.markdown(f"{fee_str}")

    with cols[5]:
        st.markdown(
            f"<span style='color: {amount_color}; font-weight: bold'>{net_str}</span>",
            unsafe_allow_html=True,
        )


def _format_date(dt: datetime | str | None) -> str:
    """Formata datetime para exibição."""
    if dt is None:
        return "—"
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except ValueError:
            return dt
    return dt.strftime("%d/%m/%Y %H:%M")


def render_summary_cards(transactions: list[dict], total_count: int) -> None:
    """
    Renderiza cards de resumo para as transações filtradas.

    Args:
        transactions: Transações da página atual.
        total_count: Total de transações (todas as páginas).
    """
    if not transactions:
        return

    # Calcula resumos sobre as transações da página
    total_in = sum(
        float(t.get("settlement_net_amount", 0))
        for t in transactions
        if float(t.get("transaction_amount", 0)) > 0
    )
    total_out = sum(
        float(t.get("settlement_net_amount", 0))
        for t in transactions
        if float(t.get("transaction_amount", 0)) < 0
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("📊 Total de Registros", total_count)

    with col2:
        st.metric("📥 Entradas (página)", mask_value(format_currency(total_in)))

    with col3:
        st.metric("📤 Saídas (página)", mask_value(format_currency(total_out)))

    with col4:
        net = total_in + total_out
        st.metric("💰 Líquido (página)", mask_value(format_currency(net, show_sign=True)))
